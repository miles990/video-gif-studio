"""PerlinDissolve — The incoming image appears through blobs of Perlin noise

Author: Rich Harris
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/PerlinDissolve.glsl
SHA256: 14913f1110ab9fc2e0a8c08bf9cc566490e6399c1a0afb9300079dba4c0ca69a
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from functools import lru_cache
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise, grid)


@lru_cache(maxsize=2)
def _noise_field(width, height, scale, context_seed, shader_seed):
    x, y = grid(width, height)
    n = noise(x*(width/height)*scale, y*scale, context_seed, shader_seed, True)
    n.flags.writeable = False
    return n


@register_transition(name='gl_perlin_dissolve', status='experimental', scale='@param Scale of the noise; higher values make smaller blobs; GLSL float, default 4.0', smoothness='@param Softness of the blob edges; GLSL float, default 0.01', seed='@param Random seed; GLSL float, default 12.9898')
def transition(a, b, p, ctx, scale=4.0, smoothness=0.01, seed=12.9898):
    """The incoming image appears through blobs of Perlin noise."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    positive(scale,'scale')
    n = _noise_field(ctx.width, ctx.height, scale, ctx.seed, seed)
    position = mix(-smoothness,1+smoothness,p)
    out = s.blend(1-smooth(position-smoothness,position+smoothness,n))
    return finish(out, a, b)
