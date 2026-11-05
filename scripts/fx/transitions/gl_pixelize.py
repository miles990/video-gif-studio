"""Pixelize — Both images pixelate, crossfade, then sharpen again

Author: gre
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/Pixelize.glsl
SHA256: f5c541b779364dcf92d71f4928efa07c414ffd83a5bfb5b8ca9280a1c73c8b32
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_pixelize', status='stable', style_tags=['復古', '像素'], squaresMin='@param Number of squares at the strongest pixelation; GLSL ivec2, default ivec2(20)', steps='@param Number of pixelation steps; 0 for a continuous effect; GLSL int, default 50')
def transition(a, b, p, ctx, squaresMin=(20, 20), steps=50):
    """Both images pixelate, crossfade, then sharpen again."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    sq = vector(squaresMin, 2, 'squaresMin')
    if np.any(sq<=0): raise ValueError('squaresMin: components must be positive')
    d = min(p,1-p)
    dist = np.ceil(d*steps)/steps if steps>0 else d
    sx, sy = 2*dist/sq[0]/s.ratio, 2*dist/sq[1]
    u, v = (np.floor(x/sx)+.5)*sx, (np.floor(y/sy)+.5)*sy
    out = s.warped(u,v,u,v,p)
    if steps>0 and d*steps<1: out=mix(s.blend(p),out,d*steps)
    return s.finish(out, displacement=True)
