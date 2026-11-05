"""Crosshatch — The incoming image appears through a crosshatch of lines spreading from the center

Author: pthrasher
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/Crosshatch.glsl
SHA256: 8066e3d78c79a6be454bae058ff69d3fef87596d562826bddc638a461e1d032c
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_crosshatch', status='experimental', center='@param Point the lines spread from; GLSL vec2, default vec2(0.5)', threshold='threshold; GLSL float, default 3.0', fadeEdge='fadeEdge; GLSL float, default 0.1')
def transition(a, b, p, ctx, center=(0.5, 0.5), threshold=3.0, fadeEdge=0.1):
    """The incoming image appears through a crosshatch of lines spreading from the center."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    cx, cy = vector(center,2,'center'); positive(threshold,'threshold')
    dist = np.hypot((x-cx)*s.ratio,y-cy)/threshold
    r = p-np.minimum(random_field(y,0,ctx.seed),random_field(0,x,ctx.seed))
    m = mix((r>=dist).astype(np.float32),1,smooth(1-fadeEdge,1,p))*smooth(0,fadeEdge,p)
    out = s.blend(m)
    return finish(out, a, b)
