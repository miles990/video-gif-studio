import cv2
from ..core import effect, warp

@effect(amount='Envelope strength', scale='Peak zoom', sampling='linear or nearest')
def zoom_punch(frame, t_ms, ctx, amount=1.0, scale=1.014, sampling='linear'):
    """Centered camera punch; use scale=1.2 for a strong opaque shot."""
    matrix = cv2.getRotationMatrix2D(((ctx.width-1)/2,(ctx.height-1)/2),0,1+(scale-1)*amount)
    return warp(frame,matrix,ctx,sampling)
