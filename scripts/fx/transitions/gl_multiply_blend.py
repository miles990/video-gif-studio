"""MultiplyBlend — A crossfade through the multiplied blend of both images

Author: Fernando Kuteken
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/MultiplyBlend.glsl
SHA256: 881452e2099c875d281dae71c85152318c769f02e9acf8ad52c247bb22f4b1b8
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_multiply_blend', status='stable', style_tags=['含蓄/柔和', '暗調'])
def transition(a, b, p, ctx):
    """A crossfade through the multiplied blend of both images."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    blended = s.a*s.b
    if not s.opaque:
        aa, ab = s.a[...,3:4], s.b[...,3:4]
        # Separable multiply contributes only in the overlap. The remaining
        # associated colours retain each source's non-overlapping coverage.
        blended[...,:3] += (1-ab)*s.a[...,:3] + (1-aa)*s.b[...,:3]
        blended[...,3:4] = aa+ab-aa*ab
    out = mix(s.a,blended,2*p) if p<.5 else mix(blended,s.b,2*p-1)
    return s.finish(out)
