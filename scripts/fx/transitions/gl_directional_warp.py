"""DirectionalWarp — A diagonal wipe with a warped, smeared edge

Author: pschroen
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/DirectionalWarp.glsl
SHA256: 9b4988a12affa2fc89a7a1d87ad2df8c8bfaf185fc83e958188e5c674dbf03ce
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_directional_warp', status='experimental', smoothness='@param Softness of the edge; GLSL float, default 0.1', direction='@param Direction of the wipe; GLSL vec2, default vec2(-1.0, 1.0)')
def transition(a, b, p, ctx, smoothness=0.1, direction=(-1.0, 1.0)):
    """A diagonal wipe with a warped, smeared edge."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    v = direction_vector(direction); v /= np.abs(v).sum()
    m = 1 - smooth(-smoothness, 0, v[0]*x + v[1]*y - (v.sum()*.5-.5+p*(1+smoothness)))
    out = s.warped((x-.5)*(1-m)+.5, (y-.5)*(1-m)+.5,
                   (x-.5)*m+.5, (y-.5)*m+.5, m)
    return finish(out, a, b)
