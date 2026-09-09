#!/usr/bin/env python3
"""Compose prepared animations and timed stills, then export selected formats."""
import argparse
import json
import math
import tempfile
from pathlib import Path
from PIL import Image
from gif_pipeline import encode, verify, natural, sha
from sprite_export import export as sprites
from video_export import export as video
from music_sync import mux_music

FORMATS = {'gif', 'apng', 'png', 'sprite', 'mov', 'webm', 'mp4'}


def duration(value):
    if not isinstance(value, (float,int)) or not math.isfinite(value) or value < 20 or value > 655350 or value % 10:
        raise ValueError('Each duration_ms must be 20..655350 in multiples of 10')
    return int(value)


def compose(plan_path, out, formats=('gif',), background='000000'):
    plan_path = Path(plan_path).resolve(); out = Path(out)
    if out.exists(): raise FileExistsError('Use a new output directory')
    if not formats or not set(formats) <= FORMATS: raise ValueError('Unknown output format')
    plan = json.loads(plan_path.read_text())
    music = plan.get('music')
    if music and not set(formats) & {'mov','webm','mp4'}:
        raise ValueError('Music requires MOV, WebM or MP4; GIF/APNG/sprites are silent')
    beatmap = None
    if 'beatmap' in plan:
        beatmap = json.loads((plan_path.parent/plan['beatmap']).read_text())['beats_ms']
        if not beatmap or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in beatmap) or any(b<=a for a,b in zip(beatmap,beatmap[1:])):
            raise ValueError('beats_ms must be finite, nonnegative and strictly increasing')
    items = []; segments = []
    def resolve(name): return (plan_path.parent / name).resolve()
    def load_animation(name):
        manifest = resolve(name); data = json.loads(manifest.read_text())
        files = sorted((manifest.parent/'frames').glob('*.png'), key=natural)
        times = data['durations_ms']
        if not files or len(files) != len(times): raise ValueError('Animation frames/timing mismatch')
        return files, [duration(v) for v in times]
    def edit_animation(segment):
        files,times=load_animation(segment['manifest'])
        begin=segment.get('in_ms',0);end=segment.get('out_ms',sum(times))
        if not isinstance(begin,(int,float)) or not isinstance(end,(int,float)) or not math.isfinite(begin+end) or begin<0 or end<=begin or end>sum(times) or begin%10 or end%10:
            raise ValueError('Invalid animation in_ms/out_ms')
        selected=[];clipped=[];cursor=0
        for file,t in zip(files,times):
            amount=min(cursor+t,end)-max(cursor,begin)
            if amount>0:selected.append(file);clipped.append(duration(amount))
            cursor+=t
        speed=segment.get('speed',1)
        if not isinstance(speed,(int,float)) or not math.isfinite(speed) or speed<=0:raise ValueError('Speed must be positive')
        target=segment.get('duration_ms') if segment['type']=='animation' else None
        if target is not None and 'speed' in segment:raise ValueError('Choose duration fitting or speed, not both')
        target=duration(target) if target is not None else round(sum(clipped)/speed/10)*10
        if target!=sum(clipped):
            edges=[0];acc=0
            for t in clipped:
                acc+=t;edges.append(round(acc/sum(clipped)*target/10)*10)
            clipped=[duration(b-a) for a,b in zip(edges,edges[1:])]
        return selected,clipped
    for original in plan['segments']:
        segment=dict(original)
        if 'end_beat' in segment:
            index=segment['end_beat']
            if beatmap is None or type(index) is not int or not 0<=index<len(beatmap):raise ValueError('Invalid zero-based end_beat')
            if 'duration_ms' in segment:raise ValueError('Choose end_beat or duration_ms')
            if segment.get('ending')=='complete_cycle':raise ValueError('Complete-cycle ending cannot guarantee a beat cut')
            offset=music.get('in_ms',0) if music else 0
            segment['duration_ms']=round((beatmap[index]-offset)/10)*10-sum(t for _,t in items)
        start = len(items)
        if segment['type'] == 'animation':
            files, times = edit_animation(segment)
            items.extend(zip(files, times))
        elif segment['type'] == 'loop':
            files, times = edit_animation(segment)
            requested = duration(segment['duration_ms'])
            ending = segment.get('ending', 'exact')
            if ending not in ('exact','complete_cycle'):
                raise ValueError('Loop ending must be exact or complete_cycle')
            cycle = sum(times)
            if ending == 'complete_cycle':
                items.extend(list(zip(files,times)) * math.ceil(requested/cycle))
            else:
                full, remaining = divmod(requested,cycle)
                items.extend(list(zip(files,times)) * full)
                for file,t in zip(files,times):
                    if not remaining: break
                    used = min(t,remaining)
                    if used < 20:
                        raise ValueError('Exact loop leaves a sub-20ms frame; adjust duration or use complete_cycle')
                    items.append((file,used));remaining -= used
        elif segment['type'] == 'still':
            selectors = [key for key in ('image','manifest','previous') if key in segment]
            if len(selectors) != 1: raise ValueError('Still requires exactly one image, manifest or previous selector')
            if 'image' in segment: file = resolve(segment['image'])
            elif 'manifest' in segment:
                files, _ = load_animation(segment['manifest'])
                which = segment.get('frame','last')
                if which not in ('first','last'): raise ValueError('frame must be first or last')
                file = files[0 if which == 'first' else -1]
            else:
                if segment['previous'] != 'last' or not items: raise ValueError('previous:last needs a preceding segment')
                file = items[-1][0]
            items.append((file, duration(segment['duration_ms'])))
        else: raise ValueError('Supported segment types: animation, still, loop')
        segments.append({'edit':original, 'start_ms':sum(t for _,t in items[:start]),
                         'requested_duration_ms':segment.get('duration_ms'),
                         'ending':segment.get('ending','exact') if segment['type']=='loop' else None,
                         'type':segment['type'], 'start_frame':start, 'end_frame_exclusive':len(items),
                         'duration_ms':sum(t for _,t in items[start:])})
    if not items: raise ValueError('Timeline must contain at least one frame')
    # Preserve original alpha/canvas; mismatched inputs require deliberate preparation.
    images = []
    for file,_ in items:
        with Image.open(file) as im: images.append(im.convert('RGBA'))
    if any(im.size != images[0].size for im in images):
        raise ValueError('All images must share one canvas; prepare sizing explicitly')
    times = [t for _,t in items]
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        root = Path(tmp)/'delivery';root.mkdir();(root/'frames').mkdir()
        for i,im in enumerate(images): im.save(root/'frames'/f'{i:05d}.png')
        manifest = {'durations_ms':times,'source_indices':list(range(len(items))), 'size':list(images[0].size),
                    'segments':segments, 'source_frames':[{'file':str(f),'sha256':sha(f)} for f,_ in items],
                    'timeline_sha256':sha(plan_path), 'duration_ms':sum(times),
                    'semantics':'Stills add time; all pixels including VFX freeze. No invented idle motion or blend.',
                    'visual_join_review':'not assessed by script'}
        (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        qc = {}
        if 'gif' in formats:
            encode(images,times,root/'animation.gif');qc['gif']=verify(root/'animation.gif',images,times)
        if 'apng' in formats:
            # Include a default poster so even a single held image is a timed APNG.
            images[0].save(root/'animation.png',save_all=True,default_image=True,append_images=images,duration=times,loop=0,disposal=0,blend=0)
            with Image.open(root/'animation.png') as decoded:
                actual = sum((decoded.seek(i) or decoded.info.get('duration',0)) for i in range(1 if decoded.info.get('default_image') else 0,decoded.n_frames))
                if abs(actual-sum(times)) > 0.1: raise RuntimeError('APNG duration mismatch')
            qc['apng_duration_ms']=actual
        if 'sprite' in formats: qc['sprite']=sprites(root/'frames',root/'manifest.json',root/'sprites')['qc']
        for fmt in ('mov','webm','mp4'):
            if fmt in formats:
                qc[fmt]=video(root/'frames',root/'manifest.json',root/('animation.'+fmt),background)
                if music:
                    qc[fmt]['audio']=mux_music(root/('animation.'+fmt),resolve(music['file']),sum(times),
                                              music.get('in_ms',0),music.get('gain_db',0),
                                              music.get('fade_in_ms',30),music.get('fade_out_ms',30))
        (root/'qc.json').write_text(json.dumps(qc,indent=2)+'\n')
        root.rename(out)
    return {'frames':len(items),'duration_ms':sum(times),'formats':list(formats),'out':str(out)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('timeline',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--formats',nargs='+',choices=sorted(FORMATS),default=['gif'])
    ap.add_argument('--background',default='000000',help='MP4 matte RGB hex')
    a=ap.parse_args();print(json.dumps(compose(a.timeline,a.out,a.formats,a.background)))


if __name__=='__main__': main()
