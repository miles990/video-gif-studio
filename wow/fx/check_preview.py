"""Measure actual preview effect tiles against the original reference tile."""
import json
from pathlib import Path
import sys
import time
import numpy as np
from PIL import Image
sys.path.insert(0,'scripts')
from fx import EFFECTS
from fx_render import preview

target=Path('wow/fx/demo2/preview.png');start=time.perf_counter()
preview(target,'wow/fx/demo/assets/freeze-b.png');elapsed=time.perf_counter()-start
sheet=np.array(Image.open(target).convert('RGB'),np.float32);original=sheet[32:212,:320];records={}
for i,name in enumerate(EFFECTS,1):
    x,y=i%3*320,i//3*212;tile=sheet[y+32:y+212,x:x+320];delta=np.abs(tile-original)
    records[name]={'MAD_255':round(float(delta.mean()),3),'fraction_delta_ge_16':round(float(np.mean(np.max(delta,axis=2)>=16)),4),
                   'pass':bool(delta.mean()>=4 and np.mean(np.max(delta,axis=2)>=16)>=.02)}
records['parallax']['note']='Explicit unavailable tile: optional model is not loaded by preview'
Path('wow/fx/preview-measurements.json').write_text(json.dumps({'seconds':elapsed,'effects':records},indent=2))
print(json.dumps({'seconds':elapsed,'below_threshold':[n for n,v in records.items() if not v['pass']]},indent=2))
