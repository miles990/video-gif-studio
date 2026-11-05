"""Wind — A ragged left-to-right wipe, as if the image was blown away by the wind

Author: gre
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/Wind.glsl
SHA256: a6af68366cd1feb21da596e6503994da8bb052c616ec73d4346006837494a01f
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_wind', status='experimental', size='@range(0, 1) Width of the ragged edge; GLSL float, default 0.2', reversed='@param Wipe from right to left instead; GLSL bool, default false')
def transition(a, b, p, ctx, size=0.2, reversed=False):
    """A ragged left-to-right wipe, as if the image was blown away by the wind."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    u = 1-x if reversed else x
    r = random_field(0,y,ctx.seed)
    m = smooth(0,-size,u*(1-size)+size*r-p*(1+size))
    out = s.blend(m)
    return finish(out, a, b)
