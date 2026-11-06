"""Prepare blinded moving technical controls; never invent panel/user votes."""
from pathlib import Path
import random
import shutil
import numpy as np
from PIL import Image
from image_common import read,write,digest
from game_animation import previews,motion_qa
from game_sprite import pixel_qa


def review_bundle(demo,out):
    demo,out=Path(demo),Path(out);out.mkdir(parents=True,exist_ok=True);pairs=[];answers=[];rng=random.Random(14168)
    palette=read(demo/'charsheet/palette.json')
    for i,(state,defect) in enumerate([('idle','foot_slide'),('idle','palette_swap'),('run','duplicate_seam'),('attack','palette_swap'),('hurt','palette_swap'),('run','foot_slide'),('idle','identical_control'),('run','identical_control')]):
        manifest=read(demo/'anim'/state/'anim.json');frames=[Image.open(demo/'anim'/state/f['file']).convert('RGBA') for f in manifest['frames']];bad=[f.copy() for f in frames];times=[f['duration_ms'] for f in manifest['frames']]
        if defect=='foot_slide':
            for j,im in enumerate(bad):
                a=np.array(im);x,y,w,h=(20,53,12,10);patch=a[y:y+h,x:x+w].copy();a[y:y+h,x:x+w]=0;shift=round(3*j/(len(bad)-1));a[y:y+h,x+shift:x+w+shift]=patch;bad[j]=Image.fromarray(a)
        elif defect=='palette_swap':
            j=len(bad)//2;a=np.array(bad[j]);mask=np.all(a[...,:3]==[43,137,144],axis=-1)|(np.all(a[...,:3]==[27,89,100],axis=-1));a[...,:3][mask]=[43,107,181];bad[j]=Image.fromarray(a)
        elif defect=='duplicate_seam':bad[-1]=bad[0].copy()
        folder=out/f'pair-{i+1:02d}';folder.mkdir(exist_ok=True);flipped=bool(rng.randrange(2))
        for name,sequence in zip(('A','B'),(bad,frames) if flipped else (frames,bad)):
            (folder/name).mkdir(exist_ok=True);previews(sequence,times,folder/name,manifest['loop'])
        expected='tie' if defect=='identical_control' else 'B' if flipped else 'A'
        pairs.append(dict(id=i+1,A=f'pair-{i+1:02d}/A/preview.gif',B=f'pair-{i+1:02d}/B/preview.gif',question='Which has fewer technical defects? A / B / tie. Cite frame/time; do not judge visual style.'))
        bad_motion=motion_qa(bad,manifest);bad_palette=pixel_qa(bad,palette,(64,64))
        answers.append(dict(id=i+1,defect=defect,expected=expected,motion=bad_motion,palette=bad_palette,automatic_rejection=bad_motion['status']=='FAIL' or bad_palette['status']=='FAIL'))
    write(out/'pairs.json',dict(pairs=pairs,panel_status='pending',user_status='pending',wilson_lower_bound=None,reason='No human votes collected; no fabricated taste score.'))
    write(out/'control-key.json',dict(answers=answers,seed=14168))
    cards=[]
    for pair in pairs:
        number=pair['id']
        cards.append(f'<section><h2>Pair {number}</h2><div><figure><img src="{pair["A"]}" alt="Pair {number} A"><figcaption>A</figcaption></figure><figure><img src="{pair["B"]}" alt="Pair {number} B"><figcaption>B</figcaption></figure></div><label>My preference <select data-pair="{number}"><option value="">Unvoted</option><option>A</option><option>B</option><option>tie</option></select></label></section>')
    (out/'taste-review.html').write_text('''<!doctype html><meta charset="utf-8"><title>Original sprite preference review</title>
<style>body{background:#142330;color:#e5eef4;font:16px system-ui;max-width:850px;margin:30px auto}section{padding:20px;margin:18px 0;background:#203747}section>div{display:flex;gap:24px}figure{margin:0}img{width:192px;height:192px;image-rendering:pixelated;background:#647383}select,button{font:inherit;padding:8px}h2{font-size:18px}</style>
<h1>Original sprite preference review</h1><p>Watch each pair. Which would you prefer in this game? Choose A, B, or tie. Leave any uncertain pair unvoted. This records your taste separately from technical screening.</p>
'''+''.join(cards)+'''<button id="save">Download my votes</button><p>No votes are sent anywhere. No score is inferred from an unanswered pair.</p>
<script>document.getElementById('save').onclick=()=>{const votes=Array.from(document.querySelectorAll('select')).filter(e=>e.value).map(e=>({pair:Number(e.dataset.pair),choice:e.value}));const blob=new Blob([JSON.stringify({axis:'user_taste',votes,wilson_lower_bound:null},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='taste-votes.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};</script>''',encoding='utf-8')
    return dict(pairs=8,panel_status='pending',user_status='pending')
