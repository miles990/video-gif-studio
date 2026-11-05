"""Verify every exported pair and refresh endpoint measurements with current code."""
import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from fx import Context, TRANSITIONS
from fx_gate_kit import source_frames, cutout_frames, distinct_shot, endpoint_checks, benchmark, write_index, ROOT, FPS
from fx_gate_pairs import write_pair_files, resolve_reference


def main():
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path)
    args=parser.parse_args();out=args.out.resolve()
    pairs=json.loads((out/'pairs.json').read_text());controls=json.loads((out/'controls.json').read_text())
    report=json.loads((out/'gate-auto.json').read_text())
    assert len(report['items'])==34 and all('error' not in i for i in report['items'])
    assert len(pairs)==34*36 and len({p['id'] for p in pairs})==len(pairs)
    assert {c['id'] for c in controls}=={p['id'] for p in pairs}
    write_pair_files(out,pairs,controls)
    by_id={p['id']:p for p in pairs}
    directories={Path(p[side]) for p in pairs for side in ('a','b')}
    for directory in directories:
        assert out in directory.parents and directory.is_dir(),directory
        images=list(directory.glob('*.png'));assert len(images)>=7,directory
        for path in images:
            with Image.open(path) as im:
                assert max(im.size)<=1280,path
                im.verify()
    for control in controls:
        if control['role']=='broken':
            assert control['expected']=='a' and control['auto']['flash_detected'],control['id']
            assert control['auto']['flash_frame'] in control['auto']['flash_frames'],control['id']
            pair=by_id[control['id']]
            with Image.open(Path(pair['b'])/'05.png') as im:broken=np.asarray(im)
            with Image.open(Path(pair['a'])/'05.png') as im:candidate=np.asarray(im)
            assert np.all(broken==broken[0,0,0]) and broken[0,0,0] in (0,255),control['id']
            assert np.abs(broken.astype(float)-candidate).mean()>255*.25,control['id']
        if control['role']=='style':
            assert control['expected']=='tie'
            pair=by_id[control['id']]
            for path in Path(pair['a']).glob('*.png'):
                with Image.open(path) as im:a=np.asarray(im).astype(int)
                with Image.open(Path(pair['b'])/path.name) as im:b=np.asarray(im).astype(int)
                assert a.shape==b.shape and np.max(np.abs(a-b))<=27,control['id']
    reference=BytesIO();Image.new('RGB',(16,16)).save(reference,format='JPEG',quality=85)
    reference.seek(0)
    with Image.open(reference) as im:maximum=float(np.mean(im.quantization[0]))*1.05
    sheets=list(out.rglob('*contact.jpg'))
    for path in sheets:
        with Image.open(path) as im:
            assert max(im.size)<=1280,path
            assert float(np.mean(im.quantization[0]))<=maximum,path
    materials={(material,size):(source_frames(ROOT/'examples/neon-zen-pv/segment-01/generation/source.mp4',size)
        if material=='opaque' else cutout_frames(ROOT/'wow/fx/demo/assets/matte-b.png',size))
        for size in ((480,270),(270,480)) for material in ('opaque','rgba')}
    summary=[]
    for item in report['items']:
        kind,name=item['id'].split(':')
        assert item['reference']==resolve_reference(kind,name,{}),item['id']
        for case in item['cases']:
            size=tuple(case['size']);material=case['material']
            a=materials[(material,size)][-1].astype(np.float32)/255
            b=distinct_shot(size,47,material)
            case['endpoints']=endpoint_checks(TRANSITIONS[name],a,b,Context(*size,fps=FPS,seed=19))
        item['benchmark']=benchmark(kind,TRANSITIONS[name],materials[('opaque',(480,270))][24],{})
        item['benchmark']['material']='opaque'
        summary.append(dict(id=item['id'],reference=item['reference'],pairs=item['pairs'],
            flags={key:sum(c[key]['level']!='PASS' for c in item['cases'])
                   for key in ('alpha','edges','black','flicker','determinism','endpoints')}))
    report['methodology']['endpoints']='Exact A/B identity, swapped endpoints, and p=1e-5 / 1-1e-5 limits; mean associated RGBA error <=1/255; actual first/last delivered-step jump > max(0.10, 4x adjacent interior step) also flagged'
    report['source']['b_shot']='Independent generated animated diamond/diagonal-gradient shot; fx_gate_kit.distinct_shot v1'
    report['verified_at']=datetime.now(timezone.utc).isoformat()
    report['validation_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/'gate-auto.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    write_index(out,report)
    result=dict(items=len(summary),pairs=len(pairs),broken_controls=sum(c['role']=='broken' for c in controls),
        style_controls=sum(c['role']=='style' for c in controls),pair_directories=len(directories),
        sheets=len(sheets),sheet_quality_floor=85,all_paths_valid=True,all_broken_controls_detected=True,
        output=str(out),verified_at=report['verified_at'],per_item=summary)
    (out/'artifact-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (ROOT/'wow/fx/gate-p2c-summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='per_item'},indent=2))


if __name__=='__main__':main()
