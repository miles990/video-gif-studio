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


def _mask_manifest(directory):
    # Carry the proposal/edit record beside the masks, if any; the extractor does not upgrade its review status.
    path = directory.parent/'manifest.json'
    if not path.exists():
        return None
    record = json.loads(path.read_text())
    if record.get('kind') not in ('effect-mask-proposal', 'effect-mask-edit'):
        return None
    return {'kind': record['kind'], 'review': record.get('review'), 'reviewed_by': record.get('reviewed_by'),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def _layer(plate, masks, centers, stage, prefix, epsilon, keep_alpha=False):
    (stage/prefix/'masks').mkdir(parents=True)
    (stage/prefix/'labels').mkdir()
    if keep_alpha:
        (stage/prefix/'alpha').mkdir()
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
        if keep_alpha:
            # Measured plate alpha inside the layer; not unmixed from anything beneath it.
            Image.fromarray(np.where(mask, a[..., 3], 0).astype(np.uint8)).save(stage/prefix/'alpha'/name)
            records[-1]['alpha'] = f'{prefix}alpha/{name}'
        previous = mask
    return records


UV_SCALE, UV_OFFSET = 8, 32768  # stored texture coordinates: 1/8 px over [-4096, 4096)
FLOW_DEADZONE = 0.5  # px; generated video jitters ~0.1-0.5 px where nothing moves, which would make still texture drift
FLOW_SMOOTH = 4.0    # px; Gaussian over foreground flow before advection
REANCHOR_LOW, REANCHOR_HIGH = 0.05, 0.15  # local deformation below which a reset copies the other layer
UV_CLOCK = 0.9       # phase advances by (texture deformation - UV_SLACK)/UV_CLOCK per frame; 0 keeps one layer
UV_SLACK = 0.03      # deformation treated as rigid; below it a point's layer weights never change


def _gray(a):
    # Composite over mid-gray so flow sees the subject against a neutral, static backdrop.
    alpha = a[..., 3:].astype(np.float32)/255
    rgb = a[..., :3].astype(np.float32)*alpha + 128*(1-alpha)
    return cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY)


def _nearest_extend(uv, known, region):
    # Continue texture coordinates linearly from the nearest trusted pixel into newly revealed surface.
    if not known.any():
        return uv
    _, labels = cv2.distanceTransformWithLabels((~known).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    coords = np.argwhere(known)  # row-major, matching DIST_LABEL_PIXEL scan order
    ys, xs = np.nonzero(region & ~known)
    ny, nx = coords[labels[ys, xs] - 1].T
    uv[ys, xs] = uv[ny, nx] + np.stack([xs - nx, ys - ny], 1)
    return uv


def distortion_map(uv, region=None):
    """Per-pixel deformation of texture coordinates: sum of |log singular values| of the uv Jacobian (0 = rigid)."""
    ux, uy = np.gradient(uv[..., 0], axis=1), np.gradient(uv[..., 0], axis=0)
    vx, vy = np.gradient(uv[..., 1], axis=1), np.gradient(uv[..., 1], axis=0)
    if region is not None:
        ux, uy, vx, vy = ux[region], uy[region], vx[region], vy[region]
    # Closed-form singular values of [[ux, uy], [vx, vy]]: s1^2 + s2^2 = |J|_F^2 and s1*s2 = |det J|.
    frob = ux*ux + uy*uy + vx*vx + vy*vy
    det = np.abs(ux*vy - uy*vx)
    root = np.sqrt(np.maximum(frob*frob - 4*det*det, 0))
    s1 = np.sqrt(np.maximum((frob + root)/2, 1e-6))
    s2 = np.clip(det/np.maximum(s1, 1e-3), 1e-3, None)
    return np.abs(np.log(s1)) + np.abs(np.log(s2))


def uv_distortion(uv, region):
    """Median local deformation of texture coordinates over a region (0 = rigid)."""
    return float(np.median(distortion_map(uv, region))) if region.any() else 0.0


def _reanchor(other, grid, fg, low=REANCHOR_LOW, high=REANCHOR_HIGH, feather=6.0):
    # Copy the other layer where it is still nearly rigid, so both layers agree there and never cross-fade;
    # fall back to fresh coordinates only where texture has actually deformed, feathered to avoid seams.
    keep = np.clip((high - distortion_map(other))/(high - low), 0, 1).astype(np.float32)
    # Judge deformation only from interior gradients: at the silhouette, uv meets the background's fresh grid and
    # looks torn. Normalized convolution then carries interior values to the edge and feathers deformed regions.
    interior = cv2.erode(fg.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
    if not interior.any():
        return grid.copy()
    weight = cv2.GaussianBlur(interior, (0, 0), feather)
    keep = cv2.GaussianBlur(keep*interior, (0, 0), feather)/np.maximum(weight, 1e-6)
    keep = np.where(fg & (weight > 1e-4), np.clip(keep, 0, 1), 0)[..., None]
    return keep*other + (1 - keep)*grid


def layer_weights(phase):
    """Per-pixel weights of the two texture layers from the surface phase; each is 0 where its layer re-anchors."""
    tri = lambda f: 1 - np.abs(2*f - 1)
    return [tri(np.mod(phase, 1)), tri(np.mod(phase + .5, 1))]


def _pack(uv):
    return np.clip(np.rint(uv*UV_SCALE) + UV_OFFSET, 0, 65535).astype(np.uint16)


def _flow_guides(plate, fg, stage, cycle=UV_CLOCK, smooth=FLOW_SMOOTH):
    h, w = fg[0].shape
    gy, gx = np.mgrid[:h, :w].astype(np.float32)
    grid = np.dstack([gx, gy])
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    gray = [_gray(a) for a in plate]
    layers = [grid.copy() for _ in range(2 if cycle else 1)]
    # Surface phase: a clock carried by each surface point that advances with how deformed its texture currently is,
    # not with time or distance. Rigid and undeformed points never advance, so they never cross-fade; deformed
    # texture (real strain, flow noise, revealed-surface seams) cycles until both layers are clean again, then stops.
    phase = np.full((h, w), .25, np.float32)
    (stage/'flow').mkdir()
    records, valid_fraction, distortion = [], [], []
    for i in range(len(plate)):
        record = {}
        if i:
            bw = dis.calc(gray[i], gray[i-1], None)   # pixel x at t came from x + bw at t-1
            fw = dis.calc(gray[i-1], gray[i], None)
            mx, my = gx + bw[..., 0], gy + bw[..., 1]
            back = cv2.remap(fw, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            err = np.linalg.norm(bw + back, axis=2)
            inside = (mx >= 0) & (mx <= w-1) & (my >= 0) & (my <= h-1)
            prev_fg = cv2.remap(fg[i-1].astype(np.uint8), mx, my, cv2.INTER_NEAREST, borderValue=0).astype(bool)
            valid = inside & prev_fg & fg[i] & (err < .5 + .05*np.linalg.norm(bw, axis=2))
            # Advect with spatially smoothed flow: generated video adds per-pixel flow noise that would marble the texture.
            move = bw
            if smooth:
                weight = cv2.GaussianBlur(fg[i].astype(np.float32), (0, 0), smooth)
                move = np.dstack([cv2.GaussianBlur(bw[..., k]*fg[i], (0, 0), smooth)/np.maximum(weight, 1e-3) for k in range(2)])
                move = np.where(fg[i][..., None], move, bw)
            speed = np.linalg.norm(move, axis=2)
            # Still foreground keeps its coordinates even where flow is untrustworthy (flat, low-texture areas).
            still = (speed < FLOW_DEADZONE) & fg[i] & fg[i-1]
            ax, ay = gx + move[..., 0], gy + move[..., 1]
            for k, uv in enumerate(layers):
                carried = cv2.remap(uv, ax, ay, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                uv = np.where(still[..., None], uv, np.where(valid[..., None], carried, grid))
                layers[k] = _nearest_extend(uv, valid | still, fg[i])
            if cycle:
                carried = np.where(still, phase, cv2.remap(phase, ax, ay, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))
                weights = layer_weights(carried)
                deformed = sum(wk*distortion_map(uv) for wk, uv in zip(weights, layers))
                deformed = cv2.GaussianBlur(np.where(fg[i], deformed, 0).astype(np.float32), (0, 0), 2)
                advanced = carried + np.where(fg[i], np.clip(deformed - UV_SLACK, 0, 1), 0)/cycle
                # Re-anchor each layer only at points whose phase just wrapped, where that layer's weight is ~0.
                for k in range(2):
                    wrapped = fg[i] & (np.floor(advanced + k/2) > np.floor(carried + k/2))
                    if wrapped.any():
                        layers[k] = np.where(wrapped[..., None], _reanchor(layers[1 - k], grid, fg[i]), layers[k])
                phase = advanced.astype(np.float32)
            record.update({'backward': bw.astype(np.float16), 'valid': np.packbits(valid)})
            valid_fraction.append(round(float(valid.sum()/max(1, fg[i].sum())), 4))
            interior = cv2.erode(fg[i].astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & valid
            weights = layer_weights(phase) if cycle else [np.ones((h, w), np.float32)]
            deformation = sum(wk*distortion_map(uv) for wk, uv in zip(weights, layers))
            distortion.append(round(float(np.median(deformation[interior])), 4) if interior.any() else 0.0)
        else:
            valid_fraction.append(None)
            distortion.append(0.0)
        for k, uv in enumerate(layers):
            record[f'uv{k}'] = _pack(uv)
        if cycle:
            record['phase'] = np.mod(phase, 1).astype(np.float16)  # weights need only the fractional phase
        np.savez_compressed(stage/'flow'/f'{i:05d}.npz', **record)
        records.append(f'flow/{i:05d}.npz')
    return {'enabled': True, 'deadzone_px': FLOW_DEADZONE, 'smooth_px': smooth, 'uv_clock': cycle, 'uv_slack': UV_SLACK,
            'method': 'OpenCV DIS (medium), backward t->t-1 with forward-backward consistency',
            'uv': f'texture coordinates advected along smoothed trusted flow (moves under {FLOW_DEADZONE} px held still); '
                  f'revealed surface extended from the nearest trusted pixel; '
                  + (f'two layers cross-weighted by a per-point phase that advances by (deformation - {UV_SLACK})/{cycle} '
                     f'per frame (rigid and undeformed points never change weight); a layer re-anchors only where its phase '
                     f'wraps, copying the other layer where its interior deformation is under {REANCHOR_LOW}-{REANCHOR_HIGH} '
                     f'(feathered) and restarting only deformed texture; '
                     if cycle else 'one layer, never re-anchored; ')
                  + f'stored as uint16 = uv*{UV_SCALE}+{UV_OFFSET}',
            'files': records, 'valid_fraction': valid_fraction, 'uv_distortion': distortion}


def load_flow(guides, manifest, i):
    """Flow guides for frame i: backward flow (None on frame 0), trusted-flow mask and advected texture coordinates.

    uv_layers pairs each texture-coordinate layer with its per-pixel blend weight map (maps sum to 1); uv takes the
    heavier layer per pixel, for plugins that sample one field and accept a seam where layers hand over.
    """
    data = np.load(Path(guides)/manifest['flow']['files'][i])
    fields = [(data[key].astype(np.float32) - UV_OFFSET)/UV_SCALE for key in ('uv0', 'uv1') if key in data]
    h, w = fields[0].shape[:2]
    weights = layer_weights(data['phase'].astype(np.float32)) if 'phase' in data else [np.ones((h, w), np.float32)]
    layers = list(zip(fields, weights))
    uv = fields[0] if len(fields) == 1 else np.where((weights[0] >= weights[1])[..., None], fields[0], fields[1])
    if 'backward' not in data:
        return {'backward': None, 'valid': np.zeros((h, w), bool), 'uv': uv, 'uv_layers': layers}
    valid = np.unpackbits(data['valid'])[:h*w].reshape(h, w).astype(bool)
    return {'backward': data['backward'].astype(np.float32), 'valid': valid, 'uv': uv, 'uv_layers': layers}


def extract(frames, manifest, out, colors=4, alpha_threshold=128, epsilon=1.0, max_samples=200000,
            effect_masks=None, effect_colors=3, effect_alpha='binary', effect_alpha_floor=None, flow=False, uv_clock=UV_CLOCK):
    frames, manifest, out = Path(frames), Path(manifest), Path(out)
    if out.exists():
        raise FileExistsError('Use a new output directory')
    if not (1 <= colors <= 254 and 1 <= effect_colors <= 254):
        raise ValueError('colors must be 1-254')
    if effect_alpha not in ('binary', 'plate'):
        raise ValueError("effect_alpha must be 'binary' or 'plate'")
    floor = alpha_threshold if effect_alpha_floor is None else effect_alpha_floor
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
    # Soft mode lets reviewed effect masks keep low-alpha glow and trail pixels the character threshold would drop.
    fx = _effect_masks(effect_masks, len(files), plate[0].shape[:2], [a[..., 3] >= max(1, floor) for a in plate])
    masks = [f & ~e for f, e in zip(fg, fx)] if fx else fg
    centers = _shared_palette(plate, masks, colors, max_samples, 'Plate has no foreground above alpha threshold')
    fx_centers = None
    if fx:
        # Palette from confident effect pixels when any exist; faint pixels have unreliable straight RGB.
        solid = [m & f for m, f in zip(fx, fg)]
        fx_centers = _shared_palette(plate, solid if any(m.any() for m in solid) else fx, effect_colors, max_samples,
                                     'Effect masks select no foreground pixels')
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        stage = Path(tmp)/'guides'
        records = _layer(plate, masks, centers, stage, '', epsilon)
        # Flow follows everything visible, character and effects alike.
        flow_record = _flow_guides(plate, fg, stage, uv_clock) if flow else {'enabled': False}
        effects = None
        if fx:
            effects = {'palette': fx_centers.astype(int).tolist(),
                       'frames': _layer(plate, fx, fx_centers, stage, 'effects/', epsilon, keep_alpha=effect_alpha == 'plate'),
                       'alpha': effect_alpha, 'alpha_floor': floor,
                       'mask_sha256': [hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(Path(effect_masks).glob('*.png'), key=natural)],
                       'mask_review': 'supplied by caller; not verified by the extractor',
                       'mask_manifest': _mask_manifest(Path(effect_masks)),
                       'limits': 'each pixel is assigned to one layer by the mask; mixed character/effect pixels are not unmixed '
                                 'and character regions hidden under effects are not recovered'}
        h, w = plate[0].shape[:2]
        record = {'kind': 'stylized-redraw-guides', 'version': VERSION, 'canvas': [w, h],
                  'durations_ms': source['durations_ms'], 'alpha_threshold': alpha_threshold, 'epsilon': epsilon,
                  'palette': centers.astype(int).tolist(), 'frames': records, 'effects': effects, 'flow': flow_record,
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
    parser.add_argument('--effect-alpha', choices=['binary', 'plate'], default='binary',
                        help='plate: keep measured soft alpha for the effect layer')
    parser.add_argument('--effect-alpha-floor', type=int, help='Lowest effect alpha kept (default: --alpha-threshold)')
    parser.add_argument('--flow', action='store_true', help='Store optical flow and motion-attached texture coordinates')
    parser.add_argument('--uv-clock', type=float, default=UV_CLOCK, help='Deformation-to-phase rate divisor; smaller re-anchors sooner; 0 never re-anchors')
    args = parser.parse_args()
    print(json.dumps(extract(args.frames, args.manifest, args.out, args.colors, args.alpha_threshold, args.epsilon,
                             effect_masks=args.effect_masks, effect_colors=args.effect_colors,
                             effect_alpha=args.effect_alpha, effect_alpha_floor=args.effect_alpha_floor, flow=args.flow,
                             uv_clock=args.uv_clock)))
