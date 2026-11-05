"""Swirl — Both images swirl around the center while crossfading

Author: Sergey Kosarevsky
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/Swirl.glsl
SHA256: fbbea8a885ed8cdf913fe481ee09e8897a79fd4f7c9ec6a1f459f6010147301e
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_swirl', status='stable', style_tags=['迷幻', '搶眼'])
def transition(a, b, p, ctx):
    """Both images swirl around the center while crossfading."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    dx, dy = (x-.5)*s.ratio, y-.5
    dist = np.hypot(dx, dy)
    theta = np.maximum(1-dist, 0)**2 * (1-abs(2*p-1)) * 8 * 3.14159
    u = (dx*np.cos(theta)-dy*np.sin(theta))/s.ratio+.5
    v = dx*np.sin(theta)+dy*np.cos(theta)+.5
    out = s.warped(u, v, u, v, p)
    return s.finish(out, displacement=True)
