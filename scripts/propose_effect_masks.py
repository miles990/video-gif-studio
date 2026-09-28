#!/usr/bin/env python3
"""Propose candidate effect masks: foreground colors absent from effect-free reference frames. Output is pending review.

This is a color heuristic, not character/effect separation. Effects that share character colors are missed, and
character details absent from the reference frames are falsely included. Review and edit every mask before passing
it to extract_guides.py --effect-masks.
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

STEP = 4  # color bin size; 64 bins per channel


def _known_colors(ref, tolerance):
    # Every color seen in the reference frames, grown by the tolerance per channel (Chebyshev distance).
    known = np.zeros((256//STEP,)*3, bool)
    b = ref//STEP
    known[b[:, 0], b[:, 1], b[:, 2]] = True
    for axis in range(3):
        for _ in range(int(np.ceil(tolerance/STEP))):
            grown = known.copy()
            grown[tuple(slice(1, None) if a == axis else slice(None) for a in range(3))] |= known[tuple(slice(None, -1) if a == axis else slice(None) for a in range(3))]
            grown[tuple(slice(None, -1) if a == axis else slice(None) for a in range(3))] |= known[tuple(slice(1, None) if a == axis else slice(None) for a in range(3))]
            known = grown
    return known


def propose(frames, manifest, out, reference_frames, threshold=32.0, min_area=16, alpha_threshold=128):
    frames, manifest, out = Path(frames), Path(manifest), Path(out)
    if out.exists():
        raise FileExistsError('Use a new output directory')
    files = sorted(frames.glob('*.png'), key=natural)
    if not files or len(files) != len(json.loads(manifest.read_text())['durations_ms']):
        raise ValueError('Frames must match timing manifest')
    if not reference_frames or any(not 0 <= i < len(files) for i in reference_frames):
        raise ValueError('Reference frames must be effect-free plate frame indices')
    plate = []
    for file in files:
        with Image.open(file) as im:
            plate.append(np.array(im.convert('RGBA')))
    if len({a.shape for a in plate}) != 1:
        raise ValueError('Shared frame canvas required')
    ref = np.concatenate([plate[i][..., :3][plate[i][..., 3] >= alpha_threshold] for i in reference_frames])
    if not len(ref):
        raise ValueError('Reference frames have no foreground')
    known = _known_colors(ref, threshold)
    out.parent.mkdir(parents=True, exist_ok=True)
    areas = []
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        stage = Path(tmp)/'proposal'
        (stage/'masks').mkdir(parents=True)
        for i, a in enumerate(plate):
            fg = a[..., 3] >= alpha_threshold
            b = a[..., :3]//STEP
            far = fg & ~known[b[..., 0], b[..., 1], b[..., 2]]
            count, labels, stats, _ = cv2.connectedComponentsWithStats(far.astype(np.uint8), connectivity=8)
            keep = np.zeros(count, bool)
            keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_area
            mask = keep[labels]
            areas.append(int(mask.sum()))
            Image.fromarray(mask.astype(np.uint8)*255).save(stage/'masks'/f'{i:05d}.png')
        record = {'kind': 'effect-mask-proposal', 'review': 'pending',
                  'method': f'foreground colors not within threshold (per channel, {STEP}-level bins) of any color in the '
                            'effect-free reference frames; components below min_area dropped',
                  'reference_frames': list(reference_frames), 'threshold': threshold, 'min_area': min_area,
                  'areas': areas,
                  'source_frame_sha256': [hashlib.sha256(f.read_bytes()).hexdigest() for f in files],
                  'known_misses': 'effects sharing character colors; character details absent from reference frames are included'}
        (stage/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
        stage.rename(out)
    return {'frames': len(files), 'out': str(out), 'review': 'pending', 'frames_with_candidates': sum(a > 0 for a in areas)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('frames', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reference-frames', type=int, nargs='+', required=True, help='Effect-free frame indices')
    parser.add_argument('--threshold', type=float, default=32.0, help='Per-channel distance from any reference color')
    parser.add_argument('--min-area', type=int, default=16)
    parser.add_argument('--alpha-threshold', type=int, default=128, help='Lower it to propose faint glow/trail pixels')
    args = parser.parse_args()
    print(json.dumps(propose(args.frames, args.manifest, args.out, args.reference_frames, args.threshold, args.min_area, args.alpha_threshold)))
