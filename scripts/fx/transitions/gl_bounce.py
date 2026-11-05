"""Bounce — The outgoing image drops out of the frame with a few bounces, revealing the incoming one

Author: Adrian Purser
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/Bounce.glsl
SHA256: cd741e187f79e905e8221225d5350eff6c87004b94c111e039643d9dae497dcd
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_bounce', status='stable', style_tags=['俏皮', '衝擊'], shadow_colour='@color Color of the shadow cast on the incoming image; GLSL vec4, default vec4(0.,0.,0.,.6)', shadow_height='@range(0.01, 0.5) Height of the shadow, relative to the image height; GLSL float, default 0.075', bounces='@range(1, 10, 1) Number of bounces before settling; GLSL float, default 3.0')
def transition(a, b, p, ctx, shadow_colour=(0.0, 0.0, 0.0, 0.6), shadow_height=0.075, bounces=3.0):
    """The outgoing image drops out of the frame with a few bounces, revealing the incoming one."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    color = vector(shadow_colour,4,'shadow_colour'); positive(shadow_height,'shadow_height')
    edge = abs(np.cos(p*np.pi*bounces))*(1-np.sin(p*np.pi/2))
    d = y-edge
    strength = ((d>0)&(d<=shadow_height))*(1-mix((d/shadow_height)*color[3]+1-color[3],1,smooth(.95,1,p)))
    strength = np.clip(strength,0,1)*s.b[...,3]
    out = s.b.copy()
    out[...,:3] = mix(out[...,:3],color[:3]*out[...,3:4],strength)
    # Reveal B only where the panel has left, including for sparse RGBA. Showing
    # B through the panel's transparent pixels would jump at p=0+.
    out *= (d>0)[...,None]
    panel = s.sample(s.a,x,y+1-edge) * (d<=0)[...,None]
    out += panel
    return s.finish(out, displacement=True)
