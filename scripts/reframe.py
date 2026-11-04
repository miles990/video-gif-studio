#!/usr/bin/env python3
"""Experimental subject-following 9:16 crop from cached masks; no model/network use.

Accepts grayscale masks or RGBA frames emitted by background_remove.py (including
BiRefNet). Missing subjects use a center path and are explicitly reported.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import cv2
import numpy as np
from PIL import Image
from fx.core import floating, premultiply, straight, restore


def bbox(mask):
    mask=np.asarray(mask)
    if mask.ndim==3: mask=mask[...,3] if mask.shape[2]==4 else mask.max(axis=2)
    ys,xs=np.nonzero(mask> (127 if mask.max(initial=0)>1 else .5))
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]


def smooth_path(target, max_speed, max_acceleration):
    target=np.asarray(target,dtype=float)
    if len(target)<2: return target.copy()
    # Symmetric offline smoothing anticipates motion and avoids causal follow lag.
    blurred=cv2.GaussianBlur(target.reshape(-1,1,2),(1,0),sigmaX=0,sigmaY=4,borderType=cv2.BORDER_REPLICATE).reshape(-1,2)
    result=[target[0]];velocity=blurred[1]-blurred[0]
    speeds=np.linalg.norm(np.diff(target,axis=0),axis=1)
    for i,desired in enumerate(blurred[1:]):
        # The configured speed is a comfort floor, not a tracking ceiling.
        # Offline lookahead follows fast subjects without accumulating lag.
        limit=max(max_speed,1.15*max(speeds[max(0,i-4):i+5],default=0))
        wanted=desired-result[-1]; norm=np.linalg.norm(wanted)
        if norm>limit: wanted*=limit/norm
        delta=wanted-velocity;norm=np.linalg.norm(delta)
        if norm>max_acceleration: delta*=max_acceleration/norm
        velocity+=delta;result.append(result[-1]+velocity)
    return np.asarray(result)


def plan_path(boxes, source_size, output_size=(1080,1920), max_speed=8, max_acceleration=3):
    w,h=source_size;ow,oh=output_size;aspect=ow/oh
    if abs(aspect-9/16)>.01: raise ValueError('subject reframe requires a 9:16 output')
    if not boxes: raise ValueError('No masks')
    # Largest inscribed portrait crop: never manufacture space outside source.
    crop_h=min(h,w/aspect)
    crop_w=crop_h*aspect;scale=oh/crop_h
    target=[];fallback=[]
    for i,b in enumerate(boxes):
        if b is None:
            target.append((w/2,h/2));fallback.append(i)
        else:
            target.append(((b[0]+b[2])/2,b[1]-.1*(b[3]-b[1])+crop_h/2))
    # Smooth an already feasible target; clamping an unconstrained trajectory
    # afterwards would create a velocity step when it leaves the source edge.
    target=np.clip(target,[crop_w/2,crop_h/2],[w-crop_w/2,h-crop_h/2])
    centers=smooth_path(target,max_speed/scale,max_acceleration/scale)
    records=[]
    for i,(center,b) in enumerate(zip(centers,boxes)):
        x,y=center[0]-crop_w/2,center[1]-crop_h/2
        if b is not None:
            # Project into the feasible coverage interval. Coverage takes priority
            # over smoothing on abrupt turns; impossible fits are reported.
            if b[2]-b[0]<=crop_w: x=np.clip(x,b[2]-crop_w,b[0])
            if b[3]-b[1]<=crop_h: y=np.clip(y,b[3]-crop_h,b[1]-.1*(b[3]-b[1])) if b[3]-b[1]<=crop_h/1.1 else b[1]
            else: y=b[1]-.1*(b[3]-b[1])  # preserve head, cut feet if necessary
        x=float(np.clip(x,0,w-crop_w));y=float(np.clip(y,0,h-crop_h))
        transformed=None if b is None else [(b[0]-x)*scale,(b[1]-y)*scale,(b[2]-x)*scale,(b[3]-y)*scale]
        clipped=bool(b is not None and (transformed[0]<-1e-6 or transformed[2]>ow+1e-6 or transformed[1]<0 or transformed[3]>oh+1e-6))
        records.append(dict(frame=i,crop=[float(x),float(y),float(crop_w),float(crop_h)],
                            subject_bbox=transformed,fallback='no_subject_center' if b is None else None,needs_review=clipped))
    return dict(size=list(output_size),source_size=list(source_size),path=records,missing_subject_frames=fallback,
                status='experimental',title_safe_zone={'x':.05,'y':.64,'right':.90,'bottom':.79},
                warning='Crop stays inside source. Speed adapts to subject motion; impossible full-body fits prefer head over feet and are marked needs_review. Title band may overlap tall subjects.')


def transform(image, record, size):
    a=floating(np.asarray(image.convert('RGBA')) if isinstance(image,Image.Image) else image)
    x,y,w,h=record['crop'];ow,oh=size
    matrix=np.array([[ow/w,0,-x*ow/w],[0,oh/h,-y*oh/h]],dtype=np.float32)
    result=straight(cv2.warpAffine(premultiply(a),matrix,(ow,oh),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE))
    return Image.fromarray(restore(result,np.uint8))


def load_masks(manifest):
    manifest=Path(manifest);data=json.loads(manifest.read_text(encoding='utf-8-sig'))
    files=[manifest.parent/p for p in data['masks']] if 'masks' in data else sorted((manifest.parent/'frames').glob('*.png'))
    times=data.get('durations_ms')
    if not files or not times or len(files)!=len(times) or any(t<=0 for t in times): raise ValueError('Mask files must match positive durations_ms')
    boxes=[];size=None
    for file in files:
        with Image.open(file) as im:
            if size is not None and im.size!=size: raise ValueError('Mask canvas changed')
            size=im.size;boxes.append(bbox(np.asarray(im)))
    return boxes,size,times


class Reframer:
    def __init__(self, manifest, source_size, output_size, duration_ms, fps):
        boxes,size,times=load_masks(manifest)
        if tuple(size)!=tuple(source_size): raise ValueError('Mask canvas differs from source')
        if abs(sum(times)-duration_ms)>1000/fps: raise ValueError('Masks must be aligned to the edited output timeline')
        edges=np.cumsum([0]+times)
        sampled=[boxes[min(len(boxes)-1,max(0,int(np.searchsorted(edges,k*1000/fps,side='right')-1)))] for k in range(round(duration_ms*fps/1000))]
        self.report=plan_path(sampled,size,output_size);self.fps=fps;self.size=output_size

    def apply(self, image, t_ms):
        index=min(len(self.report['path'])-1,max(0,round(t_ms*self.fps/1000)))
        return transform(image,self.report['path'][index],self.size)


def reframe(frames, manifest, masks, out, size=(1080,1920), fps=30):
    out=Path(out);frames=Path(frames);files=sorted(frames.glob('*.png'));data=json.loads(Path(manifest).read_text())
    if out.exists(): raise ValueError('Use a new output directory')
    if len(files)!=len(data['durations_ms']) or not files: raise ValueError('Source frame/timing mismatch')
    with Image.open(files[0]) as image: source_size=image.size
    follower=Reframer(masks,source_size,size,sum(data['durations_ms']),fps)
    edges=np.cumsum([0]+data['durations_ms']);out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as folder:
        stage=Path(folder)/'result';(stage/'frames').mkdir(parents=True)
        for k in range(len(follower.report['path'])):
            t=k*1000/fps;index=min(len(files)-1,int(np.searchsorted(edges,t,side='right')-1))
            with Image.open(files[index]) as image: follower.apply(image,t).save(stage/'frames'/f'{k:05}.png')
        # Prepared-frame manifests use the shared 10ms clock; final platform
        # encoding resamples these exposures to CFR. Keep the adapter composable.
        clock=[round(k*1000/fps/10)*10 for k in range(len(follower.report['path'])+1)]
        durations=[b-a for a,b in zip(clock,clock[1:])]
        if any(t<20 for t in durations): raise ValueError('Prepared reframe output requires fps <= 50')
        (stage/'manifest.json').write_text(json.dumps(dict(durations_ms=durations,reframe=follower.report),indent=2))
        stage.rename(out)
    return follower.report


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('frames',type=Path);ap.add_argument('--manifest',required=True,type=Path)
    ap.add_argument('--masks',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--experimental',action='store_true')
    a=ap.parse_args(argv)
    try:
        if not a.experimental: raise ValueError('Subject reframe is experimental; use --experimental')
        reframe(a.frames,a.manifest,a.masks,a.out);return 0
    except (OSError,ValueError,KeyError) as exc:
        print('reframe: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__': raise SystemExit(main())
