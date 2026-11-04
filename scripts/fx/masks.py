"""Shared shutter/wipe mask utilities."""
from functools import lru_cache
import cv2
import numpy as np
from PIL import Image


def polygon_mask(height,width,vertices):
    mask=np.zeros((height,width),np.float32)
    cv2.fillPoly(mask,[np.rint(vertices).astype(np.int32)],1)
    return mask


@lru_cache(maxsize=24)
def field(width,height,kind,seed=7):
    y,x=np.indices((height,width),dtype=np.float32);x=(x-(width-1)/2)/(width/2);y=(y-(height-1)/2)/(height/2)
    if kind in ('circle','radial'):return np.hypot(x,y)
    if kind=='diamond':return np.abs(x)+np.abs(y)
    if kind=='star':
        angle=np.arctan2(y,x)+np.pi/2;radius=.62+.38*np.cos(5*angle)
        return np.hypot(x,y)/radius
    if kind=='heart':return np.sqrt(x*x+(y+.3*np.sqrt(np.abs(x)))**2)
    if kind=='linear':return x
    if kind=='cloud':
        noise=np.random.default_rng(seed).random((12,20),dtype=np.float32)
        return cv2.GaussianBlur(cv2.resize(noise,(width,height)),(0,0),max(1,width/45))
    with Image.open(kind) as im:return np.asarray(im.convert('L').resize((width,height)),np.float32)


def reveal(value,p,softness=0):
    threshold=np.quantile(value,np.clip(p,0,1))
    mask=(value<=threshold).astype(np.float32)
    return cv2.GaussianBlur(mask,(0,0),softness/2) if softness>0 else mask
