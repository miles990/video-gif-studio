"""WindowSlices — The incoming image appears through vertical slices that widen

Author: gre
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/WindowSlices.glsl
SHA256: 128052b76eaa2802487cbc8940178daa54c2e91bfd0e157de69f2d6295e51449
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_window_slices', status='experimental', count='@param Number of slices; GLSL float, default 10.0', smoothness="@param Softness of the slices' edges; GLSL float, default 0.5")
def transition(a, b, p, ctx, count=10.0, smoothness=0.5):
    """The incoming image appears through vertical slices that widen."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    positive(count,'count')
    pr = smooth(-smoothness,0,x-p*(1+smoothness))
    out = s.blend(fract(count*x)>=pr)
    return finish(out, a, b)
