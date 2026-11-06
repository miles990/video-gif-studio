"""Experimental original-character sheets on the spec-13 subscription adapter.

Metrics are evidence, not semantic identity recognition. Uncalibrated identity
and inferred hidden views remain explicitly unassessed.
"""
from dataclasses import replace
from pathlib import Path
import re
import numpy as np
from PIL import Image, ImageDraw
from image_common import ImageError, digest, read, write
from image_identity import compare, features, METHOD

VIEWS = {'front':'front', 'side':'left', 'back':'back', 'three_quarter':'three_quarter_left'}
EXPRESSIONS = ('neutral','joy','anger','sadness','surprise','pain')
# This is a conservative named-entity guard, not a claim of exhaustive IP recognition.
NAMED_IP = re.compile(r'\b(mario|luigi|sonic|pikachu|pokemon|pokémon|kirby|zelda|link from|samus|megaman|mega man|cloud strife|sephiroth|lara croft|kratos|master chief|hollow knight|sans|undertale|goku|naruto|totoro|mickey|elsa|doraemon)\b|皮卡丘|馬利歐|马里奥|索尼克|哆啦|初音|悟空|鸣人|鳴人', re.I)


def originality(prompt, reference_licence=None):
    if NAMED_IP.search(prompt) or re.search(r'(identical to|exact copy of|一模一樣|一模一样)',prompt,re.I):
        raise ImageError('E_ORIGINAL_REQUIRED', 'This pipeline creates original characters. An original alternative is available.',
                         suggestion='Use an original lantern-bearing moth scout: rounded wing silhouette, indigo/copper palette, compass staff instead of the referenced accessories.',
                         originality={'named_ip_detected':True,'action':'offered_original'},
                         design_changes=['rounded wing silhouette','indigo and copper palette','compass staff and lantern','moth species and compact proportions'])
    if reference_licence and reference_licence not in ('original','owned','licensed'):
        raise ImageError('E_REFERENCE_RIGHTS','Reference art must be original, owned, or licensed; official character art is not accepted.')
    return dict(named_ip_detected=False,action='proceed',screening='named-entity guard; human originality review pending')


def rgba(path):
    with Image.open(path) as im:return im.convert('RGBA')


def require_alpha(im):
    from image_alpha import checkerboard
    a=np.array(im.convert('RGBA'))
    if checkerboard(a):raise ImageError('E_FAKE_ALPHA','Painted checkerboard is not transparency; regenerate with native alpha.')
    if not np.any(a[...,3]==0):raise ImageError('E_ALPHA_REQUIRED','Generated sprite has no real transparent pixels; keep it as a rejected source, not a sprite.')


def palette_of(images, limit=16, minimum=.005):
    counts={}; total=0
    for im in images:
        a=np.array(im.convert('RGBA')); colors,n=np.unique(a[...,:3][a[...,3]>127],axis=0,return_counts=True)
        total+=int(n.sum())
        for color,count in zip(colors,n):
            c=tuple(map(int,color));counts[c]=counts.get(c,0)+int(count)
    ordered=sorted(counts,key=lambda c:(-counts[c],c))
    if len(ordered)>limit:
        # Quantize visible RGB only. Transparent black must not consume a slot.
        pixels=np.concatenate([np.array(im)[...,:3][np.array(im)[...,3]>127] for im in images])
        q=Image.fromarray(pixels[None,...]).quantize(colors=limit,method=Image.Quantize.MEDIANCUT)
        pal=np.array(q.getpalette(),np.uint8).reshape(-1,3)
        order=sorted(q.getcolors(),reverse=True)
        ordered=[tuple(map(int,pal[i])) for n,i in order if n/len(pixels)>=minimum]
        counts={tuple(map(int,pal[i])):n for n,i in order}
    return [dict(name=f'color-{i+1}',hex='#%02X%02X%02X'%c,role='outline' if i==0 else 'main',area_pct=round(100*counts[c]/max(total,1),5)) for i,c in enumerate(ordered)]


def quantize(im, palette, size=None):
    """One fixed logical grid and shared palette. No dither or soft character alpha."""
    if size:im=im.resize(size,Image.Resampling.NEAREST)
    a=np.array(im.convert('RGBA')); colors=np.array([tuple(bytes.fromhex(p['hex'].lstrip('#'))) for p in palette],np.int32)
    if not len(colors):raise ImageError('E_PALETTE','Empty palette.')
    rgb=a[...,:3].astype(np.int32)
    nearest=np.argmin(((rgb[...,None,:]-colors)**2).sum(axis=-1),axis=-1)
    a[...,:3]=colors[nearest];a[...,3]=np.where(a[...,3]>=128,255,0);a[a[...,3]==0]=0
    return Image.fromarray(a)


def palette_image(palette):
    image=Image.new('RGB',(240,max(1,len(palette))*25),'#f1eee7');d=ImageDraw.Draw(image)
    for i,p in enumerate(palette):
        d.rectangle((4,i*25+3,45,i*25+21),fill=p['hex']);d.text((55,i*25+7),p['hex'],fill='black')
    return image


def identity_report(paths, negatives=(), near=None, palette=None, identity_override=None):
    """Use spec-13 refset spread/negatives; a hidden face is not a failed identity.

    Histogram and ORB disagree on close lookalikes. Preserve that uncertainty;
    only separated controls or an explicit human decision establish identity.
    """
    from image_identity import relative_controls, override_record
    override=override_record(identity_override)
    if override:
        return dict(status='pass' if identity_override=='same' else 'fail', identity_override=override,
                    controls_valid=False, method=METHOD, views={}, visual_review='user override')
    paths={n:Path(p) for n,p in paths.items()};front=paths['front']
    controls=relative_controls(list(paths.values()),[*negatives,*([near] if near else [])])
    expectations={'front':'face and asymmetric features','side':'profile; visible-side features only',
                  'back':'hidden face; costume and silhouette','three_quarter':'partial face and visible-side features'}
    rows={n:dict(**compare(front,p),expectation=expectations.get(n,'pose-dependent'),
                 status='pass' if controls['valid'] else 'unassessed') for n,p in paths.items()}
    return dict(status='pass' if controls['valid'] else 'unassessed',method=METHOD,views=rows,
                controls=controls,controls_valid=controls['valid'],negative_controls=[compare(front,p) for p in negatives],
                near_control=compare(front,near) if near else None,
                reason=controls.get('reason'),visual_review='pending')


def expressions_qa(front, expressions, face_box):
    import cv2
    from shot_match import lab,delta_e
    base=np.array(front);x,y,w,h=face_box;outside=np.ones(base.shape[:2],bool);outside[y:y+h,x:x+w]=False
    rows=[];faces=[]
    for name,im in expressions.items():
        a=np.array(im);both=(a[...,3]>127)&(base[...,3]>127)&outside
        union=((a[...,3]>127)|(base[...,3]>127))&outside
        iou=float(both.sum()/max(1,union.sum()))
        de=float(np.max(delta_e(lab(a[...,:3]),lab(base[...,:3]))[both])) if both.any() else 0.
        faces.append(cv2.cvtColor(a[y:y+h,x:x+w,:3],cv2.COLOR_RGB2GRAY))
        rows.append(dict(expression=name,outside_iou=iou,outside_max_delta_e=de,pass_outside=bool(iou>=.95 and de<=6)))
    differences=[]
    for i in range(len(faces)):
        for j in range(i):
            a,b=faces[i].astype(float),faces[j].astype(float)
            c1,c2=6.5025,58.5225
            ssim=((2*a.mean()*b.mean()+c1)*(2*np.mean((a-a.mean())*(b-b.mean()))+c2))/((a.mean()**2+b.mean()**2+c1)*(a.var()+b.var()+c2))
            differences.append(dict(pair=[j,i],ssim=float(ssim),different=bool(ssim<=.90)))
    return dict(status='pass' if all(r['pass_outside'] for r in rows) and all(r['different'] for r in differences) else 'fail',outside=rows,face_pairs=differences)


def asymmetry_qa(images,features):
    """Check authored anatomical regions, never infer handedness from mirroring.

    A feature requires a distinct color and a per-view visible region, or null
    when anatomically hidden. Free-text descriptions alone stay unassessed.
    """
    issues=[];measurements=[];assessed=0
    for feature in features:
        if not isinstance(feature,dict) or 'regions' not in feature or 'color' not in feature:continue
        color=np.array(tuple(bytes.fromhex(feature['color'].lstrip('#'))));assessed+=1
        for name,im in images.items():
            if name not in feature['regions']:continue
            a=np.array(im);mask=np.all(a[...,:3]==color,axis=-1)&(a[...,3]>127);region=feature['regions'][name]
            yy,xx=np.where(mask);observed=[float(xx.mean()),float(yy.mean())] if len(xx) else None
            valid=not len(xx) if region is None else bool(len(xx) and np.all((xx>=region[0])&(xx<region[0]+region[2])&(yy>=region[1])&(yy<region[1]+region[3])))
            measurements.append(dict(feature=feature.get('feature'),view=name,centroid=observed,valid=valid))
            if not valid:issues.append(dict(kind='asymmetric_feature_side_or_visibility',view=name,feature=feature.get('feature')))
    return dict(status='FAIL' if issues else 'PASS' if assessed else 'unassessed',issues=issues,measurements=measurements)


def sheet(adapter, request, out, image=None, pixel=None, negatives=(), near=None, asymmetric_features=None, reference_licence='original'):
    out=Path(out);original=originality(request.prompt+(' '+Path(image).stem if image else ''),reference_licence if image else None)
    size=(pixel,pixel) if pixel else tuple(map(int,request.size.split('x')))
    if pixel and not 16<=pixel<=512:raise ImageError('E_GRID','Logical grid must be 16..512.')
    refs=[str(image)] if image else [];records=[];views={};actual={};manifests=[]
    asym=asymmetric_features or []
    for name,facing in VIEWS.items():
        prompt=f'{request.prompt}\nOriginal character turnaround. ONE {facing} view. Same scale, ground line at 90% canvas height, shared camera, outfit and palette. No text. Do not mirror asymmetric features. Canvas {size[0]}x{size[1]}.'
        req=replace(request,prompt=prompt,refs=refs[-3:],transparent=True,n=1)
        result=adapter.generate(req,out/'generation'/name);source=Path(result['assets'][0]['path']);im=rgba(source);require_alpha(im)
        actual[name]=list(im.size);im=im.resize(size,Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS)
        (out/'views').mkdir(parents=True,exist_ok=True);file=out/'views'/f'{name}.png';im.save(file)
        records.append(dict(name=name,facing=facing,file=f'views/{name}.png',refs_sent=[digest(p) for p in req.refs],size_actual=actual[name]))
        views[name]=im;refs.append(str(file.resolve()));manifests.append(result)
    palette=palette_of(list(views.values()),16 if pixel else 12)
    if pixel:
        views={n:quantize(im,palette) for n,im in views.items()}
        for n,im in views.items():im.save(out/'views'/f'{n}.png')
    write(out/'palette.json',palette);palette_image(palette).save(out/'palette.png')
    front=views['front'];face=(size[0]//4,size[1]//8,size[0]//2,size[1]//3);expressions={};exp_records=[]
    for name in EXPRESSIONS:
        req=replace(request,refs=[str((out/'views/front.png').resolve())],transparent=True,n=1,
                    prompt=f'{request.prompt}\nSame front view, ONLY change eyes, eyebrows and mouth to expression {name}. Keep ears, scarf and outfit unchanged. Canvas {size[0]}x{size[1]}.')
        generated=adapter.generate(req,out/'generation'/name);im=rgba(generated['assets'][0]['path']).resize(size,Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS)
        if pixel:im=quantize(im,palette)
        # Explicit local face composite protects everything outside the reviewed face box.
        fixed=front.copy();x,y,w,h=face;fixed.paste(im.crop((x,y,x+w,y+h)),(x,y))
        (out/'expressions').mkdir(exist_ok=True);fixed.save(out/'expressions'/f'{name}.png');expressions[name]=fixed
        exp_records.append(dict(name=name,file=f'expressions/{name}.png',refs_sent=[digest(p) for p in req.refs],fallback='local_face_composite',face_box=list(face)))
        manifests.append(generated)
    paths={n:out/'views'/f'{n}.png' for n in views};identity=identity_report(paths,negatives,near,palette,request.identity_override)
    refset=dict(version=1,name=request.prompt,images=[dict(path=f'views/{n}.png',sha256=digest(p),role='identity',source='generated',licence='original generated artwork') for n,p in paths.items()],
                negative_images=[dict(path=str(Path(p).resolve()),sha256=digest(p)) for p in negatives],controls={'valid':identity['controls_valid']},visual_review={'status':'pending'})
    write(out/'refset.json',refset)
    heights=[im.getbbox()[3]-im.getbbox()[1] if im.getbbox() else 0 for im in views.values()]
    scale_spread=(max(heights)-min(heights))/max(1,np.mean(heights))
    manifest=dict(version=1,status='experimental',originality=original,canvas=list(size),pivot=[size[0]/2,round(size[1]*.9)],alpha_mode='straight',pixel=bool(pixel),pixel_scale=1,
                  palette='palette.json',views=records,expressions=exp_records,face_box=list(face),asymmetric_features=asym,mirror_ok=not bool(asym),
                  inferred_views=['side','back'] if image else [],identity=identity,expressions_qa=expressions_qa(front,expressions,face),height_spread=float(scale_spread),
                  fallback='pixel_quantize' if pixel else None,size_requested=f'{size[0]}x{size[1]} (prompt only)',size_actual=actual,review='pending')
    asymmetry=asymmetry_qa(views,asym)
    manifest['qa']=dict(status='FAIL' if scale_spread>.03 or manifest['expressions_qa']['status']=='fail' or identity['status']=='fail' or asymmetry['status']=='FAIL' else 'unassessed' if identity['status']=='unassessed' or (asym and asymmetry['status']=='unassessed') else 'PASS',
        height_consistency=bool(scale_spread<=.03),identity=identity['status'],expressions=manifest['expressions_qa']['status'],asymmetry=asymmetry)
    canvas=Image.new('RGBA',(size[0]*4,size[1]*3+40),(24,29,42,255));draw=ImageDraw.Draw(canvas);draw.text((8,8),'ORIGINAL CHARACTER / '+str(size),fill='white')
    for i,im in enumerate([*views.values(),*expressions.values()]):canvas.alpha_composite(im,((i%4)*size[0],40+(i//4)*size[1]))
    canvas.save(out/'sheet.png');write(out/'charsheet.json',manifest)
    write(out/'gen-manifest.json',dict(originality=original,generations=manifests,subscription_images=sum(not m.get('cache_hit',False) for m in manifests),fallback=manifest['fallback']))
    return manifest
