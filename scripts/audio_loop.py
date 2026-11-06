"""Experimental sample-domain loop checks and Godot/RIFF engine export.

Thresholds are provisional until live calibration and independent listening.
Every check returns evidence; a failed instrument control blocks certification.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import numpy as np
from media_runtime import executable
from image_common import write,read,ImageError

RATE=48000


def ffmpeg_pcm(x,filters=None,rate=RATE):
    args=[executable('ffmpeg'),'-v','error','-f','f32le','-ar',str(rate),'-ac',str(x.shape[1]),'-i','pipe:0']
    if filters:args+=['-af',filters]
    r=subprocess.run(args+['-f','f32le','pipe:1'],input=np.asarray(x,dtype='<f4').tobytes(),capture_output=True,check=True)
    return np.frombuffer(r.stdout,'<f4').reshape(-1,x.shape[1]).copy()


def decode(path):
    info=json.loads(subprocess.check_output([executable('ffprobe'),'-v','error','-select_streams','a:0','-show_entries','stream=sample_rate','-of','json',str(path)]))
    rate=int(info['streams'][0]['sample_rate'])
    # 48k sources need no resampler. Different rates require the specified soxr.
    filters=['-af','aresample=48000:resampler=soxr'] if rate!=RATE else []
    r=subprocess.run([executable('ffmpeg'),'-v','error','-i',str(path),*filters,'-ac','2','-f','f32le','pipe:1'],capture_output=True,check=True)
    return np.frombuffer(r.stdout,'<f4').reshape(-1,2).copy()


def encode(path,x,rate=RATE,loop_points=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    opts=['-c:a','libvorbis','-q:a','6'] if path.suffix=='.ogg' else ['-c:a','pcm_s16le']
    if loop_points is not None and path.suffix=='.ogg':
        start,end=loop_points
        if not 0<=start<end<=len(x):raise ValueError('Invalid exclusive loop points')
        opts+=['-metadata',f'LOOPSTART={start}','-metadata',f'LOOPLENGTH={end-start}']
    subprocess.run([executable('ffmpeg'),'-v','error','-y','-f','f32le','-ar',str(rate),'-ac','2','-i','pipe:0',*opts,str(path)],input=np.asarray(x,dtype='<f4').tobytes(),capture_output=True,check=True)


def loudness(x):
    r=subprocess.run([executable('ffmpeg'),'-nostats','-f','f32le','-ar',str(RATE),'-ac','2','-i','pipe:0','-af','ebur128=peak=true','-f','null','-'],input=np.asarray(x,dtype='<f4').tobytes(),capture_output=True,check=True)
    log=r.stderr.decode(errors='replace');summary=log.split('Summary:')[-1]
    def number(pattern):
        found=re.search(pattern,summary);v=float(found[1]) if found else float('nan')
        return v if math.isfinite(v) else None
    moments=[dict(t=float(t),m=float(m),s=float(s)) for t,m,s in re.findall(r't:\s*([\d.]+).*?M:\s*(-?[\d.]+).*?S:\s*(-?[\d.]+)',log)]
    return dict(lufs=number(r'I:\s*(-?[\d.]+|-inf)\s*LUFS'),true_peak=number(r'Peak:\s*(-?[\d.]+|-inf)\s*dBFS'),windows=moments)


def normalise(x,target=-16):
    measured=loudness(x)
    if measured['lufs'] is None:raise ValueError('Cannot normalise silence')
    gain=target-measured['lufs']; y=x*10**(gain/20)
    if measured['true_peak'] is not None and measured['true_peak']+gain<=-1.5:
        return y,dict(gain_db=gain,measured=loudness(y))
    # Oversampled limiter with no automatic make-up; final measurement is binding.
    y=ffmpeg_pcm(y,'aresample=192000,alimiter=limit=0.841395:attack=5:release=50:level=false:latency=true,aresample=48000')
    return y[:len(x)],dict(gain_db=gain,measured=loudness(y))


def bar_samples(bpm,meter='4/4'):
    n,d=map(int,meter.split('/'))
    if not 20<=bpm<=400 or n<1 or d not in (2,4,8,16):raise ValueError('Invalid BPM/meter')
    return RATE*60/bpm*n*4/d


def features(x):
    x=x.mean(axis=1);n=len(x);f=np.fft.rfftfreq(n,1/RATE);power=np.abs(np.fft.rfft(x*np.hanning(n)))**2
    mel=2595*np.log10(1+f/700);edges=np.linspace(0,2595*np.log10(1+24000/700),25)
    bands=np.array([power[(mel>=a)&(mel<b)].sum() for a,b in zip(edges,edges[1:])])
    midi=np.rint(69+12*np.log2(np.maximum(f,1)/440)).astype(int)%12
    chroma=np.array([power[(midi==i)&(f>60)].sum() for i in range(12)])
    # Relative log spectra retain timbre while removing constant gain.
    bands=np.log1p(bands/max(float(bands.sum()),1e-12)*1000)
    chroma/=max(float(np.linalg.norm(chroma)),1e-12)
    return np.r_[bands,chroma]


def discontinuities(x):
    n=len(x);joined=np.concatenate([x,x])
    hp=ffmpeg_pcm(joined,'highpass=f=4000:poles=2')
    power=np.mean(hp.astype(float)**2,axis=1);window=96
    c=np.r_[0,np.cumsum(power)];energy=(c[window:]-c[:-window])/window
    # Second copy avoids filter initialization; windows straddle its leading seam.
    ids=np.arange(max(0,n-window),min(len(energy),2*n-window))
    db=10*np.log10(np.maximum(energy[ids],1e-20)/max(float(np.median(energy[n:2*n-window])),1e-20))
    bad=ids[db>18];groups=[]
    for group in np.split(bad,np.where(np.diff(bad)>1)[0]+1):
        if not len(group):continue
        lo=max(0,int(group[0]));hi=min(len(joined),int(group[-1])+window)
        peak=lo+int(np.argmax(np.max(np.abs(hp[lo:hi]),axis=1)))
        groups.append(round((peak%n)*1000/RATE,6))
    differences=np.max(np.abs(np.diff(x.astype(float),axis=0)),axis=1)
    jump=float(np.max(np.abs(x[-1]-x[0])));limit=float(np.percentile(differences,99.9))
    return dict(pass_=not groups and jump<=limit+1e-7,events_ms=groups,seam_difference=jump,
                internal_difference_p999=limit,highpass_peak_db=float(db.max()))


def check(x,bpm,meter='4/4',target=-16,measured_bpm=None,source_format='wav'):
    x=np.asarray(x);n=len(x)
    if x.ndim!=2 or x.shape[1]!=2 or n<4096 or not np.isfinite(x).all():raise ValueError('Need finite stereo audio >=4096 samples')
    bar=bar_samples(bpm,meter);bars=round(n/bar);delta=abs(n-bars*bar);checks={}
    checks['length']=dict(pass_=bars>=1 and delta<=2,error_samples=delta,at_ms=n/48)
    checks['bpm']=dict(pass_=measured_bpm is not None and abs(measured_bpm-bpm)<=.5,measured=measured_bpm,requested=bpm)
    checks['format']=dict(pass_=source_format.lower()!='mp3',format=source_format)
    checks['clicks']=discontinuities(x)
    half=2048;dist=lambda a,b:float(np.linalg.norm(features(a)-features(b)))
    seam=dist(x[-half:],x[:half]);internal=[]
    for t in np.arange(bar,n-half,bar):
        t=round(t)
        if t>=half:internal.append(dist(x[t-half:t],x[t:t+half]))
    threshold=float(np.percentile(internal,95)) if internal else 0
    # A tiny numerical tolerance only; not a perceptual slack multiplier.
    checks['spectrum']=dict(pass_=bool(internal) and seam<=threshold+1e-4,distance=seam,internal_p95=threshold,at_ms=0)
    width=min(round(bar),n//2);a=x[-width:].mean(axis=1);b=x[:width].mean(axis=1)
    # Test +-20ms; an incorrect local maximum still fails the 1ms requirement.
    corr=np.fft.irfft(np.fft.rfft(a)*np.conj(np.fft.rfft(b)))
    lagids=np.arange(-960,961);values=corr[lagids%width];best=int(lagids[np.argmax(values)])
    checks['correlation']=dict(pass_=abs(best)<=48,lag_ms=best/48,at_ms=0)
    # Onset phase uses the doubled signal's 1ms energy derivative against bar pulses.
    energy=np.sqrt(np.mean(x[:n//48*48].reshape(-1,48,2)**2,axis=(1,2)))
    onset=np.maximum(energy-np.roll(energy,1),0);period=60000/bpm*4/int(meter.split('/')[1])
    first=onset[:min(len(onset),round(bar/48*2))];last=onset[max(0,len(onset)-len(first)):]
    # Compare onset grids rather than a phase centroid (the latter drifts with
    # pad modulation even for a stationary beat). Test +/- half one beat.
    phase_corr=np.fft.irfft(np.fft.rfft(first)*np.conj(np.fft.rfft(last)),n=len(first))
    phase_lags=np.arange(-round(period/2),round(period/2)+1)
    phase_lag=int(phase_lags[np.argmax(phase_corr[phase_lags%len(first)])])
    phase_error=abs((phase_lag+len(onset)-len(last)+period/2)%period-period/2)
    checks['phase']=dict(pass_=bool(phase_error<=5),error_ms=float(phase_error),at_ms=0)
    levels=loudness(x);head=loudness(x[:min(n,3*RATE)]);tail=loudness(x[-min(n,3*RATE):])
    seam_audio=np.concatenate([x[-19200:],x[:19200]])
    boundary=loudness(seam_audio)['windows'];moments=[r['m'] for r in levels['windows'] if r['t']>=.4]
    seam_m=[r['m'] for r in boundary if .4<=r['t']<=.8]
    drop=float(np.median(moments)-min(seam_m)) if moments and seam_m else float('inf')
    diff=abs((head['lufs'] or -100)-(tail['lufs'] or -100))
    checks['loudness']=dict(pass_=diff<=1 and drop<=3 and levels['lufs'] is not None and abs(levels['lufs']-target)<=1 and levels['true_peak'] is not None and levels['true_peak']<=-1,
        head_tail_lu=diff,seam_drop_lu=drop,lufs=levels['lufs'],true_peak=levels['true_peak'],at_ms=0)
    return dict(status='PASS' if all(v['pass_'] for v in checks.values()) else 'FAIL',seamless=all(v['pass_'] for v in checks.values()),
                calibration='experimental:live-listening-pending',samples=n,sample_rate=RATE,bpm=bpm,meter=meter,bar_count=bars,checks=checks)


def riff_markers(path,length,markers):
    raw=Path(path).read_bytes()
    def chunk(tag,payload):return tag+struct.pack('<I',len(payload))+payload+(b'\0' if len(payload)%2 else b'')
    # smpl dwEnd is INCLUSIVE. Sidecars and Godot use EXCLUSIVE end.
    smpl=struct.pack('<9I',0,0,round(1e9/RATE),60,0,0,0,1,0)+struct.pack('<6I',0,0,0,length-1,0,0)
    cue=struct.pack('<I',len(markers))+b''.join(struct.pack('<II4sIII',i,s,b'data',0,0,s) for i,s in enumerate(markers))
    labels=b'adtl'+b''.join(chunk(b'labl',struct.pack('<I',i)+f'bar {i+1}'.encode()+b'\0') for i in range(len(markers)))
    body=raw[8:]+chunk(b'smpl',smpl)+chunk(b'cue ',cue)+chunk(b'LIST',labels)
    Path(path).write_bytes(b'RIFF'+struct.pack('<I',len(body))+body)


def repair(x,bpm,meter='4/4',downbeat_sample=0,start_bar=1,bars=4,crossfade_beats=1,measured_bpm=None):
    """Trim measured bar boundaries and blend the outgoing bar into preroll.

    No fade to silence. The selected loop keeps its integer-bar length. The
    incoming preroll must exist before the chosen start; no invented samples.
    All six export gates must still pass after this repair.
    """
    if not 0<=crossfade_beats<=1 or start_bar<0 or bars<1 or int(bars)!=bars:raise ValueError('Integer bars and <=1 beat crossfade required')
    bar=bar_samples(bpm,meter);start=round(downbeat_sample+start_bar*bar);end=round(start+bars*bar)
    width=round(RATE*60/bpm*crossfade_beats)
    if start<width or end>len(x):raise ImageError('E_LOOP_REPAIR','Need real incoming preroll and complete bars')
    y=x[start:end].copy()
    if width:
        phase=np.linspace(0,np.pi/2,width)[:,None]
        y[-width:]=x[end-width:end]*np.cos(phase)+x[start-width:start]*np.sin(phase)
    return y,dict(method='bar-trim + equal-power preroll crossfade',start_sample=start,end_sample=end,
                  crossfade_samples=width,bar_samples=bar,qa=check(y,bpm,meter,measured_bpm=measured_bpm))


def export(source,out,bpm,meter='4/4',provenance=None,allow_failed=False):
    if not provenance or provenance.get('source') not in ('download','upload','synthetic_test'):
        raise ImageError('E_PROVENANCE','Preview audio cannot enter an engine delivery')
    x=decode(source);report=check(x,bpm,meter,measured_bpm=provenance.get('measured_bpm'))
    if report['status']!='PASS' and not allow_failed:raise ImageError('E_LOOP','Loop checks failed',checks=report)
    out=Path(out);out.mkdir(parents=True,exist_ok=True);name=Path(source).stem
    bar=bar_samples(bpm,meter);markers=[round(t) for t in np.arange(0,len(x),bar)]
    result=dict(loop_start_samples=0,loop_end_samples=len(x),sample_rate=RATE,bpm=bpm,meter=meter,
        beats_per_bar=int(meter.split('/')[0]),bar_count=report['bar_count'],bar_markers_ms=[t/48 for t in markers],
        engine_load={e:'untested' for e in ('godot4','unity','fmod','wwise')},formats={},source=provenance,qa=report)
    for fmt in ('wav','ogg'):
        path=out/(name+'.'+fmt);encode(path,x,loop_points=(0,len(x)))
        if fmt=='wav':riff_markers(path,len(x),markers)
        decoded=decode(path);q=check(decoded,bpm,meter,measured_bpm=provenance.get('measured_bpm'),source_format=fmt)
        q['sample_count_matches']=len(decoded)==len(x)
        result['formats'][fmt]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),qa=q)
        if (q['status']!='PASS' or len(decoded)!=len(x)) and not allow_failed:raise ImageError('E_ENCODE_QA','Encoded loop failed',format=fmt,qa=q)
        params='loop=true\nloop_offset=0.0\nbpm='+str(float(bpm))+'\nbeat_count='+str(round(len(x)/RATE*bpm/60))+'\nbar_beats='+str(int(meter.split('/')[0])) if fmt=='ogg' else 'edit/loop_mode=2\nedit/loop_begin=0\nedit/loop_end='+str(len(x))+'\ncompress/mode=0'
        (out/(path.name+'.import')).write_text('[remap]\nimporter="'+('oggvorbisstr' if fmt=='ogg' else 'wav')+'"\ntype="'+('AudioStreamOggVorbis' if fmt=='ogg' else 'AudioStreamWAV')+'"\n\n[deps]\nsource_file="res://'+path.name+'"\n\n[params]\n'+params+'\n',encoding='utf-8')
    write(out/(name+'.loop.json'),result)
    (out/'README.md').write_text('Loop sample ends are exclusive in JSON and Godot. RIFF smpl dwEnd is inclusive (L-1). Unity/FMOD/Wwise runtime loading is untested. Experimental; inspect QA before shipping.\n')
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('check','make','export'));p.add_argument('source',type=Path)
    p.add_argument('--bpm',required=True,type=float);p.add_argument('--measured-bpm',type=float);p.add_argument('--meter',default='4/4');p.add_argument('--out',type=Path)
    p.add_argument('--provenance',type=Path);p.add_argument('--json',action='store_true');p.add_argument('--experimental',action='store_true')
    a=p.parse_args(argv)
    try:
        if not a.experimental:raise ImageError('E_EXPERIMENTAL','Audio loop tools require --experimental')
        if a.action=='make':
            from audio_loop_make import make_loop
            if not a.out:raise ValueError('--out WAV path is required')
            y,r=make_loop(decode(a.source),a.bpm,a.meter)
            encode(a.out,y)
            r['decoded_qa']=check(decode(a.out),a.bpm,a.meter,measured_bpm=r['grid']['bpm'])
            write(a.out.with_suffix('.make.json'),r)
            r['status']=r['decoded_qa']['status']
        else:
            r=check(decode(a.source),a.bpm,a.meter,measured_bpm=a.measured_bpm,source_format=a.source.suffix[1:]) if a.action=='check' else export(a.source,a.out,a.bpm,a.meter,read(a.provenance))
        print(json.dumps(r));return 0 if r.get('status',r.get('qa',{}).get('status'))=='PASS' else 1
    except (ValueError,OSError,subprocess.SubprocessError) as e:
        print(json.dumps(dict(error=getattr(e,'error',dict(code='E_AUDIO',message=str(e))))));return 2


if __name__=='__main__':raise SystemExit(main())
