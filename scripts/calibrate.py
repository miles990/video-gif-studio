#!/usr/bin/env python3
"""Propose audited next-round threshold updates, then explicitly activate a round.

Evidence is JSON: measurements {anchor_id: [samples]}, baseline {anchor_id:
{mean, sigma}}, candidate_ids, trigger, plus class-specific fields. All anchors
must be pre-registered held-outs. No candidate measurement enters calibration.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import sys
from threshold_registry import DEFAULT_PATH, entry, finite, load, passes, validate


def decision(e, x, boundary):
    return 'pass' if passes(x,boundary,e['direction']) else 'fail'


def propose(data, ident, evidence, round_id, approved_by, confirm_flips=False):
    data=deepcopy(validate(data));e=entry(ident,data);old=e['value']
    if e['class']=='F': raise ValueError(ident+': F is immutable; no automatic standard updates')
    if e.get('status') in ('frozen','instrument_invalid'): raise ValueError(ident+': instrument requires independent repair')
    if round_id!=data.get('round',0): raise ValueError('Proposal round must equal active round')
    if not approved_by: raise ValueError('An accountable approver is required')
    if e.get('instrument') and evidence.get('instrument')!=e['instrument']:
        raise ValueError('Measurement instrument/version must match the registered method')
    if evidence.get('trigger','manual') not in ('standard_update','new_best','anchor_set_grew','control_failed','user_choice','manual'):
        raise ValueError('Unknown calibration trigger')
    if any(p['id']==ident for p in data.get('pending',[])): raise ValueError('Already pending for next round')
    context=None
    if isinstance(old,dict) and e['class']=='U':
        context=evidence.get('context')
        if context not in old: raise ValueError('U context must name a registered content/platform scope')
        old=old[context]
    if not isinstance(old,(int,float)): raise ValueError('Calibrate a scalar or U context; no implicit aggregate updates')
    anchors=e['anchors'];measurements=evidence.get('measurements',{});baseline=evidence.get('baseline',{})
    ids={a['id'] for a in anchors}
    if set(measurements)!=ids or set(baseline)!=ids:
        raise ValueError('Re-measure every registered anchor, with its baseline; no extra candidate data')
    candidates=set(evidence.get('candidate_ids',[]))
    if any(not a.get('held_out') or a['id'] in candidates or a['path'] in candidates for a in anchors):
        raise ValueError('Only held-out anchors; the candidate is forbidden')
    if not {'best','benchmark','known_worse'}<={a['role'] for a in anchors}:
        raise ValueError('P3 requires best, benchmark and known_worse anchors')
    means={};drift=[]
    for a in anchors:
        samples=measurements[a['id']];base=baseline[a['id']]
        if not isinstance(samples,list) or not finite(samples) or not finite(base.get('mean')) or not finite(base.get('sigma')) or base['sigma']<0:
            raise ValueError('Finite nonempty samples and nonnegative baseline sigma required')
        mean=statistics.mean(samples);means[a['id']]=mean
        if abs(mean-base['mean'])>2*base['sigma']+1e-12 or decision(e,mean,old)!=decision(e,base['mean'],old):
            drift.append(a['id'])
    now=datetime.now(timezone.utc).isoformat()
    record=dict(date=now,id=ident,**{'from':old,'to':old},trigger=evidence.get('trigger','manual'),
        approved_by=approved_by,round=round_id,effective_round=round_id+1,anchor_decisions=[],flips=[],
        evidence=deepcopy(evidence))
    if context is not None: record['context']=context
    def reject(status,reason):
        e['status']=status;record.update(status=status,reason=reason)
        e['history'].append(deepcopy(record));data.setdefault('audit',[]).append(record)
        return data,record
    record['drift_anchors']=drift
    controls=[a for a in anchors if a['role'] in ('positive_control','negative_control')]
    if not {'positive_control','negative_control'}<={a['role'] for a in controls}:
        raise ValueError('Positive and negative controls required before calibration')
    if any(decision(e,means[a['id']],old)!=a['expected'] for a in controls):
        return reject('instrument_invalid','Current controls fail; do not relax the boundary to fit them')
    if drift: return reject('frozen','Anchor drift >2 sigma or decision flip: '+', '.join(drift))
    cls=e['class'];new=old;mode='gate'
    if cls=='R':
        if evidence.get('trigger')!='new_best' or e['direction'] not in ('min','max'):
            raise ValueError('R needs new_best and a one-sided boundary')
        best=next(a for a in anchors if a['role']=='best')
        samples=measurements[best['id']]
        previous=evidence.get('previous_best',{})
        if len(samples)<3 or not finite(previous.get('mean')) or not finite(previous.get('sigma')) or previous['sigma']<0:
            raise ValueError('R needs at least three stable trials and previous best mean/sigma')
        sign=1 if e['direction']=='max' else -1
        if any(sign*(previous['mean']-x)<=2*previous['sigma'] for x in samples[-3:]):
            raise ValueError('R improvement must exceed 2 sigma for three consecutive trials')
        # The memory instrument registers its 1.3 multiplier as margin; fps uses 0.85.
        target=statistics.mean(samples[-3:])*e.get('margin',1)
        step=min(e.get('max_step',.1),.1)*abs(old)
        new=max(target,old-step) if sign==1 else min(target,old+step)
        if sign*(old-new)<=0: raise ValueError('R may only tighten, never relax')
    elif cls=='C':
        if not evidence.get('audited_by') or evidence['audited_by']==approved_by:
            raise ValueError('C requires an independent auditor')
        previous_count=evidence.get('previous_count')
        count=sum(len(s) for s in measurements.values())
        if evidence.get('trigger')!='control_failed' and (type(previous_count) is not int or previous_count<1 or count<math.ceil(previous_count*1.1)):
            raise ValueError('C anchor set must grow by at least 10%')
        good=[x for a in anchors if a['expected']=='pass' for x in measurements[a['id']]]
        bad=[x for a in anchors if a['expected']=='fail' for x in measurements[a['id']]]
        if len(good)<2 or len(bad)<2 or e['direction'] not in ('min','max'):
            raise ValueError('C needs good/bad distributions and a one-sided boundary')
        sigma=math.sqrt(((len(good)-1)*statistics.variance(good)+(len(bad)-1)*statistics.variance(bad))/(len(good)+len(bad)-2))
        margin=max(e.get('margin',0),.25*sigma)
        lo,hi=(max(good),min(bad)) if e['direction']=='max' else (max(bad),min(good))
        if hi-lo<=2*margin: return reject('instrument_invalid','Good/bad distributions cannot separate with margin')
        new=(lo+hi)/2
        if 'max_step' in e and abs(new-old)>abs(old)*e['max_step']+1e-12:
            raise ValueError('C boundary exceeds registered step cap; retain current threshold')
    elif cls=='U':
        if evidence.get('trigger')!='user_choice' or not finite(evidence.get('requested')):
            raise ValueError('U requires user_choice and a finite requested scalar')
        choices=evidence.get('choices',[])
        if not choices or not all(isinstance(c,dict) and c.get('source')=='user' and c.get('id') for c in choices):
            raise ValueError('U requires attributable user choices')
        if len({c['id'] for c in choices})!=len(choices): raise ValueError('Repeated choices cannot increase sample count')
        mode='default_only' if len(choices)<5 else 'gate'
        step=min(e.get('max_step',.15),.15)*abs(old)
        new=max(old-step,min(old+step,evidence['requested']))
    if 'bounds' in e: new=max(e['bounds'][0],min(e['bounds'][1],new))
    if cls=='C' and not lo+margin<=new<=hi-margin:
        return reject('instrument_invalid','Hard bounds leave no separation margin')
    if cls=='R' and ((e['direction']=='max' and new>=old) or (e['direction']=='min' and new<=old)):
        raise ValueError('R hard bounds prohibit tightening')
    decisions=[dict(anchor=a['id'],before=decision(e,means[a['id']],old),after=decision(e,means[a['id']],new)) for a in anchors]
    flips=[d for d in decisions if d['before']!=d['after']]
    record.update(to=new,anchor_decisions=decisions,flips=flips,mode=mode)
    if any(decision(e,means[a['id']],new)!=a['expected'] for a in controls):
        return reject('instrument_invalid','Proposed controls fail')
    best=next(a for a in anchors if a['role']=='best');benchmark=next(a for a in anchors if a['role']=='benchmark');worse=next(a for a in anchors if a['role']=='known_worse')
    sign=1 if e['direction']=='max' else -1
    if not sign*means[best['id']]<sign*means[benchmark['id']]<sign*means[worse['id']]:
        return reject('instrument_invalid','P3 anchors do not separate best / benchmark / worse')
    if math.isclose(means[benchmark['id']],new,abs_tol=1e-9):
        return reject('instrument_invalid','Benchmark touches decision ceiling')
    if flips and not confirm_flips:
        record['status']='confirmation_required'
    else:
        record['status']='pending'
        data.setdefault('pending',[]).append(dict(id=ident,value=new,effective_round=round_id+1,
            proposed_round=round_id,mode=mode,context=context,audit_index=len(data.get('audit',[]))))
    e['history'].append(deepcopy(record));data.setdefault('audit',[]).append(record)
    return data,record


def activate(data, round_id):
    data=deepcopy(validate(data))
    if type(round_id) is not int or round_id<=data.get('round',0):
        raise ValueError('Changes take effect only in a later round, before candidate work starts')
    remaining=[]
    for pending in data.get('pending',[]):
        if pending['effective_round']>round_id: remaining.append(pending);continue
        e=entry(pending['id'],data)
        if e['class']=='F' or e.get('status') in ('frozen','instrument_invalid'):
            raise ValueError('Cannot activate a fixed or invalid instrument')
        context=pending.get('context')
        if pending['mode']=='default_only':
            defaults=data.setdefault('defaults',{})
            if context is None: defaults[e['id']]=pending['value']
            else: defaults.setdefault(e['id'],{})[context]=pending['value']
        else:
            if context is None:e['value']=pending['value']
            else:e['value'][context]=pending['value']
            e['status']='active'
        data['audit'][pending['audit_index']]['activated_round']=round_id
    data['pending']=remaining;data['round']=round_id
    return validate(data)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registry',type=Path,default=DEFAULT_PATH)
    p.add_argument('--out',type=Path,required=True,help='New audited registry; explicit promotion is a separate operation')
    sub=p.add_subparsers(dest='command',required=True)
    proposal=sub.add_parser('propose');proposal.add_argument('id');proposal.add_argument('--evidence',type=Path,required=True)
    proposal.add_argument('--round',type=int,required=True);proposal.add_argument('--approved-by',required=True)
    proposal.add_argument('--confirm-flips',action='store_true')
    active=sub.add_parser('activate');active.add_argument('--round',type=int,required=True)
    args=p.parse_args(argv)
    try:
        data=load(args.registry)
        if args.command=='propose':
            data,record=propose(data,args.id,json.loads(args.evidence.read_text(encoding='utf-8')),args.round,args.approved_by,args.confirm_flips)
        else: data=activate(data,args.round);record={'status':'activated','round':args.round}
        args.out.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        print(json.dumps(record,indent=2));return 0 if record['status'] in ('pending','activated') else 2
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('calibrate: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
