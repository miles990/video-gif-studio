"""Dreamy — A crossfade with a gentle wavy distortion

Author: mikolalysenko
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/Dreamy.glsl
SHA256: ad95fba01344f89815da3deb1c023478800af04a25c4d56f2ff291448138ae4c
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_dreamy', status='stable', style_tags=['夢幻', '含蓄/柔和'])
def transition(a, b, p, ctx):
    """A crossfade with a gentle wavy distortion."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    ay = y + .03*p*np.cos(10*(p+x))
    by = y + .03*(1-p)*np.cos(10*(1-p+x))
    out = s.warped(x, ay, x, by, p)
    return s.finish(out, displacement=True)
