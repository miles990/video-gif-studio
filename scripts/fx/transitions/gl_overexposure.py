"""Overexposure — A crossfade through a washed-out, overexposed white

Author: Ben Zhang
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/Overexposure.glsl
SHA256: fbae3411c39af59e0b0fa6536c9a9797c6be0702a7e69303c7db8bc087efe26c
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_overexposure', status='experimental', strength='@param Amount of overexposure; GLSL float, default 0.6')
def transition(a, b, p, ctx, strength=0.6):
    """A crossfade through a washed-out, overexposed white."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    out = s.blend(p)
    out[..., :3] += (s.a[..., :3]+s.b[..., :3]) * (np.sin(np.pi*p)*strength)
    return finish(out, a, b)
