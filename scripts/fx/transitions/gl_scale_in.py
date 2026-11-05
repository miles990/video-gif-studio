"""ScaleIn — The incoming image scales in from the center while fading in

Author: haiyoucuv
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/ScaleIn.glsl
SHA256: e450c0c8712dbe464dde15d5a89a8338d4df090523792beeb6d4c320928296d5
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_scale_in', status='stable', style_tags=['含蓄/柔和', '動感'])
def transition(a, b, p, ctx):
    """The incoming image scales in from the center while fading in."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    out = mix(s.a,s.sample(s.b,(x-.5)*p+.5,(y-.5)*p+.5),p)
    return s.finish(out, displacement=True)
