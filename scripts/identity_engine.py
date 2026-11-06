"""Optional local DINOv2 structure and subject-only Lab palette instruments."""
from functools import lru_cache
import os
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from image_common import digest, ImageError

MODEL_SHA256='f22797eabf810a75e41de68d378541ebea372122b25c4ce3ef25ff618250c20a'
DEFAULT_MODEL=Path.home()/'.cache/video-gif-studio/models/dinov2-small/model.onnx'
# Cross-set calibration is recorded in build-evidence-s13-r3.json.
LIMITS={'structure': {'fail': .792300, 'pass': .823630}, 'colour': {'fail': .705904, 'pass': .762338}}

def model_path():
    return Path(os.environ.get('VGS_DINO_MODEL',str(DEFAULT_MODEL)))

@lru_cache(maxsize=4)
def _session(path,mtime):
    import onnxruntime as ort
    if digest(path)!=MODEL_SHA256:raise ValueError('Unexpected DINOv2 model SHA256.')
    options=ort.SessionOptions();options.intra_op_num_threads=2
    return ort.InferenceSession(path,sess_options=options,providers=['CPUExecutionProvider'])

def engine():
    path=model_path()
    try:
        if not path.is_file():return None,'DINOv2 model missing; ORB/HSV fallback is unassessed.'
        return _session(str(path),path.stat().st_mtime_ns),None
    except (ImportError,OSError,RuntimeError,ValueError) as exc:
        return None,f'DINOv2 unavailable ({type(exc).__name__}); ORB/HSV fallback is unassessed.'
    except Exception as exc:
        # ORT can raise its own extension exception classes on corrupt weights.
        return None,f'DINOv2 unavailable ({type(exc).__name__}); ORB/HSV fallback is unassessed.'

def capability():
    session,reason=engine();path=model_path()
    return dict(available=session is not None,path=str(path),sha256=digest(path) if path.is_file() else None,
                engine='DINOv2-small ONNX + subject Lab a*b* 12x12',reason=reason,optional=True)

def describe():
    session,reason=engine()
    return dict(name='DINOv2-small CLS + mean patch / Lab a*b* intersection' if session else 'ORB/HSV fallback',
                available=session is not None,reason=reason,limits=LIMITS)

@lru_cache(maxsize=256)
def _features(path,sha,model,mtime):
    from image_identity import subject_region
    with Image.open(path) as im:a=np.array(im.convert('RGBA'))
    mask,source=subject_region(a)
    if not mask.any():raise ImageError('E_IDENTITY_EMPTY','Reference has no visible subject.')
    rgb=a[...,:3].copy()
    lab=cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB)[mask]
    histogram,_=np.histogramdd(lab[:,[1,2]],bins=(12,12),range=((0,256),(0,256)))
    histogram=histogram.ravel()/histogram.sum()
    alpha=a[...,3:4]/255.
    rgb=np.rint(rgb*alpha+255*(1-alpha)).astype('uint8');rgb[~mask]=255
    ys,xs=np.where(mask);rgb=rgb[ys.min():ys.max()+1,xs.min():xs.max()+1]
    h,w=rgb.shape[:2];side=max(h,w);canvas=np.full((side,side,3),255,np.uint8)
    canvas[(side-h)//2:(side-h)//2+h,(side-w)//2:(side-w)//2+w]=rgb
    x=cv2.resize(canvas,(224,224)).astype('float32')/255
    x=((x-[.485,.456,.406])/[.229,.224,.225]).transpose(2,0,1)[None].astype('float32')
    session=_session(model,mtime);outputs=session.run(None,{session.get_inputs()[0].name:x})
    tokens=outputs[0]
    if tokens.ndim!=3 or tokens.shape[1]<2:
        raise ImageError('E_IDENTITY_MODEL','DINO model must expose CLS and patch tokens.')
    v=np.concatenate([tokens[0,0],tokens[0,1:].mean(axis=0)])
    return v/max(np.linalg.norm(v),1e-12),histogram,source

def features(path):
    path=Path(path).resolve();model=model_path()
    return _features(str(path),digest(path),str(model),model.stat().st_mtime_ns)

def compare(a,b):
    ea,ha,sa=features(a);eb,hb,sb=features(b)
    return dict(structure=float(np.clip(ea@eb,-1,1)),colour=float(np.minimum(ha,hb).sum()),
                subject_sources=[sa,sb])

def verdict(scores,limits=None):
    limits=limits or LIMITS
    if any(scores[k]<limits[k]['fail'] for k in limits):return 'identity_fail'
    if all(scores[k]>=limits[k]['pass'] for k in limits):return 'pass'
    return 'unassessed'
