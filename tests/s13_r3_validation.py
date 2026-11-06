"""Replay all three reviewed live sets. Scratch output only; optional native sources.

This is cross-validation/regression, not pristine-data evaluation. Missing
subscription access is explicitly recorded; oracle fakes are never AI accuracy.
"""
import sys,json,argparse
from pathlib import Path
import cv2,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from image_alpha import alpha_qa,cleanup,clear_haze,enclosed_regions
from image_edit import composite,register
from image_edit_seam import ghosting
from image_motion import seam_qa
from image_common import ImageError,write
from test_s13_r3_motion import breathe
from s13_r3_identity_evidence import evidence as identity_evidence

SETS=[('r1','live-s13',3,'sprite/cleaned.png'),('r2','live-s13-r2',2,'sprite2/native/image-1.png'),('r3','live-s13-r3',1,'spRing/native/image-1.png')]

def alpha(out,private):
    rows=[]
    positives=[('r1','live-s13/sprite/native/image-1.png'),('r1','live-s13/probe-alpha.png'),
               ('r2','live-s13-r2/sprite/native/image-1.png'),('r2','live-s13-r2/sprite2/native/image-1.png'),('r2','live-s13-r2/key/native/image-1.png'),
               ('r3','live-s13-r3/spRing/native/image-1.png'),('r3','live-s13-r3/spLegs/native/image-1.png'),('r3','live-s13-r3/icon/native/image-1.png')]
    for index,(name,relative) in enumerate(positives):
        with Image.open(ROOT/'tests/fixtures'/relative) as im:clean,_=cleanup(im)
        qa=alpha_qa(clean,overlay_path=out/f'positive-{index}.png')
        rows.append(dict(set=name,path=relative,status=qa['status'],enclosed_regions=len(qa['hole_review']['regions']),overlay=qa['hole_review'].get('overlay_path')))
    injections=[]
    if private:
        folder=private/'reviews/review-s13-r3/work/off/holes'
        for path in sorted(folder.glob('*.png')):
            with Image.open(path) as im:damaged=im.convert('RGBA')
            qa=alpha_qa(damaged,overlay_path=out/(path.stem+'.png'))
            # Oracle fake labels use the known injected alpha delta, never a
            # purported semantic inference. This verifies region reachability.
            tag=path.stem.split('_')[0];asset={'ring':'spRing','legs':'spLegs','icon':'icon'}[tag]
            with Image.open(private/f'reviews/review-s13-r3/work/live/{asset}/asset.png') as im:original=np.array(im.convert('RGBA'))
            raw=np.array(damaged);injected=raw[...,3]<original[...,3]
            a,_=clear_haze(raw);labels,_=enclosed_regions(a[...,3])
            def oracle(_path,regions):
                return {'regions':[dict(id=r['id'],classification='body_hole' if np.any(injected&(labels==r['label'])) else 'intended_gap',reason='oracle injection delta; fake judge only') for r in regions]}
            judged=alpha_qa(damaged,judge=oracle,overlay_path=out/(path.stem+'.png'))
            injections.append(dict(path=str(path),status=qa['status'],fake_judge_status=judged['status'],fake_judge_body_regions=sum(a['classification']=='body_hole' for a in judged['hole_review'].get('answers',[])),enclosed_regions=len(qa['hole_review']['regions']),overlay=qa['hole_review'].get('overlay_path')))
    return dict(designed_controls=rows,injected_controls=injections,
                injected_false_pass=sum(r['status']=='PASS' for r in injections),
                semantic_recall=None,semantic_false_pass=None,judge_status='unavailable: Codex child app-server access denied in sandbox',
                warning='Abstentions are not detections. Blocking all unreviewed components does not measure semantic recall.',
                leave_one_set_out=[dict(calibrated_on=[r for r in ('r1','r2','r3') if r!=held],held_out=held,
                    policy='No geometry approval; <=4 px specks excluded. No fitted semantic thresholds.',
                    positive_results=[r for r in rows if r['set']==held],semantic_recall=None,semantic_false_pass=None) for held in ('r1','r2','r3')])

def edits(out,private):
    rows=[];controls=[]
    for name,folder,shot,_ in SETS:
        sources=[('fixture',ROOT/'tests/fixtures'/folder)]
        if private:sources.append(('native',private/'reviews'/('review-s13' if name=='r1' else 'review-s13-'+name)/'work/live'))
        for resolution,p in sources:
            with Image.open(p/f'kf/shot-{shot}/keyframe.png') as im:base=im.convert('RGBA')
            with Image.open(p/'edit/regeneration/image-1.png') as im:candidate=im.convert('RGBA')
            with Image.open(p/'edit/mask.png') as im:mask=np.array(im.convert('L').resize(base.size,Image.Resampling.NEAREST))
            try:
                result,qa,region=composite(base,candidate,mask)
                result.save(out/f'{name}-{resolution}.needs-review.png' if qa['acceptance']=='needs_review' else out/f'{name}-{resolution}.png')
                rows.append(dict(set=name,resolution=resolution,base_size=base.size,candidate_size=candidate.size,**qa))
            except ImageError as exc:rows.append(dict(set=name,resolution=resolution,error=exc.error))
            if resolution=='fixture':
                a=np.array(base);band=(cv2.dilate(mask,np.ones((31,31),np.uint8))>0)&(cv2.erode(mask,np.ones((15,15),np.uint8))==0)
                for shift in (0,2,4,6):
                    b=cv2.warpAffine(a,np.float32([[1,0,shift],[0,1,0]]),(base.width,base.height),borderMode=cv2.BORDER_REFLECT)
                    controls.append(dict(set=name,shift_px=shift,label='clean' if shift==0 else 'ghost',**ghosting(a,b,band)))
    folds=[]
    for held in ('r1','r2','r3'):
        train=[r for r in controls if r['set']!=held];test=[r for r in controls if r['set']==held]
        # Select from a fixed grid on the two training sets ONLY. In ties keep
        # the preregistered 8-pair / 10% policy, avoiding content-driven retuning.
        candidates=[]
        for pairs in (4,8,12):
            for fraction in (.05,.10,.15):
                errors=sum((min(r['offset_edge_pixels'])>=pairs and min(r['offset_fractions'])>=fraction)!=(r['label']=='ghost') for r in train)
                candidates.append((errors,abs(pairs-8),abs(fraction-.10),pairs,fraction))
        _,_,_,pairs,fraction=min(candidates)
        results=[dict(r,calibrated_flag=min(r['offset_edge_pixels'])>=pairs and min(r['offset_fractions'])>=fraction) for r in test]
        folds.append(dict(held_out=held,calibrated_on=[n for n in ('r1','r2','r3') if n!=held],min_pairs=pairs,min_fraction=fraction,training_errors=min(candidates)[0],results=results))
    return dict(replays=rows,ghost_controls=controls,leave_one_set_out=folds,
                bounds=dict(residual_px=1,feather_px=3,flow_roundtrip_px=1,offset_range_px=[1,8],canny=[60,120]),
                caveat='Existing full-frame generations replayed. New crop-conditioned live generation is blocked by subscription CLI app-server access; no new crop quality claim.')

def loops(out):
    rows=[]
    for name,folder,_,src in SETS:
        frames=breathe(ROOT/'tests/fixtures'/folder/src)
        variants={'clean':frames,'endpoint_2s':frames[:8]+[frames[8]]*50+frames[9:],
                  'midmotion_360ms':frames[:4]+[frames[4]]*10+frames[5:]}
        jumped=frames.copy();jumped[16]=Image.fromarray(np.roll(np.array(frames[16]),12,axis=0));variants['single_jump_12px']=jumped
        for label,fs in variants.items():rows.append(dict(set=name,case=label,**seam_qa(fs)))
    # Human-requested temporal/position bounds are frozen across folds, not fit
    # to species. Training verifies them before evaluating the excluded set.
    folds=[dict(held_out=held,calibrated_on=[n for n in ('r1','r2','r3') if n!=held],
                fixed_bounds=dict(endpoint_fraction=.25,endpoint_ms=500,reversal_px=.5,jump_px=1,jump_multiple=3),
                training_errors=sum((r['status']=='PASS')!=(r['case']=='clean') for r in rows if r['set']!=held),
                results=[r for r in rows if r['set']==held]) for held in ('r1','r2','r3')]
    return dict(rows=rows,leave_one_set_out=folds)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('section',choices=['identity','alpha','edits','loops']);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--private',type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    if args.section=='identity':result=identity_evidence()
    elif args.section=='alpha':result=alpha(args.out,args.private)
    elif args.section=='edits':result=edits(args.out,args.private)
    else:result=loops(args.out)
    write(args.out/(args.section+'.json'),result);print(args.section,'saved',args.out/(args.section+'.json'))
