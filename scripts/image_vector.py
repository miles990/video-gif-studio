"""Static SVG safety, local contour tracing and dependency-free traced-path rendering."""
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from xml.parsers import expat
import cv2
import numpy as np
from PIL import Image,ImageColor,ImageDraw
from image_common import ImageError,c2pa,digest,write

ALLOWED={'svg','g','defs','path','rect','circle','ellipse','polygon','polyline','line','linearGradient','radialGradient','stop','clipPath','title','desc'}


def safe_svg(source):
    raw=Path(source).read_bytes() if isinstance(source,Path) else source.encode() if isinstance(source,str) else source
    if len(raw)>2_000_000:raise ImageError('E_SVG_SIZE','SVG exceeds the 2 MB parsing limit.')
    # Expat's DTD/entity/external handlers reject before ElementTree parsing. No
    # optional XML package, entity expansion or resource resolver is needed.
    parser=expat.ParserCreate()
    def reject(*args):raise ImageError('E_SVG_UNSAFE','DTD, entities and external resources are forbidden.')
    parser.StartDoctypeDeclHandler=reject;parser.EntityDeclHandler=reject;parser.ExternalEntityRefHandler=reject
    parser.ProcessingInstructionHandler=reject
    try:parser.Parse(raw,True);root=ET.fromstring(raw)
    except (expat.ExpatError,ET.ParseError) as exc:raise ImageError('E_SVG_PARSE',str(exc)) from None
    if root.tag.split('}')[-1]!='svg':raise ImageError('E_SVG_UNSAFE','Root must be svg.')
    nodes=0
    for node in root.iter():
        tag=node.tag.split('}')[-1];nodes+=1
        if tag not in ALLOWED:raise ImageError('E_SVG_UNSAFE',f'Forbidden SVG node: {tag}. Text must be outlined; embedded raster is forbidden.')
        if nodes>50000:raise ImageError('E_SVG_SIZE','Too many SVG nodes.')
        for name,value in node.attrib.items():
            name=name.split('}')[-1].lower();lower=value.lower()
            if name.startswith('on') or name in ('src','base') or 'javascript:' in lower or '@import' in lower or '\\' in value:
                raise ImageError('E_SVG_UNSAFE',f'Unsafe attribute: {name}.')
            if name=='href' and not value.startswith('#'):raise ImageError('E_SVG_UNSAFE','External href is forbidden.')
            for url in re.findall(r'url\s*\((.*?)\)',value,re.I):
                if not re.fullmatch(r'[\s\'\"]*#[A-Za-z_][\w.-]*[\s\'\"]*',url):raise ImageError('E_SVG_UNSAFE','External CSS URLs are forbidden.')
            if 'url' in lower and not re.search(r'url\s*\(',lower):raise ImageError('E_SVG_UNSAFE','Obfuscated CSS resource reference.')
    return root,dict(status='PASS',nodes=nodes,parser='stdlib Expat with DTD/entity/external/PI rejection',embedded_raster=False)


def trace(image,out,colors=6,tolerance=.5):
    if not 2<=colors<=16 or not 0<=tolerance<=2:raise ImageError('E_VECTOR_PARAMS','Use 2..16 colours and tolerance 0..2 pixels.')
    with Image.open(image) as im:rgba=np.array(im.convert('RGBA'));width,height=im.size
    quantized=Image.fromarray(rgba[...,:3]).quantize(colors=colors,method=Image.Quantize.MEDIANCUT)
    index=np.array(quantized);palette=np.array(quantized.getpalette(),np.uint8).reshape(-1,3)
    paths=[];vertices=0
    for _,colour in sorted(quantized.getcolors(),reverse=True):
        mask=((index==colour)&(rgba[...,3]>=128)).astype('uint8')
        contours,_=cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        commands=[]
        for contour in contours:
            points=cv2.approxPolyDP(contour,tolerance,True).reshape(-1,2)
            if len(points)<3:continue
            vertices+=len(points)
            commands.append('M '+' L '.join(f'{x},{y}' for x,y in points)+' Z')
        if commands:
            hexcolor='#'+''.join(f'{v:02x}' for v in palette[colour])
            paths.append(f'<path fill="{hexcolor}" fill-rule="evenodd" d="'+ ' '.join(commands)+'"/>')
    if not paths:raise ImageError('E_VECTOR_EMPTY','No visible graphic to trace.')
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'+''.join(paths)+'</svg>'
    _,safety=safe_svg(svg)
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(svg,encoding='utf-8')
    result=dict(fallback='raster_contour_trace',svg_source='traced',feature_used='local_vectorization',
                renderer='local polygon renderer v1',trace=dict(backend='OpenCV '+cv2.__version__,colors=colors,tolerance_px=tolerance,vertices=vertices),
                safety=safety,bytes=out.stat().st_size,path=str(out.resolve()),derived_from=dict(sha256=digest(image),**c2pa(image)),
                note='Best for flat keyframe graphics; tracing is not semantic font reconstruction. Inspect lettering and fine details.')
    write(out.with_suffix('.json'),result);return result


def polygons(data):
    tokens=re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',data)
    i=0;result=[];current=[];command=None;x=y=0.
    while i<len(tokens):
        if tokens[i].isalpha():command=tokens[i];i+=1
        if command in ('Z','z'):
            if current:result.append(current);current=[]
            command=None;continue
        if command not in ('M','L','H','V','m','l','h','v'):raise ImageError('E_SVG_RENDER','Local renderer supports polygon paths M/L/H/V/Z. Use an installed SVG rasterizer for curves.')
        count=1 if command.lower() in ('h','v') else 2
        if i+count>len(tokens):raise ImageError('E_SVG_RENDER','Incomplete path.')
        values=[float(v) for v in tokens[i:i+count]];i+=count
        if not all(math.isfinite(v) and abs(v)<1e7 for v in values):raise ImageError('E_SVG_RENDER','Invalid path coordinate.')
        relative=command.islower()
        if command.lower()=='h':x=values[0]+(x if relative else 0)
        elif command.lower()=='v':y=values[0]+(y if relative else 0)
        else:
            x,y=values[0]+(x if relative else 0),values[1]+(y if relative else 0)
            if command.lower()=='m' and current:result.append(current);current=[]
        current.append((x,y))
        if command=='M':command='L'
        elif command=='m':command='l'
    if current:result.append(current)
    return result


def rasterize(path,short_side=None):
    root,_=safe_svg(Path(path));box=[float(x) for x in root.get('viewBox','').replace(',',' ').split()]
    if len(box)!=4 or box[2]<=0 or box[3]<=0:raise ImageError('E_SVG_RENDER','A positive viewBox is required.')
    width,height=box[2:];scale=(short_side/min(width,height)) if short_side else 1
    size=(round(width*scale),round(height*scale))
    if min(size)<1 or max(size)>8192:raise ImageError('E_SVG_RENDER','Raster dimensions must be 1..8192.')
    ss=2;canvas=Image.new('RGBA',(size[0]*ss,size[1]*ss));factor=scale*ss
    def draw_node(node,inherited):
        style=dict(inherited,**node.attrib)
        for item in style.get('style','').split(';'):
            if ':' in item:
                k,v=item.split(':',1);style[k.strip()]=v.strip()
        tag=node.tag.split('}')[-1]
        if tag in ('defs','title','desc'):return
        if style.get('transform'):raise ImageError('E_SVG_RENDER','Flatten transforms before local polygon rendering.')
        fill=style.get('fill','#000000')
        if fill.startswith('url('):raise ImageError('E_SVG_RENDER','Flatten gradients to palette paths for this local renderer.')
        if tag in ('path','rect','polygon','polyline','circle','ellipse','line'):
            mask=np.zeros((canvas.height,canvas.width),np.uint8)
            paths=[]
            if tag=='path':paths=polygons(node.get('d',''))
            elif tag in ('polygon','polyline'):
                values=[float(v) for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)',node.get('points',''))]
                paths=[list(zip(values[::2],values[1::2]))]
            elif tag=='rect':
                x,y=float(node.get('x',0)),float(node.get('y',0));w,h=float(node.get('width',0)),float(node.get('height',0))
                paths=[[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]]
            elif tag in ('circle','ellipse'):
                cx,cy=float(node.get('cx',0)),float(node.get('cy',0));rx=float(node.get('r',node.get('rx',0)));ry=float(node.get('r',node.get('ry',0)))
                paths=[[(cx+rx*np.cos(t),cy+ry*np.sin(t)) for t in np.linspace(0,2*np.pi,720,endpoint=False)]]
            elif tag=='line':paths=[[(float(node.get('x1',0)),float(node.get('y1',0))),(float(node.get('x2',0)),float(node.get('y2',0)))]]
            points=[np.rint((np.array(p)-box[:2])*factor).astype('int32') for p in paths]
            if fill!='none' and tag not in ('line','polyline'):
                cv2.fillPoly(mask,points,255)
                layer=Image.new('RGBA',canvas.size,ImageColor.getcolor(fill,'RGBA'));layer.putalpha(Image.fromarray(np.rint(mask*float(style.get('opacity',1))).astype('uint8')));canvas.alpha_composite(layer)
            stroke=style.get('stroke','none')
            if stroke!='none':
                mask[:]=0;cv2.polylines(mask,points,tag not in ('line','polyline'),255,max(1,round(float(style.get('stroke-width',1))*factor)))
                layer=Image.new('RGBA',canvas.size,ImageColor.getcolor(stroke,'RGBA'));layer.putalpha(Image.fromarray(mask));canvas.alpha_composite(layer)
        for child in node:draw_node(child,style)
    draw_node(root,{})
    return canvas.resize(size,Image.Resampling.LANCZOS)


def open_image(path):
    return rasterize(path) if Path(path).suffix.lower()=='.svg' else Image.open(path)
