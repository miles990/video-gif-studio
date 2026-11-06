"""Local BPM/key measurements and bounded variant transitions; no paid calls."""
import numpy as np
from audio_loop import RATE,features,ffmpeg_pcm,discontinuities,loudness,bar_samples
from image_common import ImageError

from audio_measure import NAMES,key_name,relation,measure


def phase_lag(a,b,max_ms=100):
    """Signed 1ms onset correlation on corresponding windows (B shift to A)."""
    def onset(x):
        x=x[:len(x)//48*48]
        r=np.sqrt(np.mean(x.reshape(-1,48,2)**2,axis=(1,2)))
        return np.maximum(np.diff(r,prepend=r[0]),0)
    u,v=onset(a),onset(b)
    if len(u)!=len(v) or not len(u):raise ValueError('Equal nonempty phase windows required')
    corr=np.fft.irfft(np.fft.rfft(u)*np.conj(np.fft.rfft(v)),n=len(u))
    ids=np.arange(-max_ms,max_ms+1)
    return int(ids[np.argmax(corr[ids%len(u)])])


def align_to_loop(reference,source,bpm=120,meter='4/4',max_checks=60):
    """Re-cut real source bars on a shared onset grid, verifying loops and switches.

    The spectral accent grid is refined by measured onset correlation, then
    searched within +/-4ms for a zero crossing. We do not rotate a finished
    loop and assume its new seam is valid. No samples are synthesized/repeated.
    """
    from audio_grid import grid
    from audio_loop_make import candidates
    from audio_loop import check,normalise
    measured=grid(source,meter);original=dict(measured);stretch_report=None
    if abs(measured['bpm']-bpm)>.5:
        source,stretch_report=stretch(source,measured['bpm'],bpm)
        measured=grid(source,meter)
    bar=round(bar_samples(bpm,meter));count=round(len(reference)/bar)
    if abs(len(reference)-count*bar)>2:raise ValueError('Reference must contain whole bars')
    options=[];seen=set()
    for start in range(measured['downbeat_sample'],len(source)-len(reference)+1,bar):
        lag=phase_lag(reference,source[start:start+len(reference)])
        for delta in np.arange(-4,4.1,.5):
            origin=start-round((lag+delta)*48)
            if origin<round(RATE*60/bpm):continue
            refined=dict(measured,downbeat_sample=origin)
            for y,cut in candidates(source[:origin+len(reference)+49],bpm,meter,(count,),refined):
                key=(cut['start_sample'],cut['crossfade_samples'])
                if key in seen:continue
                seen.add(key)
                residual=phase_lag(reference,y)
                if abs(cut['correlation_lag_ms'])<=1 and abs(residual)<=2:
                    options.append((y,dict(cut,initial_phase_lag_ms=lag,
                                          grid_refinement_samples=origin-start,residual_phase_ms=residual)))
    trials=[]
    for y,cut in sorted(options,key=lambda p:p[1]['score'])[:max_checks]:
        y,gain=normalise(y);qa=check(y,bpm,meter,measured_bpm=measured['bpm'])
        entry=dict(selected=cut,qa=qa);trials.append(entry)
        if qa['status']!='PASS':continue
        transition=switches(reference,y,bpm,meter);entry['switches']=transition
        if transition['status']=='PASS':
            return y,dict(status='PASS',method='local bar grid + onset phase refinement + re-cut',
                          source_grid=original,grid=measured,stretch=stretch_report,selected=cut,
                          first_downbeat_difference_ms=abs(cut['residual_phase_ms']),
                          switch_points_ms=transition['switch_points_ms'],switches=transition,
                          qa=qa,normalization=gain,trials=trials)
    raise ImageError('E_VARIANT_ALIGN','No loop and bidirectional transition candidate passed',trials=trials)


def stretch(x,measured_bpm,target_bpm):
    if measured_bpm is None or min(measured_bpm,target_bpm)<=0:raise ValueError('Measured BPM required')
    ratio=target_bpm/measured_bpm
    if abs(ratio-1)>.04+1e-12:raise ImageError('E_STRETCH_LIMIT','Tempo correction exceeds +/-4%; request a new sounds clip',ratio=ratio)
    y=ffmpeg_pcm(x,f'rubberband=tempo={ratio:.12f}:pitch=1')
    measured=measure(y)
    return y,dict(method='ffmpeg rubberband',ratio=ratio,original_bpm=measured_bpm,target_bpm=target_bpm,
        measured=measured,spec_mismatch=measured['bpm'] is None or abs(measured['bpm']-target_bpm)>.5)


def validate_set(records,theme_key):
    errors=[];bpms=[r['measured']['bpm'] for r in records];starts=[r['downbeat_samples'] for r in records]
    if any(v is None for v in bpms) or max(bpms)-min(bpms)>.5:errors.append(dict(check='bpm',values=bpms))
    if max(starts)-min(starts)>96:errors.append(dict(check='downbeat',offsets_ms=[s/48 for s in starts]))
    for r in records:
        rel=relation(theme_key,r['measured']['key'])
        if rel in ('conflict','unknown') and r.get('key_conflict')!='user_requested':errors.append(dict(check='key',name=r['name'],measured=r['measured']['key'],relation=rel))
        elif rel!='same' and r.get('key_relation')!=rel:errors.append(dict(check='undeclared_relation',name=r['name'],relation=rel))
    return dict(status='FAIL' if errors else 'PASS',errors=errors)


def switches(a,b,bpm,meter='4/4',points=None):
    if len(a)!=len(b):raise ValueError('Align variant cycle lengths before transition testing')
    bar=bar_samples(bpm,meter);points=points or [round(s) for s in np.arange(bar,len(a),bar)]
    fade=round(RATE*60/bpm);results=[]
    for name,left,right in [('A->B',a,b),('B->A',b,a)]:
        for t in points:
            if not 0<t<len(a):raise ValueError('Switch point outside cycle')
            for mode in ('hard','equal_power'):
                y=np.concatenate([left[:t],right[t:]])
                if mode=='equal_power':
                    n=min(fade,len(y)-t);phase=np.linspace(0,np.pi/2,n)[:,None]
                    y[t:t+n]=left[t:t+n]*np.cos(phase)+right[t:t+n]*np.sin(phase)
                clicks=discontinuities(y)
                # Test the actual switch, not the unrelated end->start boundary
                # created by repeating a finite A->B demonstration recording.
                clicks['events_ms']=[v for v in clicks['events_ms'] if 2<v<len(y)/48-2]
                clicks['switch_difference']=float(np.max(np.abs(y[t]-y[t-1])))
                clicks['pass_']=not clicks['events_ms'] and clicks['switch_difference']<=clicks['internal_difference_p999']
                local=y[max(0,t-19200):min(len(y),t+19200)]
                whole=loudness(y);near=loudness(local)
                wm=[v['m'] for v in whole['windows'] if v['t']>=.4];nm=[v['m'] for v in near['windows'] if v['t']>=.4]
                drop=float(np.median(wm)-min(nm)) if wm and nm else float('inf')
                # Transient phase from onset xcorr in the two corresponding bars.
                first=max(0,t-round(bar));last=min(len(a),t+round(bar))
                def onset(x):
                    x=x[:len(x)//48*48];r=np.sqrt(np.mean(x.reshape(-1,48,2)**2,axis=(1,2)));return np.maximum(np.diff(r,prepend=r[0]),0)
                u=onset(left[first:last]);v=onset(right[first:last]);corr=np.fft.irfft(np.fft.rfft(u)*np.conj(np.fft.rfft(v)),n=len(u))
                ids=np.arange(-100,101);lag=int(ids[np.argmax(corr[ids%len(u)])])
                results.append(dict(pair=name,mode=mode,at_samples=t,at_ms=t/48,phase_error_ms=abs(lag),clicks=clicks,
                    momentary_drop_lu=drop,pass_=abs(lag)<=5 and clicks['pass_'] and drop<=3))
    return dict(status='PASS' if all(r['pass_'] for r in results) else 'FAIL',transitions=results,switch_points_ms=[t/48 for t in points])
