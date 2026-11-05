"""Measure predeclared controls, never candidate recipes; propose, do not activate.

The independent panel labels required by acceptance-amendments §5 are not
available to the builder. This file records that gap instead of inventing votes.
"""
import json
from pathlib import Path
import sys
import statistics
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import cv2
import numpy as np
from fx import EFFECTS,Context
from fx_measure import standard,moving,measures,onset_contrast,rgb,LUMA
from fx_calibrate import revision


def main():
    cv2.setNumThreads(1)
    controls=[('leak-weak-cut','light_leak',{'amount':.13,'seed':3},'invisible',True),
              ('leak-strong','light_leak',{'amount':.8,'seed':3},'visible',False),
              ('halation-default','halation',{},'visible',False),('zoom-default','zoom_punch',{},'visible',False),
              ('radial-old','radial_blur',{'amount':1,'distance':.22,'samples':12},'destructive',False),
              ('radial-current','radial_blur',{},'pending-panel',False),('grain','film_grain',{},'not-destructive',False)]
    results=[]
    for material in ('STD-P','STD-HK'):
        source=standard(material);ctx=Context(1280,720,fps=30,beats_ms=[1000],t_ms=1000,seed=6)
        for ident,name,params,label,cut in controls:
            frames=[moving(source,i) for i in range(27,33)]
            if cut:
                for i in range(3):frames[i]=255-frames[i];frames[i][...,3]=255
            after=[EFFECTS[name]['function'](f,1000+j*1000/30,ctx,**params) for j,f in enumerate(frames[3:])]
            residual=[(rgb(o)-rgb(f))@LUMA*255 for o,f in zip(after,frames[3:])]
            onset=onset_contrast([np.zeros_like(residual[0])]*3,residual,[rgb(f)@LUMA*255 for f in frames])
            m=measures(frames[3],after[0])
            results.append(dict(id=ident+'-'+material,ref=name,params=params,material=material,held_out=True,
                                expected=label,label_source='acceptance fixture; independent panel pending',onset_contrast=onset,**m))
    def proposed(metric,good,bad,minimum):
        pool=results
        if metric=='sharp4':
            # Visibility labels do not imply non-destructive sharpness. A6-1's
            # explicit sharpness negatives are zoom, grain, halation on STD-P.
            pool=[r for r in results if r['material']=='STD-P' and r['ref'] in ('zoom_punch','film_grain','halation','radial_blur')]
        a=[r[metric] for r in pool if r['expected'] in good];b=[r[metric] for r in pool if r['expected'] in bad]
        variance=lambda x:statistics.variance(x) if len(x)>1 else 0.
        sigma=(((len(a)-1)*variance(a)+(len(b)-1)*variance(b))/(len(a)+len(b)-2))**.5
        lo,hi=(max(b),min(a)) if minimum else (max(a),min(b))
        return dict(value=(lo+hi)/2,good_range=[min(a),max(a)],bad_range=[min(b),max(b)],pooled_sigma=sigma,
                    margin=.25*sigma,separable=hi-lo>2*.25*sigma,status='pending-independent-panel-and-next-round')
    result=dict(version=1,commit=revision(),date='2026-11-05',candidate_ids=[],measurements=results,
      proposals={'visibility.onset_contrast.min':proposed('onset_contrast',{'visible'},{'invisible'},True),
                 'harshness.sharp4.min':proposed('sharp4',{'visible','not-destructive'},{'destructive'},True)},
      positive_control={'ids':[r['id'] for r in results if r['expected']=='visible']},
      negative_control={'ids':[r['id'] for r in results if r['expected'] in ('invisible','destructive')]},
      limitations=['Weak light leak uses a synthetic cut, not the unavailable independently labelled demo2 clip.',
                  'No independent 2AFC votes. No C threshold activated. Candidate recipes excluded from calibration.',
                  'Numerical separation alone cannot certify human visibility; scene cuts can mask effects.'])
    path=ROOT/'references/fx-instrument-anchors.json';path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result['proposals'],indent=2))


if __name__=='__main__':main()
