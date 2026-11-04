"""Verify built demos, sequentially, without inference or model dependencies."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np
from PIL import Image
from inspect_demo import inspect, ROOT
sys.path.insert(0,str(ROOT.parents[2]/'scripts'))
from fx_reverse import reverse
from fx_render import validate_plan
from qa_media import qa


def verify():
    inspect()
    work=ROOT/f'work/verification-{time.time_ns()}';work.mkdir(parents=True)
    result={}
    for tag in ('a','b'):
        name='demo' if tag=='a' else 'demo-b'
        report=reverse(ROOT/f'{name}.mp4',work/f'reverse-{tag}',ROOT/'beats.json')
        draft_path=work/f'reverse-{tag}/draft-plan.json'
        validate_plan(draft_path)
        draft=json.loads(draft_path.read_text())
        for s in draft['segments']:
            if 'manifest' in s:s['manifest']=(draft_path.parent/s['manifest']).relative_to(ROOT).as_posix()
        (ROOT/f'draft-reverse-{tag}.json').write_text(json.dumps(draft,indent=2))
        validate_plan(ROOT/f'draft-reverse-{tag}.json')
        (ROOT/f'reverse-report-{tag}.json').write_text(json.dumps(report,indent=2))
        shutil.copy2(draft_path.parent/'shots.png',ROOT/f'reverse-shots-{tag}.png')
        truth=json.loads((ROOT/f'manifest-{tag}.json').read_text())['transitions']
        errors=[min(abs(c['time_ms']-t['cut_ms']) for c in report['cuts']) for t in truth]
        quality=qa(ROOT/f'{name}.mp4',work/f'qa-{tag}',timeline=ROOT/f'manifest-{tag}.json')
        destination=ROOT/('qa' if tag=='a' else 'qa-b');destination.mkdir(exist_ok=True)
        for file in (work/f'qa-{tag}').iterdir():
            if file.is_file():shutil.copy2(file,destination/file.name)
        with Image.open(ROOT/f'assets/freeze-{tag}.png') as im:source=np.array(im.convert('RGB'))
        with Image.open(ROOT/f'assets/matte-{tag}.png') as im:matte=np.array(im.convert('RGBA'))
        result[tag]={'cut_errors_ms':errors,'cut_types':[c['type'] for c in report['cuts']],
            'freeze_segments':[s for s in draft['segments'] if s['type']=='still'],
            'qa_level':quality['level'],'qa_checks':[{k:c[k] for k in ('name','level','message','events')} for c in quality['checks']],
            'matte_rgb_exact':bool(np.array_equal(source,matte[:,:,:3])),
            'source_luma':float((source@np.array([.2126,.7152,.0722])).mean()),
            'matte_sha256':hashlib.sha256((ROOT/f'assets/matte-{tag}.png').read_bytes()).hexdigest()}
    (ROOT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':verify()
