#!/usr/bin/env python3
"""Pack uniform RGBA frames; optional experimental native game-engine adapters."""
import argparse
import json
import math
from pathlib import Path
from PIL import Image


def export(frames, manifest, out, max_size=2048, padding=2, divisor=1, pivot=None):
    files = sorted(Path(frames).glob('*.png'))
    data = json.loads(Path(manifest).read_text())
    durations = data['durations_ms']
    indices = data.get('source_indices', [None] * len(files))
    if len(indices) != len(files):
        raise ValueError('Frame count must match source_indices')
    if not files or len(files) != len(durations):
        raise ValueError('Frame count must match durations_ms')
    if any(not isinstance(t, (int, float)) or not math.isfinite(t) or t <= 0 for t in durations):
        raise ValueError('Durations must be finite and positive')
    if divisor < 1 or padding < 0 or max_size < 1:
        raise ValueError('Invalid dimensions')
    with Image.open(files[0]) as first:
        size = first.size
    if size[0] % divisor or size[1] % divisor:
        raise ValueError('Frame dimensions must divide evenly')
    w, h = size[0] // divisor, size[1] // divisor
    pivot = pivot or (w / 2, h)
    if len(pivot) != 2 or not all(math.isfinite(v) for v in pivot):
        raise ValueError('Pivot must contain two finite output-pixel coordinates')
    cw, ch = w + padding * 2, h + padding * 2
    cols, rows = max_size // cw, max_size // ch
    if not cols or not rows:
        raise ValueError('Frame plus padding exceeds page size')
    # Validate before creating a new output directory; never overwrite a delivery.
    for file in files:
        with Image.open(file) as im:
            if im.size != size:
                raise ValueError('All frames must use the same canvas')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'frames').mkdir()
    result = {'schema_version': 1, 'alpha': 'straight', 'filter': 'nearest recommended for pixel art',
              'frame_size': [w, h], 'source_frame_size': list(size), 'scale_divisor': divisor,
              'pivot': list(pivot), 'pivot_units': 'output pixels from top-left of untrimmed frame',
              'trimmed': False, 'padding': padding, 'extrusion': 0,
              'motion': 'visual displacement retained; no root-motion track',
              'duration_ms': sum(durations), 'pages': [], 'frames': [],
              'events': [], 'engine_validation': 'not performed'}
    capacity = cols * rows
    for begin in range(0, len(files), capacity):
        chunk = files[begin:begin + capacity]
        used_cols = min(cols, len(chunk))
        page = Image.new('RGBA', (used_cols * cw, math.ceil(len(chunk) / cols) * ch))
        page_name = f'sheet-{len(result["pages"]):03d}.png'
        for local, file in enumerate(chunk):
            index = begin + local
            with Image.open(file) as im:
                frame = im.convert('RGBA').resize((w, h), Image.Resampling.NEAREST)
            x, y = local % cols * cw + padding, local // cols * ch + padding
            page.paste(frame, (x, y))  # no alpha mask: preserve RGBA exactly
            name = f'frames/{index:05d}.png'
            frame.save(out / name)
            result['frames'].append({'index': index, 'file': name, 'page': page_name,
                                     'rect': [x, y, w, h], 'duration_ms': durations[index],
                                     'source_index': indices[index]})
        page.save(out / page_name)
        result['pages'].append({'file': page_name, 'size': list(page.size)})
    # Decode every page crop and verify fractional alpha and RGB, not just packing bounds.
    for item in result['frames']:
        x, y, fw, fh = item['rect']
        with Image.open(out / item['page']) as sheet, Image.open(out / item['file']) as frame:
            if sheet.crop((x, y, x + fw, y + fh)).tobytes() != frame.tobytes():
                raise RuntimeError('Decoded sprite crop mismatch')
    result['qc'] = {'decoded_frame_crops': len(files), 'rgba_mismatches': 0}
    (out / 'sprites.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('frames', type=Path)
    ap.add_argument('--manifest', type=Path)
    ap.add_argument('--anim-manifest',nargs='+',type=Path)
    ap.add_argument('--engine',help='godot4,unity,phaser-hash,phaser-array,pixi,aseprite')
    ap.add_argument('--extrude',type=int,default=1)
    ap.add_argument('--pixel',action='store_true')
    ap.add_argument('--experimental',action='store_true')
    ap.add_argument('--allow-qa-fail',action='store_true',help='Explicit preview export; failed QA is retained.')
    ap.add_argument('--beat-sync',type=Path,help='Experimental Suno analysis/local beat map; audio-clock schedules.')
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--max-size', type=int, default=2048)
    ap.add_argument('--padding', type=int, default=2)
    ap.add_argument('--scale-divisor', type=int, default=1)
    ap.add_argument('--pivot', type=float, nargs=2, metavar=('X', 'Y'))
    a = ap.parse_args()
    if a.engine:
        from image_common import ImageError
        try:
            if not a.experimental:raise ImageError('E_EXPERIMENTAL','Engine exports require --experimental.')
            from game_engines import export_engines
            manifests=a.anim_manifest or sorted(a.frames.glob('*/anim.json'))
            syncs={}
            if a.beat_sync:
                from audio_beat_sync import schedule,retime_manifest,verify_motion,export_clock
                from image_common import read,write,ROOT
                import tempfile,shutil
                # Stage beside scratch, preserving each source frame and its hashes.
                stage=Path(tempfile.mkdtemp(prefix='beat-sync-',dir=ROOT/'.scratch'))
                try:
                    staged=[]
                    for source in manifests:
                        original=read(source);sync=schedule(original,read(a.beat_sync));syncs[original['state']]=sync
                        adjusted=retime_manifest(original,sync)
                        frames=[Image.open(source.parent/f['file']).convert('RGBA') for f in adjusted['frames']]
                        adjusted['qa']=verify_motion(adjusted,frames);sync['motion_qa']=adjusted['qa']
                        if adjusted['qa']['status']!='PASS' and not a.allow_qa_fail:
                            raise ImageError('E_QA_FAIL','Retimed motion is not certified',qa=adjusted['qa'])
                        dest=stage/original['state'];shutil.copytree(source.parent,dest);write(dest/'anim.json',adjusted);staged.append(dest/'anim.json')
                    r=export_engines(staged,a.out,a.engine.split(','),a.max_size,a.padding,a.extrude,a.pixel,a.allow_qa_fail)
                    write(a.out/'beat-sync.json',dict(states=syncs,runtime_av_sync='untested'))
                    export_clock(a.out/'audio_clock.gd')
                finally:shutil.rmtree(stage)
            else:
                r=export_engines(manifests,a.out,a.engine.split(','),a.max_size,a.padding,a.extrude,a.pixel,a.allow_qa_fail)
            print(json.dumps(dict(ok=True,result=r)));return
        except (ImageError,ValueError,OSError,KeyError) as exc:
            print(json.dumps(dict(ok=False,error=exc.error if isinstance(exc,ImageError) else dict(code='E_EXPORT',message=str(exc)))))
            raise SystemExit(2)
    if not a.manifest:ap.error('--manifest is required for generic export')
    r = export(a.frames, a.manifest, a.out, a.max_size, a.padding, a.scale_divisor, a.pivot)
    print(json.dumps({'frames': len(r['frames']), 'pages': len(r['pages']), 'qc': r['qc']}))


if __name__ == '__main__':
    main()
