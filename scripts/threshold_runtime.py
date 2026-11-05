"""Measured runtime channels sharing the threshold registry with calibration.

Visibility and harshness are screening instruments, pending independent panel
calibration. Motion uses supplied camera samples, never guessed image motion.
"""
import cv2
import numpy as np
from threshold_registry import check, check_metrics, value


def luminance(frames):
    frames=np.asarray(frames,dtype=np.float32)
    return (frames[...,:3]@np.array([.2126,.7152,.0722],np.float32))*frames[...,3]


def onset_contrast(before, after, untreated):
    """k-frame onset difference; high-pass weighted, relative to untreated motion."""
    before,after,untreated=map(luminance,(before,after,untreated))
    def weighted(frame):
        high=frame-cv2.GaussianBlur(frame,(0,0),2)
        return float(np.mean(np.abs(high))+.1*np.mean(np.abs(frame)))
    onset=weighted(np.mean(after,axis=0)-np.mean(before,axis=0))
    noise=float(np.median([weighted(b-a) for a,b in zip(untreated,untreated[1:])]))
    return onset/max(noise,1/255)


def sharp4(source, output):
    h,w=source.shape[:2]
    def sharp(frame):
        gray=cv2.resize(luminance(frame),(max(2,w//4),max(2,h//4)),interpolation=cv2.INTER_AREA)
        return float(cv2.Laplacian(gray,cv2.CV_32F).var())
    baseline=sharp(source)
    return sharp(output)/baseline if baseline>1e-12 else None


def caption_contrast(fill, stroke):
    def linear(hexcolor):
        rgb=np.array([int(hexcolor.lstrip('#')[i:i+2],16)/255 for i in (0,2,4)])
        return float(np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)@np.array([.2126,.7152,.0722]))
    a,b=linear(fill),linear(stroke)
    return (max(a,b)+.05)/(min(a,b)+.05)


def motion_smoothness(samples, fps, channel='rotation', data=None):
    samples=np.asarray(samples,dtype=float)
    if samples.ndim!=1 or len(samples)<7 or not np.isfinite(samples).all() or not np.isfinite(fps) or fps<=0:
        raise ValueError('Motion needs at least 7 finite scalar samples and positive fps')
    # Three central differences: weights at offsets -3,-1,+1,+3.
    jerk=(samples[6:]-3*samples[4:-2]+3*samples[2:-4]-samples[:-6])*(fps**3/8)
    result=check('motion.jerk.'+channel+'.max',float(np.max(np.abs(jerk))),data=data)
    result['peak_frame']=int(np.argmax(np.abs(jerk)))+3
    return result


def budget(events, bar_ms=2000, data=None):
    if bar_ms<=0: raise ValueError('bar_ms must be positive')
    for e in events:
        if not np.isfinite(e['at_ms']) or not np.isfinite(e['perceived']) or e['at_ms']<0 or e['perceived']<0:
            raise ValueError('Budget events require nonnegative finite time and perceived')
    ordered=sorted(events,key=lambda e:e['at_ms'])
    used=max((sum(x['perceived'] for x in ordered if e['at_ms']<=x['at_ms']<e['at_ms']+4000) for e in ordered),default=0)
    counts={}
    for e in ordered:
        bar=int(e['at_ms']//bar_ms);counts[bar]=counts.get(bar,0)+1
    return check_metrics({'budget.perceived.max':used,'budget.events.max':max(counts.values(),default=0)},data=data)


def audio_limits():
    return value('audio.loudness.target'),value('audio.loudness.tolerance'),value('audio.true_peak.max')
