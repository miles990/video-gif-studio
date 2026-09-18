"""Repair explicitly reviewed source-supported boundaries in RGBA frame sequences.
The caller supplies a dense y(x) contour and its editable band for each frame.
This tool does not classify materials, generate contours, or certify visual quality.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image

def repair(current, source, region, protect=None):
    if current.dtype != np.uint8 or current.ndim != 3 or current.shape[2] != 4:
        raise ValueError('Expected uint8 RGBA current frame')
    h,w=current.shape[:2]
    if source.shape != (h,w,3) or source.dtype != np.uint8:
        raise ValueError('Source RGB must match native frame dimensions')
    if region.get('reviewed') is not True:
        raise ValueError('An explicitly reviewed contour is required')
    start=int(region['startX']);curve=np.asarray(region['curveY'],dtype=float)
    inside=int(region['bandInside']);outside=int(region['bandOutside'])
    if curve.ndim!=1 or len(curve)<3 or not np.isfinite(curve).all():
        raise ValueError('Supply finite native-pixel y coordinates for each column')
    if start<0 or start+len(curve)>w or inside<1 or outside<1:
        raise ValueError('Invalid editable region')
    if curve.min()-inside<1 or curve.max()+outside>=h-1:
        raise ValueError('Contour band reaches canvas boundary; review a clipped-region recipe')
    protect=np.zeros((h,w),bool) if protect is None else (np.asarray(protect) if np.asarray(protect).dtype==bool else np.asarray(protect)>127)
    if protect.shape!=(h,w):raise ValueError('Protection mask dimensions differ')
    samples=int(region.get('coverageSamples',4))
    if samples<2 or samples>16:raise ValueError('coverageSamples must be 2..16')
    join=float(region.get('joinPixels',4))
    if join<1:raise ValueError('joinPixels must be positive')
    despill=int(region.get('despillPixels',0))
    if despill<0 or despill>inside:raise ValueError('Despill must remain inside the reviewed band')
    out=current.copy();mask=np.zeros((h,w),bool);xs=np.arange(start,start+len(curve))
    offsets=(np.arange(samples)+.5)/samples-.5
    for j,x in enumerate(xs):
        edge=curve[j];lo=int(np.floor(edge))-inside;hi=int(np.ceil(edge))+outside
        ys=np.arange(lo,hi);cx=x+offsets;ey=np.interp(cx,xs,curve)
        cov=(ys[:,None,None]+offsets[None,:,None]<ey[None,None,:]).mean(axis=(1,2))
        candidate=np.column_stack((source[lo:hi,x],np.rint(cov*255))).astype(np.uint8)
        fractional=(cov>0)&(cov<1)
        candidate[fractional,:3]=source[max(0,int(np.floor(edge))-2),x]
        if despill:
            rim=(ys>=edge-despill)&(cov>0)
            candidate[rim,1]=np.minimum(candidate[rim,1],np.maximum(candidate[rim,0],candidate[rim,2]))
        old=current[lo:hi,x].astype(float)
        # Preserve valid opaque material detail; restore source RGB only where damaged.
        intact=(old[:,3]==255)&(cov==1)
        candidate[intact,:3]=old[intact,:3].astype(np.uint8)
        candidate[cov==0]=0
        t=min(1.,j/join,(len(xs)-1-j)/join);t=t*t*(3-2*t)
        weight=t*np.minimum(1.,np.arange(hi-lo)/join)
        weight[protect[lo:hi,x]]=0
        oa=old[:,3]/255;na=candidate[:,3]/255;alpha=oa*(1-weight)+na*weight
        rgb=(old[:,:3]*(oa*(1-weight))[:,None]+candidate[:,:3]*(na*weight)[:,None])/np.maximum(alpha[:,None],1e-8)
        out[lo:hi,x]=np.column_stack((rgb,alpha*255)).round().clip(0,255).astype(np.uint8)
        # A zero-weight pixel must remain byte-identical, including hidden RGB.
        out[lo:hi,x][weight==0]=current[lo:hi,x][weight==0]
        mask[lo:hi,x]=weight>0
    np.testing.assert_array_equal(out[~mask],current[~mask])
    return out,{'changedPixels':int(np.any(out!=current,axis=2).sum()),'outsideReviewedBandChangedPixels':0,'protectedChangedPixels':0}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--frames',type=Path,required=True);p.add_argument('--source-frames',type=Path,required=True);p.add_argument('--regions',type=Path,required=True);p.add_argument('--protect-masks',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.resolve() in [a.frames.resolve(),a.source_frames.resolve()]:p.error('Use a separate candidate output directory')
    spec=json.loads(a.regions.read_text());files=sorted(a.frames.glob('*.png'))
    if not files:raise ValueError('No RGBA PNG frames')
    if set(spec['frames'])!={f.name for f in files}:raise ValueError('Every input frame needs an explicit region list, including [] for unchanged frames')
    if a.out.exists() and any(a.out.iterdir()):raise FileExistsError('Use an empty output directory; never recursively repair a prior result')
    a.out.mkdir(parents=True,exist_ok=True);rows=[]
    for f in files:
        source=a.source_frames/f.name;old=np.array(Image.open(f).convert('RGBA'));rgb=np.array(Image.open(source).convert('RGB'));out=old.copy();qc=[];protection=None
        if rgb.shape!=old.shape[:2]+(3,):raise ValueError('Native source/frame dimensions differ')
        if a.protect_masks:protection=np.array(Image.open(a.protect_masks/f.name).convert('L'))
        for region in spec['frames'][f.name]:out,report=repair(out,rgb,region,protection);qc.append(report)
        dest=a.out/f.name;temp=dest.with_suffix('.pending.png');Image.fromarray(out).save(temp)
        np.testing.assert_array_equal(np.array(Image.open(temp)),out);temp.replace(dest)
        rows.append({'frame':f.name,'inputSha256':digest(f),'sourceSha256':digest(source),'outputSha256':digest(dest),'regions':qc})
    (a.out/'repair-report.json').write_text(json.dumps({'version':'reviewed-material-boundary-v1','recipeSha256':digest(a.regions),'frames':rows,'geometryUnchanged':True,'timing':'retain source timing; no retiming performed','visualReview':'pending','decodedTargetReview':'pending','productionAccepted':False},indent=2))
    print(f'Staged {len(rows)} frames; visual, temporal and target-export review remain required')
if __name__=='__main__':main()
