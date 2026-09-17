"""Recover reviewed clipped fine detail from a green-screen RGB source.
For neutral/dark detail against a measured green key, not a general segmenter.
The review mask must exclude green subject materials and unrelated shadows.
"""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image

def recover(rgba,source,review_mask,key_rgb,protect=None,noise_floor=.06):
    a=np.asarray(rgba);rgb=np.asarray(source,dtype=np.float32)
    mask=np.asarray(review_mask)>127
    if a.ndim!=3 or a.shape[2]!=4 or rgb.shape!=(*a.shape[:2],3) or mask.shape!=a.shape[:2]:raise ValueError('Source, RGBA and mask dimensions must match')
    protected=np.zeros_like(mask) if protect is None else np.asarray(protect)>127
    if protected.shape!=mask.shape:raise ValueError('Protection mask dimensions differ')
    key=np.asarray(key_rgb,dtype=np.float32)
    if key.shape!=(3,) or np.any(key<0) or np.any(key>255):raise ValueError('Key RGB must contain three values from 0 to 255')
    chroma=key[1]-max(key[0],key[2])
    if chroma<40:raise ValueError('A measured, sufficiently green backdrop is required')
    if not 0<=noise_floor<1:raise ValueError('Noise floor must be in [0,1)')
    opacity=np.clip(1-(rgb[:,:,1]-np.maximum(rgb[:,:,0],rgb[:,:,2]))/chroma,0,1)
    foreground=np.clip((rgb-(1-opacity[:,:,None])*key)/np.maximum(opacity[:,:,None],.001),0,255)
    candidate=np.concatenate([np.rint(foreground).astype('uint8'),np.rint(opacity[:,:,None]*255).astype('uint8')],axis=2)
    candidate[opacity<noise_floor]=0
    selected=mask&(~protected);out=a.copy();out[selected]=candidate[selected]
    assert np.array_equal(out[~selected],a[~selected])
    return out,{'changedPixels':int(np.any(out!=a,axis=2).sum()),'outsideMaskChangedPixels':0,'protectedChangedPixels':0,'keyRgb':[float(x) for x in key]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('frames','source-frames','review-masks','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--protect-masks',type=Path);p.add_argument('--noise-floor',type=float,default=.06)
    keys=p.add_mutually_exclusive_group(required=True);keys.add_argument('--key-rgb',type=float,nargs=3);keys.add_argument('--key-masks',type=Path)
    args=p.parse_args();files=sorted(args.frames.glob('*.png'))
    if not files:p.error('No PNG frames')
    if args.out.resolve() in [args.frames.resolve(),args.source_frames.resolve()]:p.error('Use a separate output directory')
    args.out.mkdir(parents=True,exist_ok=True);report=[]
    for f in files:
        dest=args.out/f.name
        if dest.exists():raise FileExistsError(f'Refuse to overwrite {dest}; use a new run')
        a=np.array(Image.open(f).convert('RGBA'));rgb=np.array(Image.open(args.source_frames/f.name).convert('RGB'));mask=np.array(Image.open(args.review_masks/f.name).convert('L'))
        protect=np.array(Image.open(args.protect_masks/f.name).convert('L')) if args.protect_masks else None
        key=args.key_rgb
        if args.key_masks:
            km=np.array(Image.open(args.key_masks/f.name).convert('L'))>127
            if km.shape!=rgb.shape[:2] or not km.any():raise ValueError('Invalid key sample mask')
            key=np.median(rgb[km],axis=0)
        out,qc=recover(a,rgb,mask,key,protect,args.noise_floor);tmp=dest.with_suffix('.pending.png');Image.fromarray(out).save(tmp)
        assert np.array_equal(np.array(Image.open(tmp)),out);tmp.replace(dest);report.append({'frame':f.name,**qc})
    (args.out/'recovery-report.json').write_text(json.dumps({'status':'candidate-needs-motion-and-export-review','geometryUnchanged':True,'timing':'retain source timing','frames':report},indent=2))
    print(f'Recovered reviewed regions in {len(files)} frames; motion/export review still required')
if __name__=='__main__':main()
