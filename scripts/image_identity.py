"""Two-axis local identity reference library; optional conservative ORB fallback."""
from itertools import combinations
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from image_common import ImageError,digest,read,utc,write

METHOD=dict(name='ORB + masked HSV histogram, refset-relative controls',opencv_version=cv2.__version__,lowe_ratio=.75,
            embedding='unavailable: no local weights plus permissive licence and runtime verified; no model downloads')


def subject_region(a):
    """Foreground support; saliency is a conservative proxy, not a semantic detector."""
    rgb=a[...,:3];mask=a[...,3]>127
    if not np.all(mask):return mask,'alpha'
    border=np.concatenate((rgb[0],rgb[:,0],rgb[:,-1])).astype(float)
    background=np.median(border,axis=0)
    if np.mean(np.linalg.norm(border-background,axis=1)<12)>.85:
        return np.linalg.norm(rgb.astype(float)-background,axis=2)>18,'uniform_background'
    from taste_report import saliency
    small=cv2.resize(rgb,(192,max(1,round(192*rgb.shape[0]/rgb.shape[1]))))
    sal,_,_=saliency(small)
    mask=(sal>=max(float(sal.max())*.25,float(np.percentile(sal,65)))).astype('uint8')
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    return cv2.resize(mask,(rgb.shape[1],rgb.shape[0]),interpolation=cv2.INTER_NEAREST)>0,'saliency'


def features(path):
    with Image.open(path) as im:a=np.array(im.convert('RGBA'))
    rgb=a[...,:3];mask,_=subject_region(a)
    if not mask.any():raise ImageError('E_IDENTITY_EMPTY','Reference has no visible subject.')
    ys,xs=np.where(mask);box=(slice(ys.min(),ys.max()+1),slice(xs.min(),xs.max()+1))
    rgb=rgb[box];mask=mask[box]
    ratio=384/max(rgb.shape[:2]);size=(max(1,round(rgb.shape[1]*ratio)),max(1,round(rgb.shape[0]*ratio)))
    rgb=cv2.resize(rgb,size,interpolation=cv2.INTER_AREA)
    mask=cv2.resize(mask.astype('uint8')*255,size,interpolation=cv2.INTER_NEAREST)
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    hist=cv2.calcHist([hsv],[0,1],mask,[30,32],[0,180,0,256]);cv2.normalize(hist,hist,alpha=1,norm_type=cv2.NORM_L1)
    orb=cv2.ORB_create(nfeatures=1600,edgeThreshold=10,fastThreshold=8)
    points,descriptors=orb.detectAndCompute(cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY),mask)
    return hist,descriptors


def fallback_compare(a,b):
    ha,da=features(a);hb,db=features(b)
    distance=float(cv2.compareHist(ha,hb,cv2.HISTCMP_BHATTACHARYYA));good=0
    if da is not None and db is not None and len(db)>=2:
        matches=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da,db,k=2)
        good=sum(len(pair)==2 and pair[0].distance<.75*pair[1].distance for pair in matches)
    return dict(bhattacharyya=distance,orb_good_matches=good)


def compare(a,b):
    from identity_engine import engine,compare as semantic_compare
    return semantic_compare(a,b) if engine()[0] is not None else fallback_compare(a,b)


def build(name,images,out,role='identity',source='user',licence=None,negative=None,identity_override=None):
    from identity_engine import engine,features as semantic_features
    if not 1<=len(images)<=16:raise ImageError('E_REFSET_LIMIT','A reference library must contain 1..16 images.')
    if role not in ('identity','costume','product','scene'):raise ImageError('E_REFSET_ROLE','Invalid reference role.')
    if source not in ('user','generated','web'):raise ImageError('E_REFSET_SOURCE','Invalid reference source.')
    if source=='web' and not licence:raise ImageError('E_LICENCE','Web references require a recorded licence, including unknown.')
    records=[]
    for file in images:
        path=Path(file).resolve()
        (semantic_features if engine()[0] is not None else features)(path)
        records.append(dict(path=str(path),sha256=digest(path),role=role,source=source,licence=licence or ('user supplied' if source=='user' else 'generated')))
    pairs=[];suspects=set()
    if role in ('identity','product'):
        for i,j in combinations(range(len(images)),2):
            metric=compare(images[i],images[j]);pairs.append(dict(a=i,b=j,**metric))
    prior=relative_controls(images,negative or [])
    if role in ('identity','product') and prior.get('contradicted'):
        suspects.update(range(1,len(images)+1))
    override=override_record(identity_override)
    if identity_override=='same':suspects.clear()
    if identity_override=='different':suspects.update(range(1,len(images)+1))
    if suspects:
        indices=sorted(suspects)
        rejected=dict(status='rejected',identity_override=override,suspect_indices=indices,suspect_images=[records[i-1]['path'] for i in indices],measurements=pairs)
        raise ImageError('E_REFSET_MIXED','Reference library has contradictory identity evidence.',**rejected)
    from identity_engine import describe
    result=dict(version=2,name=name,images=records,created_at=utc(),method=describe(),pairwise=pairs,
                negative_images=[dict(path=str(Path(p).resolve()),sha256=digest(p)) for p in (negative or [])],
                identity_override=override,visual_review=dict(status='accepted' if identity_override=='same' else 'pending',question='Are these the same character/product?',chooser='user' if override else None))
    result['controls']=prior
    write(out,result);return result


def load(path):
    path=Path(path)
    try:data=read(path)
    except (OSError,ValueError,TypeError) as exc:
        raise ImageError('E_REFSET_INVALID',f'Cannot read reference library: {exc}') from None
    if not isinstance(data,dict) or data.get('status')=='rejected' or not isinstance(data.get('images'),list) or not isinstance(data.get('negative_images',[]),list):
        raise ImageError('E_REFSET_INVALID','Invalid or rejected reference library; rebuild the refset.')
    if not 1<=len(data['images'])<=16:raise ImageError('E_REFSET_LIMIT','A reference library must contain 1..16 images.')
    for item in [*data['images'],*data.get('negative_images',[])]:
        if not isinstance(item,dict) or not isinstance(item.get('path'),str) or not isinstance(item.get('sha256'),str):
            raise ImageError('E_REFSET_INVALID','Reference entries require path and sha256; rebuild the refset.')
        file=(path.parent/item['path']).resolve()
        if not file.is_file():raise ImageError('E_REFSET_INVALID',f'Reference image is missing: {file}')
        if digest(file)!=item['sha256']:raise ImageError('E_REFSET_CHANGED','Reference bytes changed; rebuild the library.')
        item['path']=str(file)
    return data


def controls(positive_a,positive_b,negative):
    return relative_controls([positive_a,positive_b],[negative])


def override_record(value):
    if value not in (None,'same','different'):raise ImageError('E_IDENTITY_OVERRIDE','Use same or different.')
    return dict(decision=value,chooser='user',timestamp=utc()) if value else None


def fallback_controls(images,negative):
    if len(set(digest(p) for p in images))<2 or not negative or set(digest(p) for p in images)&set(digest(p) for p in negative):
        return dict(valid=False,reason='Need independent positive poses and negative identities.',method=METHOD)
    positive=[fallback_compare(a,b) for a,b in combinations(images,2)]
    bad=[fallback_compare(a,b) for a in images for b in negative]
    spread=max(p['bhattacharyya'] for p in positive)
    nearest=min(p['bhattacharyya'] for p in bad)
    positive_matches=min(p['orb_good_matches'] for p in positive)
    negative_matches=max(p['orb_good_matches'] for p in bad)
    valid=nearest>spread and positive_matches>negative_matches
    return dict(valid=valid,contradicted=nearest<spread and negative_matches>positive_matches,
                positive=positive,negative=bad,positive_spread=spread,negative_distance=nearest,
                positive_matches_min=positive_matches,negative_matches_max=negative_matches,
                histogram_separation=nearest-spread,method=METHOD,
                reason=None if valid else 'Positive and negative controls overlap; identity is unassessed.')


def relative_controls(images,negative):
    from identity_engine import engine,describe,verdict,LIMITS
    if engine()[0] is None:
        result=fallback_controls(images,negative)
        result.update(valid=False,contradicted=False,reason=describe()['reason'],method=describe())
        return result
    if len(set(digest(p) for p in images))<2 or not negative or set(digest(p) for p in images)&set(digest(p) for p in negative):
        return dict(valid=False,reason='Need independent positive poses and negative identities.',method=describe())
    positive=[dict(index=i,**{axis:max(compare(a,b)[axis] for j,b in enumerate(images) if j!=i) for axis in ('structure','colour')}) for i,a in enumerate(images)]
    bad=[{axis:max(compare(n,a)[axis] for a in images) for axis in ('structure','colour')} for n in negative]
    # A library is not a candidate: an isolated unfamiliar pose can be useful.
    # Reject palette contradictions, or structural failures that positively
    # match a supplied negative. Do not reject merely for a novel silhouette.
    contradicted=any(p['colour']<LIMITS['colour']['fail'] or
                     (p['structure']<LIMITS['structure']['fail'] and
                      max(compare(images[p['index']],n)['structure'] for n in negative)>=LIMITS['structure']['pass']) for p in positive)
    # A reference in the abstention band does not contradict the library. Each
    # candidate must still independently pass both absolute, cross-set gates.
    valid=not contradicted and all(verdict(n)=='identity_fail' for n in bad)
    return dict(valid=valid,contradicted=contradicted,positive=positive,negative=bad,method=describe(),
                reason=None if valid else 'Positive and negative controls do not separate on both identity axes.')


def check(path,refset,identity_override=None):
    data=load(refset);refs=data['images'];negative=data.get('negative_images',[])
    override=override_record(identity_override)
    if override:return dict(status='pass' if identity_override=='same' else 'identity_fail',identity_override=override,refset_sha=digest(refset),visual_review='user override')
    from identity_engine import engine,describe,verdict,features as semantic_features
    if engine()[0] is None:
        return dict(status='unassessed',reason=describe()['reason'],method=describe(),positive=[fallback_compare(path,r['path']) for r in refs],visual_review='pending')
    if len(refs)<2 or not negative:
        return dict(status='unassessed',reason='Missing independent positive/negative controls',method=describe(),visual_review='pending')
    prior=relative_controls([r['path'] for r in refs],[r['path'] for r in negative])
    if not prior['valid']:
        return dict(status='unassessed',reason=prior['reason'],controls=prior,method=describe(),visual_review='pending')
    positive=[compare(path,r['path']) for r in refs]
    neg=[compare(path,r['path']) for r in negative]
    aggregate={axis:max(p[axis] for p in positive) for axis in ('structure','colour')}
    source=semantic_features(path)[2]
    status=verdict(aggregate) if source!='saliency' else 'unassessed'
    return dict(status=status,reason=None if status!='unassessed' else 'Subject evidence does not separate identity from scene/pose variation.',positive=positive,negative=neg,
                aggregate=aggregate,controls=prior,
                method=describe(),refset_sha=digest(refset),visual_review='pending')


def review(refset,same,comment=''):
    data=load(refset);data['visual_review']=dict(status='accepted' if same else 'rejected',chooser='user',comment=comment,timestamp=utc())
    write(refset,data);return data['visual_review']
