"""WaterDrop — Ripples spread from the center like a drop falling into water, crossfading to the incoming image

Author: Paweł Płóciennik
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/WaterDrop.glsl
SHA256: 35c80cdb1b528c3da5e5a993c4133dd0fef4d8c288909fb0d8daca4e4c74ef2b
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_water_drop', status='experimental', amplitude='@param Frequency of the ripples; GLSL float, default 30', speed='@param Speed of the ripples; GLSL float, default 30')
def transition(a, b, p, ctx, amplitude=30.0, speed=30.0):
    """Ripples spread from the center like a drop falling into water, crossfading to the incoming image."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    dx, dy = (x-.5)*s.ratio, y-.5
    dist = np.hypot(dx, dy)
    offset = np.where(dist <= p, np.sin(dist*amplitude-p*speed), 0)
    out = s.warped(x+dx*offset/s.ratio, y+dy*offset, x, y, p)
    return finish(out, a, b)
