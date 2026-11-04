"""Prepare repository-owned sources without modifying examples; run from repo root."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
WORK=ROOT/'work'

def character(source, target, start):
    with Image.open(source) as animation:
        frames=[]
        for i in range(start,start+30):
            animation.seek(min(i,animation.n_frames-1));frames.append(animation.convert('RGBA').copy())
    boxes=[im.getbbox() for im in frames];box=(min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes))
    factor=min(280/(box[2]-box[0]),260/(box[3]-box[1]))
    size=(round((box[2]-box[0])*factor),round((box[3]-box[1])*factor))
    (target/'frames').mkdir(parents=True,exist_ok=True)
    for i,im in enumerate(frames):
        sprite=im.crop(box).resize(size,Image.Resampling.LANCZOS)
        canvas=Image.new('RGBA',(640,360));canvas.alpha_composite(sprite,(400-size[0]//2,185-size[1]//2))
        canvas.save(target/'frames'/f'{i:05d}.png')
    (target/'manifest.json').write_text(json.dumps({'durations_ms':[40]*30,'source':str(source),'crop':box,'placement':'fixed union crop; no per-frame recentering'}))

def plate(source, target):
    with Image.open(source) as im:canvas=im.convert('RGBA')
    # Text is a static editorial plate; the renderer performs darkening and blur.
    canvas.save(target)

def plan(character,neon,background):
    return {'beatmap':'../../../examples/neon-zen-pv/music-analysis/beats.json','fps':25,
            'music':{'file':'../../../examples/neon-zen-pv/soundtrack.flac','in_ms':20,'gain_db':0.0,'fade_in_ms':100,'fade_out_ms':500},
            'segments':[
                {'type':'animation','manifest':f'work/{neon}/manifest.json','in_ms':0,'out_ms':2420,'end_beat':4},
                {'type':'still','manifest':f'work/{character}/manifest.json','frame':'first','end_beat':6,'transition':{'name':'flash_cut','duration_ms':240}},
                {'type':'animation','manifest':f'work/{character}/manifest.json','end_beat':8},
                {'type':'animation','manifest':f'work/{neon}/manifest.json','in_ms':2420,'out_ms':4790,'end_beat':12,'transition':{'name':'whip_pan','duration_ms':320}}],
            'effects':[
                {'name':'beat_bounce','stage':'source','start_ms':2930,'end_ms':5850,'amount':{'on':'beats','indices':[4,6],'decay_ms':260,'curve':'ease_out'},'translate_px':12,'rotation_deg':-3,'scale':1.04},
                {'name':'cutout_card','stage':'source','start_ms':2930,'end_ms':5850,'border_px':4,'shadow_px':8,'shadow_blur':5,'background':f'work/{background}','darken':.38,'blur':5},
                {'name':'halation','amount':.22,'radius':3},
                {'name':'grade','sat':1.06,'temp':.012,'gain':1.03},
                {'name':'flash_white','start_ms':2700,'end_ms':6100,'amount':{'on':'beats','indices':[4,8],'attack_ms':25,'decay_ms':160,'curve':'ease_out','max':.78}}]}

if __name__=='__main__':
    character(REPO/'examples/chibi-running-dash/final.apng',WORK/'chibi',18)
    character(REPO/'examples/robot-wave-no-reference/final.gif',WORK/'robot',25)
    for tag in ('a','b'):plate(WORK/f'neon-{tag}/frames/00040.png',WORK/f'plate-{tag}.png')
    for filename,data in [('plan.json',plan('chibi','neon-a','plate-a.png')),('plan-b.json',plan('robot','neon-b','plate-b.png'))]:
        # One object per line makes the complete reproducible plan readable in 19 lines.
        lines=['{', '  "beatmap": '+json.dumps(data['beatmap'])+', "fps": 25,', '  "music": '+json.dumps(data['music'])+',','  "segments": [']
        lines += ['    '+json.dumps(s)+(',' if i<len(data['segments'])-1 else '') for i,s in enumerate(data['segments'])]
        lines += ['  ],','  "effects": [']
        lines += ['    '+json.dumps(e)+(',' if i<len(data['effects'])-1 else '') for i,e in enumerate(data['effects'])]
        lines += ['  ]','}'];(ROOT/filename).write_text('\n'.join(lines)+'\n')
