"""Serial integration evidence; artifacts stay outside the worktree."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import cv2
import numpy as np
from PIL import Image
from fx_measure import standard,measures
from fx_catalog import output_root
from fx_recipes import load_recipes
from fx_render import render,validate_plan
from fx_candidates import build
from fx_calibrate import load_table


def main():
    cv2.setNumThreads(1)
    output_root().mkdir(exist_ok=True,parents=True)
    root=Path(tempfile.mkdtemp(prefix='integration-',dir=output_root()))
    Image.fromarray(standard(width=160,height=90)).save(root/'source.png')
    plan={'fps':30,'segments':[{'type':'still','image':'source.png','duration_ms':3000}],
          'effects':[{'recipe':'impact','at_ms':1000}], 'experimental':True,'fx_checks':True}
    recipe_validations=[]
    for name in load_recipes(experimental=True):
        candidate=dict(plan,effects=[{'recipe':name,'at_ms':1000}])
        path=root/(name+'-plan.json');path.write_text(json.dumps(candidate),encoding='utf-8')
        data=validate_plan(path,('mp4',),experimental=True)
        recipe_validations.append({'name':name,'layers':len(data[4])})
    path=root/'impact-plan.json';result=render(path,root/'impact-render',('mp4',),experimental=True,fps=30)
    manifest=json.loads((root/'impact-render/manifest.json').read_text())
    if len(manifest['recipe_events'])!=1 or not manifest.get('fx_checks') or not manifest.get('sfx'):raise AssertionError('Missing recipe/QA/SFX integration')
    print('recipe plan + decoded QA + audio passed',flush=True)
    # Same legacy plan through the exact main fx_render source and the working
    # implementation, sharing unchanged effect primitives. No checkout/mutation.
    old=subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'show','HEAD:scripts/fx_render.py'],cwd=ROOT)
    old_path=root/'baseline_fx_render.py';old_path.write_bytes(old)
    spec=importlib.util.spec_from_file_location('s6_baseline',old_path);baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    legacy={'segments':[{'type':'still','image':'source.png','duration_ms':1000}],
            'effects':[{'name':'zoom_punch','amount':{'keyframes':[[0,0],[200,1],[800,0]]}},
                       {'name':'grade','temp':.08},{'name':'halation','amount':.4}]}
    legacy_path=root/'legacy-plan.json';legacy_path.write_text(json.dumps(legacy))
    baseline.render(legacy_path,root/'before',('png',));render(legacy_path,root/'after',('png',))
    def hashes(folder):return [hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((folder/'frames').glob('*.png'))]
    before,after=hashes(root/'before'),hashes(root/'after')
    if not before or before!=after:raise AssertionError('Legacy frame hashes differ')
    print('legacy frame hashes equal: '+str(len(before)),flush=True)
    # Source-backed candidate selection and a derivative plan that actually validates.
    source_plan=root/'source-plan.json';source_plan.write_text(json.dumps({'fps':30,'segments':plan['segments']}))
    candidates=build(source_plan,'hook',root/'candidates',experimental=True,choose=2,reason='Review the softer hook alternative')
    validate_plan(root/'candidates/selected-plan.json',('mp4',),experimental=True)
    thumbs=[np.asarray(Image.open(root/'candidates'/c['preview']['thumbnail']).convert('RGB')) for c in candidates['candidates']]
    differences=[dict(a=i,b=j,dY=measures(thumbs[i],thumbs[j],flow=False)['dY']) for i in range(len(thumbs)) for j in range(i+1,len(thumbs))]
    data=dict(recipe_validations=recipe_validations,render=result,legacy_hash_frames=len(before),legacy_sha_equal=before==after,
              candidates=len(candidates['candidates']),candidate_pair_differences=differences,
              selected_plan=str(root/'candidates/selected-plan.json'),fx_checks=manifest['fx_checks'],sfx=manifest['sfx'])
    (ROOT/'wow/fx/s6-integration.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'recipes_validated':len(recipe_validations),'legacy_sha_frames':len(before),'candidates':len(candidates['candidates']),'differences':differences}))


if __name__=='__main__':main()
