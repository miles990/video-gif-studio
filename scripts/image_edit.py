"""Reference regeneration + registered mask composite; outside pixels stay exact."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import cv2
import numpy as np
from PIL import Image,ImageDraw
from image_common import ImageError,c2pa,digest,key,read,write


def region_mask(size,region=None,markup=None):
    if bool(region)==bool(markup):raise ImageError('E_REGION','Supply exactly one region or markup layer.')
    w,h=size
    if markup:
        with Image.open(markup) as im:
            if im.size!=size:raise ImageError('E_MASK_SIZE','Markup dimensions must equal the source.')
            if im.mode!='RGBA':raise ImageError('E_MARKUP','Markup must be a transparent RGBA layer.')
            a=np.array(im)
        mask=(a[...,3]>0).astype('uint8')*255
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(mask,contours,-1,255,cv2.FILLED)
    else:
        if isinstance(region,str):
            try:region=json.loads(region)
            except ValueError:
                try:region=[float(x) for x in region.removeprefix('bbox:').split(',')]
                except ValueError:raise ImageError('E_REGION','Use bbox x,y,width,height or a JSON polygon; auto requires storyboard image_regions metadata.') from None
        canvas=Image.new('L',size);draw=ImageDraw.Draw(canvas)
        if len(region)==4 and all(isinstance(x,(int,float)) for x in region):
            x,y,rw,rh=region
            if min(x,y)<0 or min(rw,rh)<=0 or x+rw>w or y+rh>h:raise ImageError('E_REGION','Bounding box is outside source canvas.')
            draw.rectangle((round(x),round(y),round(x+rw)-1,round(y+rh)-1),fill=255)
        elif len(region)>=3 and all(len(p)==2 for p in region):
            if any(not 0<=x<w or not 0<=y<h for x,y in region):raise ImageError('E_REGION','Polygon vertices must be inside the source.')
            draw.polygon([tuple(p) for p in region],fill=255)
        else:raise ImageError('E_REGION','Invalid region.')
        mask=np.array(canvas)
    if not mask.any() or np.all(mask):raise ImageError('E_REGION','Local edit mask must select a nonempty proper subset.')
    return mask


def register(base,candidate,region):
    if base.shape!=candidate.shape:raise ImageError('E_EDIT_SIZE','Regeneration changed dimensions; cannot certify pixel-preserving alignment.')
    a=cv2.cvtColor(base[...,:3],cv2.COLOR_RGB2GRAY);b=cv2.cvtColor(candidate[...,:3],cv2.COLOR_RGB2GRAY)
    outside=(region==0).astype('uint8')*255
    if np.array_equal(a[outside>0],b[outside>0]):return candidate,dict(method='identical_outside',residual_px=0,transform=[[1,0,0],[0,1,0]])
    orb=cv2.ORB_create(nfeatures=3000,edgeThreshold=10,fastThreshold=8)
    ka,da=orb.detectAndCompute(a,outside);kb,db=orb.detectAndCompute(b,outside)
    if da is not None and db is not None and len(da)>=2:
        matches=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(db,da,k=2)
        matches=[pair[0] for pair in matches if len(pair)==2 and pair[0].distance<.75*pair[1].distance]
        if len(matches)>=8:
            source=np.float32([kb[m.queryIdx].pt for m in matches]);target=np.float32([ka[m.trainIdx].pt for m in matches])
            matrix,inliers=cv2.estimateAffinePartial2D(source,target,method=cv2.RANSAC,ransacReprojThreshold=1)
            if matrix is not None and inliers.sum()>=8:
                predicted=source@matrix[:,:2].T+matrix[:,2];residual=float(np.median(np.linalg.norm(predicted-target,axis=1)[inliers.ravel()>0]))
                if residual<=1:
                    aligned=cv2.warpAffine(candidate,matrix,(base.shape[1],base.shape[0]),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
                    return aligned,dict(method='ORB_RANSAC',residual_px=residual,inliers=int(inliers.sum()),transform=matrix.tolist())
    try:
        matrix=np.eye(2,3,dtype=np.float32)
        correlation,matrix=cv2.findTransformECC(a,b,matrix,cv2.MOTION_TRANSLATION,
                                               (cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,100,1e-6),outside,5)
        aligned=cv2.warpAffine(candidate,matrix,(base.shape[1],base.shape[0]),flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REFLECT)
        # Check residual translation independently after alignment.
        shift,response=cv2.phaseCorrelate(a.astype('float32')*(outside/255),cv2.cvtColor(aligned[...,:3],cv2.COLOR_RGB2GRAY).astype('float32')*(outside/255))
        residual=float(np.linalg.norm(shift))
        if correlation>=.8 and residual<=1:
            return aligned,dict(method='ECC_translation',correlation=float(correlation),residual_px=residual,transform=matrix.tolist(),inverse_map=True)
    except cv2.error:pass
    raise ImageError('E_REGISTRATION','Cannot establish <=1 px alignment outside the edit; select a better reference/regeneration.')


def composite(base,candidate,mask,feather=8):
    from shot_match import lab,delta_e
    if not 0<=feather<=8:raise ImageError('E_FEATHER','Feather must be between 0 and 8 pixels.')
    a=np.array(base.convert('RGBA'));b=np.array(candidate.convert('RGBA'))
    margin=round(min(base.size)*.02)
    expanded=cv2.dilate(mask,np.ones((2*margin+1,2*margin+1),np.uint8))
    aligned,registration=register(a,b,expanded)
    outside=expanded==0;rawdiff=np.abs(a.astype(float)-b.astype(float))
    if feather:
        distance=cv2.distanceTransform((expanded>0).astype('uint8'),cv2.DIST_L2,5)
        weights=np.clip(distance/feather,0,1)
        weights=weights*weights*(3-2*weights)
    else:weights=(expanded>0).astype(float)
    result=np.rint(a*(1-weights[...,None])+aligned*weights[...,None]).astype('uint8')
    result[outside]=a[outside]
    diff=np.abs(result.astype(float)-a.astype(float))
    inside_de=float(delta_e(lab(a[...,:3]),lab(result[...,:3]))[mask>0].mean())
    metrics=dict(outside_mean=float(diff[outside].mean()),outside_p999=float(np.percentile(diff[outside],99.9)),
                 outside_fraction_over10=float(np.mean(np.any(diff[outside]>10,axis=1))),
                 outside_identical=bool(np.array_equal(a[outside],result[outside])),inside_delta_e2000=inside_de,
                 raw_outside_mean=float(rawdiff[outside].mean()),registration=registration,margin_px=margin,feather_px=feather,
                 visual_review='pending: semantic change and composite seam')
    if inside_de<8:raise ImageError('E_EDIT_NO_CHANGE','Selected region did not materially change (mean ΔE2000 <8).',metrics=metrics)
    return Image.fromarray(result),metrics,expanded


def edit(adapter,request,image,out,instruction,region=None,markup=None,feather=8,approval=None,max_usd=0):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);image=Path(image).resolve()
    with Image.open(image) as im:base=im.convert('RGBA')
    mask=region_mask(base.size,region,markup);Image.fromarray(mask).save(out/'mask.png')
    note=Image.new('RGBA',base.size);red=np.array(note);red[mask>0]=[255,0,0,90];Image.fromarray(red).save(out/'markup.png')
    refs=[str(image),*[str(p) for p in request.refs if Path(p).resolve()!=image]]
    if len(refs)>16:raise ImageError('E_REFSET_LIMIT','Source image plus identity references exceed 16; select at most 15 identity references.')
    bbox=Image.fromarray(mask).getbbox()
    req=replace(request,prompt=f'{instruction}\nEdit only the object inside pixel bbox {bbox}. Preserve framing and every other detail.',
                refs=refs,size=f'{base.width}x{base.height}',n=1,format='png',markup_sha=digest(out/'mask.png'))
    generation=adapter.generate(req,out/'regeneration',approval,max_usd)
    source=Path(generation['assets'][0]['path'])
    with Image.open(source) as candidate:result,metrics,expanded=composite(base,candidate,mask,feather)
    result.save(out/'edited.png');Image.fromarray(expanded).save(out/'composite-region.png')
    manifest=dict(generation,fallback='mask_composite',feature_used=['references'],edit=metrics,
                  derived_from=[dict(sha256=digest(image),**c2pa(image)),dict(sha256=digest(source),**c2pa(source))],
                  path=str(out/'edited.png'),sha256=digest(out/'edited.png'),ai_generated=True)
    write(out/'gen-manifest.json',manifest);return manifest


def apply_delta(board,draft,adapter,request,out,markup=None,approval=None,max_usd=0,image_feedback=None):
    from brief_edit import parse
    b=deepcopy(board);parsed=parse(draft,b,image=image_feedback);out=Path(out).resolve()
    if parsed.get('questions'):raise ImageError('E_AMBIGUOUS',parsed['questions'][0])
    changed=[]
    for change in parsed['changes']:
        if change['change']!='image_edit':raise ImageError('E_DELTA','Use brief apply for timing/layout edits; this command applies image edits only.')
        for shot in b['shots']:
            if shot['id'] not in change['target']['shots']:continue
            if not shot.get('keyframe'):raise ImageError('E_KEYFRAME','Target shot has no generated keyframe.')
            element=change['target']['element'];region=shot.get('image_regions',{}).get(element)
            if region is None and markup is None:
                raise ImageError('E_REGION_REQUIRED',f'No selected region for {element}.',suggestion='Supply --markup or shot.image_regions[element]=[x,y,width,height]; object location is never guessed.')
            result=edit(adapter,request,shot['keyframe']['path'],out/shot['id'],change['instruction'],
                        region=None if markup else region,markup=markup,approval=approval,max_usd=max_usd)
            shot['keyframe']=dict(path=result['path'],sha256=result['sha256'],gen_manifest=str(out/shot['id']/'gen-manifest.json'),status='edited',ai_generated=True)
            changed.append(shot['id'])
    b['revision']=dict(changed_shots=changed,previous_sha=key(board),keep=['all pixels outside selected regions','all other shots'])
    write(out/'storyboard.json',b);write(out/'delta.json',parsed);return b
