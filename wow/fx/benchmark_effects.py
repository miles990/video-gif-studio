"""Median of ten 720p float32 calls per registered operation, serial execution."""
import argparse
import json
from pathlib import Path
import platform
import sys
import time
import numpy as np
import cv2
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from fx import Context,EFFECTS,TRANSITIONS
from fx.timewarp import interpolate


def run(output):
    h,w=720,1280;y,x=np.indices((h,w));a=np.ones((h,w,4),np.float32)
    a[...,:3]=np.stack((.15+x/w*.5,.1+y/h*.6,.4+x/w*.3),axis=2);b=a[:,::-1].copy()
    ctx=Context(w,h,30,[0,500,1000],history=(a.copy(),)*4,history_times_ms=(0,40,80,120))
    records={}
    for kind,registry in [('effect',EFFECTS),('transition',TRANSITIONS)]:
        for name,spec in registry.items():
            kwargs={'depth':str(Path('wow/fx/demo2/assets/depth-small.png').resolve())} if name=='parallax' else {}
            args=(a,500,ctx) if kind=='effect' else (a,b,.4,ctx)
            spec['function'](*args,**kwargs);times=[]
            for _ in range(10):
                start=time.perf_counter();spec['function'](*args,**kwargs);times.append(1000*(time.perf_counter()-start))
            records[name]=round(float(np.median(times)),3);print(name,records[name],flush=True)
    times=[]
    for _ in range(10):
        start=time.perf_counter();interpolate(a,b,.5,'flow');times.append(1000*(time.perf_counter()-start))
    records['flow']=round(float(np.median(times)),3)
    result={'resolution':[w,h],'dtype':'float32','samples':10,'statistic':'median ms','numpy':np.__version__,'opencv':cv2.__version__,
        'machine':platform.platform(),'processor':platform.processor(),'timings_ms':records}
    Path(output).write_text(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='wow/fx/effect-timings.json');args=ap.parse_args();run(args.out)
