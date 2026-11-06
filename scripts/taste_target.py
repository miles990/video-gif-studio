"""Reference calibration stores scalar statistics only, never reference content."""
import argparse
from pathlib import Path
import sys
import numpy as np
from taste_common import write
from taste_report import analyze


def statistics(report):
    color=report['M5']['values'];p=report['M15']
    return dict(asl=report['M1']['asl'],cv=report['M1']['cv'],lra=report['M8']['lra'],
                event_density=report['M3']['density'],peak_valley_ratio=p['peak_to_valley_ratio'],
                color_p10=float(np.percentile(color,10)),color_p90=float(np.percentile(color,90)))


def calibrate(paths,weights=(.35,.25,.30,.10)):
    if not 1<=len(paths)<=3:raise ValueError('Supply one to three reference films')
    reports=[analyze(p,weights=weights) for p in paths]
    stats=[statistics(r) for r in reports]
    # Sort statistics, not paths: relocation and input order cannot affect bytes.
    import json
    stats=sorted(stats,key=lambda x:json.dumps(x,sort_keys=True))
    target={k:float(np.mean([s[k] for s in stats if s[k] is not None])) if any(s[k] is not None for s in stats) else None for k in stats[0]}
    effective=sorted({tuple(r['M15']['effective_weights']) for r in reports})
    return dict(version=1,threshold_class='U',sources=stats,target=target,weights=(np.asarray(weights)/sum(weights)).tolist(),effective_weights=[list(w) for w in effective],merge='Arithmetic mean of available scalar statistics; sorted sources; null means unavailable',
                content_policy='No paths, frames, audio, embeddings, hashes or per-frame arrays retained')


def compare_target(report,target):
    warnings=[];weights=report['M15'].get('requested_weights',report['M15']['weights'])
    if 'weights' not in target:warnings.append('Target has no recorded weights; intensity comparison is uncalibrated.')
    elif not np.allclose(weights,target['weights']):warnings.append('Mismatched weights: recompute reference and film with the same user weights before comparing intensity.')
    if target.get('effective_weights') and any(not np.allclose(report['M15']['effective_weights'],w) for w in target['effective_weights']):
        warnings.append('Effective weights differ because a component was unavailable; intensity ratios are not directly comparable.')
    return dict(warnings=warnings,measured=statistics(report),target=target['target'])


def plan_timing(duration,target):
    """Deterministic alternating durations realizing target ASL and population CV."""
    asl=target['asl'];cv=target['cv'] if target['cv'] is not None else 0.
    if not np.isfinite([duration,asl,cv]).all() or duration<=0 or asl<=0 or not 0<=cv<1:raise ValueError('Positive duration/ASL and CV in [0,1) required')
    count=max(1,round(duration/asl));lengths=np.array([asl*(1+cv*(-1 if i%2==0 else 1)) for i in range(count)])
    lengths*=duration/lengths.sum()
    return dict(durations=lengths.tolist(),achieved_asl=float(lengths.mean()),achieved_cv=float(lengths.std()/lengths.mean()),
                limitation='Finite duration quantizes shot count; source handles still need validation')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('references',type=Path,nargs='+');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--profile',type=Path);p.add_argument('--weights');a=p.parse_args(argv)
    from taste_pick import load
    try:write(a.out,calibrate(a.references,[float(x) for x in a.weights.split(',')] if a.weights else load(a.profile)['weights']));return 0
    except (ValueError,OSError,TypeError,KeyError,RuntimeError) as exc:print('taste_target: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
