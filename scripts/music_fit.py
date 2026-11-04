#!/usr/bin/env python3
"""Three bar-aligned music edits with zero-crossing join smoothing and beat remap."""
import argparse
import csv
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np
from sfx import read_audio, write_wav
from beat_layers import layers
from media_runtime import executable


def candidates(beatmap, target_ms, count=3):
    if count!=3: raise ValueError('music_fit produces exactly 3 candidates')
    design=layers(beatmap); end=design['duration_ms']; down=list(design['downbeats_ms'])
    bar=float(np.median(np.diff(down))) if len(down)>1 else 2000
    if not math.isfinite(target_ms) or target_ms<=0: raise ValueError('target must be positive and finite')
    if target_ms>end: raise ValueError(f'Music ({end/1000:g}s) is shorter than target ({target_ms/1000:g}s); shorten the target or use --no-music')
    edges=sorted(set(down+[end])); section_edges={s['start_ms'] for s in design['sections']}|{end}
    pool=[]
    for first in edges[1:-1]:
        for second in edges:
            if second<=first or second>=end: continue
            length=first+end-second
            if abs(length-target_ms)>bar+1e-6: continue
            # Prefer section-to-section edits, then exact target, then a balanced prefix.
            score=(int(first not in section_edges)+int(second not in section_edges),abs(length-target_ms),abs(first-target_ms*.5))
            pool.append((score,[(0,first),(second,end)]))
    pool.sort(key=lambda item:item[0]); selected=[]
    for _,spans in pool:
        if spans not in selected: selected.append(spans)
        if len(selected)==count: break
    if len(selected)!=count: raise ValueError('Not enough distinct bar edits; supply a longer song or shorter target')
    return selected


def nearest_zero(audio, sample, radius=480):
    """Nearest common low-amplitude stereo zero crossing within 10 ms at 48 kHz."""
    first=max(1,sample-radius);last=min(len(audio)-1,sample+radius)
    mono=audio.mean(axis=1); ids=np.arange(first,last+1)
    crossings=ids[mono[ids]*mono[ids-1]<=0]
    if not len(crossings): return sample
    score=np.max(np.abs(audio[crossings]),axis=1)+abs(crossings-sample)/max(radius,1)*.02
    return int(crossings[np.argmin(score)])


def join_audio(audio, spans, rate=48000, crossfade_ms=40):
    """Keep duration/beat grid; replace join neighborhood with a raised-cosine blend.

    Blend outgoing/incoming continuations centered on their nearest zero crossings.
    Boundary record remains the musical bar; actual centers are recorded separately.
    """
    chunks=[audio[round(a*rate/1000):round(b*rate/1000)].copy() for a,b in spans]
    result=np.concatenate(chunks);joins=[];clock=len(chunks[0]);half=round(crossfade_ms*rate/2000)
    for i in range(1,len(chunks)):
        out_sample=round(spans[i-1][1]*rate/1000); in_sample=round(spans[i][0]*rate/1000)
        z_out=nearest_zero(audio,out_sample,round(rate*.01));z_in=nearest_zero(audio,in_sample,round(rate*.01))
        n=min(half,clock,len(result)-clock)
        indices=np.arange(-n,n)
        left=audio[np.clip(z_out+indices,0,len(audio)-1)]
        right=audio[np.clip(z_in+indices,0,len(audio)-1)]
        fade=(.5-.5*np.cos(np.linspace(0,np.pi,2*n)))[:,None]
        blended=left*(1-fade)+right*fade
        # Also taper the tiny zero-crossing displacement back into the original grid.
        original=result[clock-n:clock+n].copy()
        # A flat center eliminates the original hard splice altogether. Smooth
        # quintic shoulders retain the original clock at either edge (C2 joins).
        phase=np.linspace(0,1,2*n)
        shoulder=np.clip(np.minimum(phase,1-phase)*4,0,1)
        window=(shoulder**3*(10-15*shoulder+6*shoulder**2))[:,None]
        result[clock-n:clock+n]=original*(1-window)+blended*window
        joins.append(dict(output_ms=clock*1000/rate,out_ms=spans[i-1][1],in_ms=spans[i][0],
                          zero_out_ms=z_out*1000/rate,zero_in_ms=z_in*1000/rate,crossfade_ms=2*n*1000/rate))
        clock+=len(chunks[i])
    fade=min(len(result),round(rate*.5))
    # 500 ms squared fade ensures last 50 ms is well below -40 dBFS for ordinary input.
    result[-fade:]*=np.linspace(1,0,fade)[:,None]**2
    return result,joins


def remap_beats(beatmap, spans):
    result={key:[] for key in ('beats_ms','downbeats_ms')}; result['sections']=[];clock=0
    for first,last in spans:
        for key in ('beats_ms','downbeats_ms'):
            result[key]+=[round(t-first+clock,6) for t in beatmap.get(key,[]) if first<=t<last]
        for section in beatmap.get('sections',[]):
            start=max(first,section['start_ms']);stop=min(last,section.get('end_ms',last))
            if stop>start: result['sections'].append(dict(section,start_ms=start-first+clock,end_ms=stop-first+clock))
        clock+=last-first
    result['duration_ms']=clock
    return result


def export_markers(beatmap, out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'beats.json').write_text(json.dumps(beatmap,indent=2),encoding='utf-8')
    with (out/'beats.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['time_ms','downbeat'])
        down=beatmap.get('downbeats_ms',[])
        writer.writerows((t,int(any(abs(t-d)<1e-6 for d in down))) for t in beatmap.get('beats_ms',[]))


def no_music_export(movie, beatmap, out):
    out=Path(out)
    if out.exists(): raise ValueError('Use a new output directory')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as folder:
        stage=Path(folder)/'delivery';stage.mkdir()
        subprocess.run([executable('ffmpeg'),'-v','error','-i',str(movie),'-map','0:v:0','-c:v','copy','-an',str(stage/'no-music.mp4')],check=True)
        export_markers(beatmap,stage);stage.rename(out)


def fit(source, beatmap, target_ms, out, count=3):
    out=Path(out)
    if out.exists(): raise ValueError('Use a new output directory')
    design=layers(beatmap);beatmap=dict(beatmap,downbeats_ms=design['downbeats_ms'],duration_ms=design['duration_ms'])
    choices=candidates(beatmap,target_ms,count); audio=read_audio(source)
    if abs(len(audio)/48-beatmap['duration_ms'])>50: raise ValueError('Beat map duration does not match decoded audio within 50 ms')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as folder:
        stage=Path(folder)/'fit';stage.mkdir();records=[]
        for i,spans in enumerate(choices):
            pcm,joins=join_audio(audio,spans);name=f'candidate-{i+1}'
            write_wav(stage/(name+'.wav'),pcm);mapped=remap_beats(beatmap,spans)
            (stage/(name+'-beats.json')).write_text(json.dumps(mapped,indent=2),encoding='utf-8')
            records.append(dict(name=name,preview=name+'.wav',duration_ms=len(pcm)/48,
                spans=[dict(in_ms=a,out_ms=b) for a,b in spans],joins=joins,sections=mapped['sections']))
        report=dict(target_ms=target_ms,candidates=records,rule='Section edges preferred; all endpoints on bars; duration tolerance one bar; 40 ms zero-crossing blend, 500 ms squared tail fade')
        (stage/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        (stage/'candidates.txt').write_text('\n'.join(f'{r["name"]}: {r["duration_ms"]:.1f} ms; spans={r["spans"]}; joins={r["joins"]}' for r in records),encoding='utf-8')
        stage.rename(out)
    return report


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source',type=Path);ap.add_argument('--beats',required=True,type=Path)
    ap.add_argument('--target',type=float);ap.add_argument('--candidates',type=int,default=3);ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--no-music',action='store_true');a=ap.parse_args(argv)
    try:
        beats=json.loads(a.beats.read_text())
        if a.no_music: no_music_export(a.source,beats,a.out)
        else:
            if a.target is None: raise ValueError('--target seconds required')
            fit(a.source,beats,a.target*1000,a.out,a.candidates)
        return 0
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
        print('music_fit: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__': raise SystemExit(main())
