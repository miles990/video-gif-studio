"""Repair reviewed unwanted-pixel masks in RGBA sequences; preserve protected detail.
Masks identify confirmed non-object pixels, not an automatically inferred silhouette.
"""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image

def repair(rgba,remove,protect=None,smooth=0.6):
 a=np.asarray(rgba);remove=np.asarray(remove)>127
 if remove.shape!=a.shape[:2]:raise ValueError('Removal mask dimensions differ')
 protect=np.zeros_like(remove) if protect is None else np.asarray(protect)>127
 if protect.shape!=remove.shape:raise ValueError('Protection mask dimensions differ')
 hit=remove&(~protect)&(a[:,:,3]>0);out=a.copy();out[hit]=0
 if smooth>0 and hit.any():
  kernel=np.ones((3,3),np.uint8);band=(cv2.dilate(hit.astype('uint8'),kernel)>0)&(~protect)
  filtered=cv2.GaussianBlur(out[:,:,3].astype('float32'),(3,3),smooth)
  # Adjacent antialiasing must not erase an attached thin foreground line.
  filtered=np.maximum(filtered,np.where(~remove,np.minimum(a[:,:,3],160),0))
  out[:,:,3]=np.where(band,np.rint(filtered),out[:,:,3]).astype('uint8')
  # Only reconstruct newly partial edge color, never flatten intact material RGB.
  core=((a[:,:,3]>=240)&(~remove)).astype('uint8')
  if core.any():
   _,labels=cv2.distanceTransformWithLabels(1-core,cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
   colors=a[:,:,:3][core>0];near=colors[np.clip(labels-1,0,len(colors)-1)]
   extend=band&(out[:,:,3]>0)&((a[:,:,3]<200)|hit)
   out[extend,:3]=near[extend]
 out[hit]=0
 out[protect]=a[protect]
 # Canonicalize only repaired transparent pixels; untouched RGB remains byte-identical.
 changed_region=cv2.dilate(hit.astype('uint8'),np.ones((3,3),np.uint8))>0
 out[changed_region&(~protect)&(out[:,:,3]==0)]=0
 assert np.array_equal(out[protect],a[protect])
 assert np.array_equal(out[~changed_region],a[~changed_region])
 return out,{'removedPixels':int(hit.sum()),'changedPixels':int(np.any(out!=a,axis=2).sum()),'protectedChangedPixels':0,'outsideBandChangedPixels':0}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--frames',type=Path,required=True);p.add_argument('--remove-masks',type=Path,required=True);p.add_argument('--protect-masks',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--smooth',type=float,default=.6,help='0 for intentional pixel-art edges');args=p.parse_args()
 if args.out.resolve()==args.frames.resolve():p.error('Use a new output directory, not the source')
 files=sorted(args.frames.glob('*.png'));assert files,'No PNG frames'
 args.out.mkdir(parents=True,exist_ok=True);report=[]
 for f in files:
  dest=args.out/f.name
  if dest.exists():raise FileExistsError(f'Refuse to overwrite {dest}; use a new run')
  src=np.array(Image.open(f).convert('RGBA'));mask=np.array(Image.open(args.remove_masks/f.name).convert('L'));protection=None
  if args.protect_masks:protection=np.array(Image.open(args.protect_masks/f.name).convert('L'))
  result,qc=repair(src,mask,protection,args.smooth);temp=dest.with_suffix('.pending.png');Image.fromarray(result).save(temp);assert np.array_equal(np.array(Image.open(temp)),result);temp.replace(dest);report.append({'frame':f.name,**qc})
 (args.out/'repair-report.json').write_text(json.dumps({'frames':report,'status':'pixel-repair-complete-needs-visual-and-export-review','geometryUnchanged':True,'timing':'retain caller source timing; no retiming performed'},indent=2))
 print(f'Repaired {len(files)} frames; visual and decoded-export review still required')
if __name__=='__main__':main()
