"""Monochrome emoji shaping for Windows Pillow builds without libraqm.

Use the installed font and OS Uniscribe shaper; no font files or emoji art bundled.
The resulting single grapheme mask is cached, including its joined modifiers.
"""
from functools import lru_cache
import sys

from PIL import Image, ImageFilter, features


@lru_cache(maxsize=256)
def emoji_mask(text, family, size):
    if sys.platform!='win32' or features.check('raqm'): return None
    import ctypes as c
    from ctypes import wintypes as w
    gdi=c.WinDLL('gdi32');usp=c.WinDLL('usp10')
    gdi.CreateCompatibleDC.argtypes=[w.HDC];gdi.CreateCompatibleDC.restype=w.HDC
    gdi.CreateFontW.argtypes=[c.c_int]*5+[w.DWORD]*8+[w.LPCWSTR];gdi.CreateFontW.restype=w.HANDLE
    gdi.SelectObject.argtypes=[w.HDC,w.HANDLE];gdi.SelectObject.restype=w.HANDLE
    gdi.DeleteObject.argtypes=[w.HANDLE];gdi.DeleteDC.argtypes=[w.HDC]
    gdi.SetTextColor.argtypes=[w.HDC,w.DWORD];gdi.SetBkColor.argtypes=[w.HDC,w.DWORD]
    class BitmapInfo(c.Structure):
        _fields_=[('size',w.DWORD),('width',w.LONG),('height',w.LONG),('planes',w.WORD),
                  ('bits',w.WORD),('compression',w.DWORD),('image',w.DWORD),('x',w.LONG),
                  ('y',w.LONG),('used',w.DWORD),('important',w.DWORD)]
    gdi.CreateDIBSection.argtypes=[w.HDC,c.POINTER(BitmapInfo),w.UINT,c.POINTER(c.c_void_p),w.HANDLE,w.DWORD]
    gdi.CreateDIBSection.restype=w.HANDLE
    usp.ScriptStringAnalyse.argtypes=[w.HDC,c.c_void_p,c.c_int,c.c_int,c.c_int,w.DWORD,c.c_int,
                                     c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p,c.POINTER(c.c_void_p)]
    usp.ScriptStringOut.argtypes=[c.c_void_p,c.c_int,c.c_int,w.UINT,c.c_void_p,c.c_int,c.c_int,w.BOOL]
    usp.ScriptStringFree.argtypes=[c.POINTER(c.c_void_p)]
    dc=gdi.CreateCompatibleDC(None);font=bitmap=old_font=old_bitmap=None;analysis=c.c_void_p()
    try:
        font=gdi.CreateFontW(-size,0,0,0,400,0,0,0,1,0,0,4,0,family)
        if not dc or not font: raise ValueError('Cannot create native caption font')
        old_font=gdi.SelectObject(dc,font)
        width=max(size*4,size*len(text)*2);height=size*3
        info=BitmapInfo(c.sizeof(BitmapInfo),width,-height,1,32,0,0,0,0,0,0);bits=c.c_void_p()
        bitmap=gdi.CreateDIBSection(dc,c.byref(info),0,c.byref(bits),None,0)
        if not bitmap: raise ValueError('Cannot allocate caption glyph mask')
        old_bitmap=gdi.SelectObject(dc,bitmap)
        c.memset(bits,0,width*height*4)
        gdi.SetTextColor(dc,0xffffff);gdi.SetBkColor(dc,0)
        buffer=c.create_unicode_buffer(text)
        # SSA_GLYPHS | SSA_FALLBACK, length in UTF-16 code units.
        status=usp.ScriptStringAnalyse(dc,buffer,len(text.encode('utf-16-le'))//2,0,-1,0xa0,width,None,None,None,None,None,c.byref(analysis))
        if status<0 or usp.ScriptStringOut(analysis,size//2,size//2,0,None,0,0,False)<0:
            raise ValueError('Cannot shape caption grapheme with the installed font')
        gdi.GdiFlush()
        mask=Image.frombytes('RGB',(width,height),c.string_at(bits,width*height*4),'raw','BGRX').getchannel('R')
        box=mask.getbbox()
        if not box: raise ValueError('Native caption grapheme has no visible glyph')
        return mask.crop(box)
    finally:
        if analysis:usp.ScriptStringFree(c.byref(analysis))
        if old_bitmap:gdi.SelectObject(dc,old_bitmap)
        if old_font:gdi.SelectObject(dc,old_font)
        if bitmap:gdi.DeleteObject(bitmap)
        if font:gdi.DeleteObject(font)
        if dc:gdi.DeleteDC(dc)


def draw_grapheme(draw, pos, text, font, fill, stroke_width, stroke_fill, mask=None):
    if mask is None:
        draw.text(pos,text,font=font,fill=fill,stroke_width=stroke_width,stroke_fill=stroke_fill)
        return
    # Match the baseline offset used by CaptionRenderer's native glyph metrics.
    x,y=round(pos[0]),round(pos[1]+font.size*.15)
    if stroke_width:
        expanded=Image.new('L',(mask.width+2*stroke_width,mask.height+2*stroke_width))
        expanded.paste(mask,(stroke_width,stroke_width))
        expanded=expanded.filter(ImageFilter.MaxFilter(2*stroke_width+1))
        draw.bitmap((x-stroke_width,y-stroke_width),expanded,fill=stroke_fill)
    draw.bitmap((x,y),mask,fill=fill)
