"""Experimental original-character sheets on the spec-13 subscription adapter.

Metrics are evidence, not semantic identity recognition. Uncalibrated identity
and inferred hidden views remain explicitly unassessed.
"""
from dataclasses import replace
from pathlib import Path
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from image_common import ImageError, digest, read, write
from image_identity import compare, relative_controls
from identity_engine import engine, describe, verdict

VIEWS = {'front':'front', 'side':'left', 'back':'back', 'three_quarter':'three_quarter_left'}
EXPRESSIONS = ('neutral','joy','anger','sadness','surprise','pain')
# This is a conservative named-entity guard, not a claim of exhaustive IP recognition.
NAMED_IP = re.compile(r'\b(mario|luigi|sonic|pikachu|pokemon|pokémon|kirby|zelda|link from|samus|megaman|mega man|cloud strife|sephiroth|lara croft|kratos|master chief|hollow knight|sans|undertale|goku|naruto|totoro|mickey|elsa|doraemon)\b|皮卡丘|馬利歐|马里奥|索尼克|哆啦|初音|悟空|鸣人|鳴人', re.I)
LOCAL_IP=re.compile(r'瑪利歐|玛利欧|林克|寶可夢|宝可梦|薩爾達|萨尔达|薩爾達傳說|\b(?:link|crash(?: bandicoot)?|shovel knight)\b',re.I)
GAME_STYLE=re.compile(r'(?:in (?:the )?style of|recreate (?:the )?look of|模仿|照著|照着).{0,12}(?:Stardew Valley|Terraria|Dead Cells|Cuphead|Hades|Celeste|Minecraft|Animal Crossing|Dark Souls|Final Fantasy|星露谷|茶杯頭|茶杯头|動物森友會)|in the style of (?:the game |["“]).+',re.I)


def original_alternative(prompt):
    import hashlib
    seed=int(hashlib.sha256(prompt.encode('utf8')).hexdigest()[:8],16)
    species=('arctic hare','sand pangolin','glasswing beetle','river otter','moss salamander','copper owl')
    shapes=('long triangular ears','rounded shell silhouette','split leaf cloak','crescent shoulder plates','wide woven hood')
    colors=('teal and ochre','aubergine and mint','slate and coral','cream and copper','navy and amber')
    props=('tuning-fork blade','folding compass shield','bell-headed staff','crystal sickle','kite-shaped spear')
    changes=[species[seed%len(species)],shapes[(seed//7)%len(shapes)],colors[(seed//31)%len(colors)],props[(seed//131)%len(props)]]
    intent='ice-themed sword action' if re.search(r'ice|冰',prompt,re.I) else 'electric movement' if re.search(r'electric|電|电',prompt,re.I) else 'walking and jumping' if re.search(r'walk|走|跳|Mario|瑪利歐|马里奥',prompt,re.I) else 'exploration and combat'
    return f'Keep the requested {intent}; create an original {changes[0]} with {changes[1]}, {changes[2]} palette, and a {changes[3]}.',changes


def originality(prompt, reference_licence=None):
    if NAMED_IP.search(prompt.replace('_',' ')) or LOCAL_IP.search(prompt.replace('_',' ')) or GAME_STYLE.search(prompt) or re.search(r'(identical to|exact copy of|一模一樣|一模一样)',prompt,re.I):
        suggestion,changes=original_alternative(prompt)
        raise ImageError('E_ORIGINAL_REQUIRED', 'This pipeline creates original characters. An original alternative is available.',
                         suggestion=suggestion,
                         originality={'named_ip_detected':True,'action':'offered_original'},
                         design_changes=changes)
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


def ensure_sprite_alpha(im):
    from image_alpha import matte_uniform,clear_haze,checkerboard
    im=im.convert('RGBA');a=np.array(im)
    if checkerboard(a):raise ImageError('E_FAKE_ALPHA','Painted checkerboard requires regeneration on a uniform backing.')
    if not np.any(a[...,3]==0):
        border=np.concatenate((a[0,:,:3],a[-1,:,:3],a[:,0,:3],a[:,-1,:3]));backing=np.median(border,axis=0)
        if np.mean(np.linalg.norm(border.astype(float)-backing,axis=1)<12)<.98:
            raise ImageError('E_MATTING','No uniform backing; use a segmented matting source or regenerate native alpha.')
        im=matte_uniform(im,backing);source='matted'
    else:
        # Generic image cleanup can interpret a dark pixel-art outline as a
        # sticker border. Native sprites retain their designed opaque contour.
        a,_=clear_haze(a);a[a[...,3]==0]=0;im=Image.fromarray(a);source='native'
    require_alpha(im)
    return im,source


def prepare_subject(im, view='front', reference_paths=()):
    """Separate large full-height components; keep a recorded canonical sheet cell.

    Four horizontally ordered turnaround cells use the requested front/side/back/
    three-quarter order. This geometric inference remains pending visual review.
    Ambiguous layouts request regeneration instead of silently taking a crowd.
    """
    import cv2
    from game_demo import isolate_single_subject
    im,alpha_source=ensure_sprite_alpha(im)
    a=np.array(im);mask=(a[...,3]>127).astype('uint8')
    # Model-drawn ground rules can connect all four figures. Remove only long
    # horizontal rules before counting; retain the original source on disk.
    rule=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((1,max(3,round(im.width*.85))),np.uint8))
    occupied_rows=np.where(mask.any(axis=1))[0];rule_rows=np.where(rule.any(axis=1))[0]
    near_ground=bool(len(rule_rows) and len(occupied_rows) and rule_rows.min()>=occupied_rows.min()+.85*np.ptp(occupied_rows))
    if near_ground and len(rule_rows)<=max(2,im.height*.02):
        mask[rule>0]=0;a[rule>0]=0;im=Image.fromarray(a)
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
    biggest=max(stats[1:,cv2.CC_STAT_AREA],default=0)
    candidates=[s for s in stats[1:] if s[cv2.CC_STAT_AREA]>=biggest*.18 and s[cv2.CC_STAT_HEIGHT]>=max(stats[1:,cv2.CC_STAT_HEIGHT],default=0)*.65]
    candidates.sort(key=lambda s:int(s[0]))
    count=len(candidates);index=0;crop=im
    if count>1:
        if count not in (2,3,4) or list(VIEWS).index(view)>=count or max(s[1] for s in candidates)-min(s[1] for s in candidates)>im.height*.2:
            raise ImageError('E_SUBJECT_COUNT','Ambiguous multiple subjects; regenerate ONE requested view.',subject_count=count)
        index=list(VIEWS).index(view)
        selection='canonical left-to-right turnaround; unassessed semantic view'
        if reference_paths and count==len(reference_paths)+1:
            # A model often echoes all references alongside the new view, and
            # may reorder them. Match the echoed sources, then select the novel
            # cell, rather than assuming the new view occupies the last column.
            from itertools import permutations
            import tempfile
            from image_common import ROOT
            with tempfile.TemporaryDirectory(dir=ROOT/'.scratch',prefix='view-select-') as tmp:
                cell_paths=[]
                for j,(cx,cy,cw,ch,_) in enumerate(candidates):
                    cell=im.crop((int(cx)-2,int(cy)-2,int(cx+cw)+2,int(cy+ch)+2));p=Path(tmp)/f'{j}.png';cell.save(p);cell_paths.append(p)
                metrics=[[compare(ref,p) for p in cell_paths] for ref in reference_paths]
                def match_score(m,row):
                    if 'structure' in m:return m['structure']+m['colour']  # two-axis engine
                    return m['orb_good_matches']/max(1,max(v['orb_good_matches'] for v in row))+1-m['bhattacharyya']  # ORB fallback
                scores=[[match_score(m,row) for m in row] for row in metrics]
                assignments=list(permutations(range(count),len(reference_paths)))
                best=max(assignments,key=lambda assignment:sum(scores[k][j] for k,j in enumerate(assignment)))
                index=next(j for j in range(count) if j not in best)
                selection='novel cell after matching echoed source references; semantic review pending'
        x,y,w,h,_=candidates[index]
        crop=Image.new('RGBA',im.size)
        # Midpoints between subjects exclude neighboring contour/support pixels.
        left=0 if index==0 else (int(candidates[index-1][0]+candidates[index-1][2])+int(x))//2
        right=im.width if index==count-1 else (int(x+w)+int(candidates[index+1][0]))//2
        crop.paste(im.crop((left,0,right,im.height)),(left,0))
    crop=isolate_single_subject(crop)
    return crop,dict(subject_count=count,selected_index=index,requested_view=view,alpha_source=alpha_source,
                     selection=selection if count>1 else 'single subject',visual_review='pending')


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


def register_subject(im, canvas, ground, height=None):
    """Register a generated standing key to one explicit ground/height contract.

    Supplied animation plans retain their authored travel and crouching. This
    fallback normalizes unregistered model stills, and records the transform.
    """
    a=np.array(im);ys,xs=np.where(a[...,3]>127)
    if not len(xs):raise ImageError('E_SUBJECT','No opaque body for registration.')
    box=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
    target_height=height or round(canvas[1]*.80);scale=min(target_height/(box[3]-box[1]),(canvas[0]-4)/(box[2]-box[0]))
    crop=im.crop(box);size=(max(1,round(crop.width*scale)),max(1,round(crop.height*scale)))
    crop=crop.resize(size,Image.Resampling.BOX if scale<1 else Image.Resampling.NEAREST)
    if scale<1:
        alpha=crop.getchannel('A');crop=crop.convert('RGB').filter(ImageFilter.MedianFilter(3)).convert('RGBA');crop.putalpha(alpha)
    x=(canvas[0]-size[0])//2;y=round(ground)-size[1]+1
    if y<1:raise ImageError('E_REGISTRATION','Body exceeds padded canvas; enlarge canvas or reduce target height.')
    result=Image.new('RGBA',canvas);result.paste(crop,(x,y))
    return result,dict(source_box=list(box),scale=scale,offset=[x,y],ground_line=ground,body_height=size[1],method='standing body bbox; inferred camera; review pending')


def quantize(im, palette, size=None):
    """Area integration, median color cleanup and nearest-palette mapping.

    Nearest sampling is reserved for enlarging an established pixel grid.
    Native same-size artwork is preserved; alpha is never median-eroded.
    """
    down=size and (size[0]<im.width or size[1]<im.height)
    if size:im=im.resize(size,Image.Resampling.BOX if down else Image.Resampling.NEAREST)
    if down:
        alpha=im.getchannel('A');im=im.convert('RGB').filter(ImageFilter.MedianFilter(3)).convert('RGBA');im.putalpha(alpha)
    a=np.array(im.convert('RGBA')); colors=np.array([tuple(bytes.fromhex(p['hex'].lstrip('#'))) for p in palette],np.int32)
    if not len(colors):raise ImageError('E_PALETTE','Empty palette.')
    rgb=a[...,:3].astype(np.int32)
    nearest=np.argmin(((rgb[...,None,:]-colors)**2).sum(axis=-1),axis=-1)
    a[...,:3]=colors[nearest];a[...,3]=np.where(a[...,3]>=128,255,0);a[a[...,3]==0]=0
    if down:
        # Remove isolated palette islands, retaining silhouette and contiguous ink.
        import cv2
        for color in colors:
            mask=np.all(a[...,:3]==color,axis=-1)&(a[...,3]>0)
            n,labels,stats,_=cv2.connectedComponentsWithStats(mask.astype('uint8'),8)
            for label in range(1,n):
                if stats[label,cv2.CC_STAT_AREA]>2:continue
                for y,x in zip(*np.where(labels==label)):
                    region=a[max(0,y-1):y+2,max(0,x-1):x+2];valid=region[...,3]>0
                    values,counts=np.unique(region[...,:3][valid],axis=0,return_counts=True)
                    if len(counts) and counts.max()>=3:a[y,x,:3]=values[counts.argmax()]
    return Image.fromarray(a)


def palette_image(palette):
    image=Image.new('RGB',(240,max(1,len(palette))*25),'#f1eee7');d=ImageDraw.Draw(image)
    for i,p in enumerate(palette):
        d.rectangle((4,i*25+3,45,i*25+21),fill=p['hex']);d.text((55,i*25+7),p['hex'],fill='black')
    return image


def view_palette_signature(path):
    """Pose-tolerant hue evidence; saturation weighting discounts metal/shadows.

    Circular smoothing tolerates lighting shifts. This cannot recognize scars,
    anatomy or an achromatic lookalike, and must never establish identity alone.
    """
    import cv2
    a=np.array(rgba(path));hsv=cv2.cvtColor(a[...,:3],cv2.COLOR_RGB2HSV).astype(float);visible=a[...,3]>127
    hist=np.bincount((hsv[...,0][visible]//10).astype(int),
                    weights=(hsv[...,1][visible]/255)**2*(hsv[...,2][visible]/255),minlength=18)
    hist=hist+.5*np.roll(hist,1)+.5*np.roll(hist,-1)
    return hist/max(float(hist.sum()),1e-9)


def view_palette_distance(a,b):
    return float(np.sqrt(max(0,1-np.sqrt(a*b).sum())))


def identity_report(paths, negatives=(), near=None, palette=None, identity_override=None):
    """Use spec-13 refset spread/negatives; a hidden face is not a failed identity.

    Histogram and ORB disagree on close lookalikes. Preserve that uncertainty;
    only separated controls or an explicit human decision establish identity.
    """
    from image_identity import relative_controls, override_record
    override=override_record(identity_override)
    if override:
        return dict(status='pass' if identity_override=='same' else 'fail', identity_override=override,
                    controls_valid=False, method=describe(), views={}, visual_review='user override')
    paths={n:Path(p) for n,p in paths.items()};front=paths['front']
    controls=relative_controls(list(paths.values()),[*negatives,*([near] if near else [])])
    signatures={n:view_palette_signature(p) for n,p in paths.items()}
    positive=list(signatures.values());negative=[view_palette_signature(p) for p in [*negatives,*([near] if near else [])]]
    spread=max((view_palette_distance(a,b) for i,a in enumerate(positive) for b in positive[i+1:]),default=0.)
    separation=min((view_palette_distance(a,b) for a in positive for b in negative),default=None)
    palette_controls=dict(valid=bool(len(positive)>1 and separation is not None and separation>spread),
                          refset_spread=spread,nearest_negative=separation,
                          method='saturation-weighted circular hue; relative refset spread versus negatives; no absolute cutoff',
                          limitation='ranking evidence only; no scar/anatomy recognition')
    def evidence(p,signature=None):
        row=compare(front,p);row['view_palette_distance']=view_palette_distance(signatures['front'],signature if signature is not None else view_palette_signature(p))
        row['relative_palette_rank']=(row['view_palette_distance']-spread)/(separation-spread) if palette_controls['valid'] else None
        return row
    expectations={'front':'face and asymmetric features','side':'profile; visible-side features only',
                  'back':'hidden face; costume and silhouette','three_quarter':'partial face and visible-side features'}
    available=engine()[0] is not None;rows={}
    for n,p in paths.items():
        metrics=[compare(p,other) for m,other in paths.items() if m!=n]
        scores={axis:max(x[axis] for x in metrics) for axis in ('structure','colour')} if available and metrics and 'structure' in metrics[0] else {}
        status=verdict(scores) if scores and controls['valid'] else 'unassessed'
        rows[n]=dict(**evidence(p,signatures[n]),expectation=expectations.get(n,'pose-dependent'),aggregate=scores,status=status,passes_threshold=status=='pass')
    statuses=[r['status'] for r in rows.values()]
    overall='fail' if 'identity_fail' in statuses else 'pass' if statuses and all(s=='pass' for s in statuses) else 'unassessed'
    return dict(status=overall,method=describe(),views=rows,
                controls=controls,controls_valid=controls['valid'],view_palette_controls=palette_controls,negative_controls=[evidence(p) for p in negatives],
                near_control=evidence(near) if near else None,
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


def sheet(adapter, request, out, image=None, pixel=None, negatives=(), near=None, asymmetric_features=None, reference_licence='original',expression_atlas=False):
    out=Path(out);original=originality(request.prompt+(' '+Path(image).stem if image else ''),reference_licence if image else None)
    size=(pixel,pixel) if pixel else tuple(map(int,request.size.split('x')))
    if pixel and not 16<=pixel<=512:raise ImageError('E_GRID','Logical grid must be 16..512.')
    refs=[str(image)] if image else [];records=[];views={};actual={};manifests=[]
    asym=asymmetric_features or []
    for name,facing in VIEWS.items():
        prompt=f'{request.prompt}\nOriginal character turnaround. ONE {facing} view. Same scale, ground line at 90% canvas height, shared camera, outfit and palette. No text. Do not mirror asymmetric features. Canvas {size[0]}x{size[1]}.'
        req=replace(request,prompt=prompt,refs=refs[-3:],transparent=True,n=1)
        result=adapter.generate(req,out/'generation'/name);source=Path(result['assets'][0]['path'])
        try:im,subject=prepare_subject(rgba(source),name,req.refs)
        except ImageError as exc:
            if exc.error['code']!='E_SUBJECT_COUNT':raise
            req=replace(req,prompt=prompt+' IMPORTANT: a single isolated character only; NOT a turnaround sheet or multiple poses.')
            result=adapter.generate(req,out/'generation'/(name+'-single'),no_cache=True);source=Path(result['assets'][0]['path'])
            im,subject=prepare_subject(rgba(source),name,req.refs)
        actual[name]=list(im.size)
        (out/'identity').mkdir(parents=True,exist_ok=True);identity_file=out/'identity'/f'{name}.png';im.save(identity_file)
        im,registration=register_subject(im,size,round(size[1]*.9))
        (out/'views').mkdir(parents=True,exist_ok=True);file=out/'views'/f'{name}.png';im.save(file)
        records.append(dict(name=name,facing=facing,file=f'views/{name}.png',refs_sent=[digest(p) for p in req.refs],size_actual=actual[name],subject=subject,registration=registration))
        views[name]=im;refs.append(str(identity_file.resolve()));manifests.append(result)
    palette=palette_of(list(views.values()),16 if pixel else 12)
    if pixel:
        views={n:quantize(im,palette) for n,im in views.items()}
        for n,im in views.items():im.save(out/'views'/f'{n}.png')
    write(out/'palette.json',palette);palette_image(palette).save(out/'palette.png')
    front=views['front'];face=(size[0]//4,size[1]//8,size[0]//2,size[1]//3);expressions={};exp_records=[]
    atlas=None
    if expression_atlas:
        atlas_req=replace(request,refs=[str((out/'identity/front.png').resolve())],transparent=True,n=1,
            prompt=f'{request.prompt}. Six full-body front views of exactly this original character in a 3 columns by 2 rows equal-cell grid, row-major expressions: {", ".join(EXPRESSIONS)}. Each cell has one centered character at identical scale, feet at 90% cell height. Transparent gaps between cells. No labels, no lines, no extra figures.')
        atlas_result=adapter.generate(atlas_req,out/'generation/expressions-atlas');atlas=rgba(atlas_result['assets'][0]['path']);manifests.append(atlas_result)
    for expression_index,name in enumerate(EXPRESSIONS):
        req=replace(request,refs=[str((out/'identity/front.png').resolve())],transparent=True,n=1,
                    prompt=f'{request.prompt}\nSame front view, ONLY change eyes, eyebrows and mouth to expression {name}. Keep ears, scarf and outfit unchanged. Canvas {size[0]}x{size[1]}.')
        if atlas is None:
            generated=adapter.generate(req,out/'generation'/name);raw=rgba(generated['assets'][0]['path']);manifests.append(generated)
        else:
            x=expression_index%3;y=expression_index//3;raw=atlas.crop((round(x*atlas.width/3),round(y*atlas.height/2),round((x+1)*atlas.width/3),round((y+1)*atlas.height/2)))
        im,_=prepare_subject(raw)
        im,registration=register_subject(im,size,round(size[1]*.9))
        if pixel:im=quantize(im,palette)
        # Explicit local face composite protects everything outside the reviewed face box.
        fixed=front.copy();x,y,w,h=face;fixed.paste(im.crop((x,y,x+w,y+h)),(x,y))
        (out/'expressions').mkdir(exist_ok=True);fixed.save(out/'expressions'/f'{name}.png');expressions[name]=fixed
        exp_records.append(dict(name=name,file=f'expressions/{name}.png',refs_sent=[digest(p) for p in req.refs],fallback='local_face_composite',face_box=list(face)))
    paths={n:out/'identity'/f'{n}.png' for n in views};identity=identity_report(paths,negatives,near,palette,request.identity_override)
    identity.update(measurement_stage='source_before_downscale',source_sizes=actual,source_sha256={n:digest(p) for n,p in paths.items()})
    refset=dict(version=1,name=request.prompt,images=[dict(path=f'identity/{n}.png',sha256=digest(p),role='identity',source='generated',licence='original generated artwork') for n,p in paths.items()],
                negative_images=[dict(path=str(Path(p).resolve()),sha256=digest(p)) for p in negatives],controls={'valid':identity['controls_valid']},visual_review={'status':'pending'})
    write(out/'refset.json',refset)
    heights=[im.getbbox()[3]-im.getbbox()[1] if im.getbbox() else 0 for im in views.values()]
    scale_spread=(max(heights)-min(heights))/max(1,np.mean(heights))
    manifest=dict(version=1,status='experimental',originality=original,canvas=list(size),pivot=[size[0]/2,round(size[1]*.9)],body_height=round(size[1]*.8),alpha_mode='straight',pixel=bool(pixel),pixel_scale=1,
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
