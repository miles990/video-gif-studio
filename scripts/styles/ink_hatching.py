"""Ink hatching style plugin: pen hatching on a tinted paper wash, glued to the moving surface.

Hatch lines live in the advected texture coordinates from `extract_guides.py --flow`, so strokes travel with the
limbs instead of sliding across them. Without flow guides the pattern falls back to canvas space (it will slide;
declare intent.texture_slides or extract with --flow). Effects keep their own color with a soft glow, unhatched.

Params: paper, ink (#RRGGBB), spacing (px), line_width (px), angle (radians), thresholds (luminance per hatch layer),
wash (0-1 paper tint from the fill colors), wobble (px of hand wobble), solid (luminance below which ink is solid),
glow (0-1), glow_radius (px).
"""
import cv2
import numpy as np

DEFAULTS = {'paper': '#F4ECDD', 'ink': '#1D1A26', 'spacing': 4.5, 'line_width': 1.0, 'angle': 0.785,
            'thresholds': [0.82, 0.6, 0.4], 'wash': 0.5, 'wobble': 0.9, 'solid': 0.16, 'glow': 0.55, 'glow_radius': 5.0}


def _hex(value):
    value = value.lstrip('#')
    return np.array([int(value[i:i+2], 16) for i in (0, 2, 4)], np.float32)


def _sample(field, u, v):
    return cv2.remap(field, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)


def render(ctx):
    p = {**DEFAULTS, **ctx['params']}
    base = ctx['base'].astype(np.float32)
    h, w = base.shape[:2]
    if ctx['uv'] is not None:
        u, v = ctx['uv'][..., 0].astype(np.float32), ctx['uv'][..., 1].astype(np.float32)
    else:
        v, u = np.mgrid[:h, :w].astype(np.float32)
    lum = (base[..., :3] @ np.float32([.299, .587, .114]))/255

    # Hand wobble sampled in texture space: it moves with the surface and never re-rolls per frame.
    wob = cv2.GaussianBlur(ctx['noise']('ink-wobble', (512, 512)).astype(np.float32), (0, 0), 7)
    wob = (wob - wob.mean())/max(float(wob.std()), 1e-6)*p['wobble']
    wobble = _sample(wob, u, v)

    ink = np.zeros((h, w), np.float32)
    for k, threshold in enumerate(p['thresholds']):
        a = p['angle'] + k*np.pi/2.6
        d = (u*np.cos(a) + v*np.sin(a) + wobble*(1 + .4*k))/p['spacing']
        dist = np.abs(d - np.round(d))*p['spacing']
        stroke = np.clip(p['line_width']/2 + .5 - dist, 0, 1)
        weight = np.clip((threshold - lum)/.08, 0, 1)
        ink = np.maximum(ink, stroke*weight)
    ink = np.maximum(ink, np.clip((p['solid'] - lum)/.04, 0, 1))

    paper = _hex(p['paper'])
    wash = paper*(1 - p['wash']) + base[..., :3]*p['wash']
    rgb = wash*(1 - ink[..., None]) + _hex(p['ink'])*ink[..., None]
    alpha = base[..., 3]/255

    fx = ctx['effects']
    if fx is not None and fx['mask'].any():
        m = fx['mask']
        rgb[m] = base[..., :3][m]
        glow_src = base*(m[..., None])
        glow = cv2.GaussianBlur(glow_src, (0, 0), p['glow_radius'])
        g_alpha = np.clip(glow[..., 3]/255*p['glow'], 0, .45)
        g_rgb = np.where(glow[..., 3:] > 0, glow[..., :3]/np.maximum(glow[..., 3:]/255, 1e-6), 0)
        # Glow sits beneath the figure and extends past it; inside the figure it brightens like a screen blend.
        screen = 255 - (255 - rgb)*(255 - g_rgb*g_alpha[..., None])/255
        rgb = np.where(alpha[..., None] > 0, screen, g_rgb)
        alpha = np.maximum(alpha, np.where(alpha > 0, alpha, g_alpha))
    return np.dstack([np.clip(rgb + .5, 0, 255), np.clip(alpha*255 + .5, 0, 255)]).astype(np.uint8)
