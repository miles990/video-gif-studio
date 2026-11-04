"""Serial fix-round evidence; scratch media lives only in the OS temp directory.

Run with the project's Python and FFmpeg on PATH. Output artifacts are retained
under --out (default wow/fx). No model inference, downloads or network access.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from captions import prepare,CaptionRenderer
from reframe import plan_path,transform
from fx.effects.camera import camera_move,whip_peak_ms,motion
from fx import Context
from delivery import settings,probe
from beat_layers import layers
from fx_render import render
from qa_media import qa
from media_runtime import executable


def background(size,kind=0):
    w,h=size;yy,xx=np.indices((h,w));a=np.empty((h,w,4),np.uint8);a[...,3]=255
    if kind==0:
        a[...,:3]=np.stack((60+(xx//24%2)*120,50+(yy//40%2)*130,80+(xx+yy)%100),axis=-1)
    elif kind==1:
        a[...,:3]=(((xx//16+yy//16)%2)*255)[...,None]
    elif kind==2:
        a[...,:3]=np.random.default_rng(42).integers(0,256,(h,w,3),dtype=np.uint8)
    else:
        a[...,:3]=np.stack((50+xx*180//w,70+yy*130//h,70+(xx//30%2)*100),axis=-1)
    return Image.fromarray(a)


def person(image,box):
    a,b,c,d=box;draw=ImageDraw.Draw(image);bw=c-a;bh=d-b
    draw.ellipse((a+bw*.25,b,c-bw*.25,b+bh*.22),fill='#FBBE89')
    draw.rectangle((a,b+bh*.23,c,b+bh*.66),fill='#F34258')
    draw.rectangle((a+bw*.1,b+bh*.66,a+bw*.43,d),fill='#58E5F1')
    draw.rectangle((a+bw*.57,b+bh*.66,c-bw*.1,d),fill='#58E5F1')


def v_walk_measure():
    """Acceptance-4 V-WALK: 100 source frames, circle r=40 on 640x360."""
    boxes=[]
    for i in range(100):
        x=40+5.6*i;y=180+30*np.sin(2*np.pi*i/50)
        boxes.append([x-40,y-40,x+40,y+40])
    tracking=plan_path(boxes,(640,360),(270,480));ratios=[];black=[]
    for box,record in zip(boxes,tracking['path']):
        source=Image.new('RGBA',(640,360),(60,90,120,255));ImageDraw.Draw(source).ellipse(box,fill=(255,20,20,255))
        before=np.asarray(source);after=np.asarray(transform(source,record,(270,480)))
        ratios.append(float(np.count_nonzero((after[...,0]>200)&(after[...,1]<50))/(np.count_nonzero((before[...,0]>200)&(before[...,1]<50))*(480/360)**2)))
        black.append(float(np.mean(np.max(after[...,:3],axis=2)<5)))
    return dict(frames=100,source_size=[640,360],measurement_size=[270,480],coverage=sum(not r['needs_review'] for r in tracking['path'])/100,min_rendered_subject_area_ratio=min(ratios),max_black_fraction=max(black),headroom_fraction=min(r['subject_bbox'][1]/(r['subject_bbox'][3]-r['subject_bbox'][1]) for r in tracking['path']))


def run(out):
    out.mkdir(parents=True,exist_ok=True)
    cfg=settings((1080,1920),platform='tiktok');tile=(270,480)
    sheet=Image.new('RGB',(1080,4*520),'#111827');draw=ImageDraw.Draw(sheet)
    report={'scope':'Builder offline and decoded render evidence; independent P1 acceptance remains pending','reframe':{},'captions':[]}
    report['reframe']['v_walk']=v_walk_measure()
    words=[dict(text='MAKE ',start_ms=0,end_ms=400),dict(text='IT ',start_ms=400,end_ms=700),dict(text='MOVE!',start_ms=700,end_ms=1300)]
    for i,preset in enumerate(('pop','typewriter','clean','bounce')):
        data=prepare(dict(words=words,style=dict(preset=preset,words_per_line=16)),ROOT,True)
        renderer=CaptionRenderer(data,cfg['size'],cfg['safe_zone'])
        boxes=[]
        for row,t in enumerate((300,900)):
            frame=renderer.overlay(background(cfg['size'],i),t)
            sheet.paste(frame.convert('RGB').resize(tile),(i*270,row*520+30))
            draw.text((i*270+10,row*520+8),f'{preset} / {t} ms',fill='white')
            boxes.append(renderer.overlay(Image.new('RGBA',cfg['size']),t).getbbox())
        report['captions'].append(dict(preset=preset,ink_boxes=boxes,font=data['style']['font']))
    for i,(bw,bh) in enumerate(((90,260),(360,850))):
        boxes=[[100+370*k/30,100,100+370*k/30+bw,100+bh] for k in range(110)]
        tracking=plan_path(boxes,(1920,1080));covered=0;blacks=[]
        for k,r in enumerate(tracking['path']):
            a,b,c,d=r['subject_bbox'];covered+=a>=-1e-6 and b>=0 and c<=1080+1e-6 and d<=1920+1e-6
            frame=background((1920,1080),3);person(frame,boxes[k]);portrait=transform(frame,r,(270,480))
            blacks.append(float(np.mean(np.max(np.asarray(portrait)[...,:3],axis=2)<5)))
            if k in (0,109):
                col=i*2+int(k>0);sheet.paste(portrait.convert('RGB'),(col*270,1070))
                draw.text((col*270+10,1048),f'{"small" if i==0 else "large"} / f{k}',fill='white')
        centers=np.array([r['crop'][:2] for r in tracking['path']])*1920/1080
        report['reframe']['small' if i==0 else 'large']=dict(frames=len(boxes),speed_source_px_s=370,coverage=covered/len(boxes),max_black_fraction=max(blacks),max_step_output_px=float(np.linalg.norm(np.diff(centers,axis=0),axis=1).max()),max_acceleration_output_px=float(np.linalg.norm(np.diff(centers,n=2,axis=0),axis=1).max()))
    base=background((1080,1920),3);person(base,(390,250,690,1450));a=np.asarray(base)
    for i,t in enumerate((0,1000/30,100,160)):
        frame=Image.fromarray(camera_move(a,t,Context(1080,1920,fps=30),move='whip'))
        sheet.paste(frame.convert('RGB').resize(tile),(i*270,1590));draw.text((i*270+10,1568),f'whip / {t:.1f} ms',fill='white')
    report['whip']=dict(end_frame_equal=bool(np.array_equal(camera_move(a,160,Context(1080,1920,fps=30),move='whip'),a)),whoosh_peak_ms=whip_peak_ms(),max_shift_per_frame=float(max(abs(np.diff([motion('whip',k*1000/30)[1] for k in range(6)])))))
    sheet.save(out/'p1-fix-contact.png')
    with tempfile.TemporaryDirectory(prefix='p1-fix-') as tmp:
        root=Path(tmp);beatmap=dict(duration_ms=8000,beats_ms=list(range(0,8000,500)),downbeats_ms=list(range(0,8000,2000)))
        (root/'beats.json').write_text(json.dumps(beatmap))
        for i in range(4): background((1080,1920),i).save(root/f'{i}.png')
        caption_words=json.loads((ROOT/'tests/fixtures/live/whisper-raw-en.json').read_text())
        plan=dict(experimental=True,beatmap='beats.json',cut_density='high',sfx='auto',segments=[dict(type='still',image=f'{i}.png',duration_ms=2000) for i in range(4)],captions=dict(words=caption_words['words'],style='pop'),effects=[dict(move='whip',start_ms=1800,end_ms=1960)])
        path=root/'plan.json';path.write_text(json.dumps(plan))
        render(path,root/'demo',('mp4',),platform='tiktok')
        video=root/'demo/animation.mp4';manifest=root/'demo/manifest.json'
        quality=qa(video,root/'qa',timeline=manifest)
        shutil.copyfile(video,out/'p1-fix-demo.mp4')
        shutil.copyfile(manifest,out/'p1-fix-demo-manifest.json')
        shutil.copyfile(root/'qa/report.json',out/'p1-fix-demo-qa.json')
        # Decode actual delivered frames, not only the pre-encoding Pillow raster.
        decoded=Image.new('RGB',(1080,520),'#111827');dd=ImageDraw.Draw(decoded)
        for i,t in enumerate((.9,1.866667,2.9,6.9)):
            raw=subprocess.check_output([executable('ffmpeg'),'-v','error','-ss',str(t),'-i',str(video),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
            frame=Image.frombytes('RGB',(1080,1920),raw);decoded.paste(frame.resize(tile),(270*i,30));dd.text((270*i+10,8),f'decoded {t:.3f}s',fill='white')
        decoded.save(out/'p1-fix-decoded-contact.png')
        report['demo']=dict(stream=next(s for s in probe(video)['streams'] if s['codec_type']=='video'),qa_flashes=next(c for c in quality['checks'] if c['name']=='flashes'),rhythm_ms=quality.get('cut_to_downbeat_median_ms'),rhythm_exclusions=len(quality.get('rhythm_excluded_effect_events',[])))
    beatmap=dict(duration_ms=64000,beats_ms=list(range(0,64000,500)),downbeats_ms=list(range(0,64000,2000)),sections=[dict(start_ms=t) for t in (0,8000,24000,40000,48000,60000)])
    report['density']={d:{'cuts':len(layers(beatmap,cut_density=d)['cuts_ms']),'accents':len(layers(beatmap,cut_density=d)['accents_ms'])} for d in ('low','mid','high')}
    (out/'measurements-p1-fix.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('captions','demo')},indent=2))
    print('Demo flash verdict:',report['demo']['qa_flashes']['level'])


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=ROOT/'wow/fx');run(ap.parse_args().out)
