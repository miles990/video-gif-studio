"""FadeGrayscale — A crossfade through grayscale

Author: gre
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/FadeGrayscale.glsl
SHA256: 54dc0a077c7949f87c6697d1a8dc8e0e167ca9a5ebddd4ccbc1022dfe9c283c0
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_fade_grayscale', status='stable', style_tags=['含蓄/柔和', '復古'], intensity='@range(0, 1) How long the grayscale phase lasts; GLSL float, default 0.3; // if 0.0, the image directly turn grayscale, if 0.9, the grayscale transition phase is very important')
def transition(a, b, p, ctx, intensity=0.3):
    """A crossfade through grayscale."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    aa, bb = s.a.copy(), s.b.copy()
    weights = np.array([.2126,.7152,.0722], np.float32)
    aa[..., :3] = mix((s.a[..., :3]@weights)[...,None], s.a[..., :3], smooth(1-intensity,0,p))
    bb[..., :3] = mix((s.b[..., :3]@weights)[...,None], s.b[..., :3], smooth(intensity,1,p))
    out = mix(aa, bb, p)
    return s.finish(out)
