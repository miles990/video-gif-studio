import cv2
import numpy as np
from ..core import transition, premultiply, straight

@transition(blur_px='Peak horizontal blur width', direction='left or right')
def whip_pan(a, b, p, ctx, blur_px=49.0, direction='left'):
    """Horizontal camera sweep, with directional motion blur."""
    if p<=0: return a
    if p>=1: return b
    # One continuous film strip: both shots exist throughout the sweep.
    strip = premultiply(np.concatenate((a,b) if direction=='left' else (b,a),axis=1))
    x = ctx.width*(p if direction=='left' else 1-p)
    kernel = max(1,round(blur_px*np.sin(np.pi*p)))
    strip = cv2.blur(strip,(kernel,1),borderType=cv2.BORDER_REFLECT_101)
    moved = cv2.warpAffine(strip,np.float32([[1,0,-x],[0,1,0]]),(ctx.width,ctx.height),flags=cv2.INTER_LINEAR)
    return straight(moved)
