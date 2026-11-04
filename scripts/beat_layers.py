#!/usr/bin/env python3
"""Deterministic downbeat cuts, beat accents and section-local experimental styles."""
import argparse
import copy
import json
import math
from pathlib import Path
import sys

DENSITIES={'low':4,'mid':2,'high':1}


def layers(beatmap, duration_ms=None, cut_density='mid'):
    if cut_density not in DENSITIES: raise ValueError('cut_density: choose low|mid|high')
    beats=beatmap.get('beats_ms',[])
    if not beats or any(not isinstance(t,(int,float)) or not math.isfinite(t) or t<0 for t in beats) or any(b<=a for a,b in zip(beats,beats[1:])):
        raise ValueError('beats_ms must be nonempty, finite and increasing')
    end=duration_ms or beatmap.get('duration_ms') or beats[-1]+(beats[-1]-beats[-2] if len(beats)>1 else 500)
    down=beatmap.get('downbeats_ms') or beats[::4]; inferred=not bool(beatmap.get('downbeats_ms'))
    if any(min(abs(t-b) for b in beats)>1 for t in down) or any(b<=a for a,b in zip(down,down[1:])):
        raise ValueError('downbeats must be ordered and on beats')
    sections=beatmap.get('sections') or [dict(start_ms=0,end_ms=end,label='unsectioned')]
    boundaries=[]
    for section in sections:
        t=section['start_ms']
        nearest=min(down,key=lambda b:abs(b-t))
        if abs(nearest-t)>10: raise ValueError('Section boundaries must be on downbeats (10 ms tolerance)')
        if 0<nearest<end: boundaries.append(nearest)
    cuts=sorted(set([t for t in down[::DENSITIES[cut_density]] if 0<t<end]+boundaries))
    # One syncopated accent per selected bar; density controls both cuts and
    # embellishment. High guarantees one non-downbeat accent in every bar.
    accents=[]
    for i,start in enumerate(down):
        if i%DENSITIES[cut_density]: continue
        stop=down[i+1] if i+1<len(down) else end
        candidates=[t for t in beats if start<t<min(stop,end)]
        if candidates: accents.append(candidates[len(candidates)//2])
    styles=[]
    names=('zoom_punch','rgb_split','beat_bounce')
    for i,section in enumerate(sections):
        start=section['start_ms'];stop=sections[i+1]['start_ms'] if i+1<len(sections) else end
        styles.append(dict(start_ms=start,end_ms=min(end,stop),label=section.get('label',section.get('name',str(i))),effect=names[i%len(names)]))
    return dict(cut_density=cut_density,cuts_ms=cuts,accents_ms=accents,downbeats_ms=down,
                downbeats_inferred=inferred,sections=styles,duration_ms=end,
                cut_distance_median_ms=0.0,rule=f'every {DENSITIES[cut_density]} bars plus section boundaries')


def apply_layers(plan, beatmap):
    """Cycle source slots; loop/animation slots are fitted by the existing renderer."""
    result=copy.deepcopy(plan); design=layers(beatmap,cut_density=plan['cut_density'])
    sources=result['segments']; segments=[]; clock=0
    for i,end in enumerate(design['cuts_ms']+[design['duration_ms']]):
        item=copy.deepcopy(sources[i%len(sources)])
        for key in ('end_beat','end_downbeat','duration_ms','transition'): item.pop(key,None)
        item['duration_ms']=round(end/10)*10-round(clock/10)*10
        segments.append(item);clock=end
    result['segments']=segments
    effects=list(result.get('effects',[]))
    for section in design['sections']:
        indices=[i for i,t in enumerate(beatmap['beats_ms']) if section['start_ms']<=t<section['end_ms'] and t in design['accents_ms']]
        if not indices: continue
        effect=dict(name=section['effect'],start_ms=section['start_ms'],end_ms=section['end_ms'])
        field,maximum={'zoom_punch':('scale',1.08),'rgb_split':('amount',.35),'beat_bounce':('amount',1)}[effect['name']]
        effect[field]=dict(on='beats',indices=indices,decay_ms=160,min=1 if field=='scale' else 0,max=maximum)
        effects.append(effect)
    result['effects']=effects
    return result,design


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('beats',type=Path)
    ap.add_argument('--cut-density',choices=DENSITIES,default='mid');ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(argv)
    try:
        data=layers(json.loads(a.beats.read_text()),cut_density=a.cut_density)
        with a.out.open('x',encoding='utf-8') as f: json.dump(data,f,indent=2)
        return 0
    except (OSError,ValueError,KeyError) as exc:
        print('beat_layers: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__': raise SystemExit(main())
