"""Serial P2b benchmark + full-HD geometry smoke checks; JSON only in repo.

Run with the skill Python. No decode/encode included. Public uint8/float32
conversion and premultiplication ARE included. No parallel workers.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts'),str(ROOT/'tests')]
from fx import Context, TRANSITIONS
from fx.transitions.gl_ports import PORT_NAMES
from test_gl_transitions import NONMONOTONIC, progress_measure, texture


def run(out, names=PORT_NAMES):
    report = dict(created=datetime.now(timezone.utc).isoformat(),python=sys.executable,
        environment=dict(platform=platform.platform(),cpu=platform.processor(),
            numpy=np.__version__,opencv=cv2.__version__,opencv_threads=cv2.getNumThreads()),
        methodology=dict(size=[1280,720],dtype='float32',warmup=1,
            progress=[.25,.5,.75],repeats_per_progress=5,
            includes='public registry call, float conversion, premultiply, remap, finish, restore; no I/O',
            monotonic='21 points, seed-1/2 opaque random textures at 160x90; average tie ranks; Spearman',
            geometry='p=.5 at 1920x1080 and 1080x1920; finite/range/opaque-alpha/shape checks'),items=[])
    a,b = texture(1280,720,1),texture(1280,720,2); ctx = Context(1280,720,seed=19)
    for name in names:
        fn = TRANSITIONS[name]['function'];samples=[]
        start=time.perf_counter();fn(a,b,.25,ctx)
        cold_ms=(time.perf_counter()-start)*1000
        for p in (.25,.5,.75):
            fn(a,b,p,ctx)
            for _ in range(5):
                start=time.perf_counter();result=fn(a,b,p,ctx)
                samples.append(dict(p=p,ms=(time.perf_counter()-start)*1000))
        errors,rho=progress_measure(name)
        item=dict(name=name,cold_ms=cold_ms,median_ms=float(np.median([s['ms'] for s in samples])),
            min_ms=min(s['ms'] for s in samples),max_ms=max(s['ms'] for s in samples),samples=samples,
            progress_mad=errors,spearman=rho,nonmonotonic_documented=name in NONMONOTONIC,
            sha256=hashlib.sha256(result.tobytes()).hexdigest(),large_canvases=[])
        for w,h in ((1920,1080),(1080,1920)):
            large_a,large_b=texture(w,h,1),texture(w,h,2)
            result=fn(large_a,large_b,.5,Context(w,h,seed=19))
            item['large_canvases'].append(dict(size=[w,h],shape_ok=result.shape==large_a.shape,
                finite=bool(np.isfinite(result).all()),minimum=float(result.min()),maximum=float(result.max()),
                alpha_max_error=float(np.max(np.abs(result[...,3]-1)))))
            del large_a,large_b,result
        report['items'].append(item)
        Path(out).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        print(f'{name}: {item["median_ms"]:.3f} ms; rho={rho:.4f}',flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'wow/fx/benchmark-p2b.json')
    parser.add_argument('--items',nargs='+',choices=PORT_NAMES,help='Optional focused remeasurement')
    args=parser.parse_args()
    run(args.out,args.items or PORT_NAMES)
