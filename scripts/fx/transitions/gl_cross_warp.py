"""CrossWarp — The outgoing image zooms in while the incoming one zooms out into place, sweeping from right to left

Author: Eke Péter <peterekepeter@gmail.com>
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/CrossWarp.glsl
SHA256: a3a8a4800489f26f8ff3be6b63ccef2ab53279d97df16d469db3d4f57b7df381
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_cross_warp', status='stable', style_tags=['流動', '含蓄/柔和'])
def transition(a, b, p, ctx):
    """The outgoing image zooms in while the incoming one zooms out into place, sweeping from right to left."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    m = smooth(0, 1, p * 2 + x - 1)
    out = s.warped((x-.5)*(1-m)+.5, (y-.5)*(1-m)+.5,
                   (x-.5)*m+.5, (y-.5)*m+.5, m)
    return s.finish(out, displacement=True)
