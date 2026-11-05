"""Serial, same-machine 720p public-call benchmark; JSON output only."""
import argparse
import json
from pathlib import Path
import platform
import sys
import time
import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from fx import Context, TRANSITIONS
from fx.transitions.gl_ports import PORT_NAMES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    cv2.setNumThreads(1)
    rng = np.random.default_rng(19)
    a, b = (rng.random((720,1280,4), dtype=np.float32) for _ in range(2))
    a[...,3] = b[...,3] = 1
    ctx = Context(1280,720,seed=19)
    rows = []
    for name in PORT_NAMES:
        fn = TRANSITIONS[name]['function']
        fn(a,b,.37,ctx)
        samples=[]
        for _ in range(20):
            start=time.perf_counter();fn(a,b,.37,ctx)
            samples.append((time.perf_counter()-start)*1000)
        rows.append(dict(name=name,median_ms=float(np.median(samples)),samples_ms=samples))
    args.out.write_text(json.dumps(dict(size=[1280,720],dtype='float32',material='opaque',
        warmup=1,frames=20,progress=.37,threads=1,platform=platform.platform(),
        python=sys.version,numpy=np.__version__,opencv=cv2.__version__,
        methodology='Public decorated calls; one heavy process; excludes decode/encode; deterministic random textures',
        items=rows),indent=2),encoding='utf-8')


if __name__=='__main__':main()
