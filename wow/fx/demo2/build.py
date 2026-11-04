"""Reproduce a 20-second neon rhythm study. Run from any working directory."""
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
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[2];WORK=ROOT/'work'
sys.path.insert(0,str(REPO/'scripts'));sys.path.insert(0,str(ROOT.parent/'demo'))
from media_runtime import executable
from fx_render import render,preview
from build_demo import export_preview


def prepare():
    WORK.mkdir(parents=True,exist_ok=True)
    for tag,number in [('a','01'),('b','03'),('c','04'),('d','05')]:
        folder=WORK/tag;(folder/'frames').mkdir(parents=True,exist_ok=True)
        source=REPO/f'examples/neon-zen-pv/segment-{number}/generation/source.mp4'
        if not (folder/'manifest.json').is_file():
            subprocess.run([executable('ffmpeg'),'-v','error','-y','-i',str(source),'-t','6','-vf','fps=25,scale=480:270','-start_number','0',str(folder/'frames/%05d.png')],check=True)
            files=sorted((folder/'frames').glob('*.png'))
            (folder/'manifest.json').write_text(json.dumps({'durations_ms':[40]*len(files),'source':str(source.relative_to(REPO)),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}))
    shutil.copy2(ROOT.parent/'demo/beats.json',ROOT/'beats.json')
    with Image.open(ROOT.parent/'demo/assets/freeze-b.png') as im:im.convert('RGBA').resize((480,270)).save(WORK/'freeze.png')


def models():
    from fx.depth import depth_map
    from fx.timewarp import interpolate
    models=Path(os.environ.get('VIDEO_GIF_MODELS','C:/Users/User/.codex/skills/video-gif-studio/.runtime/models'))
    assets=ROOT/'assets';assets.mkdir(exist_ok=True)
    a=np.array(Image.open(WORK/'freeze.png').convert('RGBA'));start=time.perf_counter()
    depth=depth_map(a,str(models/'depth-anything-v2-small.onnx'),str(WORK/'depth'))
    Image.fromarray(np.rint(depth*65535).astype('uint16')).save(assets/'depth-small.png')
    records={'depth_seconds':time.perf_counter()-start,'source':'../demo/assets/freeze-b.png','source_sha256':hashlib.sha256((WORK/'freeze.png').read_bytes()).hexdigest(),
        'depth_model':'onnx-community/Depth-Anything-V2-Small, Apache-2.0','rife_model':'latentdivergence/fixflix-rife-lite, MIT','depth_resolution':[480,270]}
    a=np.array(Image.open(WORK/'a/frames/00020.png').convert('RGBA'));b=np.array(Image.open(WORK/'a/frames/00021.png').convert('RGBA'))
    start=time.perf_counter();out=interpolate(a,b,.5,'rife',model=str(models/'rife_v4.25_lite.onnx'))
    Image.fromarray(out).save(WORK/'rife-midpoint.png');shutil.copy2(WORK/'rife-midpoint.png',assets/'rife-midpoint.png');records['rife_seconds']=time.perf_counter()-start
    (assets/'provenance.json').write_text(json.dumps(records,indent=2));print(records,flush=True)


def plan():
    beat=json.loads((ROOT/'beats.json').read_text())['beats_ms'];accent=[11,19,35,43]
    env={'on':'beats','indices':accent,'decay_ms':160,'curve':'ease_out'}
    result={'beatmap':'beats.json','fps':25,'seed':19,'interpolate':'flow',
      'music':{'file':'../../../examples/neon-zen-pv/soundtrack.flac','fade_in_ms':100,'fade_out_ms':700},
      'segments':[
        {'type':'animation','manifest':'work/a/manifest.json','end_beat':8,'ramp':{'into_beat':8,'slow':.35,'hit_ms':240}},
        {'type':'animation','manifest':'work/b/manifest.json','in_ms':0,'out_ms':2920,'end_beat':16},
        {'type':'animation','manifest':'work/c/manifest.json','in_ms':400,'out_ms':3320,'end_beat':24},
        {'type':'still','image':'work/freeze.png','end_beat':32,'transition':{'name':'shape_wipe','shape':'circle','softness':6,'duration_ms':400}},
        {'type':'animation','manifest':'work/d/manifest.json','in_ms':0,'out_ms':2920,'end_beat':40},
        {'type':'animation','manifest':'work/a/manifest.json','in_ms':800,'out_ms':5200,'end_beat':56,'transition':{'name':'luma_wipe','mask':'linear','duration_ms':320}}],
      'effects':[
        {'name':'grade','sat':1.08,'temp':.015,'gain':1.025},
        {'name':'shake','amount':env,'distance':7},
        {'name':'rgb_split','amount':env,'distance':4},
        {'name':'text','start_beat':0,'end_beat':8,'content':'慢一拍','size':46,'x':.75,'y':.78,'color':'FFF4D6','scale':{'on':'beats','indices':[0,4],'min':1,'max':1.08,'decay_ms':180}},
        {'name':'text','start_beat':8,'end_beat':16,'content':'讓光流動','size':42,'x':.5,'y':.83,'color':'FFF4D6'},
        {'name':'split_screen','stage':'source','start_beat':18,'end_beat':24,'panels':{'keyframes':[[beat[18],2],[beat[20]-1,2],[beat[20],4]]}},
        {'name':'parallax','stage':'source','start_beat':24,'end_beat':32,'depth':'assets/depth-small.png','distance':14,'amount':{'keyframes':[[beat[24],0],[beat[32],1]]}},
        {'name':'text','start_beat':26,'end_beat':32,'content':'浮光','size':46,'x':.79,'y':.78,'color':'FFF4D6'},
        {'name':'film_grain','start_beat':40,'end_beat':56,'amount':.018},
        {'name':'light_leak','start_beat':40,'end_beat':56,'amount':.13},
        {'name':'text','start_beat':48,'end_beat':56,'content':'餘韻 / AFTERGLOW','size':29,'y':.83,'color':'FFF4D6'}]}
    (ROOT/'plan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');return result


def comparisons():
    from fx.timewarp import interpolate
    a=np.array(Image.open(WORK/'a/frames/00020.png').convert('RGBA'));b=np.array(Image.open(WORK/'a/frames/00021.png').convert('RGBA'))
    board=Image.new('RGB',(480*2,300*2));draw=ImageDraw.Draw(board);timings={}
    for i,method in enumerate(('none','blend','flow','rife')):
        start=time.perf_counter()
        out=np.array(Image.open(ROOT/'assets/rife-midpoint.png')) if method=='rife' else interpolate(a,b,.5,method)
        timings[method]=1000*(time.perf_counter()-start) if method!='rife' else json.loads((ROOT/'assets/provenance.json').read_text())['rife_seconds']*1000
        x,y=i%2*480,i//2*300;board.paste(Image.fromarray(out).convert('RGB'),(x,y+30));draw.text((x+12,y+8),method,fill='white')
    board.save(ROOT/'interpolation-comparison.jpg');(ROOT/'interpolation-timings.json').write_text(json.dumps(timings,indent=2))


def build():
    if not (ROOT/'assets/depth-small.png').is_file():raise ValueError('Run --models in fx-optdeps once; cached Small depth asset required')
    plan();out=WORK/f'master-{time.time_ns()}';started=time.perf_counter();render(ROOT/'plan.json',out,('png','mp4'))
    shutil.copy2(out/'animation.mp4',ROOT/'demo.mp4');shutil.copy2(out/'manifest.json',ROOT/'manifest.json')
    record=export_preview(out,ROOT/'demo.gif',exposure=160,widths=(240,216,192,160,128));record.update(wall_seconds=time.perf_counter()-started,master=str(out.relative_to(ROOT)))
    (ROOT/'build-results.json').write_text(json.dumps(record,indent=2));preview(ROOT/'preview.png',WORK/'freeze.png');comparisons();print(record,flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--models',action='store_true');ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args()
    prepare()
    if a.models:models()
    elif not a.prepare_only:build()
