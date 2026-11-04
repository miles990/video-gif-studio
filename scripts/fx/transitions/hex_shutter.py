import cv2
import numpy as np
from ..core import transition

@transition(color='Shutter RGB hex')
def hex_shutter(a, b, p, ctx, color='121522'):
    """Six-sided aperture closes at the cut and opens onto the next shot."""
    if p<=0: return a
    if p>=1: return b
    radius = np.hypot(ctx.width,ctx.height)*.62*abs(2*p-1)
    angles = np.arange(6)*np.pi/3
    vertices = np.round(np.column_stack((ctx.width/2+radius*np.cos(angles),ctx.height/2+radius*np.sin(angles)))).astype(np.int32)
    mask = np.zeros((ctx.height,ctx.width),np.float32)
    if radius>0: cv2.fillConvexPoly(mask,vertices,1)
    result = np.ones_like(a); result[...,:3] = np.array([int(color.lstrip('#')[i:i+2],16)/255 for i in (0,2,4)])
    return (a if p<.5 else b)*mask[...,None]+result*(1-mask[...,None])
