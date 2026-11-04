"""Rebuild both demos from repository video, music and retained BiRefNet mattes.

Run from any directory with the normal project Python. No optional inference packages
are required, unless --rematte is requested. All writes stay under wow/fx/demo.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import numpy as np
from PIL import Image, ImageSequence

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
sys.path.insert(0,str(REPO/'scripts'))
from media_runtime import executable
from fx_render import render, preview
from gif_pipeline import encode, verify, browser_gif_timing


def prepare(work, rematte=False):
    work.mkdir(parents=True,exist_ok=True)
    session = None
    if rematte:
        os.environ['NUMBA_DISABLE_JIT']='1'
        os.environ.setdefault('OMP_NUM_THREADS','2')
        from rembg import new_session, remove
        session = new_session('birefnet-general', providers=['CPUExecutionProvider'])
    for tag,segment,closing in [('a','01','04'),('b','03','05')]:
        for kind,number in [('opening',segment),('closing',closing)]:
            source=REPO/f'examples/neon-zen-pv/segment-{number}/generation/source.mp4'
            folder=work/f'{kind}-{tag}';(folder/'frames').mkdir(parents=True,exist_ok=True)
            subprocess.run([executable('ffmpeg'),'-v','error','-y','-i',str(source),'-t','6',
                            '-vf','fps=25,scale=640:360','-start_number','0',str(folder/'frames/%05d.png')],check=True)
            files=sorted((folder/'frames').glob('*.png'))
            (folder/'manifest.json').write_text(json.dumps({'durations_ms':[40]*len(files),
                'source':str(source.relative_to(REPO)),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}))
        if rematte:
            with Image.open(ROOT/f'assets/freeze-{tag}.png') as source:
                started=time.perf_counter()
                rgba=source.convert('RGBA');rgba.putalpha(remove(source.convert('RGB'),session=session,only_mask=True))
                rgba.save(ROOT/f'assets/matte-{tag}.png')
                print(f'Matted {tag}: {time.perf_counter()-started:.2f}s',flush=True)
        # Fixed framing of this single freeze, with real source RGB and soft model alpha.
        with Image.open(ROOT/f'assets/matte-{tag}.png') as im:
            subject=im.convert('RGBA');box=subject.getbbox();subject=subject.crop(box)
            factor=180/subject.height
            subject=subject.resize((round(subject.width*factor),180),Image.Resampling.LANCZOS)
            canvas=Image.new('RGBA',(640,360));canvas.alpha_composite(subject,((640-subject.width)//2,90))
            canvas.save(work/f'card-{tag}.png')
        shutil.copy2(ROOT/f'assets/freeze-{tag}.png',work/f'plate-{tag}.png')


def plan(tag,work):
    relative=work.relative_to(ROOT).as_posix()
    return {'beatmap':'beats.json','fps':25,
        'music':{'file':'../../../examples/neon-zen-pv/soundtrack.flac','in_ms':0,'fade_in_ms':100,'fade_out_ms':360},
        'segments':[
            {'type':'animation','manifest':f'{relative}/opening-{tag}/manifest.json','in_ms':0,'out_ms':2920,'end_beat':8},
            {'type':'still','image':f'{relative}/card-{tag}.png','end_beat':16,'transition':{'name':'flash_cut','duration_ms':120}},
            {'type':'animation','manifest':f'{relative}/closing-{tag}/manifest.json','in_ms':0,'out_ms':1460,'end_beat':20,'transition':{'name':'whip_pan','duration_ms':320}},
            {'type':'animation','manifest':f'{relative}/opening-{tag}/manifest.json','in_ms':3200,'out_ms':5020,'end_beat':25,'transition':{'name':'hex_shutter','duration_ms':320}}],
        'effects':[
            {'name':'beat_bounce','stage':'source','start_beat':8,'end_beat':16,'amount':{'on':'beats','indices':list(range(8,16)),'decay_ms':240,'curve':'ease_out'},'translate_px':20,'rotation_deg':-3,'scale':1.06},
            {'name':'cutout_card','stage':'source','start_beat':8,'end_beat':16,'border_px':3,'shadow_px':8,'shadow_blur':5,'background':f'{relative}/plate-{tag}.png','darken':.55,'blur':12},
            {'name':'halation','amount':.16,'radius':3},
            {'name':'grade','sat':1.06,'temp':.01,'gain':1.03},
            {'name':'flash_white','start_beat':1,'end_beat':8,'amount':{'on':'beats','indices':[2,6],'decay_ms':130,'curve':'ease_out','max':.65}},
            {'name':'zoom_punch','start_beat':16,'end_beat':20,'scale':1.07,'amount':{'on':'beats','indices':[17,18,19],'decay_ms':200}},
            {'name':'zoom_punch','start_beat':20,'end_beat':25,'scale':1.09,'amount':{'on':'beats','indices':[21,22,23,24],'decay_ms':260}}]}


def write_plan(data,target):
    lines=['{','  "beatmap": "beats.json", "fps": 25,','  "music": '+json.dumps(data['music'])+',','  "segments": [']
    lines+=['    '+json.dumps(s)+(',' if i<len(data['segments'])-1 else '') for i,s in enumerate(data['segments'])]
    lines+=['  ],','  "effects": [']
    lines+=['    '+json.dumps(e)+(',' if i<len(data['effects'])-1 else '') for i,e in enumerate(data['effects'])]
    target.write_text('\n'.join(lines+['  ]','}'])+'\n')


def export_preview(out, gif):
    """Retain 12.5fps cadence; choose the largest preview under the byte budget."""
    m=json.loads((out/'manifest.json').read_text())
    for width in (360,320,288,256,240):
        frames=[];times=[];pending=0
        for i,duration in enumerate(m['durations_ms']):
            if pending==0:
                with Image.open(out/'frames'/f'{i:05d}.png') as im:
                    frame=im.convert('RGBA').resize((width,round(width*9/16)),Image.Resampling.LANCZOS)
            pending+=duration
            if pending>=80 or i==len(m['durations_ms'])-1:
                frames.append(frame);times.append(pending);pending=0
        encode(frames,times,gif)
        if gif.stat().st_size<=3_000_000:
            return {'gif_bytes':gif.stat().st_size,'gif_width':width,'gif':verify(gif,frames,times)}
    raise RuntimeError('GIF preview exceeds 3 MB')


def build(prepare_only=False,rematte=False):
    work=ROOT/'work/round1';prepare(work,rematte)
    reports={}
    for tag in ('a','b'):
        file=ROOT/('plan.json' if tag=='a' else 'plan-b.json');write_plan(plan(tag,work),file)
        if prepare_only:continue
        out=work/f'master-{tag}-{time.time_ns()}';started=time.perf_counter()
        render(file,out,('png','mp4'))
        name='demo' if tag=='a' else 'demo-b';shutil.copy2(out/'animation.mp4',ROOT/f'{name}.mp4')
        m=json.loads((out/'manifest.json').read_text())
        gif_report=export_preview(out,ROOT/f'{name}.gif')
        reports[tag]={'wall_seconds':time.perf_counter()-started,'master':str(out.relative_to(ROOT)),
                      **gif_report,'render':m['render']}
        (ROOT/f'manifest-{tag}.json').write_text(json.dumps(m,indent=2))
    if not prepare_only:
        preview(ROOT/'preview.png',ROOT/'assets/freeze-a.png')
        (ROOT/'build-results.json').write_text(json.dumps(reports,indent=2))
        print(json.dumps(reports,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--rematte',action='store_true')
    args=ap.parse_args();build(args.prepare_only,args.rematte)
