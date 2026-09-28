#!/usr/bin/env python3
"""Apply an ordered JSON edit list to effect masks and record who, if anyone, reviewed the result.

Ops: {"op": "add"|"remove"|"clear", "frames": "all"|[start, end], "rect": [x, y, w, h] | "polygon": [[x, y], ...],
      "color": "#RRGGBB", "tolerance": 16}. "add" never leaves plate foreground. The tool records --reviewed-by;
it does not decide that a mask is correct.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import cv2
import numpy as np
from PIL import Image
from gif_pipeline import natural

OPS = ('add', 'remove', 'clear')


def _check(ops, count):
    for op in ops:
        if op.get('op') not in OPS:
            raise ValueError(f"Unknown op {op.get('op')!r}; expected one of {OPS}")
        span = op.get('frames')
        if span != 'all' and not (isinstance(span, list) and len(span) == 2 and 0 <= span[0] <= span[1] < count):
            raise ValueError(f'frames must be "all" or [start, end] within 0-{count-1}: {span!r}')
        if op['op'] != 'clear' and ('rect' in op) == ('polygon' in op):
            raise ValueError(f"{op['op']} needs exactly one of rect or polygon")


def _region(op, plate):
    h, w = plate.shape[:2]
    region = np.zeros((h, w), np.uint8)
    if 'rect' in op:
        x, y, rw, rh = op['rect']
        region[max(0, y):max(0, y+rh), max(0, x):max(0, x+rw)] = 1
    else:
        cv2.fillPoly(region, [np.asarray(op['polygon'], np.int32)], 1)
    region = region.astype(bool)
    if 'color' in op:
        c = np.array([int(op['color'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)])
        region &= (np.abs(plate[..., :3].astype(int) - c).max(2) <= op.get('tolerance', 16))
    return region


def apply_edits(frames, manifest, masks, ops, out, reviewed_by=None, alpha_threshold=128):
    out, masks = Path(out), Path(masks)
    if out.exists():
        raise FileExistsError('Use a new output directory')
    files = sorted(Path(frames).glob('*.png'), key=natural)
    mask_files = sorted(masks.glob('*.png'), key=natural)
    if not files or len(files) != len(json.loads(Path(manifest).read_text())['durations_ms']) or len(mask_files) != len(files):
        raise ValueError('Plate frames, timing manifest and masks must have matching counts')
    _check(ops, len(files))
    out.parent.mkdir(parents=True, exist_ok=True)
    areas = []
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        stage = Path(tmp)/'edit'
        (stage/'masks').mkdir(parents=True)
        for i, (f, mf) in enumerate(zip(files, mask_files)):
            with Image.open(f) as im, Image.open(mf) as mk:
                plate = np.array(im.convert('RGBA'))
                mask = np.array(mk.convert('L')) > 0
            if mask.shape != plate.shape[:2]:
                raise ValueError('Mask changed dimensions')
            fg = plate[..., 3] >= alpha_threshold
            for op in ops:
                if op['frames'] != 'all' and not op['frames'][0] <= i <= op['frames'][1]:
                    continue
                if op['op'] == 'clear':
                    mask[:] = False
                elif op['op'] == 'add':
                    mask |= _region(op, plate) & fg
                else:
                    mask &= ~_region(op, plate)
            areas.append(int(mask.sum()))
            Image.fromarray(mask.astype(np.uint8)*255).save(stage/'masks'/f'{i:05d}.png')
        source = masks.parent/'manifest.json'
        source = json.loads(source.read_text()) if source.exists() else {}
        record = {'kind': 'effect-mask-edit', 'review': 'reviewed' if reviewed_by else 'pending', 'reviewed_by': reviewed_by,
                  'ops': ops, 'ops_sha256': hashlib.sha256(json.dumps(ops, sort_keys=True).encode()).hexdigest(),
                  'source_masks': str(masks), 'source_kind': source.get('kind'), 'source_review': source.get('review'),
                  'source_mask_sha256': [hashlib.sha256(m.read_bytes()).hexdigest() for m in mask_files], 'areas': areas}
        (stage/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
        stage.rename(out)
    return {'frames': len(files), 'out': str(out), 'review': record['review'], 'frames_with_mask': sum(a > 0 for a in areas)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('frames', type=Path, help='Plate RGBA frames')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--masks', type=Path, required=True)
    parser.add_argument('--ops', type=Path, required=True, help='JSON list of edit ops')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--alpha-threshold', type=int, default=128, help='Lowest plate alpha an add op may take')
    parser.add_argument('--reviewed-by', help='Name of the person who reviewed the resulting masks over playback')
    args = parser.parse_args()
    print(json.dumps(apply_edits(args.frames, args.manifest, args.masks, json.loads(args.ops.read_text()), args.out, args.reviewed_by, args.alpha_threshold)))
