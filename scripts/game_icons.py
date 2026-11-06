"""Consistent icon sets with measurable style tokens and isolated retries."""
from dataclasses import replace
from pathlib import Path
import math
import cv2
import numpy as np
from PIL import Image
from image_common import ImageError,digest,key,read,write
from game_character import rgba,quantize,originality,require_alpha,ensure_sprite_alpha


def outline_width(mask,line):
    """Median inward boundary run, excluding deep same-color material fills.

    Connected dark boot soles/internal ink are not the exterior stroke thickness.
    Distance percentiles over the whole dark component conflate those features.
    """
    distance=cv2.distanceTransform(mask.astype(np.uint8),cv2.DIST_L2,5)
    gx=cv2.Sobel(distance,cv2.CV_32F,1,0,ksize=3);gy=cv2.Sobel(distance,cv2.CV_32F,0,1,ksize=3)
    yy,xx=np.where(line&(distance<=1.1));runs=[];h,w=mask.shape
    for x,y in zip(xx,yy):
        vector=np.array([gx[y,x],gy[y,x]],float);length=np.linalg.norm(vector)
        if length<.01:continue
        vector/=length;visited=set();run=0
        for step in range(max(3,min(h,w)//5)+1):
            px,py=np.rint([x,y]+vector*step).astype(int)
            if (px,py) in visited:continue
            visited.add((px,py))
            if not 0<=px<w or not 0<=py<h or not mask[py,px] or not line[py,px]:break
            run+=1
        if 0<run<min(h,w)//5:runs.append(run)
    return float(np.median(runs)) if runs else 0.


def style_qa(images,token,pixel=False):
    from shot_match import lab,delta_e
    grid=int(token['grid']);outline=np.array(tuple(bytes.fromhex(token['outline_hex'].lstrip('#'))),np.uint8)
    rows=[];issues=[]
    for i,im in enumerate(images):
        a=np.array(im.convert('RGBA'));mask=a[...,3]>127;box=im.getbbox()
        if not box:raise ImageError('E_ICON_EMPTY','Icon has no visible pixels.',index=i)
        x0,y0,x1,y1=box;area=(x1-x0)*(y1-y0)/(grid*grid);margin=min(x0,y0,im.width-x1,im.height-y1)
        distance=cv2.distanceTransform(mask.astype(np.uint8),cv2.DIST_L2,5)
        line=mask&(delta_e(lab(a[...,:3]),lab(outline[None,None,:]))<=5)
        # Only outline connected to the exterior belongs to the stroke measurement.
        n,labels,stats,_=cv2.connectedComponentsWithStats(line.astype(np.uint8),8)
        exterior=line&(distance<=1.5);keep=np.unique(labels[exterior]);ring=line&np.isin(labels,keep[keep>0])
        width=outline_width(mask,ring)
        hsv=cv2.cvtColor(a[...,:3],cv2.COLOR_RGB2HSV).astype(float);content=mask&~ring
        y,x=np.where(content);light='n/a';r2=0
        if len(x)>3:
            values=(a[...,:3]@np.array([.2126,.7152,.0722]))[content]
            design=np.column_stack((x,y,np.ones(len(x))));fit=np.linalg.lstsq(design,values,rcond=None)[0];pred=design@fit
            variance=float(((values-values.mean())**2).sum())
            r2=1-float(((values-pred)**2).sum()/variance) if variance>1e-6 else 0.
            # Image y grows downward; report the light direction in ordinary
            # Cartesian degrees (upper-left = 135 degrees).
            if r2>=.05:light=float(np.degrees(np.arctan2(-fit[1],fit[0]))%360)
        row=dict(index=i,canvas=list(im.size),bbox_area_fraction=area,safe_margin=margin,outline_px=width,light=light,light_r_squared=r2,
                 saturation=float(hsv[...,1][mask].mean()),value=float(hsv[...,2][mask].mean()))
        rows.append(row)
        if im.size!=(grid,grid) or margin<token['safe_margin'] or not .35<=area<=.85:issues.append(dict(index=i,kind='size_or_margin',value=area))
        if abs(width-token['outline_px'])>(.01 if pixel else .5):issues.append(dict(index=i,kind='outline',value=width))
        if light!='n/a':
            delta=abs((light-token['light_deg']+180)%360-180)
            if delta>30:issues.append(dict(index=i,kind='light',delta_degrees=delta))
        if pixel:
            allowed={tuple(bytes.fromhex((p['hex'] if isinstance(p,dict) else p).lstrip('#'))) for p in token['palette']}
            new=set(map(tuple,a[...,:3][mask]))-allowed
            if new:issues.append(dict(index=i,kind='new_colors',count=len(new)))
    for field,threshold in [('bbox_area_fraction',.25),('saturation',.20),('value',.20)]:
        values=np.array([r[field] for r in rows]);center=float(np.median(values));cv=float(values.std()/max(1e-9,values.mean()))
        if cv>threshold or any(abs(v-center)>threshold*max(center,1) for v in values):
            for i,v in enumerate(values):
                if abs(v-center)>threshold*max(center,1e-6):issues.append(dict(index=i,kind=field+'_outlier',value=float(v),group_cv=cv))
    angles=np.array([r['light'] for r in rows if r['light']!='n/a']);spread=None
    if len(angles)>1:
        resultant=abs(np.mean(np.exp(1j*np.radians(angles))));spread=float(np.degrees(np.sqrt(-2*np.log(max(1e-9,resultant)))))
        if spread>20:
            mean=np.degrees(np.angle(np.mean(np.exp(1j*np.radians(angles)))))%360
            for r in rows:
                if r['light']!='n/a' and abs((r['light']-mean+180)%360-180)>20:issues.append(dict(index=r['index'],kind='light_group_outlier'))
    light_mean=float(np.degrees(np.angle(np.mean(np.exp(1j*np.radians(angles)))))%360) if len(angles) else None
    drift=dict(outline_px=float(np.median([r['outline_px'] for r in rows]))-token['outline_px'],
               padding_shortfall_px=max(0,token['safe_margin']-min(r['safe_margin'] for r in rows)),
               light_deg=abs((light_mean-token['light_deg']+180)%360-180) if light_mean is not None else None,
               light_assessed_items=len(angles),comparison='whole-set median/circular mean versus style token')
    return dict(status='PASS' if not issues else 'FAIL',icons=rows,issues=issues,outlier_indices=sorted({r['index'] for r in issues}),light_circular_std_deg=spread,set_drift=drift)


def fit_icon(im,token,pixel=False):
    """Restore safe padding before quantization; retain lighting for honest QA."""
    grid=token['grid'];box=im.getbbox()
    if not box:raise ImageError('E_ICON_EMPTY','Generated icon is empty.')
    # Leave already compliant native pixel canvases untouched.
    margin=min(box[0],box[1],im.width-box[2],im.height-box[3])
    if im.size==(grid,grid) and margin>=token['safe_margin']:return im
    crop=im.crop(box);side=grid-2*token['safe_margin'];scale=side/max(crop.size)
    size=(max(1,round(crop.width*scale)),max(1,round(crop.height*scale)))
    palette=[p if isinstance(p,dict) else dict(hex=p) for p in token['palette']]
    crop=quantize(crop,palette,size) if pixel else crop.resize(size,Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(grid,grid));canvas.paste(crop,((grid-size[0])//2,(grid-size[1])//2))
    return canvas


def iconset(adapter,request,items,token,out,pixel=False,fix=False):
    token=read(token) if isinstance(token,(str,Path)) else token;out=Path(out);originality(' '.join(items)+' '+request.prompt)
    if not 1<=len(items)<=40 or not 16<=int(token['grid'])<=1024:raise ImageError('E_ICONSET','Invalid icon count or grid.')
    token_sha=key(token);grid=token['grid'];out.mkdir(parents=True,exist_ok=True);paths=[out/f'{i:02d}.png' for i in range(len(items))]
    previous=read(out/'iconset.json') if fix and (out/'iconset.json').exists() else None
    if fix and previous is None:raise ImageError('E_ICON_FIX','--fix requires an existing icon set.')
    if previous and (previous['style_token_sha']!=token_sha or previous['items']!=items):raise ImageError('E_ICON_FIX','Style token/items changed; create a new set instead.')
    before=[digest(p) for p in paths] if previous else []
    indices=style_qa([rgba(p) for p in paths],token,pixel)['outlier_indices'] if previous else list(range(len(items)))
    records=list(previous['records']) if previous else [None]*len(items);generations=[]
    accepted=next((paths[i] for i in range(len(paths)) if i not in indices and paths[i].exists()),None)
    anchor=out/'style-anchor.png'
    if not previous:
        anchor_result=adapter.generate(replace(request,prompt=f'Original neutral faceted shield style anchor. Exact style token: {token}. ONE object, no text, transparent background. This image defines outline, palette, upper-left lighting and spacing for an inventory set.',refs=[],transparent=True,n=1),out/'generation/style-anchor')
        anchor_im,anchor_alpha=ensure_sprite_alpha(rgba(anchor_result['assets'][0]['path']))
        anchor_im=fit_icon(anchor_im,token,pixel);anchor_im.save(anchor);generations.append(anchor_result)
        anchor_record=dict(source='generated',file=anchor.name,sha256=digest(anchor),token=token,qa=style_qa([anchor_im],token,pixel))
    else:anchor_record=previous.get('style_anchor',{})
    for i in indices:
        refs=[str(accepted.resolve())] if accepted else [str(anchor.resolve())] if anchor.exists() else []
        prompt=f'Original game item icon: {items[i]}. {request.prompt}. Same exact style token: {token}. Single icon, transparent, {grid}x{grid} grid, safe margin {token["safe_margin"]} pixels, no text.'
        result=adapter.generate(replace(request,prompt=prompt,refs=refs,transparent=True,n=1),out/'generation'/f'{i:02d}-{len(previous.get("repairs",[])) if previous else 0}',no_cache=fix)
        im,alpha_source=ensure_sprite_alpha(rgba(result['assets'][0]['path']))
        im=fit_icon(im,token,pixel)
        if pixel:im=quantize(im,[p if isinstance(p,dict) else dict(hex=p) for p in token['palette']],(grid,grid))
        else:im=im.resize((grid,grid),Image.Resampling.LANCZOS)
        im.save(paths[i]);records[i]=dict(index=i,item=items[i],file=paths[i].name,sha256=digest(paths[i]),refs_sent=[digest(p) for p in refs],style_token_sha=token_sha,alpha_source=alpha_source)
        generations.append(result)
        if style_qa([im],token,pixel)['status']=='PASS' and accepted is None:accepted=paths[i]
    images=[rgba(p) for p in paths];qa=style_qa(images,token,pixel)
    if previous:
        for i,p in enumerate(paths):
            if i not in indices and digest(p)!=before[i]:raise ImageError('E_ICON_FIX','Unselected icon changed unexpectedly.')
    sheet=Image.new('RGBA',(grid*4,grid*math.ceil(len(images)/4)))
    for i,im in enumerate(images):sheet.paste(im,((i%4)*grid,(i//4)*grid))
    sheet.save(out/'sheet.png');write(out/'style.json',token)
    result=dict(status='experimental',items=items,style_token_sha=token_sha,style_anchor=anchor_record,records=records,qa=qa,repairs=[*(previous.get('repairs',[]) if previous else []),dict(indices=indices,before=before)] if fix else [],review='pending')
    write(out/'iconset.json',result);write(out/'gen-manifest.json',dict(originality=originality(' '.join(items)),generations=generations,style_token_sha=token_sha,fallback='pixel_quantize' if pixel else None))
    return result
