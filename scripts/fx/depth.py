"""Only commercially usable Depth Anything V2 Small; cache derived maps, not weights."""
import hashlib
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from .timewarp import session


def check_model(model):
    if any(word in Path(model).name.lower() for word in ('base','large','vitb','vitl')):
        raise ValueError('Depth Anything Base/Large are CC-BY-NC and must not be used; only Small is accepted')


def depth_map(frame,model='.runtime/models/depth-anything-v2-small.onnx',cache='wow/fx/demo2/work/depth',engine=None):
    check_model(model);root=Path(cache)
    digest=hashlib.sha256(frame.tobytes()+str(model).encode()).hexdigest();target=root/(digest+'.png')
    if target.is_file():return np.array(Image.open(target),dtype=np.float32)/65535
    try: engine=engine or session(model)
    except ValueError as exc:raise ValueError(f'{exc}; Depth Anything V2 Small at {model} (.runtime/models), requires onnxruntime; alternatively use beat_bounce/zoom_punch') from None
    h,w=frame.shape[:2];size=(int(np.ceil(w/14))*14,int(np.ceil(h/14))*14)
    rgb=frame[...,:3].astype(np.float32)/(255 if frame.dtype==np.uint8 else 1)
    resized=cv2.resize(rgb,size);normalized=(resized-np.float32([.485,.456,.406]))/np.float32([.229,.224,.225])
    value=engine.run(None,{'pixel_values':normalized.transpose(2,0,1)[None].astype(np.float32)})[0].squeeze()
    value=cv2.resize(value,(w,h));value=(value-value.min())/max(float(np.ptp(value)),1e-6)
    root.mkdir(parents=True,exist_ok=True);Image.fromarray(np.rint(value*65535).astype('uint16')).save(target)
    return np.rint(value*65535).astype(np.float32)/65535
