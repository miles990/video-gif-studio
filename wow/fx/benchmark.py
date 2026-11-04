"""Reproduce the S-7 pixel-render benchmark, excluding PNG and codec I/O."""
import json
import platform
from pathlib import Path
import sys
import time
import cv2
import numpy as np
sys.path.insert(0,'scripts')
from fx import Context,EFFECTS,TRANSITIONS

ctx=Context(1280,720,30,[0,500,1000,1500,2000,2500])
a=np.full((720,1280,4),[80,120,180,255],np.uint8);a[200:500,350:900,:3]=230
b=a[:,::-1].copy();started=time.perf_counter()
for i in range(90):
    t=i*1000/30;x=a
    if 1250<=t<=1750:x=TRANSITIONS['crossfade']['function'](a,b,(t-1250)/500,ctx)
    for name in ('grade','halation','beat_bounce'):x=EFFECTS[name]['function'](x,t,ctx)
elapsed=time.perf_counter()-started
record={'seconds':elapsed,'frames':90,'fps':90/elapsed,'resolution':[1280,720],'numpy':np.__version__,
        'opencv':cv2.__version__,'machine':platform.platform(),'processor':platform.processor(),
        'method':'90 RGBA frames; grade + halation + beat_bounce, centered crossfade 500ms; excludes PNG/codec I/O'}
Path('wow/fx/benchmark-latest.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
