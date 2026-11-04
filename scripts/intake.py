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
        '-of', 'json', str(path)]))
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


def intake(source, out, fps=30):
    rate(fps); source=Path(source).resolve(); out=Path(out)
    if out.exists(): raise ValueError('Use a new output directory')
    info=probe(source); video=next((s for s in info['streams'] if s['codec_type']=='video'),None)
    if video is None: raise ValueError('Input contains no video stream')
    stamps=timestamps(source); differences=np.diff(stamps)
    vfr=bool(len(differences)>1 and np.ptp(differences)>.0011)
    rotation=next((s['rotation'] for s in video.get('side_data_list',[]) if 'rotation' in s),0)
    hdr=video.get('color_transfer') in ('smpte2084','arib-std-b67')
    actions=['apply display matrix once with FFmpeg autorotate',f'fps={fps}: nearest timestamp drop/duplicate', 'preserve audio timeline']
    filters=[]
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
    duration=round(float(info['format']['duration'])*fps)/fps
    filters += ['tpad=stop_mode=clone:stop_duration=1',f'fps={fps}:round=near',f'trim=duration={duration}', 'setsar=1', 'setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709']
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as temp:
        root=Path(temp)/'intake';root.mkdir(); movie=root/'source.mp4'
        run(['-v','error','-filter_threads','1','-i',str(source),'-map','0:v:0','-map','0:a:0?',
             '-vf',','.join(filters),'-c:v','libx264','-preset','veryfast','-crf','16','-threads','2',
             '-pix_fmt','yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',
             '-color_range','tv','-metadata:s:v:0','rotate=0','-c:a','aac','-b:a','256k','-ar','48000','-ac','2',
             '-af','aresample=48000:async=1:first_pts=0','-t',str(duration),'-movflags','+faststart',str(movie)])
        sync=sync_check(movie,fps)
        if sync.get('applicable') and not sync['passed']:
            raise RuntimeError('Intake A/V timestamp check failed: '+json.dumps(sync))
        report=dict(source=str(source),fps_mode='vfr' if vfr else 'cfr',rotation=rotation,
                    color={k:video.get(k) for k in ('color_primaries','color_transfer','color_space')},
                    actions=actions,output_fps=fps,output=probe(movie),av_sync=sync)
        (root/'intake.json').write_text(json.dumps(report,indent=2));root.rename(out)
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source',type=Path)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--fps',type=int,default=30)
    a=ap.parse_args()
    try: intake(a.source,a.out,a.fps)
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError) as exc:
        print('intake: '+str(exc),file=sys.stderr);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
