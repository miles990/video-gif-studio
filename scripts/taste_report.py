"""M1-M16 local measurement, never a learned aesthetic score. See references/taste.md."""
import argparse
from pathlib import Path
import re
import sys
import cv2
import numpy as np
from taste_common import read, write, probe, run, executable, zscore, smooth, compare_curve, plot_curve, value, peaks as find_peaks


def colorfulness(rgb):
    x = np.asarray(rgb, float); rg = x[..., 0]-x[..., 1]; yb = (x[..., 0]+x[..., 1])/2-x[..., 2]
    return float(np.hypot(rg.std(), yb.std())+.3*np.hypot(rg.mean(), yb.mean()))


def saliency(rgb):
    """Multiscale local Lab contrast, with broad spatial support. No eye-tracker claim."""
    lab = cv2.cvtColor(np.asarray(rgb, np.float32)/255, cv2.COLOR_RGB2LAB)
    blur = cv2.GaussianBlur(lab, (0, 0), max(1, min(rgb.shape[:2])*.025))
    center = np.median(lab.reshape(-1, 3), axis=0)
    s = np.linalg.norm(blur-center, axis=2)
    total = s.sum(); n = max(1, int(s.size*.05)); flat = s.ravel()
    concentration = float(np.partition(flat, -n)[-n:].sum()/total) if total > 1e-8 else 0.
    yy, xx = np.indices(s.shape)
    # Do not let a large, weakly textured background pull the focus to center.
    salient=np.where(s>=max(float(s.max())*.25,float(np.percentile(s,95))),s,0)
    mass=salient.sum()
    centroid = [float((xx*salient).sum()/mass/s.shape[1]), float((yy*salient).sum()/mass/s.shape[0])] if mass > 1e-8 else None
    return s, concentration, centroid


def frame_metrics(rgb):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, concentration, centroid = saliency(rgb)
    edges = cv2.Canny(gray, 40, 100)
    return dict(colorfulness=colorfulness(rgb), clutter=float(np.mean(edges > 0)), saliency=concentration,
                centroid=centroid, p1=float(np.percentile(gray, 1)), p99=float(np.percentile(gray, 99)),
                clipping=float(np.mean(gray == 255)))


def gray_percentiles(gray):
    """Exact numpy linear P1/P99 from an 8-bit histogram without sorting pixels."""
    counts=np.bincount(gray.ravel(),minlength=256).cumsum();positions=np.array([.01,.99])*(gray.size-1)
    low=np.searchsorted(counts,np.floor(positions),side='right');high=np.searchsorted(counts,np.ceil(positions),side='right')
    result=low+(high-low)*(positions-np.floor(positions))
    return float(result[0]),float(result[1]),float(np.mean(gray==255))


def audio_metrics(path, duration):
    # EBU values and both curves are supplied by the reference implementation itself.
    ebu = run([executable('ffmpeg'), '-nostdin', '-hide_banner', '-i', str(path), '-vn',
               '-af', 'ebur128=peak=true', '-f', 'null', '-']).stderr.decode('utf-8', errors='replace')
    def last(pattern):
        vals = re.findall(pattern, ebu)
        v = float(vals[-1]) if vals else None
        return v if v is not None and np.isfinite(v) else None
    loud = dict(integrated_lufs=last(r'I:\s*([-\w.]+) LUFS'), lra=last(r'LRA:\s*([-\w.]+) LU'),
                true_peak_dbtp=last(r'Peak:\s*([-\w.]+) dBFS'))
    loud['plr'] = loud['true_peak_dbtp']-loud['integrated_lufs'] if loud['true_peak_dbtp'] is not None and loud['integrated_lufs'] is not None else None
    rows = re.findall(r't:\s*([\d.]+).*?M:\s*([-\d.]+)\s+S:\s*([-\d.]+)', ebu)
    loud.update(times=[round(float(r[0]), 3) for r in rows], momentary=[float(r[1]) for r in rows], short_term=[float(r[2]) for r in rows])
    pcm = np.frombuffer(run([executable('ffmpeg'), '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', '48000', '-f', 'f32le', '-']).stdout, '<f4').astype(float)
    audio_duration=len(pcm)/48000
    is_silent=not len(pcm) or float(np.max(abs(pcm)))<1e-7
    loud['low_confidence']=audio_duration<10
    loud['confidence_reason']='Under 10 seconds: limited loudness-range evidence' if audio_duration<10 else None
    if is_silent or audio_duration<.4:
        loud.update(integrated_lufs=None,lra=None,plr=None,reason='Silent audio' if is_silent else 'Under one complete 400 ms loudness window')
    hop = 240; size = 2048
    if len(pcm) < size: pcm = np.pad(pcm, (0, size-len(pcm)))
    frames = np.lib.stride_tricks.sliding_window_view(pcm, size)[::hop]
    power = abs(np.fft.rfft(frames*np.hanning(size), axis=1))**2
    freq = np.fft.rfftfreq(size, 1/48000); sums = power.sum(axis=1)
    centroid = (power@freq)/np.maximum(sums, 1e-20)
    low = power[:, freq < value('taste.audio.low_hz')].sum(axis=1)/np.maximum(sums, 1e-20)
    # 5 ms peak-envelope rising edges preserve clicks at the very first sample.
    count = len(pcm)//hop; envelope = np.max(abs(pcm[:count*hop].reshape(count, hop)), axis=1)
    peaks = find_peaks(np.r_[0, envelope, 0], prominence=max(float(envelope.max())*.1, 1e-8), distance=10)
    onset = (peaks-1)*hop/48000
    rms = np.sqrt(np.mean(pcm[:count*hop].reshape(count, hop)**2, axis=1))
    silent = float(np.mean(20*np.log10(np.maximum(rms, 1e-12)) < value('taste.audio.silence_db')))
    return loud, dict(times=(np.arange(len(centroid))*hop/48000).tolist(), centroid_hz=centroid.tolist(), low_band_ratio=low.tolist(), cutoff_hz=value('taste.audio.low_hz')), onset.tolist(), silent
    

def audio_analysis(path, duration):
    return audio_metrics(path,duration)


def centered_loudness(times,loud):
    """EBU S is a trailing 3 s window: its observation belongs at t-1.5 s."""
    complete=np.flatnonzero(np.asarray(loud['times'])>=2.99)
    if not len(complete):return np.zeros(len(times))
    first=int(complete[0])
    return np.interp(times,np.asarray(loud['times'][first:])-1.5,loud['short_term'][first:])


def picture_bounds(frames):
    """Conservative persistent black edge bands, ignoring fully black frames."""
    valid=[x for x in frames if not no_content(x)]
    h,w=frames[0].shape[:2]
    if not valid:return [0,0,w,h]
    # Paired bands must stay dark in every sampled content frame. A robust
    # spatial percentile tolerates sensor/compression noise and isolated pixels.
    rows=np.max([np.percentile(x,90,axis=(1,2)) for x in valid],axis=0)>8
    cols=np.max([np.percentile(x,90,axis=(0,2)) for x in valid],axis=0)>8
    yy=np.flatnonzero(rows);xx=np.flatnonzero(cols)
    if not len(yy) or not len(xx):return [0,0,w,h]
    top,bottom=int(yy[0]),int(yy[-1]+1);left,right=int(xx[0]),int(xx[-1]+1)
    # A subject on black is not a letterbox: bands must be paired and modest.
    if top<2 or h-bottom<2 or abs(top-(h-bottom))>3 or bottom-top<h*.5:top,bottom=0,h
    if left<2 or w-right<2 or abs(left-(w-right))>3 or right-left<w*.5:left,right=0,w
    return [left,top,right,bottom]


def no_content(rgb):
    """Decoded near-black RGB (limited Y around 16), tolerant of sigma=3 noise."""
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    return float(np.percentile(gray,95))<8 and float(gray.mean())<4


def motion_displacement(previous,gray,scale):
    # Robust high-frequency noise estimate (Laplacian kernel L2 norm = 6).
    noise=float(np.median(abs(cv2.filter2D(previous.astype(np.float32),-1,np.array([[1,-2,1],[-2,4,-2],[1,-2,1]],np.float32))))/(.6745*6))
    if previous.std()<max(1.,noise*4):return 0.
    a=cv2.GaussianBlur(previous,(5,5),.8);b=cv2.GaussianBlur(gray,(5,5),.8)
    points=cv2.goodFeaturesToTrack(a,100,.01,3)
    if points is None:return 0.
    moved,valid,_=cv2.calcOpticalFlowPyrLK(a,b,points,None,winSize=(31,31),maxLevel=3)
    back,back_ok,_=cv2.calcOpticalFlowPyrLK(b,a,moved,None,winSize=(31,31),maxLevel=3)
    good=(valid.ravel()>0)&(back_ok.ravel()>0)&(np.linalg.norm((back-points).reshape(-1,2),axis=1)<.6)
    dist=np.linalg.norm((moved-points).reshape(-1,2),axis=1)[good]
    return max(0.,float(np.percentile(dist,90))-.1*min(noise/3,2))/scale if len(dist) else 0.


def detect_boundaries(images,times,duration):
    """Reverse detector plus adaptive spatial HSV content changes (same palette).

    A peak must persist across the boundary and exceed local motion on both
    sides. This rejects one-frame exposure/RGB accents and moving backgrounds.
    """
    from fx_reverse import inspect_frames
    detected=inspect_frames(images,np.asarray(times)*1000,duration*1000,cuts_only=True)
    if len(images)<3:return detected
    rgb=np.asarray([np.asarray(im) for im in images],np.float32)
    hsv=np.asarray([cv2.cvtColor(x.astype(np.uint8),cv2.COLOR_RGB2HSV) for x in rgb],np.float32)
    delta=abs(np.diff(hsv,axis=0));delta[:,:,:,0]=np.minimum(delta[:,:,:,0],180-delta[:,:,:,0])
    scores=np.r_[0,delta.mean(axis=(1,2,3))];step=float(np.median(np.diff(times)));radius=max(1,round(.2/step));n=len(rgb)
    def distance(a,b):return float(abs(rgb[max(0,min(n-1,a))]-rgb[max(0,min(n-1,b))]).mean())
    candidates=find_peaks(scores,distance=max(1,round(.25/step)),prominence=10)
    for i in candidates:
        if scores[i]<27:continue
        at=float(times[i]*1000)
        if any(abs(at-f['time_ms'])<240 for f in detected['flashes']):continue
        if any(abs(at-c['time_ms'])<max(250,c.get('duration_ms',0)) for c in detected['cuts']):continue
        local=np.r_[scores[max(0,i-2*radius):max(0,i-1)],scores[i+2:min(n,i+2*radius)]]
        nonzero=local[local>1]
        baseline=float(np.median(nonzero)) if len(nonzero) else 1.
        across=distance(i-radius,i+radius)
        within=max(distance(i-2*radius,i-radius),distance(i+radius,i+2*radius))
        if scores[i]>=2*baseline and across>max(20,1.25*within):
            detected['cuts'].append(dict(time_ms=round(at),type='cut',confidence=.75,duration_ms=0,review=True,detector='adaptive spatial HSV'))
    # Extend fx_reverse's cumulative chroma path to spatial content. A gray or
    # same-palette dissolve has no chroma change but follows a near-linear blend
    # between two distinct images. Ordinary motion travels a curved pixel path.
    from fx_reverse import groups
    stride=max(1,round(.04/step));indices=np.arange(0,n,stride)
    small=np.asarray([cv2.resize(rgb[i],(40,24)) for i in indices])
    changes=np.abs(np.diff(small,axis=0)).mean(axis=(1,2,3))
    noise_floor=max(.35,float(np.percentile(changes,20))*2.5)
    for group in groups(np.flatnonzero(changes>noise_floor)):
        a,b=group[0],group[-1]+1
        span=float(times[indices[b]]-times[indices[a]])
        if not .08<=span<=3:continue
        path=small[a:b+1].reshape(b-a+1,-1)
        distance=float(np.linalg.norm(path[-1]-path[0]));travel=float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum())
        if abs(path[-1]-path[0]).mean()<3:continue
        # Reject a fade/exposure ramp: it changes amplitude, not spatial content.
        left=small[a].mean(axis=2);right=small[b].mean(axis=2)
        structure=float(abs(zscore(left)-zscore(right)).mean())
        chroma=small[[a,b]].mean(axis=(1,2));chroma/=np.maximum(chroma.sum(axis=1,keepdims=True),1)
        if structure<.12 and np.linalg.norm(chroma[1]-chroma[0])<.12:continue
        coherence=distance/max(travel,1e-8)
        # Accents may overlap a short dissolve. Require a coherent blend core
        # AND a persistent endpoint change; returning flashes fail the latter.
        core=max(3,round(.1/(step*stride)))
        local=[]
        for j in range(len(path)-core):
            q=path[j:j+core+1]
            if abs(q[-1]-q[0]).mean()>2.5:
                local.append(float(np.linalg.norm(q[-1]-q[0])/max(np.linalg.norm(np.diff(q,axis=0),axis=1).sum(),1e-8)))
        if coherence<.92 and not (span<=.4 and coherence>.5 and max(local,default=0)>.85):continue
        at=round((times[indices[a]]+times[indices[b]])*500)
        if any(abs(at-c['time_ms'])<max(250,span*500) for c in detected['cuts']):continue
        detected['cuts'].append(dict(time_ms=at,type='crossfade',confidence=.7 if coherence>=.92 else .55,duration_ms=round(span*1000),review=True,detector='cumulative spatial blend; short coherent core with persistent endpoints'))
    detected['cuts'].sort(key=lambda x:x['time_ms'])
    return detected


def arousal(times, motion, cuts, loudness, brightness, weights=(.35, .25, .30, .10)):
    weights = np.array(weights, dtype=float, copy=True)
    if weights.shape != (4,) or not np.isfinite(weights).all() or np.any(weights < 0) or weights.sum() <= 0:
        raise ValueError('weights must be four finite nonnegative numbers with positive sum')
    weights /= weights.sum()
    cutrate = np.array([sum(abs(c-t) < .5 for c in cuts) for t in times], float)
    raw = [motion, cutrate, loudness, np.abs(np.diff(brightness, prepend=brightness[0]))]
    requested=weights.copy()
    # Physical-unit variation floors, before z-scoring or weight redistribution:
    # original pixels/frame, cuts/second, LU, limited-range Y delta / 100 ms.
    # Otherwise a lone codec-noise component gets promoted to weight one.
    floors=np.array([.3, .5, .5, .5])
    raw=np.asarray(raw,float)
    active=np.ptp(raw,axis=1)>floors
    weights*=active
    if weights.sum():weights/=weights.sum()
    zs = np.array([zscore(x) if enabled else np.zeros_like(x) for x,enabled in zip(raw,active)])
    # Local physical evidence is required even when a component is variable
    # elsewhere in the film. Compute eligibility before any normalization.
    significant=[bool(np.any((np.ptp(raw[:,max(0,i-10):i+11],axis=1)>floors)&(weights>0))) for i in range(len(times))]
    intensity = smooth(weights@zs)
    return dict(times=np.round(times, 3).tolist(), weights=weights.tolist(), effective_weights=weights.tolist(),requested_weights=requested.tolist(),
                variation_floors=dict(zip(('motion_px_per_frame','cut_rate_per_second','short_term_lu','luminance_delta_y'),floors.tolist())),
                peak_significant=significant,
                components=dict(zip(('motion', 'cut_rate', 'short_term_lufs', 'luminance_delta'), zs.tolist())),
                kernel='centered 20-sample box at 10 Hz, edge replication, offsets -10..9',
                smooth_seconds=value('taste.smooth.seconds'), values=intensity.tolist())


def analyze(path, design=None, weights=None, beats=None, manifest=None, storyboard=None, weight_source=None):
    from taste_common import curve_points
    weight_source=weight_source or ('default' if weights is None else 'user')
    weights=(.35,.25,.30,.10) if weights is None else weights
    arousal(np.array([0.]),[0.],[],[0.],[0.],weights)  # Validate flags before decoding.
    if design is not None:curve_points(design)
    if isinstance(beats,dict):beats=[v/1000 for v in beats['beats_ms']] if 'beats_ms' in beats else beats.get('times',beats.get('beats'))
    if beats is not None and (not isinstance(beats,list) or not np.isfinite(beats).all() or any(b<a for a,b in zip(beats,beats[1:]))):raise ValueError('Beat timestamps must be a finite increasing seconds list or beats_ms beatmap')
    info = probe(path); cap = cv2.VideoCapture(str(path)); fps = info['fps']
    luma=[]; motion=[]; visual=[]; contrast=[]; cuts=[]; means=[]; previous=None; previous_mean=None
    scale = min(1., 320/info['width']); size=(max(2, round(info['width']*scale)), max(2, round(info['height']*scale)))
    index=0; thumbnails=[];content=[];prefix=[]
    try:
        for _ in range(max(1,round(fps))):
            ok,bgr=cap.read()
            if not ok:break
            prefix.append(bgr)
        if not prefix:raise ValueError('No decodable video frames')
        # Include distributed samples so a black/title opening cannot hide bars.
        samples=list(prefix)
        for t in np.linspace(0,max(0,info['duration']-1/fps),9):
            if cap.set(cv2.CAP_PROP_POS_MSEC,float(t*1000)):
                ok,bgr=cap.read()
                if ok:samples.append(bgr)
        if not cap.set(cv2.CAP_PROP_POS_FRAMES,len(prefix)):
            raise ValueError('Cannot restore decode position after active-picture sampling')
        bounds=picture_bounds(samples);left,top,right,bottom=bounds
        scale=min(1.,320/(right-left));size=(max(2,round((right-left)*scale)),max(2,round((bottom-top)*scale)))
        def decoded():
            yield from prefix
            while True:
                ok,bgr=cap.read()
                if not ok:break
                yield bgr
        for bgr in decoded():
            rgb = cv2.cvtColor(bgr[top:bottom,left:right], cv2.COLOR_BGR2RGB)
            # Signalstats YAVG uses limited-range luma, not full-range RGB gray.
            y = rgb.astype(np.float32)@np.array([.2126, .7152, .0722], np.float32)
            luma.append(float(16+219/255*y.mean()))
            mean = rgb.mean(axis=(0, 1)); means.append(mean.tolist())
            small=cv2.resize(rgb, size, interpolation=cv2.INTER_AREA); gray=cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
            full_gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
            thumbnails.append(__import__('PIL.Image',fromlist=['Image']).fromarray(cv2.resize(rgb,(160,90))))
            empty=no_content(rgb)
            content.append('no content' if empty else 'content')
            contrast.append(gray_percentiles(full_gray))
            is_cut = previous_mean is not None and np.linalg.norm(mean-previous_mean) > value('taste.cut.rgb_delta')
            amount=0.
            if previous is not None and not is_cut:
                amount=motion_displacement(previous,gray,scale)
            motion.append(amount)
            if index % max(1, round(fps/10)) == 0:
                metrics=frame_metrics(small); metrics['colorfulness']=colorfulness(rgb); metrics['time']=round(index/fps, 3)
                if empty:metrics.update(centroid=None,saliency=0.)
                visual.append(metrics)
            previous=gray; previous_mean=mean; index+=1
    finally: cap.release()
    if index == 0: raise ValueError('No decodable video frames')
    duration=index/fps; frame_times=np.arange(index)/fps; times=np.arange(0, duration, .1)
    detected=detect_boundaries(thumbnails,frame_times,duration)
    cuts=sorted(set(max(1,min(index-1,round(c['time_ms']*fps/1000))) for c in detected['cuts']))
    for c in cuts:motion[c]=0.
    if info['audio']:
        loud, spectrum, onsets, silent = audio_analysis(path, duration)
    else:
        loud=dict(integrated_lufs=None,lra=None,true_peak_dbtp=None,plr=None,times=[],momentary=[],short_term=[],reason='No audio stream',low_confidence=duration<10)
        spectrum=dict(times=[],centroid_hz=[],low_band_ratio=[],cutoff_hz=value('taste.audio.low_hz'),reason='No audio stream'); onsets=[]; silent=None
    loudcurve=centered_loudness(times,loud)
    # Opening fades change exposure without creating an editorial climax.
    # Identify a monotone exposure reveal from black to its first plateau.
    fade_end=0.
    if content[0]=='no content':
        lum=np.asarray(luma);smooth_lum=np.convolve(np.pad(lum,(2,2),mode='edge'),np.ones(5)/5,'valid')
        start=next((i for i,x in enumerate(content) if x=='content'),len(content))
        end=start
        while end+1<len(lum) and end<fps*5 and smooth_lum[end+1]>=smooth_lum[end]-.3:
            if end>start+fps*.2 and np.ptp(smooth_lum[max(start,end-round(fps*.2)):end+1])<.6:break
            end+=1
        if end-start>=fps*.2 and smooth_lum[min(end,len(lum)-1)]-smooth_lum[min(start,len(lum)-1)]>10:fade_end=end/fps
    proxy_luma=np.interp(times,frame_times,luma)
    proxy_motion=np.interp(times,frame_times,motion)
    if fade_end:
        proxy_luma[times<=fade_end]=np.interp(fade_end,frame_times,luma)
        proxy_motion[times<=fade_end]=0
    effective=np.asarray(weights,float).copy()
    if not loud['times'] or duration<3 or loud.get('integrated_lufs') is None:effective[2]=0
    proxy=arousal(times,proxy_motion,[c/fps for c in cuts if c/fps>fade_end],loudcurve,proxy_luma,effective if effective.sum() else weights)
    if not effective.sum():
        proxy['values']=[0.]*len(times);proxy['effective_weights']=[0.]*4
    proxy['requested_weights']=(np.asarray(weights)/np.sum(weights)).tolist()
    proxy.update(weight_source=weight_source,opening_fade_end=fade_end)
    proxy['loudness_alignment']='Complete trailing 3-second EBU windows centered at t-1.5s; nearest complete window held at edges. Unavailable loudness excluded from effective weights.'
    signal=np.asarray(proxy['values'])
    peak_indices=find_peaks(signal, distance=20, prominence=value('taste.peak.prominence'))
    if np.ptp(signal)>value('taste.peak.prominence') and int(np.argmax(signal)) not in peak_indices:
        peak_indices=[int(np.argmax(signal)),*peak_indices]
    peak_indices=[i for i in peak_indices if proxy['peak_significant'][i] and (not fade_end or times[i]>fade_end) and content[min(index-1,round(times[i]*fps))]!='no content']
    peak_indices=sorted(peak_indices, key=lambda i:(-signal[i],i))[:3]
    peak=peak_indices[0] if peak_indices else None
    valley=max(0,peak-20)+int(np.argmin(signal[max(0,peak-20):peak+1])) if peak is not None else None
    proxy.update(peaks=[dict(time=round(float(times[i]),3), value=float(signal[i])) for i in peak_indices],
                 valley=dict(time=round(float(times[valley]),3),value=float(signal[valley])) if valley is not None else None,
                 peak_to_valley_ratio=float(signal[peak]/signal[valley]) if valley is not None and abs(signal[valley])>1e-9 else None,
                 ratio_reason='Signed z-score ratio; undefined when valley is zero; not a subjective arousal scale')
    lengths=np.diff([0,*cuts,index])/fps
    cut_times=[round(c/fps,3) for c in cuts]; beat_times=beats if beats is not None else onsets
    offsets=[dict(time=t,frame=c,offset_seconds=float(t-min(beat_times,key=lambda b:abs(b-t)))) for t,c in zip(cut_times,cuts)] if beat_times else []
    # Locate the brightest forward 0.5s interval, then compare its preceding 1s.
    # Maximizing the ratio instead would mislabel T-DROP-LIT's earlier rise as the peak.
    lum=np.asarray(luma); jumps=[]
    for i in range(max(1,round(fps)),len(lum)):
        before=float(lum[max(0,i-round(fps)):i].mean()); after=float(lum[i:min(len(lum),i+round(fps*.5))].mean())
        jumps.append((after/max(before,1e-9)-1,i,before,after))
    jump,ji,jb,ja=max(jumps,key=lambda row:(row[3],-row[1]),default=(0.,0,float(lum.mean()),float(lum.mean())))
    novelty=np.linalg.norm(np.diff(np.asarray(means),axis=0),axis=1)
    boundaries=[dict(time=round((i+1)/fps,3),score=float(novelty[i])) for i in range(len(novelty)) if novelty[i]>value('taste.cut.rgb_delta')]
    result=dict(version=1, units='seconds; frame indices zero-based', media=dict(info,frames=index,duration=duration,active_picture=bounds,bar_detection='Persistent paired black bands across opening and nine distributed samples; active-picture measurements'),
        content=dict(times=np.round(times,3).tolist(),labels=[content[min(index-1,round(t*fps))] for t in times]),
        designed_black=bool((storyboard or {}).get('designed_black',False)),
        M1=dict(cut_frames=cuts,cut_times=cut_times,lengths=lengths.tolist(),asl=float(lengths.mean()),median=float(np.median(lengths)),cv=float(lengths.std()/lengths.mean()) if len(lengths)>1 else None,ddof=0,events=detected['cuts'],method='fx_reverse chroma/structure, flash rejection and cumulative dissolve detection'),
        M2=dict(offsets=offsets,within_one_frame=float(np.mean([abs(o['offset_seconds'])<=1/fps+1e-9 for o in offsets])) if offsets else None,reason=None if offsets else 'No beats/onsets or cuts'),
        M3=dict(onsets=onsets,density=len(onsets)/duration,per_second=[sum(i<=t<i+1 for t in onsets) for i in range(int(np.ceil(duration)))]),
        M4=dict(times=np.round(frame_times,3).tolist(),luma=luma,jump=max(0.,jump),peak_frame=ji if jump>value('taste.luminance.no_peak') else None,
                flash_events=detected['flashes'],window_seconds=.5,
                before_interval=[max(0,ji/fps-1),ji/fps],after_interval=[ji/fps,min(duration,ji/fps+.5)],before=jb,after=ja,formula='mean Y[t:t+0.5s] / mean Y[t-1s:t] - 1',
                warning='No main luminance peak' if jump<=value('taste.luminance.no_peak') else 'Already bright before peak' if jump<value('taste.luminance.jump.min') else None),
        M5=dict(values=[v['colorfulness'] for v in visual]),
        M6=dict(times=np.round(frame_times,3).tolist(),pixels_per_frame=motion,analysis_size=list(size),original_size=[info['width'],info['height']],method='90th percentile bidirectional LK; robust noise estimate and floor subtraction; original pixels/frame; cuts excluded'),
        M7=spectrum,M8=loud,M9=dict(values=[v['clutter'] for v in visual],method='Canny edge density (40,100)'),
        M10=dict(values=[v['saliency'] for v in visual],centroids=[v['centroid'] for v in visual],times=[v['time'] for v in visual],definition='top 5 percent local Lab saliency / total'),
        M11=dict(silence_ratio=silent,threshold_dbfs=value('taste.audio.silence_db'),reason=None if info['audio'] else 'No audio stream'),
        M12=dict(events=(manifest or {}).get('events',(manifest or {}).get('recipe_events',[])),
                 transitions=(manifest or {}).get('transitions',[]),manifest_supplied=manifest is not None,reason=None if manifest is not None else 'No manifest supplied'),
        M13=dict(p1=[v[0] for v in contrast],p99=[v[1] for v in contrast],clipping=[v[2] for v in contrast],times=np.round(frame_times,3).tolist()),
        M14=dict(value=None,reason='Optional human continuous-response recording not supplied'),M15=proxy,
        M16=dict(boundaries=boundaries,method='adjacent mean-RGB feature novelty; not semantic novelty'))
    for event in result['M12']['events']:
        t=event.get('time',event.get('at_ms',event.get('start_ms',0))/1000);i=min(index-1,max(0,round(t*fps)))
        event['measured']=dict(frame=i,luma_delta=float(lum[min(index-1,i+1)]-lum[max(0,i-1)]),
                               short_term_lufs=float(np.interp(t,loud['times'],loud['short_term'])) if loud['times'] else None)
    if design is not None:
        result['bar_seconds']=design.get('bar_seconds',2) if isinstance(design,dict) else 2
        spread=lambda x:float(np.percentile(x,90)-np.percentile(x,10)) if len(x) else None
        absolute=dict(lra=loud.get('lra'),short_term_range_lu=spread(loudcurve) if effective[2] else None,
                      luminance_range_y=spread(luma),motion_range_px=spread(motion))
        result['comparison']=compare_curve(times,signal,design,result['bar_seconds'],proxy=True,absolute=absolute)
        if 'provisional' in (storyboard or {}).get('design_origin','') or (isinstance(design,dict) and design.get('origin','').startswith('automatic') and result['comparison']['metric']=='absolute_dynamics'):
            result['comparison'].update(revise=False,automatic=True,deviations=[],reason='Automatic design is not an authored revision target')
        edges=[0,*cut_times,duration]
        if (storyboard or {}).get('shots'):
            from storyboard import normalize
            shots=normalize(storyboard)['shots']
            edges=[s['start'] for s in shots]+[shots[-1]['end']]
        for deviation in result['comparison']['deviations']:
            deviation['shots']=[i+1 for i,(a,b) in enumerate(zip(edges,edges[1:])) if a<deviation['end'] and b>deviation['start']]
    result['summary']=front_page(result,storyboard)
    return result


def front_page(result,board=None):
    from taste_lint import weakest,edit_lint,exemption_summary
    if (board or {}).get('shots'):
        from storyboard import normalize
        board=normalize(board)
    window=weakest(result);duration=result['media']['duration'];cuts=result['M1']['cut_times']
    rows=edit_lint(result,board);suggestions=[]
    authored=[]
    if (board or {}).get('shots'):
        from storyboard import normalize
        authored=normalize(board)['shots'];cuts=[s['start'] for s in authored[1:]]
    def designed_event(at,kind=None):
        """Suppress timed design events, with detected flashes as a fallback."""
        for i,s in enumerate(authored[1:],1):
            transition=s.get('transition',{})
            transition=dict(name=transition) if isinstance(transition,str) else transition
            name=str(transition.get('name',transition.get('type',''))).lower()
            duration=transition.get('duration_ms',1000*min(.2,s['duration']/2,authored[i-1]['duration']/2))/1000
            if 'flash' in name and (kind is None or kind in name) and abs(at-s['start'])<=duration/2+.05:
                return 'designed'
        def walk(obj,parent_start=0.,parent_end=None,event=False):
            if isinstance(obj,list):return any(walk(x,parent_start,parent_end,event) for x in obj)
            if not isinstance(obj,dict):return False
            start=float(obj.get('start',obj.get('time',obj.get('at_ms',obj.get('start_ms',parent_start*1000))/1000)))
            end=float(obj.get('end',obj.get('end_ms',start*1000+obj.get('duration_ms',100))/1000))
            name=str(obj.get('name',obj.get('type',obj.get('effect',obj.get('ref',''))))).lower()
            declared=bool(obj.get('rule_break') or obj.get('designed') or (event and name))
            if declared and start-.05<=at<=end+.05 and (kind is None or kind in name):return True
            return any(walk(v,start,end,k in ('effects','events','elements','transition','transitions','recipe')) for k,v in obj.items() if k not in ('rule_break','shots') and isinstance(v,(dict,list)))
        cues=result.get('M12',{})
        if any(walk(s,s['start'],s['end']) for s in authored) or walk((board or {}).get('effects',[]),event=True) or walk(cues.get('events',[]),event=True) or walk(cues.get('transitions',[]),event=True):return 'designed'
        if not cues.get('manifest_supplied',cues.get('reason') is None) and kind in (None,'flash'):
            flashes=[*result.get('M4',{}).get('flash_events',[]),*[e for e in result['M1'].get('events',[]) if e.get('type') in ('flash','flash_cut')]]
            if any(abs(at-e['time_ms']/1000)<=e.get('duration_ms',0)/2000+max(.05,1/result['media']['fps']) for e in flashes):return 'assumed designed'
        return False
    def add(start,end,action,evidence,global_scope=False):
        if global_scope:
            suggestions.append(dict(start=0.,end=duration,shot=None,scope='film',action='Whole film: '+action,evidence=evidence))
            return
        start=max(0,min(float(start),duration));end=max(start,min(float(end),duration))
        shot=1+sum(t<=start for t in cuts)
        if 'deviation' not in evidence and designed_event(start):return
        suggestions.append(dict(start=round(start,3),end=round(end,3),shot=shot,action=f'{start:.2f}-{end:.2f}s, shot {shot}: {action}',evidence=evidence))
    comparison=result.get('comparison',{})
    for row in comparison.get('deviations',[]) if comparison.get('revise') else []:
        intervals=[(max(row['start'],s['start']),min(row['end'],s['end'])) for s in authored if s['start']<row['end'] and s['end']>row['start']] or [(row['start'],row['end'])]
        for a,b in intervals:add(a,b,row['suggestion'],dict(deviation=row.get('deviation'),design=row['design'],measured=row['measured']))
    for row in rows:
        if row['status']!='annotated':add(row['time'],row['time']+1,row['suggestion'],dict(rule=row['rule'],measured=row['measured']),global_scope=row['shot']==0)
    start=window['start'] if window['start'] is not None else 0
    components=window['components'];dominant=min(components,key=components.get) if components else None
    action={
        'short_term_lufs':'Audition the music across this quieter interval; preserve an intentional release or opening fade, otherwise restore phrase/level continuity.',
        'motion':'Review the subject hold here; retain deliberate stillness, or trim only an inactive tail before the next action.',
        'cut_rate':'Review this sustained shot against the intended pacing; retain it if deliberate, or move its outgoing cut to the next meaningful action.',
        'luminance_delta':'This interval has the least exposure change; retain steady light unless the supplied lighting cues call for a change here.'
    }.get(dominant,'Review these frames for intended content; label a designed black interval explicitly or restore missing footage.')
    if window['start'] is not None:add(start,start+2,action,components)
    sal=result['M10'];valid=[i for i,c in enumerate(sal['centroids']) if c is not None]
    i=min(valid,key=lambda j:sal['values'][j]) if valid else 0
    at=sal['times'][i] if sal['times'] else start
    if valid:add(at,at+1,'Review the least concentrated focal sample here; compare the measured centroid with the intended subject before reframing.',dict(saliency=sal['values'][i],centroid=sal['centroids'][i]))
    elif any(x=='content' for x in result['content']['labels']):add(start,start+1,'This frame has no localized saliency; confirm that the uniform field is the intended composition.',dict(saliency=0,centroid=None))
    clipping=result['M13']['clipping'];i=int(np.argmax(clipping));at=result['M13']['times'][i]
    if clipping[i]>=.00005 and not designed_event(at,'flash') and any(x=='content' for x in result['content']['labels']):
        add(at,at+1,f"At the maximum clipping sample, {clipping[i]:.2%} of pixels are at full white; inspect subject detail here before changing exposure.",dict(clipped_fraction=clipping[i]))
    exemptions=exemption_summary(board or {},rows)
    assumed=[dict(time=e['time_ms']/1000,status='assumed designed',reason='Detected flash without authored event evidence')
             for e in [*result['M4'].get('flash_events',[]),*[e for e in result['M1'].get('events',[]) if e.get('type') in ('flash','flash_cut')]]
             if designed_event(e['time_ms']/1000,'flash')=='assumed designed']
    return dict(weakest=window,suggestions=suggestions,findings=rows,**exemptions,
                assumed_designed_events=assumed,
                weight_source=result['M15'].get('weight_source','default'),
                shot_numbering='authored storyboard timing' if authored else 'provisional: automatic boundaries may miss crossfades or wipes; verify shot numbers against the edit',
                interpretation='Review prompts, not aesthetic defects. Flat, ambient, bright and sustained designs are valid.')


def save_report(result, out, source=None):
    out=Path(out)
    if source is not None:
        from taste_lint import weakest
        from PIL import Image,ImageDraw
        window=weakest(result);result['weakest']=window
        cap=cv2.VideoCapture(str(source));sheet=Image.new('RGB',(720,160),'#101722');draw=ImageDraw.Draw(sheet)
        try:
            for j,t in enumerate(np.linspace(window['start'],min(result['media']['duration']-1/result['media']['fps'],window['end']),3) if window['start'] is not None else []):
                cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,bgr=cap.read()
                if ok:
                    tile=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB));tile.thumbnail((240,135));sheet.paste(tile,(j*240,0));draw.text((j*240+5,140),f'{t:.3f}s',fill='white')
        finally:cap.release()
        out.parent.mkdir(parents=True,exist_ok=True);sheet.save(out.with_name(out.stem+'-weakest.png'))
    write(out.with_suffix('.json'),result)
    summary=result['summary'];window=summary['weakest']
    lines=['# Taste review',summary['interpretation'],f"Exemptions: {summary['exemption_count']} ({summary['annotated_findings']} findings annotated)",
           'Shot numbering: '+summary['shot_numbering'], 'Weight source: '+summary['weight_source'],
           'M4 uses a 0.5-second mean window; single-frame flash events are listed separately: '+str(result['M4'].get('flash_events',[])),
           f"Weakest review window: {window['start']}–{window['end']} seconds. {window['reason']}"]
    lines += ['- '+s['action'] for s in summary['suggestions']]
    lines += ['Warning: '+w for w in summary.get('warnings',[])]
    lines += ['Exemption: '+str(e) for e in summary['exemptions']]
    lines += [f"{e['time']:.3f}s: {e['status']} — {e['reason']}" for e in summary.get('assumed_designed_events',[])]
    if result.get('comparison',{}).get('alignment'):
        lines += ['Curve comparison: '+result['comparison']['measured_domain']+'. '+result['comparison']['alignment']['method']+'. Peak timing: '+result['comparison']['peak_method']+'.']
    out.with_suffix('.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')
    p=result['M15']; times=np.asarray(p['times']); values=np.asarray(p['values'])
    peaks=[int(np.argmin(abs(times-x['time']))) for x in p['peaks']]
    valley=int(np.argmin(abs(times-p['valley']['time']))) if p['valley'] else None
    comparison=result.get('comparison',{})
    plot_curve(out.with_suffix('.png'),times,np.asarray(comparison.get('measured',values)),comparison.get('design'),peaks,valley,result.get('bar_seconds'))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('input',type=Path); ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--design',type=Path); ap.add_argument('--beats',type=Path); ap.add_argument('--manifest',type=Path); ap.add_argument('--weights')
    ap.add_argument('--profile',type=Path);ap.add_argument('--target',type=Path);ap.add_argument('--storyboard',type=Path)
    a=ap.parse_args(argv)
    try:
        from taste_pick import load
        board=read(a.storyboard) if a.storyboard else None
        weights=[float(x) for x in a.weights.split(',')] if a.weights else load(a.profile)['weights']
        source='cli' if a.weights else 'user' if a.profile or not np.allclose(weights,[.35,.25,.30,.10]) else 'default'
        result=analyze(a.input,read(a.design) if a.design else (board or {}).get('design_curve'),weights,read(a.beats) if a.beats else None,read(a.manifest) if a.manifest else None,board,weight_source=source)
        if a.target:
            from taste_target import compare_target
            result['target_comparison']=compare_target(result,read(a.target))
            result['summary'].setdefault('warnings',[]).extend(result['target_comparison']['warnings'])
        save_report(result,a.out,a.input); return 0
    except (OSError,ValueError,TypeError,KeyError,RuntimeError) as exc:
        print('taste_report: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__': raise SystemExit(main())
