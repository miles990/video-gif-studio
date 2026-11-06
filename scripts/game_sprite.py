"""Sprite-specific alpha, shared-grid and palette checks without shape erosion."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from image_common import ImageError,write
from image_alpha import nearest_opaque,checkerboard


def clean_sprite(im,particles=False):
    a=np.array(im.convert('RGBA'));before=a.copy();removed=0
    n,labels,stats,_=cv2.connectedComponentsWithStats((a[...,3]>0).astype('uint8'),8)
    if n>1 and not particles:
        largest=1+int(np.argmax(stats[1:,cv2.CC_STAT_AREA]))
        for label in range(1,n):
            if label!=largest and stats[label,cv2.CC_STAT_AREA]<=4 and np.max(a[...,3][labels==label])<128:
                removed+=int(stats[label,cv2.CC_STAT_AREA]);a[labels==label]=0
    nearest,distance=nearest_opaque(a);despilled=0
    if nearest is not None:
        from shot_match import lab,delta_e
        edge=(a[...,3]>0)&(a[...,3]<250)&(distance<=3)
        bad=edge&(delta_e(lab(a[...,:3]),lab(nearest))>20)
        despilled=int(bad.sum());a[...,:3][bad]=nearest[bad]
    a[a[...,3]==0]=0
    hard=before[...,3]>=128;changed=np.any(a!=before,axis=-1)&hard
    return Image.fromarray(a),dict(removed_speck_pixels=removed,despilled_pixels=despilled,
            opaque_alpha_changes=int(np.sum((a[...,3]!=before[...,3])&hard)),opaque_pixel_change_ratio=float(changed.sum()/max(1,hard.sum())),
            policy='remove only isolated <=4px translucent components; preserve contour, opacity, designed holes and declared particles')


def alpha_contract(im,mode='straight',particles=False,designed_holes=None):
    from shot_match import lab,delta_e
    if mode not in ('straight','premultiplied'):raise ImageError('E_ALPHA_MODE','Use straight or premultiplied.')
    a=np.array(im.convert('RGBA'));alpha=a[...,3];visible=alpha>0;semi=(alpha>0)&(alpha<250);issues=[]
    n,labels,stats,_=cv2.connectedComponentsWithStats(visible.astype('uint8'),8)
    areas=stats[1:,cv2.CC_STAT_AREA];largest=int(areas.max()) if len(areas) else 0
    tiny=int(np.sum(areas<=4)) if len(areas)>1 else 0;detached=(int(areas.sum())-largest)/max(1,largest)
    if not particles and (tiny or detached>.001):issues.append('isolated_specks')
    if checkerboard(a) or not np.any(alpha==0):issues.append('missing_real_alpha')
    border=np.concatenate((alpha[0],alpha[-1],alpha[:,0],alpha[:,-1]))
    if np.mean(border==0)<.999:issues.append('clipped_border')
    if np.any(a[alpha==0,:3]!=0):issues.append('rgb_under_zero_alpha')
    nearest,distance=nearest_opaque(a);edge_good=None;premul_evidence=None
    if mode=='premultiplied' and np.any(a[...,:3]>alpha[...,None]):issues.append('invalid_premultiplied_rgb')
    if nearest is not None and semi.any():
        raw=a[...,:3];unpremul=np.rint(np.clip(raw.astype(float)*255/np.maximum(alpha[...,None],1),0,255)).astype(np.uint8)
        edge=semi&(distance<=3)
        if edge.any():
            de_raw=delta_e(lab(raw),lab(nearest))[edge];de_un=delta_e(lab(unpremul),lab(nearest))[edge]
            bound=float(np.mean(np.all(raw<=alpha[...,None],axis=-1)[visible]))
            premul_evidence=dict(rgb_le_alpha_fraction=bound,raw_delta_e=float(np.mean(de_raw)),unpremultiplied_delta_e=float(np.mean(de_un)))
            if mode=='straight' and bound>=.98 and np.mean(de_un)+5<np.mean(de_raw) and np.mean(de_un<=20)>=.95:issues.append('premultiplied_declared_straight')
            edge_good=float(np.mean((de_raw if mode=='straight' else de_un)<=20))
            if edge_good<.95:issues.append('halo')
    # Unknown enclosed clear components remain review evidence. Only caller-supplied
    # material/negative-space annotation can establish whether a hole was intended.
    holes=0
    if designed_holes is not None:
        protection=np.array(designed_holes.convert('L'))>0
        if protection.shape!=alpha.shape:raise ImageError('E_MASK_SIZE','Designed-hole mask must share sprite canvas.')
        hn,hl,hs,_=cv2.connectedComponentsWithStats((alpha<128).astype('uint8'),8)
        boundary=set(np.r_[hl[0],hl[-1],hl[:,0],hl[:,-1]])
        holes=sum(int(np.sum((hl==i)&~protection)) for i in range(1,hn) if i not in boundary)
        if holes/max(largest,1)>.005:issues.append('unintended_holes')
    return dict(status='PASS' if not issues else 'FAIL',issues=issues,alpha_mode=mode,isolated_small_components=tiny,detached_ratio=detached,
                edge_good_fraction=edge_good,premultiplication=premul_evidence,hole_review='annotated' if designed_holes is not None else 'unassessed',unintended_hole_pixels=holes)


def pixel_qa(images,palette,logical_size,scale=1,max_colors=16,soft_effect=False):
    if not isinstance(scale,int) or scale<1 or max_colors>32 or max_colors<1:raise ImageError('E_PIXEL','Pixel scale/colors are outside the supported range.')
    allowed={tuple(bytes.fromhex(p['hex'].lstrip('#'))) if isinstance(p,dict) else tuple(bytes.fromhex(p.lstrip('#'))) for p in palette}
    if len(allowed)>max_colors:raise ImageError('E_PALETTE','Declared palette exceeds color budget.')
    issues=[];union=set();rows=[];w,h=logical_size
    for i,im in enumerate(images):
        a=np.array(im.convert('RGBA'));colors=set(map(tuple,a[...,:3][a[...,3]>0]));union|=colors
        new=colors-allowed;bad_grid=None
        if im.size!=(w*scale,h*scale):issues.append(dict(frame=i,kind='logical_size'))
        else:
            blocks=a.reshape(h,scale,w,scale,4);bad_grid=int(np.sum(np.any(blocks!=blocks[:,0,:,0,:][:,None,:,None,:],axis=(1,3,4))))
            if bad_grid:issues.append(dict(frame=i,kind='non_grid',blocks=bad_grid))
        if new:issues.append(dict(frame=i,kind='new_colors',count=len(new)))
        if not soft_effect and np.any((a[...,3]!=0)&(a[...,3]!=255)):issues.append(dict(frame=i,kind='fractional_character_alpha'))
        rows.append(dict(frame=i,new_colors=len(new),non_grid_blocks=bad_grid))
    if len(union)>max_colors:issues.append(dict(kind='color_budget',count=len(union)))
    return dict(status='FAIL' if issues else 'PASS',issues=issues,frames=rows,total_colors=len(union),filter='nearest',logical_size=list(logical_size),pixel_scale=scale)


def sprite_check(paths,pivot=None,mode='straight',palette=None,pixel=None,scale=1,cleanup=False,out=None,particles=False):
    from game_character import rgba
    images=[rgba(p) for p in paths];reports=[]
    if not images:raise ImageError('E_FRAMES','No sprite images found.')
    if len({im.size for im in images})!=1:raise ImageError('E_CANVAS','Sprite canvases differ.')
    for i,im in enumerate(images):
        correction=None
        if cleanup:
            if out is None:raise ImageError('E_OUTPUT','Cleanup requires --out.')
            im,correction=clean_sprite(im,particles);images[i]=im;Path(out).mkdir(parents=True,exist_ok=True);im.save(Path(out)/f'{i:05d}.png')
        reports.append(dict(frame=i,qa=alpha_contract(im,mode,particles),correction=correction))
    pixel_report=pixel_qa(images,palette,(pixel,pixel),scale) if pixel and palette else None
    result=dict(status='PASS' if all(r['qa']['status']=='PASS' for r in reports) and (not pixel_report or pixel_report['status']=='PASS') else 'FAIL',
                frames=reports,pixel=pixel_report,canvas=list(images[0].size),pivot=pivot or [images[0].width/2,images[0].height-1],alpha_mode=mode)
    if out:write(Path(out)/'sprite-qa.json',result)
    return result
