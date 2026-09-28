#!/usr/bin/env python3
"""Reference stylized-redraw renderer: flat fill plus tapered contour, with an optional effect layer, from extract_guides.py output."""
import argparse
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import cv2
import numpy as np
from PIL import Image
from extract_guides import load_flow

VERSION = 1
STYLES = Path(__file__).resolve().parent/'styles'
DEFAULT = {'fill': 'palette', 'palette': None, 'region_smooth': 1.0, 'background': None, 'supersample': 4,
           'plugin': None, 'plugin_params': {}, 'seed': 0, 'intent': {},
           'line': {'color': '#1A1A1A', 'width': 2.0, 'taper': 0.5, 'light': [-1, -1]}}
# Effects default to unoutlined fills over the character; glows and trails rarely read well with contours.
EFFECT_DEFAULT = {'fill': 'palette', 'palette': None, 'region_smooth': 1.0, 'order': 'over', 'opacity': 1.0, 'alpha': None,
                  'line': {'color': '#1A1A1A', 'width': 0.0, 'taper': 0.0, 'light': [-1, -1]}}


def _hex(value):
    value = str(value).lstrip('#')
    if len(value) != 6:
        raise ValueError(f'Expected #RRGGBB color, got {value!r}')
    return np.array([int(value[i:i+2], 16) for i in (0, 2, 4)], np.uint8)


def _layer_style(style, defaults, palette):
    s = {**defaults, **style, 'line': {**defaults['line'], **style.get('line', {})}}
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


def _style(style, guides):
    s, colors = _layer_style({k: v for k, v in style.items() if k != 'effects'}, DEFAULT, guides['palette'])
    if not isinstance(s['supersample'], int) or not 1 <= s['supersample'] <= 8:
        raise ValueError('supersample must be an integer 1-8')
    fx = None
    if guides.get('effects'):
        e, fx_colors = _layer_style(style.get('effects', {}), EFFECT_DEFAULT, guides['effects']['palette'])
        if e['order'] not in ('over', 'under') or not 0 <= e['opacity'] <= 1:
            raise ValueError("effects order must be 'over' or 'under' and opacity 0-1")
        soft = guides['effects'].get('alpha') == 'plate'
        e['alpha'] = e['alpha'] or ('plate' if soft else 'solid')
        if e['alpha'] not in ('plate', 'solid') or (e['alpha'] == 'plate' and not soft):
            raise ValueError("effects alpha 'plate' needs guides extracted with effect_alpha='plate'; otherwise use 'solid'")
        fx = (e, fx_colors)
        s['effects'] = e
    elif 'effects' in style:
        raise ValueError('Style sets effects but the guides have no effect layer')
    return s, colors, fx


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
            # Rings run through boundary pixel centers; shift half a pixel outward onto the fill edge.
            edge = n[i]*ss/2
            a, b, half = q[i]+edge, q[(i+1) % len(q)]+edge, n[i]*widths[i]/2
            cv2.fillConvexPoly(out, np.rint([a+half, b+half, b-half, a-half]).astype(np.int32), 255)
        for i in range(len(q)):
            r = (widths[i]+widths[i-1])/4
            if r >= .5:
                edge = (n[i]+n[i-1])*ss/4
                cv2.circle(out, tuple(np.rint(q[i]+edge).astype(int)), int(round(r)), 255, -1)
    return out


def _reduce(rgb, alpha, ss):
    # alpha holds 0/1 coverage; average premultiplied subpixels, then return straight RGBA.
    h, w = alpha.shape[0]//ss, alpha.shape[1]//ss
    a = alpha.reshape(h, ss, w, ss).sum((1, 3), dtype=np.uint32)
    c = rgb.reshape(h, ss, w, ss, 3).sum((1, 3), dtype=np.uint32)
    straight = np.where(a[..., None], (c + a[..., None]//2)//np.maximum(a, 1)[..., None], 0)
    return np.dstack([straight, (a*255 + ss*ss//2)//(ss*ss)]).astype(np.uint8)


def _fill(mask, ss):
    # Bilinear upsampling of the binary mask crosses 50% on pixel boundaries: exact area, smooth corners, thin strokes kept.
    h, w = mask.shape
    return cv2.resize(mask.astype(np.uint8)*255, (w*ss, h*ss), interpolation=cv2.INTER_LINEAR) >= 128


def render_layer(frame, root, style, colors, ss):
    mask = np.array(Image.open(root/frame['mask'])) > 0
    labels = np.array(Image.open(root/frame['labels']))
    fill = _fill(mask, ss)
    rgb = _regions(labels, fill, colors, ss, style['region_smooth'])
    line = _outline(frame['rings'], mask, ss, style['line']) > 0
    rgb[line] = _hex(style['line']['color'])
    alpha = (fill | line).astype(np.uint8)
    return _reduce(rgb*alpha[..., None], alpha, ss)


def _over(top, bottom, opacity=1.0):
    ta = top[..., 3:]/255*opacity
    ba = bottom[..., 3:]/255
    a = ta + ba*(1-ta)
    rgb = np.where(a > 0, (top[..., :3]*ta + bottom[..., :3]*ba*(1-ta))/np.where(a > 0, a, 1), 0)
    return np.dstack([np.floor(rgb+.5), np.floor(a*255+.5)]).astype(np.uint8)


def load_plugin(spec, seed=0):
    # A bare name selects a bundled style in scripts/styles (.py or .js); otherwise a path to an authored file.
    if '/' in str(spec) or str(spec).endswith(('.py', '.js')):
        path = Path(spec)
    else:
        path = next((STYLES/f'{spec}{ext}' for ext in ('.py', '.js') if (STYLES/f'{spec}{ext}').is_file()), STYLES/f'{spec}.py')
    if not path.is_file():
        raise ValueError(f'Style plugin not found: {spec}')
    if path.suffix == '.js':
        from js_style_host import JSStyle
        return JSStyle(path, seed), None
    module_spec = importlib.util.spec_from_file_location(f'style_plugin_{path.stem}', path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    if not callable(getattr(module, 'render', None)):
        raise ValueError(f'Style plugin {path} must define render(ctx)')
    return module, {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def noise_source(seed):
    # Same key, same field on every frame: stable textures by default; put the frame index in the key to boil on purpose.
    def noise(key, shape):
        digest = hashlib.sha256(f'{seed}:{key!r}'.encode()).digest()
        return np.random.default_rng(int.from_bytes(digest[:8], 'little')).random(shape)
    return noise


def _layer_context(frame, root, palette):
    if frame is None:
        return None
    return {'mask': np.array(Image.open(root/frame['mask'])) > 0, 'labels': np.array(Image.open(root/frame['labels'])),
            'rings': frame['rings'], 'palette': palette,
            'alpha': np.array(Image.open(root/frame['alpha'])) if frame.get('alpha') else None}


def render_frame(i, guides, style, colors, fx, plugin=None):
    ss, root = style['supersample'], guides['_root']
    out = render_layer(guides['frames'][i], root, style, colors, ss)
    if fx:
        e, fx_colors = fx
        frame = guides['effects']['frames'][i]
        layer = render_layer(frame, root, e, fx_colors, ss)
        if e['alpha'] == 'plate':
            measured = np.array(Image.open(root/frame['alpha'])).astype(np.uint32)
            layer[..., 3] = ((layer[..., 3]*measured + 127)//255).astype(np.uint8)
        if e['order'] == 'over':
            out = _over(layer, out, e['opacity'])
        else:
            faded = layer.copy()
            faded[..., 3] = np.floor(layer[..., 3]*e['opacity']+.5).astype(np.uint8)
            out = _over(out, faded)
    if plugin:
        w, h = guides['canvas']
        ctx = {'index': i, 'count': len(guides['frames']), 'canvas': (w, h), 'durations_ms': guides['durations_ms'],
               'base': out, 'params': style['plugin_params'], 'noise': noise_source(style['seed']),
               'character': _layer_context(guides['frames'][i], root, colors),
               'effects': _layer_context(guides['effects']['frames'][i], root, fx[1]) if fx else None,
               'uv': None, 'flow': None, 'flow_valid': None}
        if guides.get('flow', {}).get('enabled'):
            f = load_flow(root, guides, i)
            ctx.update({'uv': f['uv'], 'flow': f['backward'], 'flow_valid': f['valid']})
        out = plugin(ctx)
        if not isinstance(out, np.ndarray) or out.shape != (h, w, 4) or out.dtype != np.uint8:
            raise ValueError(f'Style plugin must return a uint8 array of shape {(h, w, 4)}')
    if style['background']:
        h, w = out.shape[:2]
        out = _over(out, np.dstack([np.broadcast_to(_hex(style['background']), (h, w, 3)), np.full((h, w), 255, np.uint8)]))
    return out


def render(guides, style, out):
    guides, out = Path(guides), Path(out)
    if out.exists():
        raise FileExistsError('Use a new output directory')
    manifest = json.loads((guides/'manifest.json').read_text())
    if manifest.get('kind') != 'stylized-redraw-guides':
        raise ValueError('Not an extract_guides.py manifest')
    style, colors, fx = _style(style, manifest)
    plugin, plugin_record = load_plugin(style['plugin'], style['seed']) if style['plugin'] else (None, None)
    manifest['_root'] = guides
    out.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack, tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        if plugin is not None and plugin_record is None:
            # JS plugins run in one browser session for the whole render.
            stack.enter_context(plugin)
            plugin_record = plugin.record()
        stage = Path(tmp)/'render'
        (stage/'frames').mkdir(parents=True)
        for i in range(len(manifest['frames'])):
            Image.fromarray(render_frame(i, manifest, style, colors, fx, plugin and plugin.render)).save(stage/'frames'/f'{i:05d}.png')
        style_json = json.dumps(style, sort_keys=True)
        record = {'durations_ms': manifest['durations_ms'], 'canvas': manifest['canvas'],
                  'pixels': 'redrawn from plate guides; no plate pixels are delivered',
                  'fill_colors': 'guide palette sampled from the plate' if style['fill'] == 'palette' and not style['palette'] else 'style sheet',
                  'effect_layer': manifest['effects'] and {'mask_review': manifest['effects']['mask_review'], 'limits': manifest['effects']['limits'],
                                                           'alpha': 'measured plate alpha, not unmixed' if style['effects']['alpha'] == 'plate' else 'solid coverage'},
                  'style': style, 'style_sha256': hashlib.sha256(style_json.encode()).hexdigest(), 'plugin': plugin_record,
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
