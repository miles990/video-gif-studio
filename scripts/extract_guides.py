#!/usr/bin/env python3
"""Measure stylized-redraw guides (masks, contours, shared palette labels) from an accepted RGBA motion plate.

Optional reviewed effect masks assign pixels to a separate effect layer; this is not unmixing of composited pixels.
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

VERSION = 1


def _palette(samples, k, iterations=20):
    # Deterministic k-means: luminance-quantile init, no random restarts.
    samples = samples.astype(np.float32)
    order = np.argsort(samples @ np.float32([.299, .587, .114]), kind='stable')
    centers = samples[order[((np.arange(k)+.5)*len(order)/k).astype(int)]].copy()
    for _ in range(iterations):
        labels = np.argmin(((samples[:, None]-centers[None])**2).sum(2), 1)
        for i in range(k):
            if (labels == i).any():
                centers[i] = samples[labels == i].mean(0)
    centers = np.rint(centers)
    return centers[np.argsort(centers @ np.float32([.299, .587, .114]), kind='stable')]


def _label(rgb, mask, centers):
    labels = np.full(mask.shape, 255, np.uint8)
    px = rgb[mask].astype(np.float32)
    if len(px):
        labels[mask] = np.argmin(((px[:, None]-centers[None])**2).sum(2), 1)
    return labels


def _rings(mask, epsilon):
    contours, hierarchy = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    rings = []
    for contour, h in zip(contours, hierarchy[0] if hierarchy is not None else []):
        points = cv2.approxPolyDP(contour, epsilon, True)[:, 0] if epsilon > 0 else contour[:, 0]
        if len(points) >= 3:
            rings.append({'points': points.tolist(), 'hole': bool(h[3] >= 0)})
    return rings


def _shared_palette(plate, masks, k, max_samples, empty):
    # One palette per layer for the whole plate so region colors cannot flicker between frames.
    px = np.concatenate([a[..., :3][m] for a, m in zip(plate, masks)])
    if not len(px):
        raise ValueError(empty)
    return _palette(px[::max(1, -(-len(px)//max_samples))], min(k, len(px)))


def _effect_masks(directory, count, shape, fg):
    if directory is None:
        return None
    files = sorted(Path(directory).glob('*.png'), key=natural)
    if len(files) != count:
        raise ValueError('Effect masks must match plate frames')
    masks = []
    for file, f in zip(files, fg):
        with Image.open(file) as im:
            m = np.array(im.convert('L')) > 0
        if m.shape != shape:
            raise ValueError('Effect mask changed dimensions')
        masks.append(m & f)
    return masks


def _layer(plate, masks, centers, stage, prefix, epsilon):
    (stage/prefix/'masks').mkdir(parents=True)
    (stage/prefix/'labels').mkdir()
    records, previous = [], None
    for i, (a, mask) in enumerate(zip(plate, masks)):
        name = f'{i:05d}.png'
        Image.fromarray(mask.astype(np.uint8)*255).save(stage/prefix/'masks'/name)
        Image.fromarray(_label(a[..., :3], mask, centers)).save(stage/prefix/'labels'/name)
        ys, xs = np.nonzero(mask)
        iou = None
        if previous is not None:
            union = (mask | previous).sum()
            iou = round(float((mask & previous).sum()/union), 4) if union else 1.0
        records.append({'mask': f'{prefix}masks/{name}', 'labels': f'{prefix}labels/{name}', 'area': int(mask.sum()),
                        'bbox': [int(xs.min()), int(ys.min()), int(xs.max()-xs.min()+1), int(ys.max()-ys.min()+1)] if len(xs) else None,
                        'iou_prev': iou, 'rings': _rings(mask, epsilon)})
        previous = mask
    return records


def extract(frames, manifest, out, colors=4, alpha_threshold=128, epsilon=1.0, max_samples=200000,
            effect_masks=None, effect_colors=3):
    frames, manifest, out = Path(frames), Path(manifest), Path(out)
    if out.exists():
        raise FileExistsError('Use a new output directory')
    if not (1 <= colors <= 254 and 1 <= effect_colors <= 254):
        raise ValueError('colors must be 1-254')
    files = sorted(frames.glob('*.png'), key=natural)
    source = json.loads(manifest.read_text())
    if not files or len(files) != len(source['durations_ms']):
        raise ValueError('Frames must match timing manifest')
    plate = []
    for file in files:
        with Image.open(file) as im:
            plate.append(np.array(im.convert('RGBA')))
    if len({a.shape for a in plate}) != 1:
        raise ValueError('Shared frame canvas required')
    if all((a[..., 3] == 255).all() for a in plate):
        raise ValueError('Plate has no alpha; key it or run background_remove.py first')
    fg = [a[..., 3] >= alpha_threshold for a in plate]
    fx = _effect_masks(effect_masks, len(files), plate[0].shape[:2], fg)
    masks = [f & ~e for f, e in zip(fg, fx)] if fx else fg
    centers = _shared_palette(plate, masks, colors, max_samples, 'Plate has no foreground above alpha threshold')
    fx_centers = _shared_palette(plate, fx, effect_colors, max_samples, 'Effect masks select no foreground pixels') if fx else None
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        stage = Path(tmp)/'guides'
        records = _layer(plate, masks, centers, stage, '', epsilon)
        effects = None
        if fx:
            effects = {'palette': fx_centers.astype(int).tolist(), 'frames': _layer(plate, fx, fx_centers, stage, 'effects/', epsilon),
                       'mask_sha256': [hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(Path(effect_masks).glob('*.png'), key=natural)],
                       'mask_review': 'supplied by caller; not verified by the extractor',
                       'limits': 'each pixel is assigned to one layer by the mask; mixed character/effect pixels are not unmixed '
                                 'and character regions hidden under effects are not recovered'}
        h, w = plate[0].shape[:2]
        record = {'kind': 'stylized-redraw-guides', 'version': VERSION, 'canvas': [w, h],
                  'durations_ms': source['durations_ms'], 'alpha_threshold': alpha_threshold, 'epsilon': epsilon,
                  'palette': centers.astype(int).tolist(), 'frames': records, 'effects': effects,
                  'source': {'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
                             'frame_sha256': [hashlib.sha256(f.read_bytes()).hexdigest() for f in files]},
                  'extractor': {'name': 'extract_guides.py', 'version': VERSION, 'opencv': cv2.__version__,
                                'palette': 'deterministic k-means per layer, shared across frames, sorted by luminance'},
                  'visual_review': 'required; framewise masks can flicker, check iou_prev drops against real motion'}
        (stage/'manifest.json').write_text(json.dumps(record)+'\n')
        stage.rename(out)
    low = [i for i, r in enumerate(records) if r['iou_prev'] is not None and r['iou_prev'] < .8]
    return {'frames': len(files), 'out': str(out), 'palette': record['palette'], 'low_iou_frames': low}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('frames', type=Path, help='Numbered RGBA PNG plate frames with real alpha')
    parser.add_argument('--manifest', type=Path, required=True, help='Timing manifest with durations_ms')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--colors', type=int, default=4)
    parser.add_argument('--alpha-threshold', type=int, default=128)
    parser.add_argument('--epsilon', type=float, default=1.0, help='Contour simplification in pixels; 0 keeps every boundary pixel')
    parser.add_argument('--effect-masks', type=Path, help='Reviewed numbered effect masks (nonzero = effect layer), one per plate frame')
    parser.add_argument('--effect-colors', type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(extract(args.frames, args.manifest, args.out, args.colors, args.alpha_threshold, args.epsilon,
                             effect_masks=args.effect_masks, effect_colors=args.effect_colors)))
