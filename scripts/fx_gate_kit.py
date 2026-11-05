#!/usr/bin/env python3
"""Render default FX evidence and objective measurements, never aesthetic scores.

Serial, bounded-memory gate kit. All artifacts default to an OS temporary directory.
MP4 previews composite RGBA on a checker; alpha checks operate on original RGBA.
Optional parallax needs onnxruntime and Small weights, or records a resource error.
"""
import argparse
from collections import deque
from datetime import datetime
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import warnings
import wave
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

from fx import Context, EFFECTS, TRANSITIONS
from fx.core import premultiply, straight
from fx.transitions.gl_ports import PORT_NAMES
from media_runtime import executable
from qa_media import media_info, picture, analyse_picture

ROOT=Path(__file__).resolve().parents[1]
FPS=24
COUNT=48
LIMIT=300_000_000
PRESERVE_ALPHA={'flash_white','grade','halation','rgb_split','film_grain','vignette',
                'light_leak','dust_scratches','invert_flash','black_flash','posterize','halftone'}


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def beat_audio(path):
    rate=24000;t=np.arange(rate*2)/rate;phase=t%.5
    signal=.3*np.sin(2*np.pi*880*phase)*np.exp(-phase*90)*(phase<.08)
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate)
        stream.writeframes(np.rint(signal*32767).astype('<i2').tobytes())


def source_frames(source,size):
    w,h=size
    result=subprocess.run([executable('ffmpeg'),'-v','error','-i',str(source),'-t','2',
        '-vf',f'fps={FPS},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}',
        '-frames:v',str(COUNT),'-f','rawvideo','-pix_fmt','rgba','-'],capture_output=True)
    if result.returncode:raise ValueError(result.stderr.decode(errors='replace'))
    values=np.frombuffer(result.stdout,np.uint8)
    if values.size!=COUNT*w*h*4:raise ValueError('Demo source must supply 2 seconds of frames: '+str(source))
    return values.reshape(COUNT,h,w,4)


def cutout_frames(path,size):
    # Retained repo matte, gently translated to expose temporal trails.
    w,h=size
    with Image.open(path) as source:
        source=source.convert('RGBA');box=source.getbbox()
        if box is None:raise ValueError('Empty cutout: '+str(path))
        subject=ImageOps.contain(source.crop(box),(round(w*.64),round(h*.72)))
    canvas=Image.new('RGBA',size);canvas.alpha_composite(subject,((w-subject.width)//2,(h-subject.height)//2))
    base=np.asarray(canvas,dtype=np.float32)/255
    result=[]
    for i in range(COUNT):
        dx=round(w*.06*np.sin(2*np.pi*i/COUNT))
        moved=cv2.warpAffine(premultiply(base),np.float32([[1,0,dx],[0,1,0]]),size)
        result.append(np.rint(np.clip(straight(moved),0,1)*255).astype(np.uint8))
    return np.stack(result)


def checker(frame):
    h,w=frame.shape[:2];y,x=np.indices((h,w));bg=np.where((x//16+y//16)%2,56,36).astype(np.float32)
    alpha=frame[...,3:4].astype(np.float32)/255
    return np.rint(frame[...,:3].astype(np.float32)*alpha+bg[...,None]*(1-alpha)).clip(0,255).astype(np.uint8)


def edge_metrics(frame):
    """Border gradient ratios detect abrupt seams and replicated stretch streaks.

    Heuristics only: intentional graphic boundaries can trigger a flag. Report
    raw ratios and frame indices; never suppress flags by effect name.
    """
    rgb=frame[...,:3]*frame[...,3:4]
    gx=np.abs(np.diff(rgb,axis=1)).mean(axis=2);gy=np.abs(np.diff(rgb,axis=0)).mean(axis=2)
    seam=0.;stretch=0.
    for gradients in (gx,gx[:,::-1],gy.T,gy[::-1].T):
        if gradients.shape[1]<12:continue
        edge=float(gradients[:,:2].mean());inside=float(gradients[:,3:12].mean())
        seam=max(seam,edge/(inside+.002))
        stretch=max(stretch,inside/(edge+.002) if inside>.015 else 0)
    return seam,stretch


def invoke(kind,spec,a,b,i,ctx,resources):
    t=i*1000/FPS;ctx.t_ms=t
    if kind=='transition':return spec['function'](a,b,i/(COUNT-1),ctx)
    return spec['function'](a,t,ctx,**resources)


def render_case(kind,name,spec,source,size,material,out,audio,resources):
    w,h=size;label=f'{material}-{w}x{h}';target=out/(label+'.mp4')
    ctx=Context(w,h,fps=FPS,beats_ms=[0,500,1000,1500],downbeats_ms=[0],seed=19)
    history=deque(maxlen=spec['history']);times=deque(maxlen=spec['history'])
    hashes=[hashlib.sha256(),hashlib.sha256()];thumbs=[];black=[];alpha_errors=[];seams=[];streaks=[]
    max_seam=max_stretch=alpha_delta=0.;hidden_delta=0.;messages=set()
    command=[executable('ffmpeg'),'-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}',
        '-r',str(FPS),'-i','-','-i',str(audio),'-c:v','libx264','-threads','1','-preset','veryfast',
        '-crf','25','-maxrate','700k','-bufsize','1400k','-pix_fmt','yuv420p','-c:a','aac','-b:a','48k',
        '-t','2','-movflags','+faststart',str(target)]
    with subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE) as encoder:
        try:
            for i,raw in enumerate(source):
                a=raw.astype(np.float32)/255
                b=np.ascontiguousarray(source[(i+COUNT//2)%COUNT,:,::-1]).astype(np.float32)/255
                # A visibly distinct second shot without adding another treatment.
                ctx.history=tuple(reversed(history));ctx.history_times_ms=tuple(reversed(times))
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    output=invoke(kind,spec,a,b,i,ctx,resources)
                messages.update(str(w.message) for w in caught)
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore');repeat=invoke(kind,spec,a,b,i,ctx,resources)
                hashes[0].update(output.tobytes());hashes[1].update(repeat.tobytes())
                if output.shape!=a.shape or not np.isfinite(output).all() or np.min(output[...,3])<0 or np.max(output[...,3])>1:alpha_errors.append(i)
                if name in PRESERVE_ALPHA:
                    delta=float(np.max(np.abs(output[...,3]-a[...,3])));alpha_delta=max(alpha_delta,delta)
                    if delta>1/255:alpha_errors.append(i)
                if material=='opaque' and i in (0,24,47):
                    delta=float(np.max(np.abs(output[...,3]-1)));alpha_delta=max(alpha_delta,delta)
                    if delta>1/255:alpha_errors.append(i)
                if i in (0,24,47) and material=='rgba':
                    hidden=a.copy();hidden[hidden[...,3]==0,:3]=[1,0,1]
                    hidden_b=b.copy();hidden_b[hidden_b[...,3]==0,:3]=[0,1,0]
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore');probe=invoke(kind,spec,hidden,hidden_b,i,ctx,resources)
                    hidden_delta=max(hidden_delta,float(np.max(np.abs(premultiply(output)-premultiply(probe)))))
                visible=output[...,3]>.01
                luminance=output[...,:3]@np.array([.299,.587,.114],np.float32)
                if not np.any(visible) or float(luminance[visible].mean())<5/255:black.append(i)
                seam,stretch=edge_metrics(output);max_seam=max(max_seam,seam);max_stretch=max(max_stretch,stretch)
                if seam>6:seams.append(i)
                if stretch>8:streaks.append(i)
                rgb=checker(np.rint(output*255).clip(0,255).astype(np.uint8))
                encoder.stdin.write(rgb.tobytes())
                if i in (0,12,24,36,47):thumbs.append(Image.fromarray(rgb))
                history.append(a);times.append(i*1000/FPS)
            encoder.stdin.close();error=encoder.stderr.read();code=encoder.wait()
            if code:raise ValueError('FFmpeg: '+error.decode(errors='replace'))
        except BaseException:
            encoder.kill();encoder.wait();raise
    info=media_info(target,FPS);edges=np.r_[0,np.cumsum(info['durations'])]
    stats=picture(target,info,edges);qa=analyse_picture(stats,edges)
    flicker=next(c for c in qa if c['name']=='flashes')
    if hidden_delta>1/255:alpha_errors.append('hidden RGB leak')
    result=dict(material=material,size=list(size),clip=target.name,frames=COUNT,duration_seconds=2,
        alpha=dict(level='FAIL' if alpha_errors else 'PASS',events=alpha_errors,max_preserved_delta=alpha_delta,hidden_rgb_delta=hidden_delta),
        edges=dict(level='WARN' if seams or streaks else 'PASS',seam_frames=seams,stretch_frames=streaks,max_seam_ratio=max_seam,max_stretch_ratio=max_stretch),
        black=dict(level='FAIL' if black else 'PASS',frames=black),flicker=flicker,
        determinism=dict(level='PASS' if hashes[0].digest()==hashes[1].digest() else 'FAIL',sha256=hashes[0].hexdigest(),repeat_sha256=hashes[1].hexdigest()),
        qa_media=qa,warnings=sorted(messages))
    return result,thumbs


def contact(rows,path):
    board=Image.new('RGB',(1000,len(rows)*220),'#101820');draw=ImageDraw.Draw(board)
    for row,(label,images) in enumerate(rows):
        draw.text((10,row*220+5),label,fill='white')
        for col,im in enumerate(images):
            im=ImageOps.contain(im,(196,184));board.paste(im,(col*200+(200-im.width)//2,row*220+25))
            draw.text((col*200+6,row*220+205),f'{(0,12,24,36,47)[col]/FPS:.2f}s',fill='white')
    board.save(path,quality=88)


def benchmark(kind,spec,frame,resources):
    a=cv2.resize(frame,(1280,720)).astype(np.float32)/255;b=a[:,::-1].copy()
    ctx=Context(1280,720,fps=FPS,beats_ms=[0,500,1000,1500],seed=19,history=(a.copy(),)*spec['history'])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');invoke(kind,spec,a,b,24,ctx,resources)
        samples=[]
        for _ in range(10):
            start=time.perf_counter();invoke(kind,spec,a,b,24,ctx,resources);samples.append((time.perf_counter()-start)*1000)
    return dict(size=[1280,720],dtype='float32',samples_ms=samples,median_ms=float(np.median(samples)),warmup=1,includes='public effect call; warm resource/cache; excludes decode/encode')


def write_index(out,report):
    cards=[]
    for item in report['items']:
        slug=item['id'].replace(':','-');links=' '.join(f'<a href="{slug}/{c["clip"]}">{c["material"]} {c["size"]}</a>' for c in item['cases'])
        flags=sum(c[k]['level']!='PASS' for c in item['cases'] for k in ('alpha','edges','black','flicker','determinism'))
        timing=item.get('benchmark',{}).get('median_ms')
        measured=f'{timing:.2f}' if timing is not None else 'unavailable'
        cards.append(f'<article><h2>{html.escape(item["id"])}</h2><p>{item["status"]} · {flags} check flags · {measured} ms/frame at 720p</p>'
            + (f'<a href="{slug}/contact.jpg"><img src="{slug}/contact.jpg" loading="lazy"></a>' if item['cases'] else '')
            +f'<p>{links}</p><pre>{html.escape(item.get("error",""))}</pre></article>')
    page='<!doctype html><meta charset="utf-8"><title>FX default gate evidence</title><style>body{background:#0d141e;color:#eef1f5;font:16px system-ui;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:20px}article{background:#182331;padding:16px;border-radius:12px}img{width:100%}a{color:#8be0ff;margin-right:12px}pre{white-space:pre-wrap}</style>'
    page+='<h1>Default FX review kit</h1><p>2 seconds · 24 fps · two materials · both aspect ratios · shared 120 BPM accent. Click a clip to play with sound.</p><p>Measurements are heuristics, not aesthetic scores. Intentional flashes, black dips and graphic edges remain flagged. RGBA previews are composited; alpha measurements use the uncomposited frames. Independent review is pending.</p><p><a href="gate-auto.json">Machine measurements and provenance</a></p><main>'+''.join(cards)+'</main>'
    (out/'index.html').write_text(page,encoding='utf-8')


def run(out,items=None,models=None):
    out=Path(out).resolve()
    if out==ROOT or ROOT in out.parents:raise ValueError('Gate output must be outside the repository')
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new or empty output directory')
    selected=[(kind,name,spec) for kind,registry in (('effect',EFFECTS),('transition',TRANSITIONS)) for name,spec in registry.items() if not items or name in items or f'{kind}:{name}' in items]
    if items:
        known={name for _,name,_ in selected}|{f'{kind}:{name}' for kind,name,_ in selected}
        if set(items)-known:raise ValueError('Unknown items: '+', '.join(sorted(set(items)-known)))
    source=ROOT/'examples/neon-zen-pv/segment-01/generation/source.mp4'
    matte=ROOT/'wow/fx/demo/assets/matte-b.png'
    out.mkdir(parents=True,exist_ok=True);audio=out/'beat.wav';beat_audio(audio)
    report=dict(schema=1,created=datetime.now().isoformat(),command=sys.argv,python=sys.executable,
        environment=dict(platform=platform.platform(),numpy=np.__version__,opencv=cv2.__version__,cpu=platform.processor()),
        source=dict(opaque=str(source.relative_to(ROOT)),opaque_sha256=sha(source),rgba=str(matte.relative_to(ROOT)),rgba_sha256=sha(matte)),
        methodology=dict(defaults='All catalog visual defaults, including experimental; only parallax model/cache resources relocated',
            alpha='Range/finite/shape every frame; exact alpha for colour-only items; opaque coverage and hidden-RGB probes at frames 0,24,47',
            edges='Border normal-gradient ratio >6 seam; inverse ratio >8 stretch with interior gradient >.015; review heuristics',
            flicker='qa_media on decoded MP4, no effect exemptions',determinism='Two complete raw RGBA render hashes',
            black='Visible mean luminance <5/255 or no coverage',aesthetics='No score; independent review required'),items=[])
    # Source buffers are tiny proxies; no whole 720p movie is ever retained.
    materials={(material,size):(source_frames(source,size) if material=='opaque' else cutout_frames(matte,size)) for size in ((480,270),(270,480)) for material in ('opaque','rgba')}
    for kind,name,spec in selected:
        print(f'{kind}:{name}',flush=True);folder=out/f'{kind}-{name}';folder.mkdir()
        item=dict(id=f'{kind}:{name}',status=spec['status'],defaults={k:v['default'] for k,v in spec['params'].items()},
            source=str(Path(spec['source']).relative_to(ROOT)),source_sha256=sha(spec['source']),seed=19,beats_ms=[0,500,1000,1500],cases=[])
        resources={}
        if name=='parallax':
            if models:resources['model']=str(Path(models)/'depth-anything-v2-small.onnx')
            resources['cache']=str(folder/'depth-cache')
        item['resource_overrides']=resources;rows=[]
        try:
            for (material,size),frames in materials.items():
                case,thumbs=render_case(kind,name,spec,frames,size,material,folder,audio,resources)
                item['cases'].append(case);rows.append((f'{material} {size[0]}x{size[1]}',thumbs))
            contact(rows,folder/'contact.jpg')
            benchmark_material='rgba' if name=='multi_cutout' else 'opaque'
            item['benchmark']=benchmark(kind,spec,materials[(benchmark_material,(480,270))][24],resources)
            item['benchmark']['material']=benchmark_material
        except (ValueError,RuntimeError,OSError,cv2.error) as exc:
            item['error']=str(exc);print('  ERROR: '+str(exc),flush=True)
        report['items'].append(item)
        report['total_bytes']=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
        if report['total_bytes']>=LIMIT:raise ValueError('Output reached 300 MB safety budget; use --items in separate runs')
        (out/'gate-auto.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
        write_index(out,report)
    report['total_bytes']=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    (out/'gate-auto.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path(tempfile.gettempdir())/('fx-gate-'+datetime.now().strftime('%Y%m%d-%H%M%S')))
    selection=parser.add_mutually_exclusive_group()
    selection.add_argument('--items',nargs='+',help='Catalog names or effect:name / transition:name')
    selection.add_argument('--gl-transitions',action='store_true',help='Render all 32 experimental P2b gl-transitions ports')
    parser.add_argument('--models',type=Path,default=os.environ.get('VIDEO_GIF_MODELS'),help='Existing Small model directory; no downloads')
    args=parser.parse_args(argv)
    try:
        result=run(args.out,list(PORT_NAMES) if args.gl_transitions else args.items,args.models)
        print(str(args.out.resolve()/'index.html'),flush=True)
        return 2 if any('error' in item for item in result['items']) else 0
    except (ValueError,RuntimeError,OSError) as exc:
        print('fx_gate_kit: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
