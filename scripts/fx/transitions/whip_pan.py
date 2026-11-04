import cv2
import numpy as np
from ..core import transition, premultiply, straight

@transition(blur_px='Peak horizontal blur width', direction='left or right')
def whip_pan(a, b, p, ctx, blur_px=49.0, direction='left'):
    """Horizontal camera sweep, with directional motion blur."""
    if p<=0: return a
    if p>=1: return b
    sign = -1 if direction=='left' else 1
    x = sign*ctx.width*(p if p<.5 else p-1)
    source = premultiply(a if p<.5 else b)
    moved = cv2.warpAffine(source,np.float32([[1,0,x],[0,1,0]]),(ctx.width,ctx.height),borderMode=cv2.BORDER_REPLICATE)
    kernel = max(1,round(blur_px*np.sin(np.pi*p)))
    return straight(cv2.blur(moved,(kernel,1)))
