import numpy as np
import cv2
from ..core import effect

@effect(temp='Warmth: red +temp, blue -temp', sat='Saturation multiplier')
def grade(frame, t_ms, ctx, lift=0.0, gamma=1.0, gain=1.0, sat=1.0, temp=0.0):
    """Lift/gamma/gain, luminance saturation and restrained warmth."""
    if (lift,gamma,gain,sat,temp)==(0,1,1,1,0): return frame
    r,g,b,alpha=cv2.split(frame)
    rgb=cv2.merge([r,g,b])
    if lift: rgb=cv2.add(rgb,(lift,lift,lift,0))
    if gamma!=1: rgb=cv2.pow(cv2.max(rgb,0),1/max(gamma,.001))
    matrix=np.eye(3,dtype=np.float32)*sat+(1-sat)*np.tile(np.array([.2126,.7152,.0722],np.float32),(3,1))
    rgb=cv2.transform(rgb,matrix*gain)
    rgb=cv2.add(rgb,(temp,0,-temp,0))
    return cv2.merge([*cv2.split(rgb),alpha])
