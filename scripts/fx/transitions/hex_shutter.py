import cv2
import numpy as np
from ..core import transition, premultiply, straight
from ..masks import polygon_mask
from .gl_common import mix, smooth

@transition(style_tags=['幾何', '搶眼/衝擊'], color='Shutter RGB hex')
def hex_shutter(a, b, p, ctx, color='121522'):
    """Six-sided aperture closes at the cut and opens onto the next shot."""
    if p<=0: return a
    if p>=1: return b
    radius = np.hypot(ctx.width,ctx.height)*.62*abs(2*p-1)
    angles = np.arange(6)*np.pi/3
    vertices = np.round(np.column_stack((ctx.width/2+radius*np.cos(angles),ctx.height/2+radius*np.sin(angles)))).astype(np.int32)
    mask = polygon_mask(ctx.height,ctx.width,vertices) if radius>0 else np.zeros((ctx.height,ctx.width),np.float32)
    source = a if p<.5 else b
    opaque = bool(np.all(a[...,3]==1) and np.all(b[...,3]==1))
    if not opaque:
        source = mix(premultiply(a),premultiply(b),smooth(.47,.53,p))
    result = np.ones_like(a); result[...,:3] = np.array([int(color.lstrip('#')[i:i+2],16)/255 for i in (0,2,4)])
    result[...,3] = source[...,3]
    if not opaque:
        result[...,:3] *= result[...,3:4]
    out = source*mask[...,None]+result*(1-mask[...,None])
    return out if opaque else straight(out)
