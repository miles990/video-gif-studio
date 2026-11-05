"""ClockWipe — A wipe that sweeps around the center from a starting angle

Author: Fernando Kuteken
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/ClockWipe.glsl
SHA256: bd7e6168eec558178685c6ea4ad4f7e0902c3feb904e39b7435f24971409dee3
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_clock_wipe', status='stable', style_tags=['幾何', '含蓄/柔和'], startingAngle='@range(0, 360) Angle where the wipe starts, in degrees; GLSL float, default 90')
def transition(a, b, p, ctx, startingAngle=90.0):
    """A wipe that sweeps around the center from a starting angle."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    angle = np.arctan2(y - .5, (x - .5) * s.ratio) + np.deg2rad(startingAngle)
    out = s.blend(p >= fract((angle + np.pi) / (2 * np.pi)))
    return s.finish(out)
