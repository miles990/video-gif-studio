"""Decoded output versus concurrent no-effect reference, with streaming WCAG."""
import argparse
from collections import deque
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import cv2
import numpy as np
from fx_measure import rgb, LUMA, measures, onset_contrast, classify, FlashCounter
from fx_measure import visibility_residual,visibility_family
from threshold_registry import value


def decoded(path):
    """Full-resolution sequential decode; no subsampling away small flash regions."""
    cap=cv2.VideoCapture(str(path))
    if not cap.isOpened():raise ValueError('Cannot decode '+str(path))
    try:
        while True:
            ok,bgr=cap.read()
            if not ok:break
            yield cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
    finally:cap.release()


def check_video(path, reference=None, events=(), fps=30):
    if not np.isfinite(fps) or fps<=0:raise ValueError('fps must be positive')
    frames=decoded(path);refs=iter(decoded(reference)) if reference else None
    counter=FlashCounter();previous=deque(maxlen=3);count=0
    reports=[]
    for event in events:
        reports.append(dict(event=event,peak=None,onset_before=[],onset_after=[],scene=[],bad_run=0,max_bad_run=0))
    for index,frame in enumerate(frames):
        count+=1;t=index*1000/fps;counter.push_frame(frame,index,fps)
        ref=next(refs,None) if refs is not None else None
        if refs is not None and ref is None:raise ValueError('Reference has fewer frames than output')
        if ref is None:continue
        if ref.shape!=frame.shape:raise ValueError('Reference size differs from output')
        for r in reports:
            e=r['event'];start=e.get('start_ms',e.get('at_ms',0));end=e.get('end_ms',start+500)
            if start<=t<end:
                family=e.get('family',visibility_family(e['name']))
                residual,scene=visibility_residual(ref,frame,family)
                m=measures(ref,frame)
                if r['peak'] is None or (m['perceived'] is not None and m['perceived']>r['peak']['perceived']):
                    r['peak']=m;r['peak_ms']=t
                if m['sharp4'] is not None and m['sharp4']<value('harshness.sharp4.min') and m['ssim_loss']>value('harshness.ssim_loss.max'):r['bad_run']+=1
                else:r['bad_run']=0
                r['max_bad_run']=max(r['max_bad_run'],r['bad_run'])
                if len(r['onset_after'])<3:
                    before=[visibility_residual(a,b,family) for a,b in previous]
                    if not r['onset_before']:r['onset_before']=[p[0] for p in before] or [np.zeros_like(residual)]
                    r['onset_after'].append(residual);r['scene'].append(scene)
                    if len(r['scene'])==1:r['scene']=[p[1] for p in before]+r['scene']
        previous.append((ref,frame))
    if not count:raise ValueError('Empty decoded output')
    if refs is not None and next(refs,None) is not None:raise ValueError('Reference has more frames than output')
    wcag=counter.report();output=[]
    for r in reports:
        if r['peak'] is None:raise ValueError('Effect event has no decoded output frames')
        e=r['event'];onset=onset_contrast(r['onset_before'],r['onset_after'],r['scene'])
        v=classify(r['peak'],onset,e.get('intent','hit'),e.get('kind')=='transition',r['max_bad_run'],family=e.get('family',visibility_family(e['name'])))
        v['wcag_flashes_max_per_s']=wcag['max_flashes_per_s']
        start=e.get('start_ms',e.get('at_ms',0))/1000;end=e.get('end_ms',start*1000+500)/1000
        if any(w['start_seconds']<end and w['end_seconds']>start for w in wcag['windows']):v['status']='harsh';v['advice']='Reduce flash frequency or area; WCAG 2.3.1 failed.'
        output.append(dict(event=e,peak_ms=r['peak_ms'],visibility=v))
    return dict(frames=count,wcag=wcag,events=output,reference=str(reference) if reference else None,
                limitations='Visibility and destructive-blur decisions require active C anchor calibration; unknown is not a pass.')


def check_render(movie,plan,path,fps,root,experimental):
    from fx_render import render
    from fx_director import events_from_plan
    reference=deepcopy(plan);reference.pop('fx_checks',None);reference.pop('recipe_events',None);reference.pop('sfx',None)
    reference['keep_audio']=False
    reference['effects']=[]
    # Keep transitions: the matched reference must retain concurrent scene motion.
    with tempfile.TemporaryDirectory(prefix='vgs-fx-reference-',dir=Path(root).parent) as temp:
        ref_path=Path(temp)/'reference.json'
        # Resolve relative media paths before moving the derivative plan.
        for s in reference['segments']:
            for key in ('manifest','image'):
                if key in s:s[key]=str((path.parent/s[key]).resolve())
        for key in ('beatmap',):
            if key in reference:reference[key]=str((path.parent/reference[key]).resolve())
        for key in ('music','source_audio'):
            reference.pop(key,None)
        ref_path.write_text(json.dumps(reference),encoding='utf-8')
        ref_out=Path(temp)/'render';render(ref_path,ref_out,('mp4',),experimental=experimental,fps=fps)
        from fx_recipes import load_recipes
        recipes=load_recipes(experimental=True)
        events=[dict(name=e['name'],start_ms=e.get('start_ms',0),end_ms=e.get('end_ms',500),
                     intent=recipes.get(e.get('recipe_name'),{}).get('intent','texture' if e['name']=='grade' else 'hit')) for e in plan.get('effects',[])]
        result=check_video(movie,ref_out/'animation.mp4',events,fps)
    (Path(root)/'fx-qa.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('--reference',type=Path)
    ap.add_argument('--events',type=Path);ap.add_argument('--fps',type=float,default=30);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(argv)
    try:
        events=json.loads(a.events.read_text(encoding='utf-8')) if a.events else []
        result=check_video(a.input,a.reference,events,a.fps)
        a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
        return int(result['wcag']['status']=='harsh' or any(e['visibility']['status']=='destructive' for e in result['events']))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('fx_check: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
