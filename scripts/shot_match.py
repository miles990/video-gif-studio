"""Linear-light shot matching before the creative LUT, with D65 CIEDE2000 evidence."""
import argparse
from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image
from taste_common import read,write


def linear(rgb):
    s=np.asarray(rgb,float)/255
    return np.where(s<=.04045,s/12.92,((s+.055)/1.055)**2.4)


def srgb(x):
    x=np.maximum(x,0)
    return np.rint(np.clip(np.where(x<=.0031308,12.92*x,1.055*x**(1/2.4)-.055),0,1)*255).astype(np.uint8)


def delta_e(a,b):
    """Vectorized Sharma et al. CIEDE2000, D65 Lab inputs (degrees internally)."""
    a=np.asarray(a,float);b=np.asarray(b,float);l1,a1,b1=np.moveaxis(a,-1,0);l2,a2,b2=np.moveaxis(b,-1,0)
    c1=np.hypot(a1,b1);c2=np.hypot(a2,b2);cm=(c1+c2)/2;g=.5*(1-np.sqrt(cm**7/(cm**7+25**7)))
    aa1=(1+g)*a1;aa2=(1+g)*a2;c1=np.hypot(aa1,b1);c2=np.hypot(aa2,b2)
    h1=np.degrees(np.arctan2(b1,aa1))%360;h2=np.degrees(np.arctan2(b2,aa2))%360
    dl=l2-l1;dc=c2-c1;dh=h2-h1;dh=np.where(dh>180,dh-360,np.where(dh< -180,dh+360,dh));dh=np.where(c1*c2==0,0,dh)
    dh=2*np.sqrt(c1*c2)*np.sin(np.radians(dh/2));lm=(l1+l2)/2;cm=(c1+c2)/2
    hm=np.where(c1*c2==0,h1+h2,np.where(abs(h1-h2)<=180,(h1+h2)/2,np.where(h1+h2<360,(h1+h2+360)/2,(h1+h2-360)/2)))
    t=1-.17*np.cos(np.radians(hm-30))+.24*np.cos(np.radians(2*hm))+.32*np.cos(np.radians(3*hm+6))-.20*np.cos(np.radians(4*hm-63))
    sl=1+.015*(lm-50)**2/np.sqrt(20+(lm-50)**2);sc=1+.045*cm;sh=1+.015*cm*t
    rt=-2*np.sqrt(cm**7/(cm**7+25**7))*np.sin(np.radians(60*np.exp(-((hm-275)/25)**2)))
    return np.sqrt(np.maximum(0,(dl/sl)**2+(dc/sc)**2+(dh/sh)**2+rt*(dc/sc)*(dh/sh)))


def lab(rgb):return cv2.cvtColor(np.asarray(rgb,np.float32)/255,cv2.COLOR_RGB2LAB)


def fit(reference,source):
    a=linear(reference[...,:3]).reshape(-1,3);b=linear(source[...,:3]).reshape(-1,3)
    # Quantile-matched channel gains tolerate different composition; no pixel-copy.
    qa=np.percentile(a,[25,50,75,90],axis=0);qb=np.percentile(b,[25,50,75,90],axis=0)
    gains=np.sum(qa*qb,axis=0)/np.maximum(np.sum(qb*qb,axis=0),1e-12)
    return gains


def apply(rgb,gains,strength=1):
    if not np.isfinite(strength) or not 0<=strength<=1:raise ValueError('strength must be 0..1')
    if strength==0:return np.asarray(rgb).copy()
    result=np.asarray(rgb).copy();result[...,:3]=srgb(linear(result[...,:3])*(1+(np.asarray(gains)-1)*strength));return result


def measure(reference,source):
    if reference.shape!=source.shape:source=cv2.resize(source,(reference.shape[1],reference.shape[0]))
    de=delta_e(lab(reference[...,:3]),lab(source[...,:3]));a=reference[...,:3].astype(float);b=source[...,:3].astype(float)
    gray=np.ptp(a,axis=2)<5
    hsv=cv2.cvtColor(reference[...,:3],cv2.COLOR_RGB2HSV);skin=(hsv[...,0]>=7)&(hsv[...,0]<=25)&(hsv[...,1]>30)
    return dict(mean_delta_e2000=float(de.mean()),max_delta_e2000=float(de.max()),luma_difference=float(abs((a-b).mean(axis=(0,1))@np.array([.2126,.7152,.0722]))/255),
                gray_delta_e2000=float(de[gray].mean()) if gray.any() else None,skin_delta_e2000=float(de[skin].mean()) if skin.any() else None,
                mask_reason='Gray: channel spread <5; skin proxy: HSV hue 14..50 degrees, saturation >30. Not an identity detector.')


def match(reference,source,strength=1):
    gains=fit(reference,source);result=apply(source,gains,strength)
    return result,dict(gains=gains.tolist(),before=measure(reference,source),after=measure(reference,result),order=['decode sRGB','linear exposure/white balance match','creative LUT (downstream)'])


def load_lut(path):
    size=None;rows=[];lo=np.zeros(3);hi=np.ones(3)
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        fields=line.split('#',1)[0].strip().split()
        if not fields or fields[0]=='TITLE':continue
        if fields[0]=='LUT_3D_SIZE':size=int(fields[1])
        elif fields[0]=='DOMAIN_MIN':lo=np.array(fields[1:],float)
        elif fields[0]=='DOMAIN_MAX':hi=np.array(fields[1:],float)
        elif fields[0].startswith('LUT_'):raise ValueError('Only 3D .cube LUTs are supported')
        else:rows.append([float(v) for v in fields])
    if size is None or size<2 or len(rows)!=size**3 or any(len(r)!=3 for r in rows) or not np.isfinite(rows).all() or np.any(hi<=lo):raise ValueError('Invalid 3D cube LUT')
    return dict(grid=np.array(rows).reshape(size,size,size,3),domain_min=lo,domain_max=hi)


def apply_lut(rgb,lut):
    """Trilinear .cube evaluation; red is the fastest-varying source coordinate."""
    result=np.asarray(rgb).copy();grid=lut['grid'];n=len(grid)
    point=np.clip((rgb[...,:3]/255-lut['domain_min'])/(lut['domain_max']-lut['domain_min']),0,1)*(n-1)
    low=np.minimum(np.floor(point).astype(int),n-2);weight=point-low;out=np.zeros_like(point)
    for corner in ((0,0,0),(0,0,1),(0,1,0),(0,1,1),(1,0,0),(1,0,1),(1,1,0),(1,1,1)):
        offset=np.array(corner);idx=low+offset;w=np.prod(np.where(offset,weight,1-weight),axis=-1)
        out+=grid[idx[...,2],idx[...,1],idx[...,0]]*w[...,None]
    result[...,:3]=np.rint(np.clip(out,0,1)*255).astype(np.uint8);return result


def match_plan(plan_path,out,ref_shot=0,strength=1,lut=None):
    from copy import deepcopy
    if not np.isfinite(strength) or not 0<=strength<=1:raise ValueError('strength must be 0..1')
    plan_path=Path(plan_path);plan=read(plan_path);result=deepcopy(plan);out=Path(out)
    def sources(s):
        if s['type']=='still':return [plan_path.parent/s['image']]
        manifest=plan_path.parent/s['manifest'];return sorted((manifest.parent/'frames').glob('*.png'))
    paths=[sources(s) for s in plan['segments']]
    if not 0<=ref_shot<len(paths) or any(not p for p in paths):raise ValueError('Invalid reference shot or empty source')
    reference=np.array(Image.open(paths[ref_shot][0]).convert('RGB'));reports=[]
    creative=load_lut(lut) if lut else None
    if out.exists():raise ValueError('Use a new output directory')
    for i,(s,files) in enumerate(zip(result['segments'],paths)):
        source=np.array(Image.open(files[0]).convert('RGB'));gains=fit(reference,source)
        if (i==ref_shot or strength==0) and creative is None:
            for key in ('image','manifest'):
                if key in s:s[key]=str((plan_path.parent/s[key]).resolve())
            corrected=source
        else:
            folder=out/f'shot-{i}'/'frames';folder.mkdir(parents=True)
            for j,file in enumerate(files):
                with Image.open(file) as im:arr=np.array(im.convert('RGBA'))
                corrected_frame=arr if i==ref_shot else apply(arr,gains,strength)
                Image.fromarray(apply_lut(corrected_frame,creative) if creative else corrected_frame).save(folder/f'{j:05d}.png')
            corrected=source if i==ref_shot else apply(source,gains,strength)
            if s['type']=='still':s['image']=str((folder/'00000.png').resolve())
            else:
                manifest=read(plan_path.parent/s['manifest']);write(folder.parent/'manifest.json',manifest);s['manifest']=str((folder.parent/'manifest.json').resolve())
        row=dict(shot=i,gains=gains.tolist(),before=measure(reference,source),after=measure(reference,corrected))
        if creative:row['after_lut']=measure(apply_lut(reference,creative),apply_lut(corrected,creative))
        reports.append(row)
    for key in ('beatmap',):
        if key in result:result[key]=str((plan_path.parent/result[key]).resolve())
    for key in ('music','source_audio'):
        if isinstance(result.get(key),dict):result[key]['file']=str((plan_path.parent/result[key]['file']).resolve())
    write(out/'plan.json',result);write(out/'match.json',dict(shots=reports,order=['shot matching','existing plan LUT/effects']))
    return reports


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--ref-shot',type=int,default=0);p.add_argument('--strength',type=float,default=1);p.add_argument('--lut',type=Path);a=p.parse_args(argv)
    try:match_plan(a.plan,a.out,a.ref_shot,a.strength,a.lut);return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:print('shot_match: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
