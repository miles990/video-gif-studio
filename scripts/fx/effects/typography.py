"""System-font typography; font files are never packaged or copied."""
from functools import lru_cache
from pathlib import Path
import os
import struct
import warnings
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


@lru_cache(maxsize=16)
def font_codepoints(font):
    """Read Unicode cmap 4/12 from TTF/OTF or first TTC face; no fontTools dependency."""
    data = Path(font).read_bytes()
    u16 = lambda at: struct.unpack_from('>H', data, at)[0]
    u32 = lambda at: struct.unpack_from('>I', data, at)[0]
    base = u32(12) if data[:4] == b'ttcf' else 0
    cmap = None
    for i in range(u16(base+4)):
        at = base+12+16*i
        if data[at:at+4] == b'cmap': cmap = u32(at+8); break
    if cmap is None: raise ValueError('Font has no Unicode cmap: '+font)
    found = set()
    for i in range(u16(cmap+2)):
        at = cmap+4+8*i; platform, encoding = u16(at), u16(at+2)
        if platform != 0 and not (platform == 3 and encoding in (1,10)): continue
        table = cmap+u32(at+4); fmt = u16(table)
        if fmt == 12:
            for j in range(u32(table+12)):
                first, last, glyph = struct.unpack_from('>III', data, table+16+j*12)
                found.update(range(first+(glyph == 0), last+1))
        elif fmt == 4:
            count = u16(table+6)//2; ends = table+14
            starts = ends+2*count+2; deltas = starts+2*count; offsets = deltas+2*count
            for j in range(count):
                first, last = u16(starts+2*j), u16(ends+2*j)
                delta, offset = u16(deltas+2*j), u16(offsets+2*j)
                for code in range(first, min(last,65534)+1):
                    glyph = u16(offsets+2*j+offset+2*(code-first)) if offset else code
                    if glyph and (glyph+delta)&65535: found.add(code)
    return frozenset(found)


@lru_cache(maxsize=128)
def check_glyphs(font, content, strict=False):
    missing = sorted({ord(c) for c in content if not c.isspace()}-font_codepoints(font))
    if missing:
        message = 'Missing glyphs in '+font+': '+', '.join(f'U+{c:04X}' for c in missing)
        warnings.warn(message, UserWarning, stacklevel=2)
        if strict: raise ValueError(message+'; choose a font covering these code points')
    return missing


@lru_cache(maxsize=32)
def lettering(width,height,content,font,size,color,stroke,stroke_color,shadow_px,shadow_color,x,y):
    check_glyphs(font,content)
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
