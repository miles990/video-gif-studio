"""Decoded reference non-embedding audit, separate from licensing preflight."""
from pathlib import Path
from collections import OrderedDict
import hashlib
import cv2
import numpy as np


def frames(path, step=None, fps=30):
    path=Path(path)
    if path.is_dir():
        files=sorted(path.glob('*.png'))
        if not files:raise ValueError('Cannot decode empty frame directory: '+str(path))
        for i,file in enumerate(files):
            frame=cv2.imread(str(file))
            if frame is None:raise ValueError('Cannot decode frame: '+str(file))
            yield i/fps,frame
        return
    if path.suffix.lower() in ('.png','.jpg','.jpeg','.webp'):
        frame=cv2.imread(str(path))
        if frame is None:raise ValueError('Cannot decode reference image: '+str(path))
        yield 0.,frame;return
    cap=cv2.VideoCapture(str(path));fps=cap.get(cv2.CAP_PROP_FPS)
    if fps<=0:cap.release();raise ValueError('Cannot decode media: '+str(path))
    index=0;stride=max(1,round((step or 0)*fps))
    while True:
        ok,frame=cap.read()
        if not ok:break
        if index%stride==0:yield index/fps,frame
        index+=1
    cap.release()


def signature(frame):
    # Normalize even small references; record the limitation in the audit.
    # Upscaling supplies a common analysis canvas, not additional source detail.
    return _signature(frame)+(_signature(cv2.flip(frame,1)),)


def _signature(frame):
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    small=cv2.resize(gray,(32,32)).astype(np.float32);dct=cv2.dct(small)[:8,:8].flatten();bits=dct>np.median(dct[1:])
    scale=720/min(gray.shape);gray=cv2.resize(gray,None,fx=scale,fy=scale)
    detector=cv2.ORB_create(nfeatures=1800,fastThreshold=8);points=[];descriptors=[]
    # Keep the audit canvas at 720 short-side. An internal scale pyramid also
    # recognizes a reference embedded as a small inset in that canvas.
    for factor in (1.,.5,.4):
        level=gray if factor==1 else cv2.resize(gray,None,fx=factor,fy=factor)
        kp,desc=detector.detectAndCompute(level,None)
        if desc is None:continue
        for point in kp:point.pt=(point.pt[0]/factor,point.pt[1]/factor)
        points.extend(kp);descriptors.append(desc)
    return bits,points,np.concatenate(descriptors) if descriptors else None


def _matches(a,b):
    distance=int(np.count_nonzero(a[0]!=b[0]));inliers=0
    if a[2] is not None and b[2] is not None and len(a[2])>=8 and len(b[2])>=8:
        pairs=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(a[2],b[2],k=2)
        good=[p[0] for p in pairs if len(p)==2 and p[0].distance<.75*p[1].distance]
        if len(good)>=8:
            src=np.float32([a[1][m.queryIdx].pt for m in good]);dst=np.float32([b[1][m.trainIdx].pt for m in good])
            _,mask=cv2.findHomography(src,dst,cv2.RANSAC,4)
            if mask is not None:inliers=int(mask.sum())
    # Uniform images cannot establish copying; retain raw pHash for audit.
    informative=len(a[1])>=8
    return dict(phash_distance=distance,orb_inliers=inliers,embedded=(informative and distance<12) or inliers>=25)


def matches(a,b):
    normal=_matches(a,b)
    if normal['embedded'] or len(b)<4:return dict(normal,mirrored=False)
    mirrored=_matches(a,b[3])
    return dict(mirrored,mirrored=True) if mirrored['embedded'] else dict(normal,mirrored=False)


def audit(movie, references, fps=30):
    refs=[(str(p),t,signature(frame)) for p in references for t,frame in frames(p,.25)];hits=[];checked=0
    # Audit every decoded frame, but reuse comparisons for byte-identical holds.
    # Bound the cache so a long moving clip cannot accumulate full signatures.
    cache=OrderedDict()
    for time,frame in frames(movie,fps=fps) if refs else []:
        checked+=1;key=(frame.shape,hashlib.sha256(frame.tobytes()).digest())
        if key not in cache:
            sig=signature(frame);found=[]
            for path,ref_time,ref in refs:
                match=matches(sig,ref)
                if match['embedded']:found.append(dict(reference=path,reference_time=ref_time,**match))
            cache[key]=found
            if len(cache)>128:cache.popitem(last=False)
        cache.move_to_end(key)
        hits.extend(dict(time=time,**match) for match in cache[key])
    return dict(pass_nonembedding=not hits,frames_checked=checked,hits=hits,analysis_short_side=720,
                limitation='Small sources are upscaled to a 720 px analysis canvas without adding detail. Textureless images cannot establish copying; asset-path isolation remains mandatory.')
