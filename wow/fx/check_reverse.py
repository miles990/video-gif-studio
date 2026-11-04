"""Three independent known edit orders; writes measured confusion, not expectations."""
import json
from pathlib import Path
import sys
import tempfile
import numpy as np
from PIL import Image
sys.path[:0]=['scripts','tests']
from test_fx import synthetic
from fx_render import render
from fx_reverse import inspect_frames

orders=[['cut','crossfade','whip_pan','hex_shutter','flash_cut'],
        ['flash_cut','hex_shutter','cut','crossfade','whip_pan'],
        ['whip_pan','flash_cut','crossfade','cut','hex_shutter']]
matrix={k:{} for k in orders[0]};cases=[]
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);synthetic(root)
    for run,order in enumerate(orders):
        plan={'beatmap':'beats.json','fps':25,'segments':[],'effects':[{'name':'flash_white','start_ms':500,'end_ms':660,'amount':{'keyframes':[[500,1],[620,0]]}}]}
        for i in range(6):
            s={'type':'animation','manifest':('A' if i%2==0 else 'B')+'/manifest.json','in_ms':0,'out_ms':1000}
            if i and order[i-1]!='cut':s['transition']={'name':order[i-1],'duration_ms':320}
            plan['segments'].append(s)
        (root/'plan.json').write_text(json.dumps(plan));out=root/str(run);render(root/'plan.json',out,('png',))
        m=json.loads((out/'manifest.json').read_text());times=np.cumsum([0]+m['durations_ms']).tolist()[:-1]
        images=[]
        for file in sorted((out/'frames').glob('*.png')):
            with Image.open(file) as im:images.append(im.convert('RGBA'))
        report=inspect_frames(images,times,6000,list(range(0,6001,500)))
        errors=[]
        for i,truth in enumerate(order):
            t=(i+1)*1000;near=min(report['cuts'],key=lambda c:abs(c['time_ms']-t),default=None)
            predicted=near['type'] if near and abs(near['time_ms']-t)<=200 else 'missed'
            matrix[truth][predicted]=matrix[truth].get(predicted,0)+1
            errors.append({'truth':truth,'time_ms':t,'predicted':predicted,'error_ms':near['time_ms']-t if near else None})
        cases.append({'order':order,'events':errors,'flashes':report['flashes'],'report':report})
result={'matrix':matrix,'cases':cases,'method':'Three 6s rendered PNG timelines, five edits each, all builtins three times; standalone flash at 500ms. Detection has no access to plans.'}
Path('wow/fx/reverse-confusion.json').write_text(json.dumps(result,indent=2));print(json.dumps(matrix,indent=2))
