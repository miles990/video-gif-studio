"""Local original VFX sprites with graded alpha and explicit lifetime checks."""
from pathlib import Path
import numpy as np
from PIL import Image
from image_common import ImageError,write
from game_animation import frame_distance,previews


def vfx_qa(frames,loop=False):
    arrays=[np.array(im.convert('RGBA')) for im in frames];sums=np.array([a[...,3].sum() for a in arrays],float);peak=max(1,float(sums.max()));issues=[]
    soft=sum(np.count_nonzero((a[...,3]>0)&(a[...,3]<255)) for a in arrays)/max(1,sum(np.count_nonzero(a[...,3]) for a in arrays))
    if soft<.10:issues.append(dict(kind='lost_soft_alpha',fraction=soft))
    if any(np.any(a[a[...,3]==0,:3]) for a in arrays):issues.append(dict(kind='transparent_rgb_contribution'))
    if not loop:
        if sums[0]/peak>.05:issues.append(dict(kind='abrupt_start',ratio=float(sums[0]/peak)))
        if sums[-1]/peak>.02:issues.append(dict(kind='truncated_decay',ratio=float(sums[-1]/peak)))
        seam=None
    else:
        ordinary=np.median([frame_distance(a,b) for a,b in zip(frames,frames[1:])]);seam=frame_distance(frames[-1],frames[0])/max(1e-9,ordinary)
        if not .3<=seam<=1.5:issues.append(dict(kind='loop_seam',ratio=float(seam)))
    border=max(float(np.r_[a[:2,:,:3].ravel(),a[-2:,:,:3].ravel(),a[:,:2,:3].ravel(),a[:,-2:,:3].ravel()].mean()) for a in arrays)
    if border>1:issues.append(dict(kind='border_contribution',value=border))
    return dict(status='FAIL' if issues else 'PASS',issues=issues,soft_fraction=soft,alpha_sums=sums.tolist(),start_peak_ratio=float(sums[0]/peak),end_peak_ratio=float(sums[-1]/peak),seam_ratio=None if seam is None else float(seam))


def additive_preview(im,background=(12,18,30)):
    a=np.array(im.convert('RGBA'));premult=np.rint(a[...,:3].astype(float)*a[...,3:4]/255).astype(np.uint8)
    result=np.clip(premult.astype(int)+np.array(background),0,255).astype(np.uint8)
    return Image.fromarray(result).convert('RGBA'),Image.fromarray(premult)


def vfx(out,kind='explosion',frames=12,size=96,loop=False,pixel=False,blend='add',color='#80DAFF'):
    budget=16 if pixel else 32
    if not 8<=frames<=budget:raise ImageError('E_FRAME_BUDGET',f'Use 8..{budget} frames; do not silently truncate an effect.',frame_budget=budget,suggestion=f'Resample the complete lifetime to {budget} frames.')
    if kind not in ('explosion','magic','hit','pickup') or blend not in ('add','alpha'):raise ImageError('E_VFX','Unknown kind/blend.')
    if not 32<=size<=1024:raise ImageError('E_SIZE','VFX size must be 32..1024.')
    out=Path(out);(out/'frames').mkdir(parents=True,exist_ok=True);(out/'premultiplied').mkdir(exist_ok=True)
    yy,xx=np.indices((size,size));x=(xx-(size-1)/2)/(size/2);y=(yy-(size-1)/2)/(size/2);r=np.hypot(x,y);theta=np.arctan2(y,x)
    rgb=np.array(tuple(bytes.fromhex(color.lstrip('#'))));images=[];add=[];records=[]
    for i in range(frames):
        t=i/(frames-1);phase=2*np.pi*(i+.25)/frames
        strength=.7+.3*np.sin(phase) if loop else np.sin(np.pi*t)**2
        radius=.30+.06*np.cos(phase) if loop else .12+.45*t
        if kind=='magic':field=np.exp(-((r-radius)/.055)**2)+.3*np.exp(-(r/.3)**2)
        elif kind=='hit':field=np.exp(-(r/.42)**2)*(np.maximum(0,np.cos(4*theta))**8+.15)
        elif kind=='pickup':field=np.exp(-((abs(x)+abs(y)-radius)/.04)**2)+.25*np.exp(-(r/.25)**2)
        else:field=np.exp(-(r/max(radius,.03))**3)*(1+.15*np.cos(7*theta+4*t))
        opacity=np.rint(np.clip(field*strength*230,0,255)).astype(np.uint8);opacity[r>.82]=0
        a=np.zeros((size,size,4),np.uint8);a[...,:3]=rgb;a[...,3]=opacity;a[opacity==0]=0
        im=Image.fromarray(a);im.save(out/'frames'/f'{i:05d}.png');images.append(im);composite,premult=additive_preview(im);premult.save(out/'premultiplied'/f'{i:05d}.png');add.append(composite)
        records.append(dict(index=i,file=f'frames/{i:05d}.png',duration_ms=80,source='local_procedural'))
    qa=vfx_qa(images,loop);previews(images,[80]*frames,out,loop)
    (out/'additive').mkdir(exist_ok=True);previews(add,[80]*frames,out/'additive',loop)
    manifest=dict(state=kind,canvas=[size,size],pivot=[size/2,size/2],fps=12.5,loop=loop,events=[],frames=records,alpha_mode='straight',blend=blend,pixel_scale=1,
                  frame_budget=budget,qa=qa,provenance=dict(tool='game_vfx',version=1,effect_id=kind,source='original local procedural effect; no video generation'),review='pending',status='experimental')
    write(out/'anim.json',manifest);write(out/'gen-manifest.json',dict(provenance=manifest['provenance'],subscription_images=0,network_requests=0,frame_budget=budget))
    return manifest
