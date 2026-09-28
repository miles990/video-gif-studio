"""Paper cut-out style plugin: paper grain on the reference fill plus a soft drop shadow.

Params: grain (0-1, brightness modulation), grain_scale (px blur of the grain), shadow_offset [x, y],
shadow_alpha (0-1), anchor ("canvas", "centroid" or "uv").

anchor "canvas" keeps grain fixed on the page, so still body parts never change; moving parts slide under it.
anchor "centroid" moves grain with the figure's centroid, which makes still parts swim whenever a limb moves;
qc_redraw.py flags that unless the style declares it as intended.
anchor "uv" samples grain at the advected texture coordinates from extract_guides.py --flow, so it moves with each part.
"""
import cv2
import numpy as np

DEFAULTS = {'grain': 0.08, 'grain_scale': 1.2, 'shadow_offset': [3, 3], 'shadow_alpha': 0.35, 'anchor': 'canvas'}


def _grain(ctx, p, h, w, pad):
    field = ctx['noise']('paper-grain', (h + 2*pad, w + 2*pad)).astype(np.float32)
    if p['grain_scale'] > 0:
        field = cv2.GaussianBlur(field, (0, 0), p['grain_scale'])
    field = (field - field.mean())/max(float(field.std()), 1e-6)
    return np.clip(field, -2.5, 2.5)/2.5


def render(ctx):
    p = {**DEFAULTS, **ctx['params']}
    if p['anchor'] not in ('canvas', 'centroid', 'uv'):
        raise ValueError("paper_cutout anchor must be 'canvas', 'centroid' or 'uv'")
    if p['anchor'] == 'uv' and ctx['uv'] is None:
        raise ValueError("paper_cutout anchor 'uv' needs guides extracted with --flow")
    base = ctx['base'].astype(np.float32)
    h, w = base.shape[:2]
    pad = 64
    grain = _grain(ctx, p, h, w, pad)
    dy = dx = 0
    if p['anchor'] == 'centroid':
        ys, xs = np.nonzero(base[..., 3] >= 128)
        if len(xs):
            dx, dy = int(round(xs.mean())) % pad, int(round(ys.mean())) % pad
    if p['anchor'] == 'uv':
        # Blend re-anchored texture layers by weight so no layer is seen at the moment it resets.
        layers = ctx.get('uv_layers') or [(ctx['uv'], 1.0)]
        grain = sum(wk*cv2.remap(grain, uv[..., 0].astype(np.float32) + pad, uv[..., 1].astype(np.float32) + pad,
                                 cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP) for uv, wk in layers)
    else:
        grain = grain[pad - dy:pad - dy + h, pad - dx:pad - dx + w]
    rgb = np.clip(base[..., :3]*(1 + p['grain']*grain[..., None]), 0, 255)
    alpha = base[..., 3:]/255
    # Drop shadow: the figure's own coverage, offset and darkened, composited beneath it.
    ox, oy = p['shadow_offset']
    shadow = np.zeros((h, w), np.float32)
    shadow[max(0, oy):h + min(0, oy), max(0, ox):w + min(0, ox)] = \
        base[max(0, -oy):h - max(0, oy), max(0, -ox):w - max(0, ox), 3]/255*p['shadow_alpha']
    shadow = shadow[..., None]
    out_a = alpha + shadow*(1 - alpha)
    out_rgb = np.where(out_a > 0, rgb*alpha/np.where(out_a > 0, out_a, 1), 0)
    return np.dstack([np.floor(out_rgb + .5), np.floor(out_a*255 + .5)]).astype(np.uint8)
