import cv2
from ..core import effect, warp

@effect(amount='Envelope strength', translate_px='Upward displacement at peak', rotation_deg='Peak rotation', scale='Peak scale multiplier', sampling='linear or nearest')
def beat_bounce(frame, t_ms, ctx, amount=1.0, translate_px=8.0, rotation_deg=2.0, scale=1.01, sampling='linear'):
    """A card accent, never a substitute for character movement."""
    matrix = cv2.getRotationMatrix2D(((ctx.width-1)/2,(ctx.height-1)/2),rotation_deg*amount,1+(scale-1)*amount)
    matrix[1,2] -= translate_px*amount
    return warp(frame,matrix,ctx,sampling)
