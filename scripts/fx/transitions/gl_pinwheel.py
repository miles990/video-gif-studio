"""Pinwheel — A spinning pinwheel reveals the incoming image

Author: Mr Speaker
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/Pinwheel.glsl
SHA256: fb8dea2ecd066a23d683726714add1f40885e68ac124532be1d774f169b08d8d
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_pinwheel', status='stable', style_tags=['幾何', '俏皮'], speed='@param Rotation speed; GLSL float, default 2.0')
def transition(a, b, p, ctx, speed=2.0):
    """A spinning pinwheel reveals the incoming image."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    angle = np.arctan2(y-.5,(x-.5)*s.ratio)+p*speed
    out = s.blend(p > np.mod(angle,3.1415/4))
    return s.finish(out)
