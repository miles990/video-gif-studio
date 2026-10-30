#!/usr/bin/env python3
"""Measured QA for GIF/APNG, RGBA PNG sequences and video.

Adapted from win4r/video-director scripts/qa_video.py (MIT).
Copyright (c) 2026 win4r. See THIRD_PARTY.md for the full license.
Alpha-aware timing, hold subtraction and repeated-frame handling are local adaptations.
"""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw
from media_runtime import executable, locate


def command(args):
    result = subprocess.run(args, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[-1200:])
    return result.stdout


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def media_info(path, fps):
    if path.is_dir():
        files = sorted((p for p in path.glob('*.png') if p.stem.isdigit()), key=lambda p: int(p.stem))
        if not files:
            raise ValueError('PNG directory must contain numerically named frames')
        with Image.open(files[0]) as im:
            size = im.size
        return dict(kind='png', files=files, size=size, durations=[1/fps]*len(files), audio=False, loop=False)
    if path.suffix.lower() in ('.gif', '.apng', '.png'):
        with Image.open(path) as im:
            poster = int(bool(im.info.get('default_image', False)))
            durations = []
            for i in range(poster, getattr(im, 'n_frames', 1)):
                im.seek(i)
                durations.append(float(im.info.get('duration', 1000/fps))/1000)
            return dict(kind='pillow', size=im.size, durations=durations, poster=poster,
                        audio=False, loop=im.info.get('loop') == 0)
    ffprobe = locate('ffprobe')
    if not ffprobe:
        return ffmpeg_info(path)
    data = json.loads(command([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))
    video = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if video is None:
        raise ValueError('No video stream')
    frame_data = json.loads(command([ffprobe, '-v', 'error', '-select_streams', 'v:0', '-show_frames',
        '-show_entries', 'frame=best_effort_timestamp_time,pkt_duration_time,duration_time', '-of', 'json', str(path)]))['frames']
    timestamps = [float(f['best_effort_timestamp_time']) for f in frame_data]
    if not timestamps:
        raise ValueError('No decoded frames')
    num, den = map(float, video.get('avg_frame_rate', '25/1').split('/'))
    last_duration = float(frame_data[-1].get('duration_time', frame_data[-1].get('pkt_duration_time', den/num)))
    durations = list(np.diff(timestamps)) + [last_duration]
    return dict(kind='video', size=(video['width'], video['height']), durations=durations,
                audio=any(s['codec_type']=='audio' for s in data['streams']), loop=False)


def ffmpeg_info(path):
    """Read frame presentation times when an existing FFmpeg has no ffprobe pair.

    showinfo is decoded evidence, not guessed CFR metadata. Older FFmpeg versions
    without frame duration_time require the normal ffprobe runtime instead.
    """
    result = subprocess.run([executable('ffmpeg'), '-nostats', '-i', str(path), '-map', '0:v:0',
        '-vf', 'scale=360:-2,showinfo', '-an', '-f', 'null', '-'],capture_output=True)
    log = result.stderr.decode(errors='replace')
    if result.returncode:
        raise RuntimeError(log[-1200:])
    stamps, durations = [], []
    size = None
    for line in log.splitlines():
        if 'showinfo' not in line or 'pts_time:' not in line:
            continue
        stamp = re.search(r'\bpts_time:([\d.eE+-]+)',line)
        duration = re.search(r'\bduration_time:([\d.eE+-]+)',line)
        dimensions = re.search(r'\bs:(\d+)x(\d+)',line)
        if stamp and duration and dimensions:
            stamps.append(float(stamp[1]));durations.append(float(duration[1]))
            size = tuple(map(int,dimensions.groups()))
    if not stamps or durations[-1]<=0:
        raise RuntimeError('Frame timing unavailable; run scripts/media_runtime.py --install for ffprobe')
    return dict(kind='video',size=size,durations=list(np.diff(stamps))+[durations[-1]],
                audio=bool(re.search(r'Stream #.*Audio:',log)),loop=False)


def frames(path, info):
    if info['kind'] == 'png':
        for file in info['files']:
            with Image.open(file) as im:
                yield im.convert('RGBA')
    elif info['kind'] == 'pillow':
        with Image.open(path) as im:
            for i in range(info['poster'], im.n_frames):
                im.seek(i)
                yield im.convert('RGBA')
    else:
        w = 360
        h = max(2, round(w*info['size'][1]/info['size'][0]/2)*2)
        # Drain stderr to a file so a decoder error cannot block a full pipe.
        import tempfile
        with tempfile.TemporaryFile() as errors:
            with subprocess.Popen([executable('ffmpeg'), '-v', 'error', '-i', str(path), '-map', '0:v:0',
                '-vf', f'scale={w}:{h}:flags=area', '-vsync', '0', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'],
                stdout=subprocess.PIPE, stderr=errors) as proc:
                try:
                    while True:
                        raw = proc.stdout.read(w*h*3)
                        if not raw:
                            break
                        if len(raw) != w*h*3:
                            raise RuntimeError('Incomplete decoded frame')
                        yield Image.frombytes('RGB', (w,h), raw).convert('RGBA')
                finally:
                    proc.stdout.close()
                    if proc.poll() is None:
                        proc.wait()
                if proc.returncode:
                    errors.seek(0)
                    raise RuntimeError(errors.read().decode(errors='replace')[-1200:])


def runs(mask):
    start = None
    for i, value in enumerate(list(mask)+[False]):
        if value and start is None:
            start = i
        elif not value and start is not None:
            yield start, i
            start = None


def subtract_holds(start, end, holds):
    pieces = [(start, end)]
    for a, b in sorted(holds):
        pieces = [(x,y) for s,e in pieces for x,y in ((s,min(e,a)),(max(s,b),e)) if y>x]
    return pieces


def plan_settings(path):
    """Read compose_timeline plans or their emitted manifests. Joins are not cuts."""
    if path is None:
        return [], [], []
    plan = read_json(path)
    holds = [(float(h['from']), float(h['to'])) for h in plan.get('holds', [])]
    cuts = [float(t) for t in plan.get('expect_cuts', [])]
    joins = []
    beats = read_json(path.parent/plan['beatmap'])['beats_ms'] if 'beatmap' in plan else None
    cursor = 0.0
    for segment in plan.get('segments', []):
        start = float(segment.get('start_ms', cursor*1000))/1000
        if 'end_beat' in segment and beats is not None:
            end = (beats[segment['end_beat']]-plan.get('music', {}).get('in_ms',0))/1000
        elif 'duration_ms' in segment:
            end = start + float(segment['duration_ms'])/1000
        elif 'manifest' in segment:
            manifest = read_json(path.parent/segment['manifest'])
            length = sum(manifest['durations_ms'])
            end = start+(segment.get('out_ms',length)-segment.get('in_ms',0))/1000/segment.get('speed',1)
        else:
            raise ValueError('Timeline segment needs duration_ms, end_beat or a readable manifest')
        if start > 0:
            (cuts if segment.get('transition') == 'cut' else joins).append(start)
        if segment.get('type') in ('still','hold'):
            holds.append((start,end))
        cursor = end
    return holds, cuts, joins


def sample_indices(edges, times):
    return [min(len(edges)-2, max(0,int(np.searchsorted(edges, t, side='right')-1))) for t in times]


def picture(path, info, edges):
    duration = edges[-1]
    targets = {
        'contact_sheet': sample_indices(edges, np.linspace(0, max(0,duration-1e-6), min(12,len(edges)-1))),
        'phone_sheet': sample_indices(edges, np.arange(0,duration,1)),
        'hook_sheet': sample_indices(edges, np.arange(0,min(3,duration),.5)),
    }
    wanted = set(i for indices in targets.values() for i in indices)
    thumbs = {}
    d, skip, pops, means, contrasts = [], [], [], [], []
    first = prev = prev2 = None
    for i, im in enumerate(frames(path, info)):
        if im.size != tuple(info['size']) and info['kind'] != 'video':
            raise ValueError('All frames must share one canvas')
        if i in wanted:
            thumbs[i] = im.resize((360,max(1,round(im.height*360/im.width))), Image.Resampling.LANCZOS)
        # Pillow resizes RGBA with premultiplied alpha; hidden RGB never enters metrics.
        width = min(192, im.width)
        small = im.resize((width,max(1,round(im.height*width/im.width))), Image.Resampling.BOX)
        rgba = np.asarray(small, dtype=np.float32)
        alpha = rgba[:,:,3]/255
        gray = rgba[:,:,:3] @ np.array([.299,.587,.114], dtype=np.float32)
        weight = float(alpha.sum())
        mean = float((gray*alpha).sum()/weight) if weight else 0.0
        contrast = float(np.sqrt(((gray-mean)**2*alpha).sum()/weight)) if weight else 0.0
        means.append(mean); contrasts.append(contrast)
        # Premultiply solely for *differences*, not frame-0 exposure. Retain RGB:
        # equal-luminance colored objects can move without changing grayscale.
        visible = rgba[:,:,:3]*alpha[:,:,None]
        d.append(float(np.abs(visible-prev).mean()) if prev is not None else 0.0)
        skip.append(0.0); pops.append(0.0)
        if prev2 is not None:
            skip[i-1] = float(np.abs(visible-prev2).mean())
            # A local patch returning immediately, distinct from moving silhouettes.
            stable = np.abs(visible-prev2).mean(axis=2)<5
            excursion = np.minimum(np.abs(prev-visible).mean(axis=2), np.abs(prev-prev2).mean(axis=2))
            pops[i-1] = float(np.mean(stable & (excursion>40)))
        if first is None:
            first = visible.copy()
        prev2, prev = prev, visible
    if len(d) != len(edges)-1:
        raise ValueError('Decoded frame count does not match timestamps')
    return dict(d=np.array(d), skip=np.array(skip), patch=np.array(pops), mean=means, contrast=contrasts,
                seam=float(np.abs(prev-first).mean()), targets=targets, thumbs=thumbs)


def event(edges, start, end=None, **extra):
    item = {'frame':int(start), 'seconds':round(float(edges[start]),6)}
    if end is not None:
        item.update(end_frame=int(min(end,len(edges)-2)), end_seconds=round(float(edges[end]),6))
    item.update(extra)
    return item


def analyse_picture(st, edges, loop=False, holds=(), expected=(), joins=()):
    n = len(edges)-1
    checks = []
    def add(name, level, message, events=(), **metrics):
        checks.append(dict(name=name,level=level,message=message,events=list(events),**metrics))
    mean, contrast = st['mean'][0], st['contrast'][0]
    bad = mean<8 or contrast<6
    add('frame0','FAIL' if bad else 'PASS', 'Black frame' if mean<8 else ('Flat frame' if contrast<6 else 'Visible composition has exposure and contrast'),
        [event(edges,0)], mean=mean,contrast=contrast)
    d, skip = st['d'], st['skip']
    # Median of actual visual steps: duplicated encoder frames do not lower the baseline.
    active = d[1:][d[1:]>=.01]
    med = float(np.median(active)) if len(active) else 0.0
    flashes = [i for i in range(1,n-1) if d[i]>max(2,4*med) and d[i+1]>max(2,4*med)
               and skip[i]<.35*min(d[i],d[i+1])]
    flash_edges = set(flashes) | {i+1 for i in flashes}
    pop = [i for i in range(1,n-1) if i not in flash_edges and
           ((st['patch'][i]>.01 and d[i]>.5 and d[i+1]>.5) or
            (d[i]>max(2,3*med) and d[i+1]>2 and skip[i]<.8*min(d[i],d[i+1])))]
    add('flashes','FAIL' if flashes else 'PASS','Single-frame flash scan', [event(edges,i) for i in flashes])
    add('pops','WARN' if pop else 'PASS','Small transient pop scan; inspect in context', [event(edges,i) for i in pop])
    frozen, designed = [], []
    still = d<.25
    still[0] = False
    intervals = [(float(edges[a-1]),float(edges[b])) for a,b in runs(still)]
    # GIF/APNG encoders may merge identical frames into one long-duration frame.
    intervals += [(float(edges[i]),float(edges[i+1])) for i in range(n) if edges[i+1]-edges[i]>=1]
    merged = []
    for a,b in sorted(intervals):
        if b-a<1-1e-8:
            continue
        if merged and a<=merged[-1][1]+1e-8:
            merged[-1] = (merged[-1][0],max(b,merged[-1][1]))
        else:
            merged.append((a,b))
    def span(a,b):
        start = sample_indices(edges,[a])[0]
        end = min(n,int(np.searchsorted(edges,b-1e-8,side='left')))
        return event(edges,start,end,seconds=round(a,6),end_seconds=round(b,6))
    for a,b in merged:
        if b-a<1-1e-8:
            continue
        for x,y in holds:
            if min(b,y)>max(a,x):
                designed.append(span(max(a,x),min(b,y)))
        frozen += [span(x,y) for x,y in subtract_holds(a,b,holds) if y-x>=1-1e-8]
    add('freeze','WARN' if frozen else 'PASS','Frozen stretches; mark intended pauses with --holds START-END or timeline still segments',frozen,
        designed_holds=designed)
    cuts = []
    for i in range(1,n):
        local = np.concatenate((d[max(1,i-15):i],d[i+1:min(n,i+16)]))
        local = local[local>=.25]
        baseline = float(np.median(local)) if len(local) else 0
        if i not in flash_edges and d[i]>max(6,3.5*(baseline+.5)):
            cuts.append(i)
    cut_events = []
    if expected:
        matched = set()
        for t in expected:
            index = sample_indices(edges,[t])[0]
            candidates = [i for i in cuts if abs(float(edges[i])-t)<=max(edges[index+1]-edges[index],edges[i+1]-edges[i])+1e-6]
            if candidates:
                matched.add(min(candidates,key=lambda i:abs(edges[i]-t)))
            else:
                cut_events.append(event(edges,index,seconds=float(t),kind='missing planned cut'))
        cut_events += [event(edges,i,kind='unplanned cut') for i in cuts if i not in matched]
    add('cuts','FAIL' if cut_events else 'PASS','Hard cuts compared within one frame' if expected else 'Detected cut candidates (no hard cuts required)',
        cut_events, detected=[event(edges,i) for i in cuts], expected_seconds=list(expected))
    add('timeline_joins','PASS','Continuation/edit boundaries are not required hard cuts; review continuity',
        [event(edges,sample_indices(edges,[t])[0],seconds=float(t)) for t in joins])
    if loop and n>1:
        # Look through duplicated endpoint frames to adjacent moving steps.
        moving = np.flatnonzero(d>=.01)
        speed_in = float(d[moving[-1]] / (edges[moving[-1]]-edges[moving[-1]-1])) if len(moving) else 0
        speed_out = float(d[moving[0]] / (edges[moving[0]]-edges[moving[0]-1])) if len(moving) else 0
        ratio = (speed_in+.05)/(speed_out+.05)
        position = st['seam']<.5 or st['seam']<=2*med
        stationary = bool(not len(moving) or max(d[moving[0]],d[moving[-1]])<.25)
        speed = stationary or .5<=ratio<=2
        add('loop','PASS' if position and speed else 'FAIL',
            'Loop position and speed' + ('' if speed else ': speed mismatch'),
            [event(edges,n-1,seconds=float(edges[-1]),to_frame=0)], seam=st['seam'],median_step=med,
            seam_ratio=st['seam']/max(med,1e-6),speed_ratio=ratio,position_pass=position,speed_pass=speed,
            speed_applicable=not stationary)
    else:
        add('loop','PASS','N/A: no loop requested' if not loop else 'N/A: single frame')
    return checks


def analyse_audio(path, info, edges):
    if not info['audio']:
        return [dict(name=name,level='PASS',message='N/A: no audio track',events=[]) for name in ('loudness','true_peak','loudest_100ms','silence')]
    ffmpeg = executable('ffmpeg')
    result = subprocess.run([ffmpeg,'-nostats','-i',str(path),'-map','0:a:0','-af','ebur128=peak=true','-f','null','-'],capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[-1200:])
    log = result.stderr.decode(errors='replace').split('Summary:')[-1]
    loudness = re.search(r'I:\s+(-?[\d.]+|-inf)\s+LUFS',log)
    peak = re.search(r'True peak:\s+Peak:\s+(-?[\d.]+|-inf)\s+dBFS',log)
    if loudness is None or peak is None:
        raise RuntimeError('FFmpeg ebur128 returned no loudness/true peak summary')
    lufs, tp = float(loudness[1]), float(peak[1])
    raw = command([ffmpeg,'-v','error','-i',str(path),'-map','0:a:0','-ac','1','-ar','16000','-f','f32le','-'])
    x = np.frombuffer(raw,np.float32)
    win, hop = 1600,800
    db = np.array([10*math.log10(float(np.mean(x[k:k+win]**2))+1e-12) for k in range(0,max(1,len(x)-win+1),hop)])
    k = int(np.argmax(db)); at=k*.05
    threshold = min(-40,float(np.percentile(db,90))-15)
    silences = [(a*.05,(b-1)*.05+.1) for a,b in runs(db<threshold) if (b-a-1)*.05+.1>=.4-1e-8]
    def span(a,b):
        i,j = sample_indices(edges,[a,b])
        return event(edges,i,j,seconds=round(a,6),end_seconds=round(b,6))
    full = span(0,float(edges[-1]))
    return [dict(name='loudness',level='PASS' if abs(lufs+14)<=1 else 'WARN',message='Integrated loudness: target -14 LUFS +/-1',
                 events=[full],lufs=lufs if math.isfinite(lufs) else None),
            dict(name='true_peak',level='PASS' if tp<=-1 else 'FAIL',message='True peak ceiling -1 dBTP',
                 events=[full],dbtp=tp if math.isfinite(tp) else None),
            dict(name='loudest_100ms',level='PASS',message='Loudest 100 ms RMS window (50 ms hop)',events=[span(at,at+.1)],dbfs=float(db[k])),
            dict(name='silence',level='WARN' if silences else 'PASS',message='Silence >=0.4 s; inspect whether intended',
                 events=[span(a,b) for a,b in silences],threshold_dbfs=threshold)]


def sheet(st, edges, name, out):
    indices = st['targets'][name]
    cols = 1 if name=='phone_sheet' else (3 if name=='contact_sheet' else 2)
    height = next(iter(st['thumbs'].values())).height
    tile_h = height+28
    canvas = Image.new('RGB',(360*cols,math.ceil(len(indices)/cols)*tile_h),(24,28,36))
    draw = ImageDraw.Draw(canvas)
    for k,i in enumerate(indices):
        x,y = (k%cols)*360,(k//cols)*tile_h
        # Explicit checkerboard makes transparency visible in the review sheet.
        yy,xx = np.indices((height,360))
        gray = np.where((xx//12+yy//12)%2,96,144).astype(np.uint8)
        background = Image.fromarray(np.repeat(gray[:,:,None],3,axis=2)).convert('RGBA')
        background.alpha_composite(st['thumbs'][i])
        canvas.paste(background.convert('RGB'),(x,y+28))
        draw.text((x+8,y+7),f'f{i}  |  {edges[i]:.3f} s',fill='white')
    canvas.save(out/(name+'.jpg'),quality=90)
    return [event(edges,i) for i in indices]


def qa(path, out, fps=25, loop=False, holds=(), expected=(), timeline=None):
    started = time.perf_counter()
    path, out = Path(path),Path(out)
    if not math.isfinite(fps) or fps<=0:
        raise ValueError('--fps must be finite and positive')
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new or empty output directory')
    info = media_info(path,fps)
    durations = info['durations']
    if not durations or any(not math.isfinite(t) or t<=0 for t in durations):
        raise ValueError('Every decoded frame must have a positive duration')
    edges = np.concatenate(([0.0],np.cumsum(durations)))
    planned_holds, planned_cuts, joins = plan_settings(Path(timeline) if timeline else None)
    holds = list(holds)+planned_holds
    if any(not math.isfinite(a+b) or a<0 or b<=a for a,b in holds):
        raise ValueError('Holds require finite 0 <= START < END')
    expected = list(expected)+planned_cuts
    if any(not math.isfinite(t) or t<0 or t>=edges[-1] for t in expected):
        raise ValueError('Expected cuts must fall within the media duration')
    st = picture(path,info,edges)
    checks = analyse_picture(st,edges,loop or info['loop'],holds,expected,joins)
    checks += analyse_audio(path,info,edges)
    out.mkdir(parents=True,exist_ok=True)
    sheets = {name:sheet(st,edges,name,out) for name in st['targets']}
    report = dict(input=str(path),frames=len(durations),duration_seconds=float(edges[-1]),
                  frame_times_seconds=edges[:-1].tolist(),checks=checks,sheets=sheets,
                  limitations='Numeric screening is not proof of natural motion, correct semantics, good matting or audio/video sync. Review playback independently.',
                  elapsed_seconds=time.perf_counter()-started)
    report['level'] = 'FAIL' if any(c['level']=='FAIL' for c in checks) else ('WARN' if any(c['level']=='WARN' for c in checks) else 'PASS')
    (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    lines = [f'# Media QA: {report["level"]}', '', f'{path.name} | {len(durations)} frames | {edges[-1]:.3f} s', '', report['limitations'], '']
    for c in checks:
        lines += [f'## {c["level"]} — {c["name"]}', '', c['message']]
        for e in c['events']:
            label = f'f{e["frame"]} / {e["seconds"]:.3f} s'
            if 'end_seconds' in e:
                label += f' to f{e["end_frame"]} / {e["end_seconds"]:.3f} s (time end exclusive)'
            if 'to_frame' in e:
                label += f' -> f{e["to_frame"]}'
            lines += [f'- {label}' + (f': {e["kind"]}' if 'kind' in e else '')]
        metrics = {k:v for k,v in c.items() if k not in ('name','level','message','events')}
        if metrics:
            lines += ['', '```json',json.dumps(metrics,indent=2,ensure_ascii=False,allow_nan=False),'```']
        lines += ['']
    lines += [f'![{name}]({name}.jpg)' for name in sheets]
    lines += ['',f'Analysis and sheets: {report["elapsed_seconds"]:.3f} s.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--fps',type=float,default=25,help='PNG sequence rate; GIF/APNG use embedded delays')
    parser.add_argument('--loop',action='store_true',help='Check position and speed at wrap (also automatic for infinite GIF/APNG)')
    parser.add_argument('--holds',default='',help='Designed holds in seconds, e.g. 1.0-3.0,5.0-6.5')
    parser.add_argument('--expect-cuts',default='',help='Explicit hard-cut times in seconds, comma-separated')
    parser.add_argument('--timeline',type=Path,help='compose_timeline plan or emitted manifest; ordinary joins are not hard cuts')
    args = parser.parse_args(argv)
    try:
        holds = [tuple(map(float,item.split('-'))) for item in args.holds.split(',') if item]
        if any(len(h)!=2 for h in holds):
            raise ValueError('Use --holds START-END[,START-END]')
        report = qa(args.input,args.out,args.fps,args.loop,holds,
                    [float(v) for v in args.expect_cuts.split(',') if v],args.timeline)
    except (OSError,ValueError,RuntimeError,KeyError,IndexError,TypeError,ZeroDivisionError) as exc:
        print(f'qa_media: {exc}',file=sys.stderr)
        return 2
    print(f'{report["level"]}: {args.out / "report.md"} ({report["elapsed_seconds"]:.3f} s)')
    return int(report['level']=='FAIL')


if __name__=='__main__':
    raise SystemExit(main())
