#!/usr/bin/env python3
"""Reference stylized-redraw renderer: flat fill plus tapered contour, drawn from extract_guides.py output."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import cv2
import numpy as np
from PIL import Image

VERSION = 1
DEFAULT = {'fill': 'palette', 'palette': None, 'region_smooth': 1.0, 'background': None, 'supersample': 4,
           'line': {'color': '#1A1A1A', 'width': 2.0, 'taper': 0.5, 'light': [-1, -1]}}


def _hex(value):
    value = str(value).lstrip('#')
    if len(value) != 6:
        raise ValueError(f'Expected #RRGGBB color, got {value!r}')
    return np.array([int(value[i:i+2], 16) for i in (0, 2, 4)], np.uint8)


def _style(style, palette):
    s = {**DEFAULT, **style, 'line': {**DEFAULT['line'], **style.get('line', {})}}
    if not isinstance(s['supersample'], int) or not 1 <= s['supersample'] <= 8:
        raise ValueError('supersample must be an integer 1-8')
    if s['fill'] == 'palette':
        colors = [_hex(c) for c in s['palette']] if s['palette'] else [np.array(c, np.uint8) for c in palette]
        if len(colors) != len(palette):
            raise ValueError('palette override must match the guide palette length')
    elif str(s['fill']).startswith('#'):
        colors = [_hex(s['fill'])]*len(palette)
    else:
        raise ValueError("fill must be 'palette' or #RRGGBB")
    if s['line']['width'] < 0 or not 0 <= s['line']['taper'] <= 1:
        raise ValueError('line width must be >= 0 and taper 0-1')
    return s, np.array(colors, np.uint8)


def _scaled(points, ss):
    # Map pixel centers onto the supersampled grid.
    return (np.asarray(points, np.int64)*ss + ss//2).astype(np.int32)


def _regions(labels, fill, colors, ss, smooth):
    # Smooth region boundaries by upsampling blurred one-hot labels, then taking the strongest label per subpixel.
    h, w = labels.shape
    best = np.zeros((h*ss, w*ss), np.uint8)
    index = np.zeros((h*ss, w*ss), np.uint8)
    for k in range(len(colors)):
        onehot = (labels == k).astype(np.float32)
        if not onehot.any():
            continue
        if smooth > 0:
            onehot = cv2.GaussianBlur(onehot, (0, 0), smooth)
        score = cv2.resize(np.rint(onehot*255).astype(np.uint8), (w*ss, h*ss), interpolation=cv2.INTER_LINEAR)
        win = score > best
        best[win], index[win] = score[win], k
    return np.where(fill[..., None], colors[index], 0).astype(np.uint8)


def _outline(rings, mask, ss, line):
    h, w = mask.shape
    out = np.zeros((h*ss, w*ss), np.uint8)
    width = line['width']*ss
    if width <= 0:
        return out
    light = np.asarray(line['light'], np.float64)
    light = light/np.linalg.norm(light) if np.linalg.norm(light) else light
    for ring in rings:
        p = np.asarray(ring['points'], np.float64)
        d = np.roll(p, -1, 0)-p
        length = np.linalg.norm(d, axis=1)
        keep = length > 0
        if keep.sum() < 2:
            continue
        n = np.stack([d[:, 1], -d[:, 0]], 1)/np.where(length, length, 1)[:, None]
        mid = p+d/2+n
        xi, yi = np.rint(mid[:, 0]).astype(int), np.rint(mid[:, 1]).astype(int)
        inside = (0 <= xi) & (xi < w) & (0 <= yi) & (yi < h)
        inside[inside] = mask[yi[inside], xi[inside]]
        # Orient each ring by vote so normals face away from the fill; start point and winding do not matter.
        if inside[keep].sum()*2 > keep.sum():
            n = -n
        # Width depends on normal direction, not arc length, so the taper does not crawl as contours change.
        widths = width*(1-line['taper']*(.5+.5*(n @ light)))
        q = p*ss+ss//2
        for i in np.nonzero(keep)[0]:
            a, b, half = q[i], q[(i+1) % len(q)], n[i]*widths[i]/2
            cv2.fillConvexPoly(out, np.rint([a+half, b+half, b-half, a-half]).astype(np.int32), 255)
        for i in range(len(q)):
            r = (widths[i]+widths[i-1])/4
            if r >= .5:
                cv2.circle(out, tuple(np.rint(q[i]).astype(int)), int(round(r)), 255, -1)
    return out


def _reduce(rgb, alpha, ss):
    # alpha holds 0/1 coverage; average premultiplied subpixels, then return straight RGBA.
    h, w = alpha.shape[0]//ss, alpha.shape[1]//ss
    a = alpha.reshape(h, ss, w, ss).sum((1, 3), dtype=np.uint32)
    c = rgb.reshape(h, ss, w, ss, 3).sum((1, 3), dtype=np.uint32)
    straight = np.where(a[..., None], (c + a[..., None]//2)//np.maximum(a, 1)[..., None], 0)
    return np.dstack([straight, (a*255 + ss*ss//2)//(ss*ss)]).astype(np.uint8)


def render_frame(frame, guides, style, colors):
    w, h = guides['canvas']
    ss = style['supersample']
    root = guides['_root']
    mask = np.array(Image.open(root/frame['mask'])) > 0
    labels = np.array(Image.open(root/frame['labels']))
    fill = np.zeros((h*ss, w*ss), np.uint8)
    polys = [_scaled(r['points'], ss) for r in frame['rings']]
    if polys:
        # Even-odd fill keeps holes from the guide contours.
        cv2.fillPoly(fill, polys, 255)
    rgb = _regions(labels, fill > 0, colors, ss, style['region_smooth'])
    line = _outline(frame['rings'], mask, ss, style['line']) > 0
    rgb[line] = _hex(style['line']['color'])
    alpha = ((fill > 0) | line).astype(np.uint8)
    out = _reduce(rgb*alpha[..., None], alpha, ss)
    if style['background']:
        bg = _hex(style['background']).astype(np.uint32)
        a = out[..., 3:].astype(np.uint32)
        out = np.dstack([(out[..., :3]*a + bg*(255-a) + 127)//255, np.full((h, w), 255)]).astype(np.uint8)
    return out


def render(guides, style, out):
    guides, out = Path(guides), Path(out)
    if out.exists():
        raise FileExistsError('Use a new output directory')
    manifest = json.loads((guides/'manifest.json').read_text())
    if manifest.get('kind') != 'stylized-redraw-guides':
        raise ValueError('Not an extract_guides.py manifest')
    style, colors = _style(style, manifest['palette'])
    manifest['_root'] = guides
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        stage = Path(tmp)/'render'
        (stage/'frames').mkdir(parents=True)
        for i, frame in enumerate(manifest['frames']):
            Image.fromarray(render_frame(frame, manifest, style, colors)).save(stage/'frames'/f'{i:05d}.png')
        style_json = json.dumps(style, sort_keys=True)
        record = {'durations_ms': manifest['durations_ms'], 'canvas': manifest['canvas'],
                  'pixels': 'redrawn from plate guides; no plate pixels are delivered',
                  'fill_colors': 'guide palette sampled from the plate' if style['fill'] == 'palette' and not style['palette'] else 'style sheet',
                  'style': style, 'style_sha256': hashlib.sha256(style_json.encode()).hexdigest(),
                  'guides_manifest_sha256': hashlib.sha256((guides/'manifest.json').read_bytes()).hexdigest(),
                  'renderer': {'name': 'render_stylized.py', 'version': VERSION, 'opencv': cv2.__version__,
                               'renderer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                  'visual_review': 'required; check shape popping, contour crawl, identity drift, occlusion and contacts at playback speed'}
        (stage/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
        stage.rename(out)
    return {'frames': len(manifest['frames']), 'out': str(out)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('guides', type=Path, help='extract_guides.py output directory')
    parser.add_argument('--style', type=Path, help='Style sheet JSON; omitted keys use reference defaults')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.guides, json.loads(args.style.read_text()) if args.style else {}, args.out)))
