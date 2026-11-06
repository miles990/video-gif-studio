"""Consistent icon sets with measurable style tokens and isolated retries."""
from dataclasses import replace
from pathlib import Path
import math
import cv2
import numpy as np
from PIL import Image
from image_common import ImageError,digest,key,read,write
from game_character import rgba,quantize,originality


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
        width=float(np.percentile(distance[ring],90)) if ring.any() else 0
        hsv=cv2.cvtColor(a[...,:3],cv2.COLOR_RGB2HSV).astype(float);content=mask&~ring
        y,x=np.where(content);light='n/a';r2=0
        if len(x)>3:
            values=(a[...,:3]@np.array([.2126,.7152,.0722]))[content]
            design=np.column_stack((x,y,np.ones(len(x))));fit=np.linalg.lstsq(design,values,rcond=None)[0];pred=design@fit
            r2=1-float(((values-pred)**2).sum()/max(1e-9,((values-values.mean())**2).sum()))
            if r2>=.05:light=float(np.degrees(np.arctan2(-fit[1],-fit[0]))%360)
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
    return dict(status='PASS' if not issues else 'FAIL',icons=rows,issues=issues,outlier_indices=sorted({r['index'] for r in issues}),light_circular_std_deg=spread)


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
    for i in indices:
        refs=[str(accepted.resolve())] if accepted else []
        prompt=f'Original game item icon: {items[i]}. {request.prompt}. Same exact style token: {token}. Single icon, transparent, {grid}x{grid} grid, safe margin {token["safe_margin"]} pixels, no text.'
        result=adapter.generate(replace(request,prompt=prompt,refs=refs,transparent=True,n=1),out/'generation'/f'{i:02d}-{len(previous.get("repairs",[])) if previous else 0}',no_cache=fix)
        im=rgba(result['assets'][0]['path']).resize((grid,grid),Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS)
        if pixel:im=quantize(im,[p if isinstance(p,dict) else dict(hex=p) for p in token['palette']])
        im.save(paths[i]);records[i]=dict(index=i,item=items[i],file=paths[i].name,sha256=digest(paths[i]),refs_sent=[digest(p) for p in refs],style_token_sha=token_sha)
        generations.append(result)
        if style_qa([im],token,pixel)['status']=='PASS' and accepted is None:accepted=paths[i]
    images=[rgba(p) for p in paths];qa=style_qa(images,token,pixel)
    if previous:
        for i,p in enumerate(paths):
            if i not in indices and digest(p)!=before[i]:raise ImageError('E_ICON_FIX','Unselected icon changed unexpectedly.')
    sheet=Image.new('RGBA',(grid*4,grid*math.ceil(len(images)/4)))
    for i,im in enumerate(images):sheet.paste(im,((i%4)*grid,(i//4)*grid))
    sheet.save(out/'sheet.png');write(out/'style.json',token)
    result=dict(status='experimental',items=items,style_token_sha=token_sha,records=records,qa=qa,repairs=[*(previous.get('repairs',[]) if previous else []),dict(indices=indices,before=before)] if fix else [],review='pending')
    write(out/'iconset.json',result);write(out/'gen-manifest.json',dict(originality=originality(' '.join(items)),generations=generations,style_token_sha=token_sha,fallback='pixel_quantize' if pixel else None))
    return result
