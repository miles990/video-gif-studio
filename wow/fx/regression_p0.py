"""Compare raster bytes and explicit legacy MP4 pixels against the worktree base.

Archives tracked scripts to a temporary directory; never checks out or changes Git.
No downloads, optional models, or writes outside this worktree.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]


def worker(scripts, plan, out, current):
    sys.path.insert(0,str(scripts))
    from fx_render import render
    from video_export import export
    render(plan,out,('png','gif','apng'),experimental=True)
    if plan.stem!='demo2':
        if current:render(plan,out/'direct',('mp4',),experimental=True,fps=100)
        else:export(out/'frames',out/'manifest.json',out/'legacy.mp4')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--worker',nargs=4);a=ap.parse_args()
    if a.worker:
        scripts,plan,out,current=a.worker;worker(Path(scripts),Path(plan),Path(out),current=='True');return
    git=['git','-c','safe.directory='+ROOT.as_posix()]
    base=subprocess.check_output([*git,'rev-parse','HEAD'],cwd=ROOT).decode().strip()
    archive=subprocess.check_output([*git,'archive','HEAD','scripts'],cwd=ROOT)
    results={'base_commit':base,'plans':[],'unavailable_plans':['demo3','demo4']}
    sys.path.insert(0,str(ROOT/'scripts'))
    from media_runtime import executable
    with tempfile.TemporaryDirectory(dir=ROOT) as temp:
        p=Path(temp);baseline=p/'base';baseline.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(baseline,filter='data')
        source=p/'source';(source/'frames').mkdir(parents=True)
        for i in range(50):
            yy,xx=np.indices((64,96));rgb=np.stack(((xx*2+i*5)%256,(yy*3+i*7)%256,(xx+yy+i*3)%256),2).astype(np.uint8)
            Image.fromarray(rgb).save(source/'frames'/f'{i:05d}.png')
        (source/'manifest.json').write_text(json.dumps({'durations_ms':[40]*50}))
        (p/'beats.json').write_text(json.dumps({'beats_ms':[0,517,1034,1551]}))
        plans=[{'segments':[{'type':'animation','manifest':'source/manifest.json'}]},
            {'beatmap':'beats.json','segments':[{'type':'animation','manifest':'source/manifest.json'}],
             'effects':[{'name':'zoom_punch','amount':{'on':'beats'}},{'name':'grade','sat':.8}]},
            {'experimental':True,'beatmap':'beats.json','segments':[{'type':'animation','manifest':'source/manifest.json','duration_ms':2000,'ramp':{'into_beat':2,'slow':.3,'hit_ms':200}}],
             'effects':[{'name':'film_grain','amount':.02}]}]
        names=['P-plain','P-base','P-ramp']
        demo_path=ROOT/'wow/fx/demo2/plan.json'
        if demo_path.exists():
            demo=json.loads(demo_path.read_text(encoding='utf-8-sig'))
            # A silent visual derivative: this plan's music has no offset and no
            # audio-driven envelopes. Both old/new renderers get identical input.
            assert demo.get('music',{}).get('in_ms',0)==0
            demo.pop('music',None)
            demo['beatmap']=str((demo_path.parent/demo['beatmap']).resolve())
            for segment in demo['segments']:
                for key in ('manifest','image'):
                    if key in segment:segment[key]=str((demo_path.parent/segment[key]).resolve())
            for effect in demo['effects']:
                for key in ('depth','background'):
                    if effect.get(key):effect[key]=str((demo_path.parent/effect[key]).resolve())
            plans.append(demo);names.append('demo2')
        for i,plan in enumerate(plans):
            path=p/(names[i]+'.json');path.write_text(json.dumps(plan));outs=[]
            for scripts,current in ((baseline/'scripts',False),(ROOT/'scripts',True)):
                out=p/f'{i}-{current}';outs.append(out)
                subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(scripts),str(path),str(out),str(current)],check=True)
            old,new=outs
            hashes=lambda root:[hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((root/'frames').glob('*.png'))]
            record={'name':names[i],'frames':len(hashes(old)),
                'png_bytes_identical':hashes(old)==hashes(new),
                'gif_bytes_identical':(old/'animation.gif').read_bytes()==(new/'animation.gif').read_bytes(),
                'apng_bytes_identical':(old/'animation.png').read_bytes()==(new/'animation.png').read_bytes()}
            if names[i]!='demo2':
                arrays=[]
                for movie in (old/'legacy.mp4',new/'direct/animation.mp4'):
                    raw=subprocess.check_output([executable('ffmpeg'),'-v','error','-i',str(movie),'-f','rawvideo','-pix_fmt','rgb24','-'])
                    arrays.append(np.frombuffer(raw,np.uint8).astype(float))
                mse=np.mean((arrays[0]-arrays[1])**2)
                record['legacy_mp4_psnr_db']=float(10*np.log10(255**2/mse)) if mse else 'identical'
            else:
                record['note']='Silent visual derivative; soundtrack removed for both raster runs; no visual edits'
            results['plans'].append(record)
            print(json.dumps(record),flush=True)
    (ROOT/'wow/fx/regression-p0.json').write_text(json.dumps(results,indent=2))
    if not all(r['png_bytes_identical'] and r['gif_bytes_identical'] and r['apng_bytes_identical'] and
               (r.get('legacy_mp4_psnr_db','identical')=='identical' or r['legacy_mp4_psnr_db']>=45) for r in results['plans']):
        raise SystemExit(1)


if __name__=='__main__':main()
