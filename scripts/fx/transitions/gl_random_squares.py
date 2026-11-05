"""RandomSquares — The incoming image appears in random squares

Author: gre
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/RandomSquares.glsl
SHA256: 844211ca33ae9f126fddfa9f3987bc853933c7ee2f919ca2d09def7d8040cb6a
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_random_squares', status='stable', style_tags=['幾何', '數位'], size='@param Number of squares (columns, rows); GLSL ivec2, default ivec2(10, 10)', smoothness="@param Softness of each square's switch; GLSL float, default 0.5")
def transition(a, b, p, ctx, size=(10, 10), smoothness=0.5):
    """The incoming image appears in random squares."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    sx, sy = vector(size, 2, 'size'); positive(sx,'size'); positive(sy,'size')
    r = random_field(np.floor(x*s.ratio*sx),np.floor(y*sy),ctx.seed)
    out = s.blend(smooth(0,-smoothness,r-p*(1+smoothness)))
    return s.finish(out)
