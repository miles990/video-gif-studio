"""Deterministic director query and per-section effect budget lint."""
from collections import Counter
from fractions import Fraction
import json
import math
from pathlib import Path
import numpy as np
from fx.core import catalog
from fx_calibrate import load_table, interpolate
from fx_recipes import load_recipes
from threshold_registry import value


def recipe_cards(experimental=False):
    cat=catalog(experimental)
    result=[]
    for name,r in sorted(load_recipes(experimental=experimental).items()):
        ingredients=[cat['effects' if l['kind']=='effect' else 'transitions'].get(l['ref'],{}) for l in r['layers']]
        if any(i.get('card') in ('missing','incomplete') or 'needs' not in i or i.get('status')!='stable' for i in ingredients):continue
        costs=[i['cost_ms_per_frame@720p'] for i in ingredients]
        result.append(dict(name=name,kind='recipe',status=r['status'],intent=[r['intent']],energy=r['perceived_target'],
            needs=sorted(set(r['needs'])|{n for i in ingredients for n in i['needs']}),good_for=r['good_for'],avoid_for=r['avoid_for'],
            gate=r['gate'],style_tags=[r['intent']],duration_ms=[100,max(l['offset_ms']+l['duration_ms'] for l in r['layers'])],
            pairs_with_sfx=[r['sfx']] if r['sfx'] else [],conflicts=[],
            components=sorted({l['ref'] for l in r['layers']}),**{'cost_ms_per_frame@720p':sum(costs) if all(c is not None for c in costs) else None}))
    return result


def all_cards(experimental=False):
    return [dict(c,name=n,kind=k[:-1],components=[n]) for k,entries in catalog(experimental).items() for n,c in entries.items()]+recipe_cards(experimental)


def query(intent, needs=(), max_cost=math.inf, section='', history=(), experimental=False, diagnostics=None):
    if not math.isfinite(max_cost) and max_cost!=math.inf or max_cost<0:raise ValueError('max-cost must be nonnegative')
    from fx_catalog import INTENTS,NEEDS
    if intent not in INTENTS or set(needs)-set(NEEDS):
        from fx_diagnostics import describe
        raise ValueError(describe('Unknown intent or needs',[intent,*needs]))
    if not isinstance(history,list) and not isinstance(history,tuple):raise ValueError('history must be a list of names or choice objects')
    history=[e if isinstance(e,str) else e['name'] for e in history]
    cards=all_cards(experimental);recent=history[-int(value('query.history.window')):]
    result=[];removed=dict(card=0,status=0,cost_unknown=0,max_cost=0,needs=0,section=0,energy=0,intent=0)
    for card in cards:
        if card.get('card') in ('missing','incomplete'):removed['card']+=1;continue
        if card['status']=='needs-review':removed['status']+=1;continue
        cost=card['cost_ms_per_frame@720p']
        if cost is None:removed['cost_unknown']+=1;continue
        if cost>max_cost:removed['max_cost']+=1;continue
        if not set(card['needs'])<=set(needs):removed['needs']+=1;continue
        if section in card['avoid_for']:removed['section']+=1;continue
        if section=='breathe' and card['energy']>value('director.breathe.max'):removed['energy']+=1;continue
        match=1. if intent in card['intent'] else value('query.related.match') if intent=='hit' and any(x in card['intent'] for x in ('drop','play','transition-energy')) else 0.
        if not match:removed['intent']+=1;continue
        gate=1. if card['gate']['status']=='stable' else 0.
        penalty=history.count(card['name'])*value('query.diversity.weight')
        score=match*value('query.intent.weight')+gate*value('query.gate.weight')-cost*value('query.cost.weight')-penalty
        result.append(dict(card,score=score,reason=dict(intent_match=match,technical_gate_pass=gate,cost_ms=cost,diversity_penalty=penalty),
                           recent_exclusion=card['name'] in recent))
    # When >=N choices exist, the last N-1 choices are withheld from top-1.
    n=int(value('query.history.window'))
    eligible=[c for c in result if c['name'] not in history[-(n-1):]] if len(result)>=n else result
    eligible_names={c['name'] for c in eligible}
    explanation=dict(candidates=len(cards),removed=removed,remaining=len(result),method='Sequential filters; each candidate counted once')
    if diagnostics is not None:diagnostics.update(explanation)
    elif not result:
        import sys
        print('No FX candidates: '+json.dumps(explanation,sort_keys=True),file=sys.stderr)
    return sorted(result,key=lambda c:(c['name'] not in eligible_names,-c['score'],c['name'],c['kind']))


def events_from_plan(plan, beats=None, table=None):
    table=table or load_table();beats=beats or plan.get('beats_ms',[])
    recipes=load_recipes(experimental=True);events=[]
    for e in plan.get('effects',[]):
        if 'recipe' in e:
            r=recipes[e['recipe']];at=beats[e['at_beat']] if 'at_beat' in e else e.get('at_ms',0)
            events.append(dict(name=e['recipe'],at_ms=at,perceived=e.get('perceived',r['perceived_target']),components=[l['ref'] for l in r['layers']]))
            continue
        name=e['name'];start=beats[e['start_beat']] if 'start_beat' in e else e.get('start_ms',0)
        end=beats[e['end_beat']] if 'end_beat' in e else e.get('end_ms',math.inf)
        knob=table.get('effects',{}).get(name,{}).get('control','amount')
        default=0 if knob=='temp' else 1
        strength=e.get(knob,default)
        points=[]
        if isinstance(strength,dict):
            if 'keyframes' in strength:
                keys=strength['keyframes']
                points=[(t,v) for i,(t,v) in enumerate(keys) if v>0 and (i==0 or v>=keys[i-1][1]) and (i==len(keys)-1 or v>keys[i+1][1])]
            else:
                times=plan.get('downbeats_ms',beats[::4]) if strength.get('on')=='downbeats' else beats
                indices=strength.get('indices',strength.get('beats',list(range(0,len(times),strength.get('every',1)))))
                points=[(times[i],strength.get('max',1)) for i in indices]
        else:points=[(start,strength)]
        for at,amount in points:
            if not start<=at<end:continue
            p=e.get('perceived')
            if p is None:p=interpolate(name,float(amount),table)
            events.append(dict(name=name,at_ms=float(at),perceived=float(p),components=[name]))
    # Explicit transition events for conflict/budget consumers.
    for e in plan.get('transitions',[]):
        events.append(dict(name=e['name'],at_ms=e['at_ms'],perceived=e.get('perceived',.5),components=[e['name']]))
    cursor=0
    for index,s in enumerate(plan.get('segments',[])):
        start=s.get('start_ms',cursor)
        tr=s.get('transition')
        if index and tr and tr!='cut':
            tr={'name':tr} if isinstance(tr,str) else tr
            events.append(dict(name=tr['name'],at_ms=start,perceived=tr.get('perceived',.5),components=[tr['name']],segment_index=index))
        if 'end_beat' in s:cursor=round(beats[s['end_beat']]/10)*10
        elif 'end_downbeat' in s:cursor=round(plan['downbeats_ms'][s['end_downbeat']]/10)*10
        elif 'duration_ms' in s:cursor=start+s['duration_ms']
        elif 'out_ms' in s:cursor=start+s['out_ms']-s.get('in_ms',0)
        else:raise ValueError(f'segments[{index}]: duration unresolved; lint CLI resolves manifest timing')
    return sorted(events,key=lambda e:(e['at_ms'],e['name']))


def lint(plan, beats=None, table=None):
    from delivery import quantize
    events=events_from_plan(plan,beats,table);issues=[];usage=[]
    if any(not math.isfinite(e['at_ms']) or e['at_ms']<0 or not math.isfinite(e['perceived']) or e['perceived']<0 for e in events):raise ValueError('Invalid budget event')
    fps=plan.get('fps',30)
    if not math.isfinite(fps) or fps<=0:raise ValueError('fps must be positive')
    cards={c['name']:c for c in all_cards(True)}
    for i,a in enumerate(events):
        for b in events[i+1:]:
            if quantize(a['at_ms'],fps)['frame']!=quantize(b['at_ms'],fps)['frame']:continue
            for x in a['components']:
                for y in b['components']:
                    if y in cards.get(x,{}).get('conflicts',[]) or x in cards.get(y,{}).get('conflicts',[]):
                        issues.append(dict(level='error',rule='conflict',at_ms=a['at_ms'],message=f'{x} conflicts with {y} on the same frame'))
    bar=plan.get('bar_ms',2000)
    if not math.isfinite(bar) or bar<=0:raise ValueError('bar_ms must be positive')
    sections=plan.get('sections',[])
    valid=[]
    for index,s in enumerate(sections):
        start,end=s['start_ms'],s['end_ms']
        if not all(math.isfinite(v) for v in (start,end,s.get('energy',.5))) or start<0 or not 0<=s.get('energy',.5)<=1:raise ValueError('Invalid section')
        if end<=start:
            issues.append(dict(level='warning',rule='invalid-section',section_index=index,message=f'sections[{index}] has zero/reversed duration; events assigned to nearest valid neighbour'))
        else:valid.append((index,s))
    assigned={index:[] for index,_ in valid}
    for e in events:
        containing=[(index,s) for index,s in valid if s['start_ms']<=e['at_ms']<s['end_ms']]
        if valid:
            index,s=(containing or sorted(valid,key=lambda pair:(min(abs(e['at_ms']-pair[1]['start_ms']),abs(e['at_ms']-pair[1]['end_ms'])),-pair[1]['start_ms'])))[0]
            assigned[index].append(e)
    for index,s in valid:
        name=s.get('name',s.get('label','section'));start=s['start_ms'];end=s['end_ms'];energy=s.get('energy',.5)
        local=assigned[index]
        limit=value('director.budget.base')+value('director.budget.gain')*energy
        density=max(1,math.floor(value('director.density.base')+value('director.density.gain')*energy))
        windows=[]
        for at in sorted({e['at_ms'] for e in local}):
            # Neighbour-assigned gap events retain their actual timestamps and
            # must still contribute, even just beyond the neighbour's endpoint.
            window_end=min(max(end,max(e['at_ms'] for e in local)+1000/fps),at+4000)
            used=sum(e['perceived'] for e in local if at<=e['at_ms']<window_end)
            windows.append(dict(start_ms=at,end_ms=window_end,used=used,limit=limit))
            if used>limit:
                issues.append(dict(level='warning' if energy>=value('director.energy.high') else 'error',rule='over-budget',section=name,
                    start_ms=at,end_ms=window_end,used=used,limit=limit,message=f'{name}: perceived {used:.6f} > {limit:.6f}; reduce or spread effects'))
        counts=Counter(int((min(max(e['at_ms'],start),max(start,end-1000/fps))-start)//bar) for e in local)
        for b,count in sorted(counts.items()):
            if count>density:issues.append(dict(level='warning' if energy>=value('director.energy.high') else 'error',rule='event-density',section=name,bar=b,used=count,limit=density,message='Reduce events per bar'))
        flashes=[e for e in local if any(x in ('flash_white','flash_cut','gl_overexposure') for x in e['components'])]
        if len(flashes)>1 and energy<=value('director.energy.low') or len(flashes)>value('director.flash.run.max'):
            issues.append(dict(level='error' if energy<=value('director.energy.low') else 'warning',rule='every-beat-flash',section=name,
                beat_range=[start/(bar/4),end/(bar/4)],message=f'{name}: every-beat flash; use only the section first beat or one downbeat every two bars'))
        usage.append(dict(section=name,section_index=index,events=local,energy=energy,perceived_limit=limit,event_limit_per_bar=density,windows=windows))
    flash_frames=sorted({quantize(e['at_ms'],fps)['frame'] for e in events if 'flash_white' in e['components'] or 'flash_cut' in e['components']})
    rate=Fraction(str(fps))
    for frame in flash_frames:
        count=sum(0<=(t-frame)*rate.denominator<rate.numerator for t in flash_frames)
        if count>value('wcag.flashes.max'):
            at=frame*1000/fps
            issues.append(dict(level='error',rule='WCAG 2.3.1 potential flash',start_ms=at,end_ms=at+1000,flashes=count,
                message='Plan may exceed WCAG 2.3.1; reduce flashes and verify decoded general/red area.'))
            break
    return dict(events=events,sections=usage,issues=issues,errors=sum(i['level']=='error' for i in issues))
