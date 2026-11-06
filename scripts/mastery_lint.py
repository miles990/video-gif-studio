"""Lossless category ablations and review evidence, without an AI appeal verdict."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
import numpy as np
from PIL import Image
from taste_common import read,write
from taste_lint import ablation_measure,weakest,focal_overlap,finding


def absolutize(plan,base):
    result=deepcopy(plan)
    for s in result['segments']:
        for key in ('image','manifest'):
            if key in s:s[key]=str((base/s[key]).resolve())
    if 'beatmap' in result:result['beatmap']=str((base/result['beatmap']).resolve())
    for key in ('music','source_audio'):
        if isinstance(result.get(key),dict):result[key]['file']=str((base/result[key]['file']).resolve())
    return result


def ablate(plan_path,out):
    from fx_render import render
    from delivery import encode_frames,settings
    plan_path=Path(plan_path);out=Path(out)
    if out.exists():raise ValueError('Use a new external output directory')
    plan=absolutize(read(plan_path),plan_path.parent)
    categories=sorted({e.get('recipe',e.get('name')) for e in plan.get('effects',[])})
    # PNG cannot carry music. Visual differences are measured before encoding;
    # audio-only contribution is never declared a no-op by absence of evidence.
    original=deepcopy(plan)
    for key in ('music','source_audio','keep_audio','sfx','loudnorm','duck'):original.pop(key,None)
    write(out/'original.json',original);render(out/'original.json',out/'original',('png',),experimental=True)
    files=sorted((out/'original/frames').glob('*.png'))
    if not files:raise ValueError('No lossless render frames')
    baseline=[np.array(Image.open(p).convert('RGB')) for p in files];results=[]
    for category in categories:
        removed=deepcopy(original);removed['effects']=[e for e in removed.get('effects',[]) if e.get('recipe',e.get('name'))!=category]
        folder=out/category;write(folder/'plan.json',removed);render(folder/'plan.json',folder/'removed',('png',),experimental=True)
        other=[np.array(Image.open(p).convert('RGB')) for p in sorted((folder/'removed/frames').glob('*.png'))]
        measured=ablation_measure(baseline,other)
        events=[e for e in plan['effects'] if e.get('recipe',e.get('name'))==category]
        if any('recipe' in e for e in events):
            recipe=read(Path(__file__).resolve().parents[1]/'recipes'/f'{category}.json')
            if recipe.get('sfx'):
                measured.update(noop=False,suggestion='Needs user paired comparison: recipe also contributes audio',delta_lufs=None,audio_reason='Lossless visual ablation does not establish audio equivalence')
        # Render PNG uses 10 ms output samples; derive actual sample clock from manifest.
        manifest=read(out/'original/manifest.json');durations=manifest['durations_ms'];ts=np.r_[0,np.cumsum(durations)[:-1]]/1000
        start=min((e.get('at_ms',e.get('start_ms',0))/1000 for e in events),default=0);end=min(float(sum(durations)/1000),start+2)
        indices=[int(np.argmin(abs(ts-t))) for t in np.arange(start,end,1/25)]
        cfg=settings((baseline[0].shape[1],baseline[0].shape[0]),25)
        for name,frames in (('with',baseline),('without',other)):
            encode_frames((Image.fromarray(frames[i]).convert('RGBA') for i in indices),folder/(name+'.mp4'),cfg)
        measured.update(category=category,pair=dict(A=str((folder/'with.mp4').resolve()),B=str((folder/'without.mp4').resolve()),user_choice=None,judge_choice=None,protocol='P-STABLE paired core; user appeal decides'))
        write(folder/'comparison.json',measured);results.append(measured)
    result=dict(categories=results,coverage=1. if categories else None,reason=None if categories else 'No effect categories',lossless=True)
    write(out/'ablation.json',result);return result


def inspect_focal(frame,mask,shot=1):
    metrics=focal_overlap(frame,mask)
    from taste_common import value
    rows=[]
    if metrics['overlap'] is not None and metrics['overlap']<value('taste.focal.overlap.min'):
        rows.append(finding('focal_hierarchy',shot,metrics,value('taste.focal.overlap.min'),'Reduce the competing focal element or relocate the subject.'))
    return dict(metrics=metrics,findings=rows)


def focal_movie(movie,board,base=Path('.')):
    """Sample the middle of each shot against its explicit subject_mask sidecar."""
    import cv2
    from storyboard import normalize
    b=normalize(board);cap=cv2.VideoCapture(str(movie));rows=[];findings=[]
    if not cap.isOpened():raise ValueError('Cannot open focal-analysis movie')
    try:
        for i,s in enumerate(b['shots'],1):
            if not s.get('subject_mask'):
                rows.append(dict(shot=i,value=None,reason='No subject_mask sidecar supplied'));continue
            cap.set(cv2.CAP_PROP_POS_MSEC,(s['start']+s['end'])*500);ok,bgr=cap.read()
            if not ok:raise ValueError(f'Cannot decode focal sample for shot {i}')
            with Image.open(Path(base)/s['subject_mask']) as im:mask=np.array(im.convert('L'))
            result=inspect_focal(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB),mask,i)
            for row in result['findings']:
                findings.append(finding('focal_hierarchy',i,row['measured'],row['threshold'],row['suggestion'],s,b['fps']))
            rows.append(dict(shot=i,**result['metrics']))
    finally:cap.release()
    return dict(shots=rows,findings=findings)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args(argv)
    try:ablate(a.plan,a.out);return 0
    except (ValueError,OSError,KeyError,TypeError,RuntimeError) as exc:print('mastery_lint: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
