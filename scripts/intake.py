#!/usr/bin/env python3
"""Offline phone intake: apply display rotation, CFR resample, PQ/HLG to SDR."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
from delivery import probe, run, rate
from media_runtime import executable


def timestamps(path):
    data = json.loads(subprocess.check_output([executable('ffprobe'), '-v', 'error',
        '-select_streams', 'v:0', '-show_entries', 'frame=best_effort_timestamp_time',
        '-of', 'json', str(path)],stderr=subprocess.PIPE))
    return [float(f['best_effort_timestamp_time']) for f in data['frames']]


def sync_check(path, fps):
    """Check stream start/end skew; content markers need independent verification."""
    streams = probe(path)['streams']
    video = next(s for s in streams if s['codec_type']=='video')
    audio = next((s for s in streams if s['codec_type']=='audio'), None)
    if not audio: return dict(applicable=False)
    start = abs(float(video.get('start_time',0))-float(audio.get('start_time',0)))
    end = abs(float(video.get('duration',0))+float(video.get('start_time',0))-
              float(audio.get('duration',0))-float(audio.get('start_time',0)))
    return dict(applicable=True, start_skew_ms=start*1000, end_skew_ms=end*1000,
                passed=max(start,end)<=1/fps+.002,
                method='stream timestamps; does not establish perceptual lip sync')


def timestamp_repairs(stamps, step, origin, fps):
    """Separate long discontinuities from ordinary missing-frame intervals.

    PTS alone cannot establish the cause. A jump is a gap with at least 100 ms
    (and three nominal frame periods) missing. Counts exclude the original frame.
    Times are on the repaired, zero-origin timeline and use the CFR rounding rule.
    """
    jumps, drops = [], []
    jump_threshold = max(.1, 3*step)
    previous = stamps[0]
    for current in stamps[1:]:
        if current <= previous: continue
        missing = current-previous-step
        if missing > step*.5:
            first = int(np.floor((previous-origin)*fps+.5))
            last = int(np.floor((current-origin)*fps+.5))
            record = dict(start_seconds=previous+step-origin, length_seconds=missing,
                          observed_pts_gap_seconds=current-previous,
                          nominal_frame_seconds=step,
                          length_interpretation='combined missing interval; a timestamp jump and adjacent dropped frame cannot be separated from PTS alone',
                          frozen_frame_count=max(0, last-first-1))
            (jumps if missing >= jump_threshold-1e-6 else drops).append(record)
        previous = current
    return dict(timestamp_jumps=jumps, ordinary_dropped_frames=drops,
                timestamp_jump_threshold_seconds=jump_threshold,
                timestamp_repair_rule='gap minus nominal frame duration; >= max(100 ms, 3 nominal frames) is a jump; frozen count excludes original frame')


def intake(source, out, fps=30):
    rate(fps); source=Path(source).resolve(); out=Path(out)
    if out.exists(): raise ValueError('Use a new output directory')
    info=probe(source); video=next((s for s in info['streams'] if s['codec_type']=='video'),None)
    if video is None: raise ValueError('Input contains no video stream')
    stamps=timestamps(source); differences=np.diff(stamps)
    if not stamps: raise ValueError('Input contains no decodable video frames')
    audio=next((s for s in info['streams'] if s['codec_type']=='audio'),None)
    origin=min(stamps[0],float(audio.get('start_time',stamps[0]))) if audio else stamps[0]
    positive=differences[differences>0]
    step=float(np.median(positive)) if len(positive) else 1/fps
    end=stamps[-1]+step
    if audio:
        audio_end=(float(audio.get('start_time',origin))+float(audio['duration']) if 'duration' in audio
                   else float(info['format']['duration']))
        end=max(end,audio_end)
    duration=max(1,round((end-origin)*fps))/fps
    vfr=bool(len(differences)>1 and np.ptp(differences)>.0011)
    rotation=next((s['rotation'] for s in video.get('side_data_list',[]) if 'rotation' in s),0)
    hdr=video.get('color_transfer') in ('smpte2084','arib-std-b67')
    actions=['apply display matrix once with FFmpeg autorotate',f'shift both streams by {-origin:.6f} seconds',
             'discard duplicate/backward video timestamps',f'fps={fps}: hold frames across timestamp gaps',
             'pad start/end to common duration without changing relative A/V timing']
    displayed=(video['height'],video['width']) if abs(rotation)%180==90 else (video['width'],video['height'])
    padded=[v+v%2 for v in displayed]
    dimensions=dict(displayed=list(displayed),encoded=padded,pad_right_px=displayed[0]%2,
                    pad_bottom_px=displayed[1]%2,rule='pad right/bottom by one black pixel when odd, after rotation')
    if list(displayed)!=padded: actions.append(dimensions['rule'])
    filters=[f'setpts=PTS-{origin:.9f}/TB',"select='isnan(prev_selected_t)+gt(t,prev_selected_t)'",
             'pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:black']
    if hdr:
        available=run(['-filters'])
        if 'zscale' not in available:
            # Some builds write filter listings to stdout, so query explicitly.
            listing=subprocess.check_output([executable('ffmpeg'),'-hide_banner','-filters'],stderr=subprocess.DEVNULL).decode()
            if 'zscale' not in listing: raise RuntimeError('HDR intake requires zscale; install an FFmpeg build with libzimg. Refusing to relabel PQ as SDR.')
        filters += ['zscale=t=linear:npl=100', 'format=gbrpf32le', 'zscale=p=bt709',
                    'tonemap=tonemap=mobius:param=0.3:desat=0', 'zscale=t=bt709:m=bt709:r=limited', 'format=yuv420p']
        actions.append('HDR to SDR: linearize, BT.2020 to BT.709, mobius tonemap, BT.709 transfer')
    else:
        filters += ['scale=out_color_matrix=bt709:out_range=limited', 'format=yuv420p']
    filters += [f'tpad=stop_mode=clone:stop_duration={duration}',f'fps={fps}:round=near:start_time=0',f'trim=duration={duration}', 'setsar=1', 'setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709']
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as temp:
        root=Path(temp)/'intake';root.mkdir(); movie=root/'source.mp4'
        run(['-v','error','-filter_threads','1','-copyts','-i',str(source),'-map','0:v:0','-map','0:a:0?',
             '-vf',','.join(filters),'-c:v','libx264','-preset','veryfast','-crf','16','-threads','2',
             '-pix_fmt','yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',
             '-color_range','tv','-metadata:s:v:0','rotate=0','-c:a','aac','-b:a','256k','-ar','48000','-ac','2',
             '-af',f'asetpts=PTS-{origin:.9f}/TB,aresample=48000:async=1:first_pts=0,apad,atrim=duration={duration}',
             '-t',str(duration),'-movflags','+faststart',str(movie)])
        sync=sync_check(movie,fps)
        if sync.get('applicable') and not sync['passed']:
            raise RuntimeError('Intake A/V timestamp check failed: '+json.dumps(sync))
        report=dict(source=str(source),fps_mode='vfr' if vfr else 'cfr',rotation=rotation,
                    color={k:video.get(k) for k in ('color_primaries','color_transfer','color_space')},
                    actions=actions,output_fps=fps,output=probe(movie),av_sync=sync,dimensions=dimensions,
                    timestamp_origin_seconds=origin,duplicate_or_backward_pts=int(np.sum(differences<=0)),
                    timestamp_gaps=int(np.sum(differences>step*1.5)),
                    **timestamp_repairs(stamps,step,origin,fps))
        (root/'intake.json').write_text(json.dumps(report,indent=2));root.rename(out)
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source',type=Path)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--fps',type=int,default=30)
    a=ap.parse_args()
    try: intake(a.source,a.out,a.fps)
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError) as exc:
        detail=' '.join(str(exc).split())
        if isinstance(exc,RuntimeError) and len(detail)>300:
            detail='FFmpeg could not normalize this clip; check that its streams are decodable. '+detail[-200:]
        print('intake: '+detail,file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
