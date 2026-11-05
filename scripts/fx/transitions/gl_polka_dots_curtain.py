"""PolkaDotsCurtain — The incoming image appears through growing polka dots

Author: bobylito
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/PolkaDotsCurtain.glsl
SHA256: 1a11af446cf3c50bf58d1a2b1547092e386bdcf1b7dff71179661f6a4c71d29a
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_polka_dots_curtain', status='experimental', dots='@param Number of dots across the image; GLSL float, default 20.0', center='center; GLSL vec2, default vec2(0, 0)')
def transition(a, b, p, ctx, dots=20.0, center=(0.0, 0.0)):
    """The incoming image appears through growing polka dots."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    positive(dots,'dots'); cx, cy = vector(center,2,'center')
    dist = np.hypot(fract(x*s.ratio*dots)-.5,fract(y*dots)-.5)
    origin = np.hypot((x-cx)*s.ratio,y-cy)
    out = s.blend(dist < p/np.maximum(origin,1e-8))
    return finish(out, a, b)
