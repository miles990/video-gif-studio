"""DreamyZoom — Zooms and rotates into a bright flash, then out to the incoming image

Author: Zeh Fernando
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/DreamyZoom.glsl
SHA256: 8d3b21accab1dafe21e35c131aec87ce494977f43671ae3d318b3b4dde1ed259
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_dreamy_zoom', status='experimental', rotation='rotation; GLSL float, default 6', scale='scale; GLSL float, default 1.2')
def transition(a, b, p, ctx, rotation=6.0, scale=1.2):
    """Zooms and rotates into a bright flash, then out to the incoming image."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    positive(scale, 'scale')
    phase = p*2 if p < .5 else (p-.5)*2
    # Preserve the upstream constant (despite its misleading DEG2RAD comment).
    angle = (rotation*phase if p < .5 else -rotation*(1-phase))*.039269908169872415
    zoom = mix(1, scale, phase) if p < .5 else mix(scale, 1, phase)
    dx, dy = (x-.5)*s.ratio/zoom, (y-.5)/zoom
    u = (np.cos(angle)*dx-np.sin(angle)*dy)/s.ratio+.5
    v = np.sin(angle)*dx+np.cos(angle)*dy+.5
    out = s.sample(s.a if p < .5 else s.b, u, v)
    out[..., :3] += out[..., 3:4] * (phase if p < .5 else 1-phase)
    return finish(out, a, b)
