"""Reproducible leave-one-set-out calibration; no provider requests."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from identity_engine import compare,verdict,LIMITS

SETS=[('r1','live-s13',['ref1','ref2'],['neg']),('r2','live-s13-r2',['refA','refB'],['neg','imp']),('r3','live-s13-r3',['refFront','refSide','refBack','refAction'],['impSpecies','impRecolor'])]

def calibrate(rows):
    limits={}
    for axis in ('structure','colour'):
        floor=min(r[axis] for r in rows if r['label']=='same')
        # An impostor can be identical on one axis (e.g. recolour structure).
        # Calibrate that axis using separable negatives; require the other to
        # reject inseparable negatives, and verify the joint rule below.
        ceiling=max(r[axis] for r in rows if r['label']=='different' and r[axis]<floor)
        gap=floor-ceiling
        limits[axis]={'fail':ceiling+gap/3,'pass':ceiling+2*gap/3}
    return limits

def evidence():
    rows=[];root=Path(__file__).resolve().parents[1]/'tests/fixtures'
    for name,folder,refs,negs in SETS:
        p=root/folder
        for n in refs+negs:
            scores=[compare(p/n/'image-1.png',p/r/'image-1.png') for r in refs if n!=r]
            rows.append(dict(set=name,name=n,label='same' if n in refs else 'different',**{a:max(s[a] for s in scores) for a in ['structure','colour']}))
    folds=[]
    for held in ('r1','r2','r3'):
        train=[r for r in rows if r['set']!=held];test=[r for r in rows if r['set']==held];limits=calibrate(train)
        folds.append(dict(held_out=held,calibrated_on=sorted({r['set'] for r in train}),limits=limits,
                          results=[dict(r,status=verdict(r,limits)) for r in test],
                          training_errors=sum(verdict(r,limits)!=('pass' if r['label']=='same' else 'identity_fail') for r in train)))
    return dict(rows=rows,leave_one_set_out=folds,pooled_limits=calibrate(rows),production_limits=LIMITS,
                caveat='Cross-validation on three already reviewed live sets; not a claim of untouched future data.')

if __name__=='__main__':
    result=evidence();out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    for fold in result['leave_one_set_out']:print(fold['held_out'],fold['limits'],[(r['name'],r['status']) for r in fold['results']])
