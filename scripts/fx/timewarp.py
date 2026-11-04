"""Output-clock integration and bounded, premultiplied frame interpolation."""
from functools import lru_cache
from pathlib import Path
import os
import cv2
import numpy as np
from .core import evaluate, floating, premultiply, straight, restore


def source_clock(segment, local_ms, ctx):
    """Integrate speed on a 1ms grid; keyframes are piecewise linear."""
    if 'ramp' in segment:
        ramp=segment['ramp'];hit=ctx.beats_ms[ramp['into_beat']]-ctx.segment['start_ms']
        boundary=max(0,hit-ramp.get('hit_ms',200))
        return min(local_ms,boundary)*ramp.get('slow',.3)+max(0,local_ms-boundary)*2.0
    speed=segment.get('speed',1)
    if not isinstance(speed,dict): return local_ms*speed
    points=np.arange(0,local_ms,1,dtype=np.float64)
    points=np.r_[points,local_ms]
    values=np.array([evaluate(speed,t+ctx.segment['start_ms'],ctx) for t in points])
    return float(np.sum((values[:-1]+values[1:])*.5*np.diff(points)))


@lru_cache(maxsize=2)
def session(model):
    try: import onnxruntime as ort
    except ImportError: raise ValueError('onnxruntime required; use fx-optdeps or pip install -r requirements-fx-optional.txt') from None
    if not Path(model).is_file(): raise ValueError(f'Model missing: {model}; place weights in .runtime/models')
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    return ort.InferenceSession(str(model),sess_options=options,providers=['CPUExecutionProvider'])


def rife(a,b,p,model='',engine=None):
    """RIFE lite RGB+RGB+t, padded to 32; alpha is interpolated separately."""
    h,w=a.shape[:2];pad=((0,(-h)%32),(0,(-w)%32),(0,0))
    rgb=np.concatenate((premultiply(a)[...,:3],premultiply(b)[...,:3],np.full((h,w,1),p,np.float32)),axis=2)
    tensor=np.pad(rgb,pad,mode='edge').transpose(2,0,1)[None].astype(np.float32)
    engine=engine or session(model or os.environ.get('VIDEO_GIF_RIFE_MODEL','.runtime/models/rife_v4.25_lite.onnx'))
    result=engine.run(None,{'input':tensor})[0][0,:3,:h,:w].transpose(1,2,0)
    return straight(np.dstack((result,a[...,3]*(1-p)+b[...,3]*p)))


def flow_pair(a,b):
    """Bidirectional DIS, with coherent translation correction for textureless bars."""
    gray=[cv2.cvtColor(np.rint(x[...,:3]*x[...,3:4]*255).astype('uint8'),cv2.COLOR_RGB2GRAY) for x in (a,b)]
    dis=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    forward=dis.calc(gray[0],gray[1],None);backward=dis.calc(gray[1],gray[0],None)
    # Phase correlation resolves aperture-ambiguous, globally translating graphics.
    shift,response=cv2.phaseCorrelate(gray[0].astype('float32'),gray[1].astype('float32'),cv2.createHanningWindow((a.shape[1],a.shape[0]),cv2.CV_32F))
    if response>.65 and np.linalg.norm(shift)<min(a.shape[:2])*.4:
        matrix=np.float32([[1,0,shift[0]],[0,1,shift[1]]])
        moved=cv2.warpAffine(gray[0],matrix,(a.shape[1],a.shape[0]),borderMode=cv2.BORDER_REPLICATE)
        if np.abs(moved.astype(float)-gray[1]).mean()<2:
            forward[:]=shift;backward[:]=np.negative(shift)
    return forward,backward


def interpolate(a,b,p,method='flow',engine=None,model='',flows=None):
    p=float(p)
    if method=='none' or p<=1e-6:return a.copy()
    if p>=1-1e-6:return b.copy()
    dtype=a.dtype;a,b=floating(a),floating(b)
    if method=='rife': result=rife(a,b,p,model,engine)
    elif method=='blend':result=straight(cv2.addWeighted(premultiply(a),1-p,premultiply(b),p,0))
    elif method=='flow':
        forward,backward=flows if flows is not None else flow_pair(a,b)
        yy,xx=np.indices(a.shape[:2],dtype=np.float32)
        left=cv2.remap(premultiply(a),xx-forward[...,0]*p,yy-forward[...,1]*p,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
        right=cv2.remap(premultiply(b),xx-backward[...,0]*(1-p),yy-backward[...,1]*(1-p),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
        result=straight(cv2.addWeighted(left,1-p,right,p,0))
    else:raise ValueError('interpolate: choose none, blend, flow, rife')
    return restore(result,dtype)
