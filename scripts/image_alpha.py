"""Transparent sticker QA/cleanup; detects painted checkerboards before matting."""
from dataclasses import replace
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from image_common import ImageError,c2pa,digest,write


def checkerboard(a):
    rgb=a[...,:3].astype(float);h,w=rgb.shape[:2]
    if a.shape[2]==4 and np.any(a[...,3]<255):return False
    # Require a periodic neutral two-colour pattern along >=3 frame edges.
    lines=[rgb[min(2,h-1)],rgb[max(0,h-3)],rgb[:,min(2,w-1)],rgb[:,max(0,w-3)]]
    hits=0
    for line in lines:
        if len(line)<64 or np.mean(np.ptp(line,axis=1)<5)<.95:continue
        y=line.mean(axis=1);lo,hi=np.percentile(y,[10,90]);difference=hi-lo
        if not 10<=difference<=60:continue
        if np.mean(np.minimum(abs(y-lo),abs(y-hi))<4)<.9:continue
        y=y-y.mean()
        for block in range(8,33):
            if len(y)<=2*block+2:continue
            def corr(shift):return float(np.dot(y[:-shift],y[shift:])/max(np.sqrt(np.sum(y[:-shift]**2)*np.sum(y[shift:]**2)),1e-9))
            if corr(2*block)>=.5 and corr(block)<=-.5:
                hits+=1;break
    return hits>=3


def nearest_opaque(a):
    opaque=(a[...,3]>=250)
    if not opaque.any():return None,None
    distance,labels=cv2.distanceTransformWithLabels((~opaque).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
    colors=np.zeros((int(labels.max())+1,3),np.uint8)
    colors[labels[opaque]]=a[...,:3][opaque]
    return colors[labels],distance


def alpha_qa(image):
    from shot_match import lab,delta_e
    a=np.array(image.convert('RGBA'));alpha=a[...,3];visible=alpha>0
    frame=np.zeros(alpha.shape,bool);frame[:2]=True;frame[-2:]=True;frame[:,:2]=True;frame[:,-2:]=True
    fake=checkerboard(a);fraction=float(np.mean(alpha==0));clear_border=float(np.mean(alpha[frame]==0))
    n,labels,stats,_=cv2.connectedComponentsWithStats(visible.astype('uint8'),8)
    areas=stats[1:,cv2.CC_STAT_AREA];largest=int(areas.max()) if len(areas) else 0
    specks=(int(areas.sum())-largest)/max(largest,1)
    nearest,distance=nearest_opaque(a);semi=(alpha>0)&(alpha<250)
    halo_good=None
    if nearest is not None and semi.any():
        edge=semi&(distance<=5)
        if edge.any():halo_good=float(np.mean(delta_e(lab(a[...,:3]),lab(nearest))[edge]<=20))
    center=(alpha>=128).astype('uint8');outer=cv2.dilate(center,np.ones((7,7),np.uint8)).astype(bool)&~center.astype(bool)
    luma=a[...,:3]@np.array([.2126,.7152,.0722])*(alpha/255)
    black_outer=float(luma[outer].mean()) if outer.any() else 0.
    # Enclosed nonopaque components; outside-connected alpha is not an interior hole.
    hn,hl,hs,_=cv2.connectedComponentsWithStats((alpha<250).astype('uint8'),8)
    boundary=set(np.unique(hl[frame]));holes=0;negative_space=0
    for i in range(1,hn):
        if i in boundary:continue
        area=int(hs[i,cv2.CC_STAT_AREA]);values=alpha[hl==i]
        clear=int(np.sum(values==0))
        # Antialiased outlines may surround a fully clear intentional gap.
        if clear>max(64,largest*.005) and clear/area>=.80:
            negative_space+=area
        else:holes+=area
    hole_ratio=holes/max(largest,1)
    issues=[]
    if fake:issues.append('fake_transparency')
    if not .15<=fraction<=.90:issues.append('transparent_fraction')
    if clear_border<.99:issues.append('clipped_border')
    if specks>.001:issues.append('isolated_specks')
    if hole_ratio>.005:issues.append('interior_holes')
    if halo_good is not None and halo_good<.95 or black_outer>8:issues.append('halo')
    return dict(status='PASS' if not issues else 'FAIL',issues=issues,fake_transparency=fake,
                transparent_fraction=fraction,clear_border_fraction=clear_border,speck_ratio=specks,
                interior_hole_ratio=hole_ratio,designed_negative_space_pixels=negative_space,halo_good_fraction=halo_good,black_outer_luma=black_outer,
                fractional_alpha_pixels=int(np.sum((alpha>0)&(alpha<255))),visual_review='pending')


def cleanup(image):
    from shot_match import lab,delta_e
    a=np.array(image.convert('RGBA'));before=alpha_qa(image)
    n,labels,stats,_=cv2.connectedComponentsWithStats((a[...,3]>0).astype('uint8'),8)
    areas=stats[1:,cv2.CC_STAT_AREA];removed=0
    if len(areas):
        largest=int(areas.max())
        for label in range(1,n):
            if stats[label,cv2.CC_STAT_AREA]<=max(4,largest*.01):
                pixels=labels==label;removed+=int(pixels.sum());a[pixels]=0
    # Hard stickers sometimes have attached white fragments as well as detached
    # specks. Smooth only near-binary silhouettes; retain genuine soft assets.
    visible=a[...,3]>0
    hard_sticker=bool(visible.any() and np.mean(a[...,3][visible]>=240)>.90)
    if hard_sticker:
        radius=max(1,min(3,round(min(image.size)/400)))
        kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,2*radius+1))
        silhouette=cv2.morphologyEx((a[...,3]>=128).astype('uint8')*255,cv2.MORPH_OPEN,kernel)
        silhouette=cv2.erode(silhouette,np.ones((3,3),np.uint8))
        envelope=cv2.GaussianBlur(silhouette.astype('float32'),(0,0),.4)
        a[...,3]=np.minimum(a[...,3],np.rint(envelope).astype('uint8'))
    nearest,distance=nearest_opaque(a);recolored=0
    if nearest is not None:
        edge=(a[...,3]>0)&(a[...,3]<250)&(distance<=5)
        bad=edge&(delta_e(lab(a[...,:3]),lab(nearest))>20)
        recolored=int(bad.sum());a[...,:3][bad]=nearest[bad]
    result=Image.fromarray(a)
    return result,dict(before=before,after=alpha_qa(result),removed_speck_pixels=removed,despilled_pixels=recolored,hard_sticker_edge_cleanup=hard_sticker,
                       alpha_policy='preserve graded alpha except isolated components; straight RGB edge despill')


def matte_uniform(image,background):
    a=np.array(image.convert('RGBA'));rgb=a[...,:3].astype(float);bg=np.array(background,float)
    distance=np.linalg.norm(rgb-bg,axis=2)
    a[...,3]=np.minimum(a[...,3],np.rint(np.clip((distance-8)/32,0,1)*255).astype('uint8'))
    # Remove known backing colour from mixed edge pixels before nearest-colour cleanup.
    alpha=a[...,3:4]/255
    a[...,:3]=np.rint(np.clip((rgb-(1-alpha)*bg)/np.maximum(alpha,1/255),0,255)).astype('uint8')
    return cleanup(Image.fromarray(a))[0]


def choose_backing(image):
    from shot_match import lab,delta_e
    rgb=np.array(image.convert('RGB').resize((32,32)))
    candidates=np.array([[0,255,0],[255,0,255],[0,0,255],[0,255,255]],np.uint8)
    # Maximize separation from the visible subject's dominant colours.
    palette=Image.fromarray(rgb).quantize(colors=5)
    colors=np.array(palette.getpalette(),np.uint8).reshape(-1,3)
    dominant=np.array([colors[i] for _,i in sorted(palette.getcolors(),reverse=True)[:3]])
    distances=delta_e(lab(candidates[:,None,:]),lab(dominant[None,:,:]))
    scores=distances.min(axis=1);idx=int(scores.argmax())
    if scores[idx]<30:raise ImageError('E_MATTING','No safe solid backing colour found.')
    return candidates[idx].tolist(),float(scores[idx])


def transparent_asset(adapter,req,out,approval=None,max_usd=0,no_cache=False):
    if req.n!=1:raise ImageError('E_COUNT','Transparent asset QA processes one image per request; use separate output directories.')
    out=Path(out).resolve();raw=adapter.generate(replace(req,transparent=True),out/'native',approval,max_usd,no_cache)
    source=Path(raw['assets'][0]['path'])
    with Image.open(source) as im:
        native=im.convert('RGBA');report=alpha_qa(native)
    alpha_source='native';fallback=None;backing=None
    if report['fake_transparency'] or np.all(np.array(native)[...,3]==255):
        adapter.invalidate(raw['cache_key'],'native transparency QA failed')
        backing,separation=choose_backing(native);hexcolor='#'+''.join(f'{c:02X}' for c in backing)
        retry=replace(req,transparent=False,prompt=req.prompt+f'\nUse a perfectly uniform {hexcolor} background, no checkerboard, no shadows on the background.')
        raw=adapter.generate(retry,out/'matting-source',approval,max_usd)
        source=Path(raw['assets'][0]['path'])
        with Image.open(source) as im:native=matte_uniform(im,backing)
        alpha_source='matted';fallback='solid_background_chroma_matte'
    cleaned,clean_report=cleanup(native)
    if clean_report['after']['status']!='PASS':
        adapter.invalidate(raw['cache_key'],'final alpha QA failed')
        write(out/'alpha-qa.json',clean_report)
        raise ImageError('E_ALPHA','Transparent asset did not pass alpha QA; no final asset delivered.',report=clean_report)
    cleaned.save(out/'asset.png');binary=np.array(cleaned);binary[...,3]=np.where(binary[...,3]<128,0,255)
    Image.fromarray(binary).save(out/'asset-gif-alpha.png')
    from gif_pipeline import encode,verify
    encode([Image.fromarray(binary)],[100],out/'asset.gif')
    verify(out/'asset.gif',[Image.fromarray(binary)],[100])
    for name,color in [('black',(0,0,0,255)),('white',(255,255,255,255)),('magenta',(255,0,255,255))]:
        composite=Image.new('RGBA',cleaned.size,color);composite.alpha_composite(cleaned);composite.convert('RGB').save(out/f'on-{name}.png')
    result=dict(raw,alpha_source=alpha_source,fallback=fallback,matting_background=backing,cleanup=clean_report,
                derived_from=dict(sha256=digest(source),**c2pa(source)),asset=str(out/'asset.png'),ai_generated=True)
    write(out/'gen-manifest.json',result);write(out/'alpha-qa.json',clean_report);return result
