"""Small reproducible evidence probes; no optional model runs."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
from fx_reverse import inspect_frames
from fx_render import preview

a=np.full((90,160,3),[220,40,40],np.uint8);b=np.full_like(a,[40,60,220])
frames=[Image.fromarray(a)]*25+[Image.fromarray(np.rint(a*(1-p)+b*p).astype(np.uint8)) for p in np.linspace(0,1,31)]+[Image.fromarray(b)]*25
report=inspect_frames(frames,np.arange(len(frames))*40,len(frames)*40)
assert len(report['cuts'])==1 and report['cuts'][0]['type']=='crossfade'
assert report['cuts'][0]['duration_ms']==1200
record={'dissolve_1200ms':report['cuts']}
for mode in ('text','json'):
    result=subprocess.run([sys.executable,str(REPO/'scripts/fx_render.py'),'--list','--no-user-fx']+(['--json'] if mode=='json' else []),capture_output=True,text=True,check=True)
    (ROOT/f'catalog.{mode}').write_text(result.stdout,encoding='utf8')
    if mode=='json':record['catalog_counts']={k:len(v) for k,v in json.loads(result.stdout).items()}
record['rembg_present_in_test_environment']=importlib.util.find_spec('rembg') is not None
if not record['rembg_present_in_test_environment']:
    with tempfile.TemporaryDirectory(dir=ROOT/'demo/work') as folder:
        p=Path(folder);(p/'frames').mkdir();Image.new('RGBA',(16,16),'red').save(p/'frames/00000.png')
        (p/'manifest.json').write_text(json.dumps({'durations_ms':[40]}))
        result=subprocess.run([sys.executable,str(REPO/'scripts/background_remove.py'),str(p/'frames'),'--manifest',str(p/'manifest.json'),'--out',str(p/'out'),'--model','birefnet-general'],capture_output=True,text=True)
        assert result.returncode==2 and 'requirements-matting.txt' in result.stderr and 'Traceback' not in result.stderr
        record['missing_rembg']={'exit_code':result.returncode,'stderr':result.stderr.strip()}
started=time.perf_counter();preview(ROOT/'demo/preview.png',ROOT/'demo/assets/freeze-a.png')
record['preview_seconds']=time.perf_counter()-started
record['preview_tiles']=1+record['catalog_counts']['effects']+3*record['catalog_counts']['transitions']
(ROOT/'fix-evidence.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
