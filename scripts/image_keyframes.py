"""Storyboard PNG keyframes with aspect-safe fitting and visible quality evidence."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import re
import cv2
import numpy as np
from PIL import Image, ImageOps
from image_common import ImageError, c2pa, digest, read, write
from image_route import Request
from storyboard import validate, lint

SHOT_WORDS = {'EWS':'extreme wide shot; entire subject <=20% of frame height',
              'WS':'wide shot; full subject 20-55% of frame height',
              'MS':'medium shot; waist-up subject 45-85% of frame height',
              'CU':'close-up; face or main object >=45% of frame width',
              'ECU':'extreme close-up; eye or cup rim detail >=60% of frame width'}


def fit_image(image, size, background=None):
    """Crop small aspect errors; refuse misleading large flat-colour padding."""
    image=image.convert('RGBA')
    ratio=(image.width/image.height)/(size[0]/size[1]);loss=1-min(ratio,1/ratio)
    if loss>.20:
        raise ImageError('E_ASPECT_UNFIXABLE','Returned aspect requires excessive padding or cropping; regenerate with the requested framing.',status='aspect_unfixable',source_size=list(image.size),target_size=list(size),padding_fraction=loss)
    if loss<=.03:
        fitted=ImageOps.fit(image,size,Image.Resampling.LANCZOS)
        return fitted,dict(method='uniform_crop',source_size=list(image.size),size=list(size),scale=max(size[0]/image.width,size[1]/image.height),offset=[0,0],content_size=list(size),padding_fraction=0,crop_fraction=loss,stretched=False)
    fitted=ImageOps.contain(image,size,Image.Resampling.LANCZOS)
    if background is None:
        corners=np.array(image)[[0,0,-1,-1],[0,-1,0,-1],:3]
        background=tuple(np.median(corners,axis=0).astype(int))+(255,)
    result=Image.new('RGBA',size,background)
    offset=((size[0]-fitted.width)//2,(size[1]-fitted.height)//2)
    result.paste(fitted,offset)
    return result,dict(method='uniform_contain',source_size=list(image.size),size=list(size),
                       scale=fitted.width/image.width,offset=list(offset),content_size=list(fitted.size),
                       padding_fraction=1-fitted.width*fitted.height/(size[0]*size[1]),stretched=False)


def swatch(board, shot):
    value=shot.get('color_script',shot.get('background',''))
    found=re.search(r'#[0-9a-fA-F]{6}',str(value))
    if found:return found[0]
    script=board.get('color_script',{})
    if isinstance(script,dict):
        found=re.search(r'#[0-9a-fA-F]{6}',str(script.get(value,'')))
        if found:return found[0]
    return None


def keyframe_prompt(board, shot):
    return '\n'.join([
        f"Storyboard {shot['id']}: {shot['size']} — {SHOT_WORDS[shot['size']]}",
        f"Subject: {shot.get('subject',board.get('subject','original subject'))}; action: {shot.get('action','')}",
        f"Composition: {shot.get('composition','preserve full head and important props; title safe area 10%')}",
        f"Angle: {shot.get('angle',0)}; lens: {shot.get('lens','standard')}; motion intention: {shot['motion']}",
        f"Lighting: {shot.get('lighting','intentional directional light')}",
        f"Colour script: {shot.get('color_script','')}; dominant swatch: {swatch(board,shot) or 'authored palette'}",
        f"Aesthetic: {board.get('aesthetic',board.get('core','authored cinematic storyboard'))}",
        f"Identity references: {shot.get('reference_id','shared refset')}; retain identity, costume, markings and props.",
        'Create one cinematic keyframe, no contact sheet, no labels.'
    ])


def frame_qa(path, shot, colour=None, subject_mask=None):
    from shot_match import lab,delta_e
    with Image.open(path) as image:
        a=np.array(image.convert('RGBA'))
        thumbnail=image.convert('RGB');thumbnail.thumbnail((192,192))
        quantized=thumbnail.quantize(colors=5)
        counts=sorted(quantized.getcolors(),reverse=True)[:3]
        palette=np.array(quantized.getpalette(),np.uint8).reshape(-1,3)
        top=np.array([palette[i] for _,i in counts],np.uint8)
    result=dict(visual_review='pending',size_status='unassessed',palette=top.tolist())
    if colour:
        rgb=np.array([int(colour[i:i+2],16) for i in (1,3,5)],np.uint8)
        distances=delta_e(lab(top[None,...]),lab(rgb[None,None,...])).ravel()
        result.update(swatch=colour,swatch_delta_e2000=float(distances.min()),colour_pass=bool(distances.min()<=15))
    mask=None
    if subject_mask is not None:
        mask=np.asarray(subject_mask)>0
        if mask.shape!=a.shape[:2]:raise ImageError('E_MASK','Subject mask must match the keyframe.')
    else:
        from image_identity import subject_region
        mask,method=subject_region(a)
        result['subject_method']=method
    # No opaque portrait/face detector is falsely inferred from a bounding box.
    if mask is not None and mask.any():
        y,x=np.where(mask);h=(y.max()-y.min()+1)/a.shape[0];w=(x.max()-x.min()+1)/a.shape[1]
        size=shot['size'];ok={'EWS':h<=.20,'WS':.20<=h<=.55,'MS':.45<=h<=.85,'CU':w>=.45,'ECU':w>=.60}[size]
        result.update(subject_height_fraction=float(h),subject_width_fraction=float(w),size_status='pass' if ok else 'size_mismatch')
    return result


def keyframes(board, adapter, out, request=None, selected=None, approval=None, max_usd=0):
    b=validate(board)
    if lint(b)['errors']:raise ImageError('E_STORYBOARD','Resolve structural storyboard errors before generation.')
    req=request or Request('',experimental=b.get('experimental',False))
    # Validate guards before individual-shot fallback handling.
    replace(req,prompt='preflight').normalized()
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    width,height=int(b.get('width',1080)),int(b.get('height',1920))
    if min(width,height)<=0:raise ImageError('E_SIZE','Storyboard dimensions must be positive.')
    minside=720 if req.quality=='draft' else 1080
    scale=max(1,minside/min(width,height));size=(round(width*scale),round(height*scale))
    rows=[]
    for index,shot in enumerate(b['shots'],1):
        if selected and str(index) not in selected and shot['id'] not in selected:continue
        folder=out/f'shot-{index}';folder.mkdir(exist_ok=True)
        prompt=keyframe_prompt(b,shot)
        current=replace(req,prompt=prompt,size=f'{size[0]}x{size[1]}',aspect=f'{width}:{height}',n=1)
        write(folder/'prompt.json',dict(prompt=prompt))
        try:
            generated=adapter.generate(current,folder/'generation',approval,max_usd)
            source=Path(generated['assets'][0]['path'])
            identity=None
            if req.refset_path:
                from image_identity import check
                identity=check(source,req.refset_path)
                if identity['status']=='identity_fail':
                    retry=replace(current,prompt=current.prompt+'\nIdentity correction: match all supplied identity details exactly. Preserve face, markings and costume.')
                    try:
                        retried=adapter.generate(retry,folder/'identity-retry',approval,max_usd)
                    except ImageError as exc:
                        if exc.error['code']!='E_CAP':raise
                        identity=dict(identity,retry_error=exc.error,generation_retained='first')
                    else:
                        generated=retried
                        source=Path(generated['assets'][0]['path']);identity=check(source,req.refset_path)
            with Image.open(source) as image:frame,fit=fit_image(image,size)
            path=folder/'keyframe.png';frame.save(path)
            qa=frame_qa(path,shot,swatch(b,shot))
            if identity:qa['identity']=identity
            manifest=dict(generated,derived_from=dict(sha256=digest(source),**c2pa(source)),
                          fallback='aspect_contain' if fit['padding_fraction']>.005 else 'uniform_resize',fit=fit,qa=qa,
                          size_actual=[list(size)],aspect_actual=[size[0]/size[1]],ai_generated=True)
            write(folder/'gen-manifest.json',manifest)
            shot['keyframe']=dict(path=str(path),sha256=digest(path),gen_manifest=str(folder/'gen-manifest.json'),
                                  status='identity_fail' if identity and identity['status']=='identity_fail' else qa['size_status'],colour_pass=qa.get('colour_pass'),ai_generated=True)
            shot.pop('keyframe_failure',None)
        except (ImageError,OSError,ValueError) as exc:
            shot.pop('keyframe',None)
            shot['keyframe_failure']=exc.error if isinstance(exc,ImageError) else dict(code='E_KEYFRAME',message=str(exc))
        rows.append(dict(shot=shot['id'],keyframe=shot.get('keyframe'),error=shot.get('keyframe_failure')))
    write(out/'storyboard.json',b);write(out/'keyframes.json',dict(shots=rows,visual_review='pending',ai_generated=True))
    contact_sheet(b,out,req.refs)
    return b


def contact_sheet(board,out,refs=()):
    """Reference/shot comparison for human identity and framing review."""
    from PIL import ImageDraw
    cells=[(f'reference {i+1}',str(p)) for i,p in enumerate(refs)]
    cells += [(f"{s['id']} / {s['size']}",s.get('keyframe',{}).get('path')) for s in board['shots']]
    columns=min(4,len(cells));tile=(240,440)
    canvas=Image.new('RGB',(columns*tile[0],((len(cells)+columns-1)//columns)*tile[1]),'#142027')
    draw=ImageDraw.Draw(canvas)
    for i,(label,path) in enumerate(cells):
        x=i%columns*tile[0];y=i//columns*tile[1]
        if path and Path(path).is_file():
            with Image.open(path) as im:thumbnail=ImageOps.contain(im.convert('RGB'),(224,398))
            canvas.paste(thumbnail,(x+(240-thumbnail.width)//2,y+28))
        draw.text((x+8,y+8),label,fill='white')
    canvas.save(Path(out)/'contact-sheet.jpg',quality=92)


def attach_keyframes(board, directory):
    revised=read(Path(directory)/'storyboard.json');mapping={s['id']:s for s in revised['shots']};b=deepcopy(board)
    for s in b['shots']:
        for field in ('keyframe','keyframe_failure'):
            if field in mapping.get(s['id'],{}):s[field]=mapping[s['id']][field]
    return b
