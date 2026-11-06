"""Local identity reference library. ORB/HSV fallback; controls gate every verdict."""
from itertools import combinations
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from image_common import ImageError,digest,read,utc,write

METHOD=dict(name='ORB + masked HSV histogram',opencv_version=cv2.__version__,lowe_ratio=.75,
            same_hist_max=.40,same_matches_min=25,different_hist_min=.50,different_matches_max=9,
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


def compare(a,b):
    ha,da=features(a);hb,db=features(b)
    distance=float(cv2.compareHist(ha,hb,cv2.HISTCMP_BHATTACHARYYA));good=0
    if da is not None and db is not None and len(db)>=2:
        matches=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da,db,k=2)
        good=sum(len(pair)==2 and pair[0].distance<.75*pair[1].distance for pair in matches)
    return dict(bhattacharyya=distance,orb_good_matches=good,
                same=distance<=METHOD['same_hist_max'] and good>=25,different=distance>=.50 or good<10)


def build(name,images,out,role='identity',source='user',licence=None,negative=None):
    if not 1<=len(images)<=16:raise ImageError('E_REFSET_LIMIT','A reference library must contain 1..16 images.')
    if role not in ('identity','costume','product','scene'):raise ImageError('E_REFSET_ROLE','Invalid reference role.')
    if source not in ('user','generated','web'):raise ImageError('E_REFSET_SOURCE','Invalid reference source.')
    if source=='web' and not licence:raise ImageError('E_LICENCE','Web references require a recorded licence, including unknown.')
    records=[]
    for file in images:
        path=Path(file).resolve();features(path)
        records.append(dict(path=str(path),sha256=digest(path),role=role,source=source,licence=licence or ('user supplied' if source=='user' else 'generated')))
    pairs=[]
    if role in ('identity','product'):
        for i,j in combinations(range(len(images)),2):
            metric=compare(images[i],images[j]);pairs.append(dict(a=i,b=j,**metric))
            if metric['different']:
                raise ImageError('E_REFSET_MIXED','Reference library cannot establish one identity.',suspect_indices=[i+1,j+1],measurement=metric)
    result=dict(version=1,name=name,images=records,created_at=utc(),method=METHOD,pairwise=pairs,
                negative_images=[dict(path=str(Path(p).resolve()),sha256=digest(p)) for p in (negative or [])],
                visual_review=dict(status='pending',question='Are these the same character/product?',chooser=None))
    if len(images)>=2 and negative:
        result['controls']=controls(images[0],images[1],negative[0])
    else:result['controls']=dict(valid=False,reason='Need two distinct positive poses and a different-identity negative reference.')
    write(out,result);return result


def load(path):
    path=Path(path);data=read(path)
    if not 1<=len(data['images'])<=16:raise ImageError('E_REFSET_LIMIT','A reference library must contain 1..16 images.')
    for item in [*data['images'],*data.get('negative_images',[])]:
        file=(path.parent/item['path']).resolve()
        if digest(file)!=item['sha256']:raise ImageError('E_REFSET_CHANGED','Reference bytes changed; rebuild the library.')
        item['path']=str(file)
    return data


def controls(positive_a,positive_b,negative):
    if digest(positive_a)==digest(positive_b):
        return dict(valid=False,reason='Positive controls must be distinct images/poses; identity is unassessed.',method=METHOD)
    positive=compare(positive_a,positive_b);bad=compare(positive_a,negative)
    separation=bad['bhattacharyya']-positive['bhattacharyya']
    result=dict(valid=positive['same'] and bad['different'] and separation>=.10,positive=positive,negative=bad,method=METHOD,histogram_separation=separation)
    if not result['valid']:result['reason']='Positive and negative controls are not separated; no artwork verdict.'
    return result


def check(path,refset):
    data=load(refset);refs=data['images'];negative=data.get('negative_images',[])
    if len(refs)<2 or not negative:
        return dict(status='unassessed',reason='Missing independent positive/negative controls',method=METHOD,visual_review='pending')
    prior=controls(refs[0]['path'],refs[1]['path'],negative[0]['path'])
    if not prior['valid']:
        return dict(status='unassessed',reason=prior['reason'],controls=prior,method=METHOD,visual_review='pending')
    positive=[compare(path,r['path']) for r in refs]
    neg=[compare(path,r['path']) for r in negative]
    # ORB has no vector centroid: use the library distribution, not a fictitious cosine.
    h=float(np.median([r['bhattacharyya'] for r in positive]));matches=float(np.median([r['orb_good_matches'] for r in positive]))
    ok=h<=METHOD['same_hist_max'] and matches>=25 and all(r['different'] and r['bhattacharyya']-h>=.10 for r in neg)
    # A failed match is not evidence of another identity, especially under scene
    # lighting or an uncertain saliency crop. Require a separated negative match.
    negative_h=min(r['bhattacharyya'] for r in neg)
    negative_match=any(r['same'] for r in neg) and h-negative_h>=.10
    status='pass' if ok else 'identity_fail' if negative_match else 'unassessed'
    return dict(status=status,reason=None if status!='unassessed' else 'Subject evidence does not separate identity from scene/pose variation.',positive=positive,negative=neg,
                aggregate=dict(bhattacharyya_median=h,orb_good_matches_median=matches),controls=prior,
                method=METHOD,refset_sha=digest(refset),visual_review='pending')


def review(refset,same,comment=''):
    data=load(refset);data['visual_review']=dict(status='accepted' if same else 'rejected',chooser='user',comment=comment,timestamp=utc())
    write(refset,data);return data['visual_review']
