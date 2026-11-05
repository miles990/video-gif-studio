"""BurnThrough — The outgoing image burns away in noisy, glowing patches

Author: liubailin2020@gmail.com
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/BurnThrough.glsl
SHA256: d572b6d93c74292c14c1feb3cf55eccfc03ffb98a6bfa3b0900162295f6aa0e9
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from functools import lru_cache
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise, grid)


@lru_cache(maxsize=2)
def _burn_field(width, height, seed):
    """Static shader field, cached independently of source images and progress."""
    x, y = grid(width, height)
    n = np.zeros_like(x)
    for octave in range(4):
        n += (.5 / 2**octave) * noise(x*(width/height)*4*2**octave, y*4*2**octave, seed)
    n.flags.writeable = False
    return n


@register_transition(name='gl_burn_through', status='stable', style_tags=['搶眼/衝擊', '有機', '火焰'], burnColor='@color Color of the burning edges; GLSL vec3, default vec3(1.0, 0.5, 0.0)')
def transition(a, b, p, ctx, burnColor=(1.0, 0.5, 0.0)):
    """The outgoing image burns away in noisy, glowing patches."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    color = vector(burnColor, 3, 'burnColor')
    n = _burn_field(ctx.width, ctx.height, ctx.seed)
    l = smooth(p, p+.05, n)
    out = mix(s.b, s.a, l)
    out[..., :3] += color * ((1-l)*l*5)[...,None] * out[...,3:4]
    return s.finish(out)
