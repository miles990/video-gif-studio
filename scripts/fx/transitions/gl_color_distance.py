"""ColorDistance — Pixels switch to the incoming image in order of how close their colors are

Author: P-Seebauer
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/ColorDistance.glsl
SHA256: 23fe510bb77ab400098ef7c50d032ed834add102b192e629ba0f966beb72ec58
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_color_distance', status='experimental', power='power; GLSL float, default 5.0')
def transition(a, b, p, ctx, power=5.0):
    """Pixels switch to the incoming image in order of how close their colors are."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    positive(power, 'power')
    # Use associated colors for the threshold: hidden RGB must not select pixels.
    m = np.linalg.norm(s.a-s.b, axis=2) <= p
    out = mix(s.blend(m), s.b, p**power)
    return finish(out, a, b)
