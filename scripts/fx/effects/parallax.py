from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from ..core import effect, over, premultiply, straight
from ..depth import depth_map, check_model


@lru_cache(maxsize=4)
def layers(raw,shape,depth_file):
    frame=np.frombuffer(raw,np.float32).reshape(shape)
    depth=cv2.resize(np.asarray(Image.open(depth_file),np.float32),(shape[1],shape[0]))
    depth=(depth-depth.min())/max(float(np.ptp(depth)),1e-6)
    mask=(depth>.55).astype(np.uint8)
    expanded=cv2.dilate(mask,np.ones((13,13),np.uint8))
    rgb=np.rint(frame[...,:3]*255).astype('uint8')
    plate=cv2.inpaint(rgb,expanded,5,cv2.INPAINT_TELEA).astype(np.float32)/255
    foreground=frame.copy();foreground[...,3]*=mask
    return premultiply(np.dstack((plate,frame[...,3]))),premultiply(foreground)


@effect(status='experimental',depth='Cached Small depth PNG, larger means nearer',model='Small ONNX path',cache='Derived depth cache directory',distance='Near-layer horizontal travel pixels',amount='Camera progress 0..1; may be keyframed')
def parallax(frame,t,ctx,amount=1.0,depth='',model='.runtime/models/depth-anything-v2-small.onnx',cache='wow/fx/demo2/work/depth',distance=18.0):
    """Two depth layers; dilated foreground removal and inpaint prevent exposed holes."""
    check_model(model)
    if amount==0:return frame
    if not depth:
        import hashlib
        depth_map(frame,model,cache)
        depth=str(Path(cache)/(hashlib.sha256(frame.tobytes()+str(model).encode()).hexdigest()+'.png'))
    plate,foreground=layers(frame.tobytes(),frame.shape,depth)
    moved=[]
    for layer,factor in ((plate,.2),(foreground,1.0)):
        matrix=np.float32([[1,0,distance*amount*factor],[0,1,-distance*.18*amount*factor]])
        moved.append(cv2.warpAffine(layer,matrix,(ctx.width,ctx.height),borderMode=cv2.BORDER_REFLECT_101))
    alpha=1-moved[1][...,3]
    return straight(cv2.add(moved[1],cv2.merge([cv2.multiply(c,alpha) for c in cv2.split(moved[0])])) )
