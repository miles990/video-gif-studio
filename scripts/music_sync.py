#!/usr/bin/env python3
"""Local music waveform/tempo candidates and continuous soundtrack muxing."""
import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path
import numpy as np


def analyze(source, out, bpm=None, offset_ms=None):
    source=Path(source).resolve();out=Path(out)
    if out.exists(): raise FileExistsError('Use a new analysis directory')
    if bpm is not None and (not math.isfinite(bpm) or not 20 <= bpm <= 400): raise ValueError('BPM must be 20..400')
    if offset_ms is not None and (not math.isfinite(offset_ms) or offset_ms < 0): raise ValueError('Offset must be nonnegative')
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(source),'-vn','-ac','1','-ar','8000','-f','f32le','pipe:1'])
    x=np.frombuffer(raw,dtype='<f4');total_ms=len(x)/8
    if not len(x): raise ValueError('No decoded audio')
    hop=80;count=len(x)//hop
    energy=np.sqrt(np.mean(x[:count*hop].reshape(count,hop)**2,axis=1)) if count else np.zeros(1)
    onset=np.maximum(energy-np.concatenate(([0],energy[:-1])),0)
    strength=float(np.dot(onset,onset));candidates=[]
    if total_ms >= 2000 and strength > 1e-10:
        for tempo in range(60,201):
            lag=round(6000/tempo)
            score=float(np.dot(onset[lag:],onset[:-lag])/strength) if lag<len(onset) else 0
            candidates.append({'bpm':tempo,'periodicity':score})
        candidates.sort(key=lambda a:a['periodicity'],reverse=True)
    chosen=bpm if bpm is not None else (candidates[0]['bpm'] if candidates and candidates[0]['periodicity']>.1 else None)
    offset=offset_ms
    if offset is None:
        offset=float(np.argmax(onset[:max(1,min(len(onset),round(6000/chosen)))]))*10 if chosen else 0
    beats=[] if chosen is None else np.arange(offset,total_ms,60000/chosen).tolist()
    bins=np.array_split(np.abs(x),min(1000,len(x)));wave=[float(v.max()) for v in bins]
    peaks=[]
    for i in range(1,len(onset)-1):
        if onset[i] > max(float(onset.max())*.2,1e-6) and onset[i]>=onset[i-1] and onset[i]>onset[i+1]: peaks.append(i*10)
    record={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'duration_ms':total_ms,'bpm':chosen,'offset_ms':offset,'beats_ms':beats,'onsets_ms':peaks,
            'waveform':wave,'tempo_candidates':candidates[:5],
            'method':'Manual BPM' if bpm is not None else '10ms RMS-onset periodicity heuristic',
            'review':'Unreviewed candidates. Not downbeat/chord/phrase detection; half/double-tempo and variable-tempo errors possible. Edit beats_ms or override BPM/offset.'}
    out.mkdir(parents=True);(out/'beats.json').write_text(json.dumps(record,indent=2)+'\n')
    scale=max(max(wave),1e-9);points=' '.join(f'{i*1200/max(1,len(wave)-1):.2f},{120-v/scale*90:.2f}' for i,v in enumerate(wave))
    lines=''.join(f'<path d="M {t/total_ms*1200:.2f} 15 V 225" stroke="#ea9d2d" opacity=".6"/>' for t in beats[:1000])
    (out/'waveform.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="240"><rect width="1200" height="240" fill="#19212b"/>{lines}<polyline points="{points}" fill="none" stroke="#72dec8"/><text x="10" y="235" fill="white">Beat candidates — review BPM, offset and beat times before editing</text></svg>')
    return record


def mux_music(movie, source, duration_ms, in_ms=0, gain_db=0, fade_in_ms=30, fade_out_ms=30):
    movie=Path(movie);source=Path(source).resolve()
    for v in (in_ms,fade_in_ms,fade_out_ms):
        if not isinstance(v,(int,float)) or not math.isfinite(v) or v<0: raise ValueError('Invalid audio timing')
    if not math.isfinite(gain_db) or not -60<=gain_db<=20:raise ValueError('gain_db must be -60..20')
    if max(fade_in_ms,fade_out_ms)>duration_ms:raise ValueError('Audio fades exceed timeline')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=codec_type','-show_entries','format=duration','-of','json',str(source)]))
    if not probe.get('streams') or in_ms>=float(probe['format']['duration'])*1000:raise ValueError('Audio missing or in_ms beyond source')
    sec=duration_ms/1000
    filt=f'atrim=start={in_ms/1000},asetpts=PTS-STARTPTS,volume={gain_db}dB,apad,atrim=duration={sec}'
    if fade_in_ms:filt+=f',afade=t=in:st=0:d={fade_in_ms/1000}'
    if fade_out_ms:filt+=f',afade=t=out:st={sec-fade_out_ms/1000}:d={fade_out_ms/1000}'
    codec='libopus' if movie.suffix=='.webm' else ('pcm_s16le' if movie.suffix=='.mov' else 'aac')
    with tempfile.TemporaryDirectory(dir=movie.parent) as temp:
        target=Path(temp)/movie.name
        subprocess.run(['ffmpeg','-v','error','-i',str(movie),'-i',str(source),'-map','0:v:0','-map','1:a:0','-c:v','copy','-af',filt,'-c:a',codec,'-t',str(sec),str(target)],check=True)
        actual=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_type,codec_name','-show_entries','format=duration','-of','json',str(target)]))
        if {v['codec_type'] for v in actual['streams']}!={'video','audio'}:raise RuntimeError('Missing audio/video stream')
        if abs(float(actual['format']['duration'])*1000-duration_ms)>100:raise RuntimeError('Audio/video duration mismatch')
        # Force an actual audio decode, not only a container metadata check.
        pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(target),'-vn','-ac','1','-ar','8000','-f','f32le','pipe:1'])
        if abs(len(pcm)/32-duration_ms)>100:raise RuntimeError('Decoded audio timeline mismatch')
        target.replace(movie)
    report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'in_ms':in_ms,'gain_db':gain_db,'fade_in_ms':fade_in_ms,'fade_out_ms':fade_out_ms,'codec':codec,'decoded_audio_duration_ms':len(pcm)/32,'short_source':'padded with silence','video':'stream copied; soundtrack continuous across visual cuts'}
    sidecar=movie.with_suffix(movie.suffix+'.json');data=json.loads(sidecar.read_text());data['audio']=report;sidecar.write_text(json.dumps(data,indent=2)+'\n')
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('music',type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--bpm',type=float);ap.add_argument('--offset-ms',type=float)
    a=ap.parse_args();r=analyze(a.music,a.out,a.bpm,a.offset_ms);print(json.dumps({k:r[k] for k in ('duration_ms','bpm','offset_ms','review')}))


if __name__=='__main__':main()
