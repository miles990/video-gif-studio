"""Opt-in sound design. Kenney assets are CC0 (https://kenney.nl/assets).

No Kenney audio is bundled. download_kenney_audio.py records pack provenance.
The deterministic NumPy fallback below is original code, not sampled pack audio.
"""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave
import numpy as np
from media_runtime import executable

RULES = {
    'whip_pan':'whoosh', 'push':'whoosh', 'slide':'whoosh', 'whip':'whoosh',
    'flash_white':'hit', 'flash_cut':'hit', 'zoom_punch':'hit', 'punch':'hit', 'crash_in':'hit', 'crash_out':'hit',
    'caption':'pop', 'text':'pop', 'sticker':'pop', 'cutout_card':'pop',
    'ramp':'riser', 'freeze':'click', 'shutter':'click', 'glitch':'glitch', 'rgb_split':'glitch',
}
KINDS = ('whoosh','hit','pop','riser','click','glitch')


def read_audio(path, rate=48000):
    path=Path(path)
    wav=None
    if path.suffix.lower()=='.wav':
        try: wav=wave.open(str(path),'rb')
        except wave.Error: pass  # Float/extensible WAV is decoded by FFmpeg below.
    if wav is not None:
        with wav as f:
            if f.getsampwidth()==2:
                source_rate=f.getframerate();channels=f.getnchannels()
                data=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(np.float32).reshape(-1,channels)/32768
                if channels==1: data=np.repeat(data,2,axis=1)
                elif channels!=2: raise ValueError('SFX WAV must be mono or stereo')
                if source_rate!=rate:
                    target=np.arange(round(len(data)*rate/source_rate))*source_rate/rate
                    data=np.column_stack([np.interp(target,np.arange(len(data)),data[:,c]) for c in (0,1)])
                return data.astype(np.float32)
    raw=subprocess.check_output([executable('ffmpeg'),'-v','error','-i',str(path),'-ac','2','-ar',str(rate),'-f','f32le','-'])
    return np.frombuffer(raw,'<f4').reshape(-1,2).copy()


def write_wav(path, data, rate=48000):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(rate)
        f.writeframes((np.clip(data,-1,1)*32767).astype('<i2').tobytes())


def synthesize(kind, rate=48000):
    if kind not in KINDS: raise ValueError('Unknown SFX: '+str(kind))
    duration={'whoosh':.22,'hit':.16,'pop':.12,'riser':.65,'click':.035,'glitch':.13}[kind]
    t=np.arange(round(rate*duration))/rate; rng=np.random.default_rng(KINDS.index(kind)+891)
    noise=rng.uniform(-1,1,len(t)); p=t/duration
    if kind=='whoosh': signal=noise*(1-p)**2
    elif kind=='hit': signal=np.sin(2*np.pi*(95*t-100*t*t))*np.exp(-30*t)+noise*.25*np.exp(-70*t)
    elif kind=='pop': signal=np.sin(2*np.pi*(700*t-1700*t*t))*np.exp(-45*t)
    elif kind=='riser': signal=(np.sin(2*np.pi*(180*t+1800*t*t))+noise*.35)*p**2
    elif kind=='click': signal=(noise+np.sin(2*np.pi*2400*t))*.5*np.exp(-140*t)
    else: signal=np.sin(2*np.pi*(1200*t+400*np.floor(t*70)*t))*(.3+.7*(np.sin(t*180)>0))*(1-p)
    envelope=np.minimum(1,t/.001)*np.minimum(1,(duration-t)/.003)
    signal=signal*envelope; signal=.35*signal/max(float(np.max(np.abs(signal))),1e-9)
    return np.repeat(signal[:,None],2,axis=1).astype(np.float32)


def resolve(kind, user_folder=None, kenney_folder=None):
    for source,folder,license_name in [('user',user_folder,'user-supplied; verify rights'),('kenney',kenney_folder,'CC0-1.0')]:
        if not folder: continue
        root=Path(folder)
        mapping=root/'sfx-map.json'
        if mapping.is_file():
            names=json.loads(mapping.read_text(encoding='utf-8-sig')); name=names.get(kind)
            candidates=[root/name] if name else []
        else:
            candidates=sorted(p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in ('.wav','.ogg','.mp3') and p.stem.lower().startswith(kind)) if root.is_dir() else []
        if candidates:
            file=candidates[0].resolve()
            if not file.is_relative_to(root.resolve()): raise ValueError('SFX map path escapes its source folder')
            if not file.is_file(): raise ValueError('SFX map references missing file: '+str(file))
            return read_audio(file),dict(source=source,path=str(file),license=license_name,sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    return synthesize(kind),dict(source='procedural',path=None,license='original project synthesis')


def events_from_plan(plan, effects, transitions, segments, captions=None, fps=None):
    from delivery import quantize
    events=[]
    def add(name, at):
        if name in RULES:
            # Align sound to delivered visual frames; never round to a 10ms audio grid.
            delivered=quantize(at,fps)['quantized_ms'] if fps else at
            events.append(dict(kind=RULES[name],event=name,requested_ms=at,at_ms=delivered))
    for e in effects:
        if e.get('recipe_name'):
            # Recipe sounds are explicitly aligned to measured visual peaks below.
            continue
        name=e['params'].get('move',e['name'])
        if plan.get('cut_density') and RULES.get(name)=='hit' and e.get('trigger_times_ms'): continue
        for at in e.get('trigger_times_ms') or [e.get('requested_start_ms',e['start_ms'])]:
            if name=='whip':
                from fx.effects.camera import whip_peak_ms
                at+=whip_peak_ms(e['params'].get('duration_ms',0),fps or 30)
            add(name,at)
            if name=='whip': events[-1]['alignment']='peak'
    for tr in transitions: add(tr['name'],tr.get('requested_cut_ms',tr['cut_ms']))
    for s in segments:
        if plan.get('cut_density') and s['start_ms']>0: add('punch',s['start_ms'])
        edit=s.get('edit',{})
        if 'ramp' in edit:
            # Resolved by the caller from the beat map when available.
            add('ramp',edit['ramp'].get('hit_at_ms',s['start_ms']+s['duration_ms']))
        if edit.get('previous')=='last' or edit.get('type')=='freeze': add('freeze',s['start_ms'])
    if captions:
        # Accent phrase starts: at most one pop / 1.5 s and no adjacent lines.
        last=-float('inf');last_index=-2
        for index,line in enumerate(captions['lines']):
            if index-last_index>=2 and line['start_ms']-last>=1500:
                add('caption',line['start_ms']);last=line['start_ms'];last_index=index
    for recipe in plan.get('recipe_events',[]):
        if recipe['sfx']:
            at=recipe['sfx_at_ms']
            delivered=quantize(at,fps)['quantized_ms'] if fps else at
            events.append(dict(kind=recipe['sfx'],event=recipe['recipe'],requested_ms=at,at_ms=delivered,alignment='onset'))
    unique={ (e['kind'],round(e['at_ms'],6)):e for e in events }
    return sorted(unique.values(),key=lambda e:e['at_ms'])


def render_track(events, duration_ms, target, user_folder=None, kenney_folder=None, gain_db=0):
    if not math.isfinite(duration_ms) or duration_ms<=0 or not math.isfinite(gain_db) or not -60<=gain_db<=12:
        raise ValueError('Invalid SFX duration/gain')
    count=round(duration_ms*48); report=[]; assets={}
    # Memory-mapped scratch is scoped to this output operation; no full-film RAM buffer.
    scratch=Path(target).with_suffix('.f32.partial')
    try:
        mix=np.memmap(scratch,dtype='float32',mode='w+',shape=(count,2));mix[:]=0
        for event in events:
            kind=event['kind']
            if kind not in assets: assets[kind]=resolve(kind,user_folder,kenney_folder)
            data,provenance=assets[kind]; anchor=round(event['at_ms']*48)
            peak=int(np.argmax(np.max(np.abs(data),axis=1)))
            first=anchor-len(data) if kind=='riser' else anchor-peak if event.get('alignment')=='peak' else anchor
            start=max(0,first); stop=min(count,first+len(data))
            if stop>start: mix[start:stop]+=data[start-first:stop-first]*10**(gain_db/20)
            report.append(dict(event,**provenance,start_sample=start,anchor_sample=anchor,
                               alignment='end' if kind=='riser' else event.get('alignment','onset'),sample_rate=48000))
        # Use float PCM via ffmpeg: do not clip overlapping sounds before P0's limiter.
        mix.flush();del mix
        process=subprocess.run([executable('ffmpeg'),'-v','error','-f','f32le','-ar','48000','-ac','2','-i',str(scratch),
                                '-c:a','pcm_f32le',str(target)],capture_output=True)
        if process.returncode: raise RuntimeError('SFX encode failed: '+process.stderr.decode(errors='replace')[-1500:])
    finally:
        scratch.unlink(missing_ok=True)
    return report
