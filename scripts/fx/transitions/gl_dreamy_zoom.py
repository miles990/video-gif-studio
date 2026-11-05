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


@register_transition(name='gl_dreamy_zoom', status='stable', style_tags=['夢幻', '搶眼/衝擊', '閃白'], rotation='rotation; GLSL float, default 6', scale='scale; GLSL float, default 1.2')
def transition(a, b, p, ctx, rotation=6.0, scale=1.2):
    """Zooms and rotates into a bright flash, then out to the incoming image."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    positive(scale, 'scale')
    if not s.opaque and .45 < p < .55:
        # Keep both silhouettes present through the white interval. Each shot
        # follows its own transform up to/from the midpoint, so neither its
        # coverage nor its rotation switches discontinuously at p=.5.
        shots = []
        for source, amount, sign in ((s.a,min(2*p,1),1),
                                     (s.b,min(2*(1-p),1),-1)):
            angle = sign*rotation*amount*.039269908169872415
            zoom = mix(1,scale,amount)
            dx,dy = (x-.5)*s.ratio/zoom,(y-.5)/zoom
            u = (np.cos(angle)*dx-np.sin(angle)*dy)/s.ratio+.5
            v = np.sin(angle)*dx+np.cos(angle)*dy+.5
            shot = s.sample(source,u,v)
            shot[...,:3] = np.minimum(shot[...,:3]+shot[...,3:4]*amount,shot[...,3:4])
            shots.append(shot)
        return s.finish(mix(shots[0],shots[1],smooth(.45,.55,p)), displacement=True)
    phase = p*2 if p < .5 else (p-.5)*2
    # Preserve the upstream constant (despite its misleading DEG2RAD comment).
    angle = (rotation*phase if p < .5 else -rotation*(1-phase))*.039269908169872415
    zoom = mix(1, scale, phase) if p < .5 else mix(scale, 1, phase)
    dx, dy = (x-.5)*s.ratio/zoom, (y-.5)/zoom
    u = (np.cos(angle)*dx-np.sin(angle)*dy)/s.ratio+.5
    v = np.sin(angle)*dx+np.cos(angle)*dy+.5
    out = s.sample(s.a if p < .5 else s.b, u, v)
    out[..., :3] += out[..., 3:4] * (phase if p < .5 else 1-phase)
    return s.finish(out, displacement=True)
