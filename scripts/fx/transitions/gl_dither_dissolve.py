"""DitherDissolve — The incoming image appears through a regular 8x8 ordered dither pattern, like a retro computer screen

Author: gre
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/DitherDissolve.glsl
SHA256: 7775dbc0feef21ccf8e0cd58760f1db53ec32fd78832c8de7bf8b2cd22d089d8
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_dither_dissolve', status='stable', style_tags=['復古', '像素'], dotSize='@range(0.002, 0.05) Size of a dither dot, relative to the height; GLSL float, default 0.02')
def transition(a, b, p, ctx, dotSize=0.02):
    """The incoming image appears through a regular 8x8 ordered dither pattern, like a retro computer screen."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    positive(dotSize, 'dotSize')
    cx, cy = np.floor(x*s.ratio/dotSize).astype(np.int64), np.floor(y/dotSize).astype(np.int64)
    value = np.zeros_like(x)
    for bit in range(3):
        bx, by = (cx>>bit)&1, (cy>>bit)&1
        value += (16/4**bit)*(2*(bx^by)+by)
    out = s.blend(p >= (value+.5)/64)
    return s.finish(out)
