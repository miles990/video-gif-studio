import cv2
import numpy as np
from ..core import effect

@effect(radius='Gaussian sigma in pixels', warm='Warm highlight spill', amount='Spill gain')
def halation(frame, t_ms, ctx, amount=0.8, radius=6.0, warm=True, threshold=0.65):
    """Local highlight bloom; alpha never expands."""
    if np.min(frame[...,3])>=1:
        highlights=cv2.max(cv2.subtract(frame,(threshold,threshold,threshold,1)),0)
        glow=cv2.GaussianBlur(highlights,(0,0),max(.1,radius))
        tint=(amount,amount*.55,amount*.2,0) if warm else (amount,amount,amount,0)
        return cv2.add(frame,cv2.multiply(glow,tuple(v/(1-threshold+1e-6) for v in tint)))
    channels=cv2.split(frame)
    highlights=cv2.merge([cv2.multiply(cv2.max(cv2.subtract(c,threshold),0),channels[3],scale=1/(1-threshold+1e-6)) for c in channels[:3]])
    glow = cv2.GaussianBlur(highlights,(0,0),max(.1,radius))
    tint = np.array([1,.55,.2] if warm else [1,1,1],np.float32)
    return cv2.merge([cv2.addWeighted(c,1,g,float(tint[i]*amount),0) for i,(c,g) in enumerate(zip(channels[:3],cv2.split(glow)))]+[channels[3]])
