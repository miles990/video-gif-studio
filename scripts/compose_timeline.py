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
    items = []; segments = []
    def resolve(name): return (plan_path.parent / name).resolve()
    def load_animation(name):
        manifest = resolve(name); data = json.loads(manifest.read_text())
        files = sorted((manifest.parent/'frames').glob('*.png'), key=natural)
        times = data['durations_ms']
        if not files or len(files) != len(times): raise ValueError('Animation frames/timing mismatch')
        return files, [duration(v) for v in times]
    for segment in plan['segments']:
        start = len(items)
        if segment['type'] == 'animation':
            files, times = load_animation(segment['manifest'])
            items.extend(zip(files, times))
        elif segment['type'] == 'loop':
            files, times = load_animation(segment['manifest'])
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
        segments.append({'requested_duration_ms':segment.get('duration_ms'),
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
            if fmt in formats: qc[fmt]=video(root/'frames',root/'manifest.json',root/('animation.'+fmt),background)
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
