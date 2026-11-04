import cv2
import numpy as np
from ..core import effect

@effect(radius='Gaussian sigma in pixels', warm='Warm highlight spill', amount='Spill gain')
def halation(frame, t_ms, ctx, amount=0.8, radius=6.0, warm=True, threshold=0.65):
    """Local highlight bloom; alpha never expands."""
    highlights = np.maximum(frame[..., :3]-threshold,0)/(1-threshold+1e-6)*frame[...,3:4]
    glow = cv2.GaussianBlur(highlights,(0,0),max(.1,radius))
    tint = np.array([1,.55,.2] if warm else [1,1,1],np.float32)
    frame[..., :3] += glow*tint*amount
    return frame
