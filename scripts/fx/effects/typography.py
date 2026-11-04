"""System-font typography; font files are never packaged or copied."""
from functools import lru_cache
from pathlib import Path
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ..core import effect, over, warp, evaluate


def resolve_font(font=''):
    candidates=[font] if font else [os.environ.get('VIDEO_GIF_FONT',''),'C:/Windows/Fonts/msjh.ttc',
        '/System/Library/Fonts/PingFang.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    for name in candidates:
        if name and Path(name).is_file():return str(Path(name).resolve())
    raise ValueError(f'Font not found: {candidates}; use Microsoft JhengHei (Windows), PingFang (macOS), Noto CJK (Linux); provide font path')


@lru_cache(maxsize=32)
def lettering(width,height,content,font,size,color,stroke,stroke_color,shadow_px,shadow_color,x,y):
    face=ImageFont.truetype(font,max(1,round(size)));layer=Image.new('RGBA',(width,height));draw=ImageDraw.Draw(layer)
    box=draw.textbbox((0,0),content,font=face,stroke_width=round(stroke))
    pos=(x-(box[2]+box[0])/2,y-(box[3]+box[1])/2)
    draw.text((pos[0]+shadow_px,pos[1]+shadow_px),content,font=face,fill='#'+shadow_color,stroke_width=round(stroke),stroke_fill='#'+shadow_color)
    draw.text(pos,content,font=face,fill='#'+color,stroke_width=round(stroke),stroke_fill='#'+stroke_color)
    return np.array(layer,dtype=np.float32)/255


@effect(status='experimental',content='Unicode text',font='System font file path; empty searches CJK fonts',size='Font pixels',x='Center x fraction',y='Center y fraction',entrance='pop or scale',amount='Layer opacity',scale='Additional envelope scale')
def text(frame,t,ctx,content='節奏 RHYTHM',font='',size=64.0,color='FFF2CE',stroke=3.0,stroke_color='142132',shadow_px=4.0,shadow_color='080F18',x=.5,y=.5,entrance='pop',amount=1.0,scale=1.0):
    """Centered CJK lettering with stroke, shadow, 180ms entrance and subtle beat pop."""
    if amount==0:return frame
    layer=lettering(ctx.width,ctx.height,content,resolve_font(font),size,color,stroke,stroke_color,shadow_px,shadow_color,ctx.width*x,ctx.height*y).copy()
    elapsed=max(0,t-ctx.effect_start_ms);progress=min(1,elapsed/180)
    entry=(.65+.35*(1-(1-progress)**3)) if entrance=='pop' else .65+.35*progress
    beat=evaluate({'on':'beats','decay_ms':180},t,ctx) if ctx.beats_ms else 0
    matrix=cv2.getRotationMatrix2D((ctx.width*x,ctx.height*y),0,scale*entry*(1+.1*beat))
    layer=warp(layer,matrix,ctx);layer[...,3]*=amount
    return over(layer,frame)
