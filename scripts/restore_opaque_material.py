"""Recover opaque interior pixels using explicit reviewed masks and matched source RGB.
Masks describe confirmed material interiors, not an inferred full-object matte.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image

def binary_mask(value,shape,name):
    value=np.asarray(value)
    if value.shape!=shape:raise ValueError(name+' dimensions differ')
    if value.dtype==bool:return value
    if not np.isin(value,[0,255]).all():raise ValueError(name+' must be binary; do not supply a graded alpha matte')
    return value==255

def restore(current,source,reviewed,protect=None,rgb_policy='preserve-valid',rgb_damage=None):
    if current.dtype!=np.uint8 or current.ndim!=3 or current.shape[2]!=4:
        raise ValueError('Expected native uint8 RGBA frame')
    if source.dtype!=np.uint8 or source.shape!=(*current.shape[:2],3):
        raise ValueError('Expected matching uint8 source RGB')
    if rgb_policy not in ('preserve-valid','source'):
        raise ValueError('Unknown RGB recovery policy')
    mask=binary_mask(reviewed,current.shape[:2],'Reviewed opaque mask')
    damaged=np.zeros(mask.shape,bool) if rgb_damage is None else binary_mask(rgb_damage,mask.shape,'Reviewed RGB damage mask')
    if np.any(damaged&~mask):raise ValueError('RGB damage mask must stay within the reviewed opaque interior')
    if protect is not None:mask=mask&~binary_mask(protect,current.shape[:2],'Protection mask')
    damaged=damaged&mask
    mask=mask&(current[:,:,3]<255)
    # Inputs are straight RGBA. Keep valid despill/lighting when restoring coverage.
    # Fully erased pixels need source color; damaged nonzero RGB requires explicit opt-in.
    recover=(mask if rgb_policy=='source' else mask&(current[:,:,3]==0))|damaged
    out=current.copy();out[recover,:3]=source[recover];out[mask,3]=255
    opaque_changed=(current[:,:,3]==255)&np.any(out[:,:,:3]!=current[:,:,:3],axis=2)
    return out,{'restoredPixels':int(mask.sum()),'sourceRgbRecoveredPixels':int(recover.sum()),'rgbPolicy':rgb_policy,'outsideMaskChangedPixels':0,'alreadyOpaqueRgbChangedPixels':int(opaque_changed.sum()),'reviewedRgbDamagePixels':int(damaged.sum())}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['frames','source-frames','opaque-masks','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--protect-masks',type=Path)
    p.add_argument('--rgb-damage-masks',type=Path,help='Optional separately reviewed RGB corruption masks, including already opaque damage; must lie inside opaque masks')
    p.add_argument('--rgb-policy',choices=['preserve-valid','source'],default='preserve-valid',help='Straight RGBA only; source also replaces damaged nonzero RGB inside the reviewed repair')
    a=p.parse_args();files=sorted(a.frames.glob('*.png'))
    if not files:raise ValueError('No PNG frames')
    names={f.name for f in files}
    for directory in [a.source_frames,a.opaque_masks]+([a.protect_masks] if a.protect_masks else [])+([a.rgb_damage_masks] if a.rgb_damage_masks else []):
        if {f.name for f in directory.glob('*.png')}!=names:raise ValueError('Every frame requires a matching source and explicit mask, including empty masks')
    if a.out.exists() and any(a.out.iterdir()):raise FileExistsError('Use an empty output directory')
    if a.out.resolve() in [a.frames.resolve(),a.source_frames.resolve(),a.opaque_masks.resolve()]:raise ValueError('Use a separate output directory')
    a.out.mkdir(parents=True,exist_ok=True);rows=[]
    for f in files:
        src=a.source_frames/f.name;mp=a.opaque_masks/f.name
        old=np.array(Image.open(f).convert('RGBA'));rgb=np.array(Image.open(src).convert('RGB'));mask=np.array(Image.open(mp).convert('L'))
        protect=np.array(Image.open(a.protect_masks/f.name).convert('L')) if a.protect_masks else None
        damage=np.array(Image.open(a.rgb_damage_masks/f.name).convert('L')) if a.rgb_damage_masks else None
        out,qc=restore(old,rgb,mask,protect,a.rgb_policy,damage);dest=a.out/f.name;tmp=dest.with_suffix('.pending.png');Image.fromarray(out).save(tmp)
        np.testing.assert_array_equal(np.array(Image.open(tmp)),out);tmp.replace(dest)
        rows.append({'frame':f.name,'inputSha256':digest(f),'sourceSha256':digest(src),'maskSha256':digest(mp),'protectionMaskSha256':digest(a.protect_masks/f.name) if a.protect_masks else None,'rgbDamageMaskSha256':digest(a.rgb_damage_masks/f.name) if a.rgb_damage_masks else None,'outputSha256':digest(dest),**qc})
    (a.out/'repair-report.json').write_text(json.dumps({'version':'reviewed-opaque-interior-v3','algorithmSha256':digest(Path(__file__)),'alphaRepresentation':'straight','rgbPolicy':a.rgb_policy,'frames':rows,'geometryUnchanged':True,'timing':'retain original source timing','visualReview':'pending','decodedTargetReview':'pending','productionAccepted':False},indent=2))
    print(f'Restored reviewed opaque interiors in {len(rows)} frames; motion and target-export review remain pending')
if __name__=='__main__':main()
