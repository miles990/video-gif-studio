"""Reproduce both-family calibration and held-out measurements from repo fixtures.

Run from the repository root; scratch images go to .scratch/s14-calibration.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,'scripts')
import numpy as np,cv2
from PIL import Image
from game_character import prepare_subject,quantize,palette_of,identity_report
from game_sprite import pixel_noise,alpha_contract
from image_identity import compare
from game_icons import style_qa
from game_tiles import tile_qa
from image_common import write
root=Path('tests/fixtures/live-s14');out=Path('.scratch/s14-calibration');out.mkdir(exist_ok=True)
report={'protocol':'Freeze thresholds using front/side from BOTH families; back is a per-family positive holdout. Injected halo/noise controls use the same split. No held-out tuning.',
 'thresholds':{'isolated_color_fraction':.12,'opaque_rim_contaminated_fraction':.15,'near_identity':'refset-relative ordering, no absolute BH cutoff'},'characters':[],'icons':[],'textures':[]}
for family in ('rimewick','wolf'):
    paths={}
    for view in ('front','side','back'):
        with Image.open(root/f'{family}-{view}.png') as source:im,selection=prepare_subject(source.convert('RGBA'),view)
        p=out/f'{family}-{view}.png';im.save(p);paths[view]=p
        pal=palette_of([im]);old=quantize(im.resize((64,64),Image.Resampling.NEAREST),pal);new=quantize(im,pal,(64,64))
        a=np.array(new);mask=a[...,3]>127;distance=cv2.distanceTransform(mask.astype('uint8'),cv2.DIST_L2,5);band=mask&(distance<=2)
        damaged=a.copy();damaged[band,:3]=np.rint(a[band,:3]*.2+255*.8)
        from image_alpha import nearest_opaque
        nearest,_=nearest_opaque(a);outside=(cv2.dilate(mask.astype('uint8'),np.ones((3,3),np.uint8))>0)&~mask
        damaged[outside,:3]=np.rint(nearest[outside]*.2+255*.8);damaged[outside,3]=96
        clean_q=alpha_contract(new);bad_q=alpha_contract(Image.fromarray(damaged))
        report['characters'].append(dict(family=family,view=view,split='held_out' if view=='back' else 'calibration',subject_count=selection['subject_count'],
            old_noise=pixel_noise(old),new_noise=pixel_noise(new),old_noise_detected=pixel_noise(old)>.12,new_noise_pass=pixel_noise(new)<=.12,
            clean_rim_false_positive='opaque_rim_halo' in clean_q['issues'],injected_rim_detected='opaque_rim_halo' in bad_q['issues'],rim_evidence=bad_q['opaque_rim']))
    negative=root/f'{family}-negative.png'
    near=root/'wolf-near.png' if family=='wolf' else negative
    if family=='wolf':paths['front']=root/'wolf-front-single.png'
    trained={n:p for n,p in paths.items() if n!='back'}
    report[family+'_identity']=identity_report(trained,[negative],near)
    from game_character import view_palette_signature,view_palette_distance
    holdout=view_palette_distance(view_palette_signature(paths['front']),view_palette_signature(paths['back']))
    boundary=report[family+'_identity']['view_palette_controls']['nearest_negative']
    report[family+'_identity']['held_out_back']=dict(view_palette_distance=holdout,below_training_negative=holdout<boundary,semantic_status='unassessed')
token=json.loads((root/'wolf-icon-style.json').read_text(encoding='utf8'))
for i in range(4):
    with Image.open(root/f'wolf-icon-{i}.png') as im:
        report['icons'].append(dict(family='wolf',index=i,split='held_out' if i==3 else 'calibration',qa=style_qa([im.convert('RGBA')],token)))
token=json.loads((root/'rimewick-icon-style.json').read_text(encoding='utf8'))
for i in range(8):
    with Image.open(root/f'rimewick-icon-{i}.png') as source:
        im=source.convert('RGBA')
        report['icons'].append(dict(family='rimewick',index=i,split='held_out' if i==7 else 'calibration',qa=style_qa([im],token)))
for family,name in (('rimewick','texture'),('wolf','slate')):
    with Image.open(root/f'{family}-{name}.png') as im:report['textures'].append(dict(family=family,split='held_out',qa=tile_qa(im)))
from game_animation import motion_qa
report['motion']=[]
for state in ('run','idle'):
    m=json.loads((root/'motion'/f'rimewick-{state}.json').read_text())
    frames=[]
    for row in m['frames']:
        with Image.open(root/'motion'/row['file']) as im:frames.append(im.convert('RGBA'))
    report['motion'].append(dict(family='rimewick',state=state,split='held_out' if state=='idle' else 'calibration',qa=motion_qa(frames,m),
        limitation='Legacy run boxes overlap; same-foot left/right attribution remains unassessed. Do not count this as anatomical validation.'))
for name in ('WALK-8','WALK-LIMP','WALK-JUMPSEAM','WALK-SLIDE','WALK-AIR','WALK-DUPSEAM'):
    frames=[]
    for p in sorted((root/'motion').glob(name+'-*.png')):
        with Image.open(p) as im:frames.append(im.convert('RGBA'))
    m=dict(state='walk',pivot=[32,60],ground_line=60,pixel=True,loop=True,frames=[dict(duration_ms=100) for _ in frames],
           foot_boxes={'left':[[18,50,14,14]]*len(frames),'right':[[33,50,14,14]]*len(frames)})
    report['motion'].append(dict(family='reviewer_control',state=name,split='held_out' if name in ('WALK-SLIDE','WALK-AIR','WALK-DUPSEAM') else 'calibration',qa=motion_qa(frames,m)))
write(root/'calibration.json',report)
print(json.dumps({'characters':report['characters'],'identity':{f:report[f+'_identity'] for f in ('rimewick','wolf')}},indent=2))
