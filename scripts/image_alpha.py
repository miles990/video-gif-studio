"""Transparent sticker QA/cleanup; detects painted checkerboards before matting."""
from dataclasses import replace
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from image_common import ImageError,c2pa,digest,write

NEAR_ZERO_ALPHA=10


def clear_haze(a):
    """Keep two pixels of true edge coverage, discard remote near-zero haze."""
    a=a.copy();_,distance=nearest_opaque(a)
    haze=(a[...,3]>0)&(a[...,3]<=NEAR_ZERO_ALPHA)
    if distance is not None:haze &= distance>2
    a[haze]=0
    return a,int(haze.sum())


def wall_profile(component, exterior):
    """Ray lengths through enclosing material; limb gaps have unequal walls."""
    depth=cv2.distanceTransform(component.astype('uint8'),cv2.DIST_L2,5)
    cy,cx=np.unravel_index(depth.argmax(),depth.shape);h,w=depth.shape
    radii=np.arange(1,np.hypot(h,w)+1)
    walls=[]
    for angle in np.linspace(0,2*np.pi,32,endpoint=False):
        x=np.rint(cx+radii*np.cos(angle)).astype(int);y=np.rint(cy+radii*np.sin(angle)).astype(int)
        valid=(x>=0)&(x<w)&(y>=0)&(y<h);x=x[valid];y=y[valid]
        leave=np.flatnonzero(~component[y,x]);reach=np.flatnonzero(exterior[y,x])
        if len(leave) and len(reach):walls.append(float(reach[0]-leave[0]))
    return min(walls,default=0),float(np.median(walls)) if walls else 0.


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
    a,_=clear_haze(np.array(image.convert('RGBA')));alpha=a[...,3];visible=alpha>NEAR_ZERO_ALPHA
    frame=np.zeros(alpha.shape,bool);frame[:2]=True;frame[-2:]=True;frame[:,:2]=True;frame[:,-2:]=True
    fake=checkerboard(a);fraction=float(np.mean(alpha<=NEAR_ZERO_ALPHA));clear_border=float(np.mean(alpha[frame]<=NEAR_ZERO_ALPHA))
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
    boundary=set(np.unique(hl[frame]));holes=0;negative_space=0;body_holes=0;geometry=[]
    exterior=np.isin(hl,list(boundary))
    wall_distance=cv2.distanceTransform((~exterior).astype('uint8'),cv2.DIST_L2,5)
    for i in range(1,hn):
        if i in boundary:continue
        area=int(hs[i,cv2.CC_STAT_AREA]);values=alpha[hl==i]
        component=hl==i
        radius=float(cv2.distanceTransform(component.astype('uint8'),cv2.DIST_L2,5).max())
        bridge=float(wall_distance[component].min())
        _,_,w,h,_=hs[i];elongation=max(w,h)/max(1,min(w,h))
        # A thin enclosing ring or elongated limb gap opens into the exterior
        # after crossing a narrow wall. Deep, compact body holes do not.
        thin,median_wall=wall_profile(component,exterior) if radius>=2 else (0,0)
        # Compact holes in opaque body/shaft material are not limb gaps, even
        # when the body is longer in one direction. A limb-bounded gap is
        # elongated/angular relative to its inscribed disk AND has thin walls.
        shape_extent=area/max(np.pi*radius*radius,1)
        limb_gap=shape_extent>=1.4 and ((elongation>=1.4 and bridge<=2*radius) or thin<median_wall/2)
        designed=(values<=NEAR_ZERO_ALPHA).any() and (bridge<=radius or limb_gap)
        geometry.append(dict(area=area,radius_px=radius,wall_px=bridge,elongation=float(elongation),shape_extent=float(shape_extent),minimum_ray_wall=thin,median_ray_wall=median_wall,designed=bool(designed)))
        if designed:
            negative_space+=area
        else:
            holes+=area
            if radius>=2:body_holes+=1
    hole_ratio=holes/max(largest,1)
    issues=[]
    if fake:issues.append('fake_transparency')
    if not .15<=fraction<=.90:issues.append('transparent_fraction')
    if clear_border<.99:issues.append('clipped_border')
    if specks>.001:issues.append('isolated_specks')
    if body_holes or hole_ratio>.005:issues.append('interior_holes')
    if halo_good is not None and halo_good<.95 or black_outer>8:issues.append('halo')
    return dict(status='PASS' if not issues else 'FAIL',issues=issues,fake_transparency=fake,
                transparent_fraction=fraction,clear_border_fraction=clear_border,speck_ratio=specks,
                interior_hole_ratio=hole_ratio,designed_negative_space_pixels=negative_space,halo_good_fraction=halo_good,black_outer_luma=black_outer,
                fractional_alpha_pixels=int(np.sum((alpha>0)&(alpha<255))),hole_geometry=geometry,near_zero_alpha=NEAR_ZERO_ALPHA,visual_review='pending')


def cleanup(image):
    from shot_match import lab,delta_e
    a,haze_removed=clear_haze(np.array(image.convert('RGBA')));before=alpha_qa(image)
    original=a.copy()
    _,edge_distance=nearest_opaque(a)
    soft_edge=(a[...,3]>0)&(a[...,3]<=NEAR_ZERO_ALPHA)
    if edge_distance is not None:soft_edge &= edge_distance<=2
    # Only preserve colour-consistent coverage; white fragments are not soft edges.
    nearest,_=nearest_opaque(a)
    if nearest is not None:soft_edge &= delta_e(lab(a[...,:3]),lab(nearest))<=20
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
        if not soft_edge.any():silhouette=cv2.erode(silhouette,np.ones((3,3),np.uint8))
        envelope=cv2.GaussianBlur(silhouette.astype('float32'),(0,0),.4)
        a[...,3]=np.minimum(a[...,3],np.rint(envelope).astype('uint8'))
        a[...,3][soft_edge]=original[...,3][soft_edge]
    nearest,distance=nearest_opaque(a);recolored=0
    if nearest is not None:
        edge=(a[...,3]>0)&(a[...,3]<250)&(distance<=5)
        bad=edge&(delta_e(lab(a[...,:3]),lab(nearest))>20)
        recolored=int(bad.sum());a[...,:3][bad]=nearest[bad]
    a,final_haze=clear_haze(a);haze_removed+=final_haze
    result=Image.fromarray(a)
    return result,dict(before=before,after=alpha_qa(result),removed_haze_pixels=haze_removed,removed_speck_pixels=removed,despilled_pixels=recolored,hard_sticker_edge_cleanup=hard_sticker,
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
    clean_report['fake_transparency_detected']=report['fake_transparency']
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
    result=dict(raw,fake_transparency_detected=report['fake_transparency'],native_alpha_qa=report,alpha_source=alpha_source,fallback=fallback,matting_background=backing,cleanup=clean_report,
                derived_from=dict(sha256=digest(source),**c2pa(source)),asset=str(out/'asset.png'),ai_generated=True)
    write(out/'gen-manifest.json',result);write(out/'alpha-qa.json',clean_report);return result
