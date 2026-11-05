"""SquaresWipe — Squares grow along a diagonal sweep to reveal the incoming image

Author: gre
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/SquaresWipe.glsl
SHA256: 32f24c18612a2e5647eedad26b65a02605be7e69871403d911323a9f13cbe9e3
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_squares_wipe', status='experimental', squares='@param Number of squares (columns, rows); GLSL ivec2, default ivec2(10,10)', direction='@param Direction of the sweep; GLSL vec2, default vec2(1.0, -0.5)', smoothness='@param Softness of the sweep; GLSL float, default 1.6')
def transition(a, b, p, ctx, squares=(10, 10), direction=(1.0, -0.5), smoothness=1.6):
    """Squares grow along a diagonal sweep to reveal the incoming image."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    sx, sy = vector(squares,2,'squares'); positive(sx,'squares'); positive(sy,'squares')
    v = direction_vector(direction); v /= np.abs(v).sum()
    pr = smooth(-smoothness,0,v[0]*x+v[1]*y-(v.sum()*.5-.5+p*(1+smoothness)))
    qx,qy = fract(x*s.ratio*sx),fract(y*sy)
    m = (qx>=pr/2)&(qy>=pr/2)&(qx<=1-pr/2)&(qy<=1-pr/2)
    out = s.blend(m)
    return finish(out, a, b)
