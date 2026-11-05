"""Measure declared visibility anchors and optionally ingest independent 2AFC labels.

Never activates a registry threshold. Labels: [{id, observer, choice}], where
choice is effect/reference/tie. Multiple observers may label one anchor once.
"""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from fx import EFFECTS,Context
from fx_measure import standard,moving,measures,onset_contrast,visibility_residual,visibility_family


def attach_labels(measurements, labels):
    known={r['id'] for r in measurements};seen=set();votes={k:[] for k in known}
    for label in labels:
        ident=label['id'];observer=label['observer'];choice=label['choice']
        if ident not in known or not isinstance(observer,str) or not observer.strip() or choice not in ('effect','reference','tie'):
            raise ValueError('Unknown anchor, observer or 2AFC choice')
        key=(ident,observer)
        if key in seen:raise ValueError('Duplicate observer vote for '+ident)
        seen.add(key);votes[ident].append(dict(observer=observer,choice=choice))
    return [dict(row,panel=votes[row['id']],label_status='labelled' if votes[row['id']] else 'pending') for row in measurements]


def run(anchors, labels=(), width=320, height=180):
    cv2.setNumThreads(1);rows=[]
    for anchor in anchors['measurements']:
        name=anchor['ref'];source=standard(anchor['material'],width,height)
        ctx=Context(width,height,fps=30,beats_ms=[1000],t_ms=1000,seed=6)
        frames=[moving(source,i) for i in range(27,33)]
        if 'weak-cut' in anchor['id']:
            for f in frames[:3]:f[...,:3]=255-f[...,:3]
        family=visibility_family(name);after=[];scenes=[]
        for index,frame in enumerate(frames):
            output=frame if index<3 else EFFECTS[name]['function'](frame,1000+(index-3)*1000/30,ctx,**anchor['params'])
            residual,scene=visibility_residual(frame,output,family)
            if index>=3:after.append(residual)
            scenes.append(scene)
        rows.append(dict(id=anchor['id'],ref=name,material=anchor['material'],family=family,held_out=anchor.get('held_out',True),
                         onset_contrast=onset_contrast([np.zeros_like(after[0])]*3,after,scenes),**measures(frames[-1],output)))
    return dict(version=2,instrument='Lab-texture-v2',status='calibrate_first',resolution=[width,height],
                measurements=attach_labels(rows,labels),activation='Independent audit and future-round approval required; this harness never activates thresholds')


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--anchors',type=Path,default=Path(__file__).resolve().parents[1]/'references/fx-instrument-anchors.json')
    ap.add_argument('--labels',type=Path);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args(argv)
    result=run(json.loads(args.anchors.read_text(encoding='utf-8')),json.loads(args.labels.read_text(encoding='utf-8')) if args.labels else [])
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
