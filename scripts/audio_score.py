"""Measured Suno timing adapter and local video score fitting (experimental)."""
import numpy as np
from audio_loop import decode,normalise,loudness,encode,discontinuities
from music_fit import candidates,join_audio,remap_beats
from image_common import ImageError,write
from pathlib import Path


def beat_map(analysis):
    beats=analysis.get('beats',[])
    return dict(beats_ms=[b['time_s']*1000 for b in beats],
        downbeats_ms=[b['time_s']*1000 for b in beats if b['bar_position']==1],
        duration_ms=(analysis.get('duration_s') or 0)*1000,bpm=analysis.get('bpm'),
        sections=[dict(start_ms=s['start_s']*1000,end_ms=s['end_s']*1000,label=s['label']) for s in analysis.get('sections',[])])


def crosscheck(provider,local):
    remote=beat_map(provider);a=np.asarray(remote['downbeats_ms']);b=np.asarray(local.get('downbeats_ms',[]))
    if not len(a) or not len(b):return dict(status='unavailable',authoritative='local',reason='Both downbeat maps required')
    errors=[float(np.min(np.abs(a-t))) for t in b];ratio=provider['bpm']/local['bpm']
    factor=min((.5,1,2),key=lambda k:abs(ratio/k-1));bpm_error=abs(ratio/factor-1)
    med=float(np.median(errors))
    return dict(status='PASS' if med<=20 and bpm_error<=.01 else 'FAIL',median_error_ms=med,
        bpm_relative_error=bpm_error,tempo_factor=factor,authoritative='local',engine=local.get('engine','unknown'))


def extension_request(clip_id,beatmap,target_ms):
    down=[t for t in beatmap['downbeats_ms'] if t<beatmap['duration_ms']]
    if not down:raise ValueError('Extension needs a measured bar line')
    point=down[-1]
    return dict(tool='audio_extensions_create',params=dict(id=clip_id,continue_at=point/1000,instrumental=True,
        duration=max(15,(target_ms-point)/1000)),join=dict(tool='audio_full_song',id='returned extension id'),
        continue_at_ms=point,reason='Source is shorter than the video; no silent padding')


def drop_alignment(beatmap,drops,bpm):
    sections=[s['start_ms'] for s in beatmap.get('sections',[])]
    limit=min(250,60000/bpm);result=[]
    for drop in drops:
        options=sorted(sections,key=lambda t:abs(t-drop))[:2]
        result.append(dict(requested_ms=drop,measured_ms=options[0] if options else None,
            error_ms=abs(options[0]-drop) if options else None,pass_=bool(options and abs(options[0]-drop)<=limit),
            candidates=[dict(section_ms=t,shift_ms=drop-t) for t in options]))
    return result


def score(source,beatmap,target_ms,out,fps=30,drops=(),clip_id=None):
    if target_ms<=0 or fps<=0:raise ValueError('Positive video length and fps required')
    x=decode(source);duration=len(x)/48
    if duration+1000/fps<target_ms:
        return dict(status='extension_required',measured_duration_ms=duration,request=extension_request(clip_id,beatmap,target_ms))
    spans=[(0,target_ms)];joins=[]
    if duration>target_ms+1000/fps:
        choices=candidates(beatmap,target_ms)
        usable=[s for s in choices if sum(b-a for a,b in s)>=target_ms]
        if not usable:raise ImageError('E_SCORE_FIT','No bar cut reaches exact duration',candidates=choices)
        spans=usable[0];y,joins=join_audio(x,spans)
    else:y=x.copy()
    y=y[:round(target_ms*48)]
    if abs(len(y)/48-target_ms)>1000/fps:raise ImageError('E_DURATION','Score misses video frame tolerance')
    y,norm=normalise(y,-14);mapped=remap_beats(beatmap,spans);mapped['duration_ms']=len(y)/48
    aligned=drop_alignment(mapped,drops,beatmap['bpm']);join_checks=[]
    for join in joins:
        t=round(join['output_ms']*48);window=y[max(0,t-19200):min(len(y),t+19200)]
        clicks=discontinuities(window)
        clicks['events_ms']=[v for v in clicks['events_ms'] if 2<v<len(window)/48-2]
        clicks['pass_']=not clicks['events_ms'] # window endpoints are not a loop
        local=loudness(window);mom=[r['m'] for r in local['windows'] if r['t']>=.4]
        reference=loudness(y);all_m=[r['m'] for r in reference['windows'] if r['t']>=.4]
        drop=float(np.median(all_m)-min(mom)) if mom and all_m else float('inf')
        join_checks.append(dict(at_ms=t/48,clicks=clicks,loudness_drop_lu=drop,pass_=clicks['pass_'] and drop<=3))
    out=Path(out);out.mkdir(parents=True,exist_ok=True);encode(out/'score.wav',y);levels=loudness(decode(out/'score.wav'))
    ok=all(v['pass_'] for v in aligned+join_checks) and abs(levels['lufs']+14)<=1 and levels['true_peak']<=-1
    result=dict(status='PASS' if ok else 'FAIL',measured_duration_ms=duration,final_duration_ms=len(y)/48,
        target_ms=target_ms,spans=spans,joins=joins,join_checks=join_checks,drops=aligned,measured=levels,normalization=norm)
    write(out/'score-report.json',result);write(out/'beats.json',mapped);return result
