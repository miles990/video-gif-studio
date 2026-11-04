"""Serial offline P0 benchmark. Samples the complete process tree every 50 ms.

python wow/fx/benchmark_p0.py --out wow/fx/benchmark-p0.json
Use --quick for the small offline regression test. No optional model dependencies.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from media_runtime import executable
from delivery import probe
from process_memory import tree_memory, psutil


def fixture(root, size, seconds, stable=False):
    root.mkdir(parents=True, exist_ok=True)
    frames=root/'frames';frames.mkdir(exist_ok=True)
    w,h=size
    # A moving deterministic textured gradient. Sources repeat each second;
    # film_grain changes at every output frame throughout the film.
    rng=np.random.default_rng(19)
    tile=rng.integers(0,45,(64,64,1),dtype=np.uint8)
    yy,xx=np.indices((h,w))
    gradient=np.stack((30+xx*130//w,30+yy*130//h,60+(xx+yy)*80//(w+h)),axis=2)
    for k in range(30):
        arr=np.uint8(gradient+tile[(yy+k*3)%64,(xx+k*5)%64])
        Image.fromarray(arr).save(frames/f'{k:05d}.png',compress_level=1)
    times=[30,40,30]*10
    (root/'source.json').write_text(json.dumps({'durations_ms':times}))
    (root/'beats.json').write_text(json.dumps({'beats_ms':list(range(0,seconds*1000,500))}))
    plan={'segments':[{'type':'loop','manifest':'source.json','duration_ms':seconds*1000}],
          'beatmap':'beats.json','seed':42,'effects':[
              {'name':'zoom_punch','amount':{'on':'beats','decay_ms':200}},
              {'name':'rgb_split','distance':4}, {'name':'film_grain','amount':.025}]}
    if stable:
        plan['effects']=[{'name':'zoom_punch','amount':{'on':'beats','decay_ms':200}},
                         {'name':'grade','sat':.9,'gain':1.03},{'name':'halation','amount':.2}]
    (root/'plan.json').write_text(json.dumps(plan))
    return root/'plan.json'


def measure(plan, out, proxy=False, platform_name=None):
    cmd=[sys.executable,str(ROOT/'scripts/fx_render.py'),str(plan),'--out',str(out),
         '--formats','mp4','--no-user-fx','--experimental']
    if proxy:cmd+=['--proxy']
    if platform_name:cmd+=['--platform',platform_name]
    samples=[];peak=0;peak_wset=0
    started=time.perf_counter()
    with tempfile.TemporaryFile() as log:
        proc=subprocess.Popen(cmd,stdout=log,stderr=log,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        while proc.poll() is None:
            rss,wset=tree_memory(proc.pid)
            peak=max(peak,rss);peak_wset=max(peak_wset,wset)
            files=list(out.parent.rglob('*.mp4'))
            # Source fixtures contain PNG only; this trial has its own output parent.
            size=sum(f.stat().st_size for f in files if f.exists())
            samples.append([round(time.perf_counter()-started,3),rss,size])
            time.sleep(.05)
        elapsed=time.perf_counter()-started
        if proc.returncode:
            log.seek(0);raise RuntimeError(log.read().decode(errors='replace'))
    movie=out/'animation.mp4'
    data=probe(movie);v=next(s for s in data['streams'] if s['codec_type']=='video')
    count=int(v['nb_frames']);final=movie.stat().st_size
    halfway=min(samples,key=lambda row:abs(row[0]-elapsed/2))
    return dict(seconds=elapsed,fps=count/elapsed,frames=count,size=[v['width'],v['height']],
        peak_rss_bytes=peak,peak_wset_bytes=peak_wset,peak_bytes=max(peak,peak_wset),
        final_bytes=final,halfway_bytes=halfway[2],halfway_fraction=halfway[2]/final,
        samples=samples,proxy=proxy,command=cmd)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--quick',action='store_true');ap.add_argument('--stable',action='store_true');a=ap.parse_args()
    result={'machine':platform.platform(),'processor':platform.processor(),'python':sys.version,
        'ffmpeg':subprocess.check_output([executable('ffmpeg'),'-version']).decode().splitlines()[0],
        'method':'50ms sum parent + recursive children RSS; Windows also sum peak_wset, report larger; '+('psutil' if psutil else 'Win32 Toolhelp32Snapshot / GetProcessMemoryInfo'),
        'effects':['zoom_punch','grade','halation'] if a.stable else ['zoom_punch','rgb_split','film_grain'],
        'runs':[]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    trials=[((192,320),2,False,None),((192,320),6,False,None)] if a.quick else [
        ((1080,1920),10,False,'tiktok'),((1080,1920),30,False,'tiktok'),
        ((1080,1920),30,False,'tiktok'),((1080,1920),30,False,'tiktok'),
        ((720,1280),30,False,None),((1080,1920),30,True,'tiktok')]
    if a.stable:trials=[((1080,1920),10,False,'tiktok'),((1080,1920),30,False,'tiktok'),((720,1280),30,False,None),((1080,1920),30,True,'tiktok')]
    with tempfile.TemporaryDirectory(dir=ROOT) as temp:
        for i,(size,seconds,proxy,preset) in enumerate(trials):
            base=Path(temp)/str(i);plan=fixture(base/'input',size,seconds,a.stable)
            output=base/'output';output.mkdir()
            run=measure(plan,output/'render',proxy,preset)
            run.update(duration_seconds=seconds,source_size=list(size));result['runs'].append(run)
            a.out.write_text(json.dumps(result,indent=2))
            print(json.dumps({k:v for k,v in run.items() if k not in ('samples','command')}),flush=True)
    return result


if __name__=='__main__': main()
