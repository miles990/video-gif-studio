"""RotateScaleFade — The outgoing image spins and zooms while fading to the incoming one, over a background color

Author: Fernando Kuteken
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/RotateScaleFade.glsl
SHA256: 4484386f72f9d955851feea332d4c449c70e9e25de4cbcefda6e6764c6709144
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_rotate_scale_fade', status='stable', style_tags=['旋轉', '衝擊'], center='@param Center of the rotation; GLSL vec2, default vec2(0.5, 0.5)', rotations='@param Number of turns; GLSL float, default 1', scale='@param Maximum zoom; GLSL float, default 8', backColor='@color Background color; GLSL vec4, default vec4(0.15, 0.15, 0.15, 1.0)')
def transition(a, b, p, ctx, center=(0.5, 0.5), rotations=1.0, scale=8.0, backColor=(0.15, 0.15, 0.15, 1.0)):
    """The outgoing image spins and zooms while fading to the incoming one, over a background color."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    cx, cy = vector(center, 2, 'center'); positive(scale, 'scale')
    bg = vector(backColor, 4, 'backColor').copy(); bg[:3] *= bg[3]
    dx, dy = (x-cx)*s.ratio, y-cy
    angle = 2*np.pi*rotations*p
    zoom = mix(scale, 1, 2*abs(p-.5))
    u = cx+(dx*np.cos(angle)-dy*np.sin(angle))/zoom/s.ratio
    v = cy+(dx*np.sin(angle)+dy*np.cos(angle))/zoom
    out = s.warped(u, v, u, v, p)
    out = np.where(((u<0)|(u>1)|(v<0)|(v>1))[...,None], bg, out)
    return s.finish(out, displacement=True)
