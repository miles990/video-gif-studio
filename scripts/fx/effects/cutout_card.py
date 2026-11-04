import cv2
import numpy as np
from ..core import effect, over, warp

@effect(bg='Empty preserves transparency; otherwise RGB hex', background='Optional image path behind subject', darken='Background brightness multiplier', blur='Background blur sigma', border_px='White border radius', shadow_px='Shadow offset down and right', amount='Card opacity')
def cutout_card(frame, t_ms, ctx, border_px=6.0, shadow_px=7.0, shadow_blur=4.0, bg='', background='', darken=0.4, blur=8.0, amount=1.0):
    """Alpha silhouette, solid white border, soft shadow down/right; clean straight RGB."""
    r = max(0,round(border_px)); alpha = frame[...,3]
    border = cv2.dilate((alpha>.01).astype(np.float32),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1)))
    white = np.ones_like(frame); white[...,3] = border
    shadow = np.zeros_like(frame)
    shifted = cv2.warpAffine(border,np.float32([[1,0,shadow_px],[0,1,shadow_px]]),(ctx.width,ctx.height))
    shadow[...,3] = cv2.GaussianBlur(shifted,(0,0),max(.1,shadow_blur))*.42
    card = over(over(frame,white),shadow); card[...,3] *= amount
    base = np.zeros_like(frame)
    if background:
        from PIL import Image
        with Image.open(background) as im: base = np.asarray(im.convert('RGBA').resize((ctx.width,ctx.height)),dtype=np.float32)/255
        base = cv2.GaussianBlur(base,(0,0),max(.1,blur)); base[...,:3] *= darken
    elif bg:
        base[...,:3] = np.array([int(bg.lstrip('#')[i:i+2],16)/255 for i in (0,2,4)]); base[...,3] = 1
    return over(card,base)
