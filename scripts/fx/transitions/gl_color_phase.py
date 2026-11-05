"""ColorPhase — A crossfade in which each color channel changes at a different time

Author: gre
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/ColorPhase.glsl
SHA256: 464c552944723e9d62bcd0bdcaeca67523e4b7c85a3a5591bc062e0056a5fd34
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_color_phase', status='stable', style_tags=['迷幻', '色彩', '復古'], fromStep='@range(0, 1) When each channel (r, g, b, a) starts changing; GLSL vec4, default vec4(0.0, 0.2, 0.4, 0.0)', toStep='@range(0, 1) When each channel (r, g, b, a) finishes changing; GLSL vec4, default vec4(0.6, 0.8, 1.0, 1.0)')
def transition(a, b, p, ctx, fromStep=(0.0, 0.2, 0.4, 0.0), toStep=(0.6, 0.8, 1.0, 1.0)):
    """A crossfade in which each color channel changes at a different time."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    lo, hi = vector(fromStep,4,'fromStep'),vector(toStep,4,'toStep')
    if np.any(lo>=hi): raise ValueError('fromStep must precede toStep in every channel')
    phase = smooth(lo,hi,p)
    if s.opaque:
        out = mix(s.a,s.b,phase)
    else:
        aa, ab = a[...,3:4], b[...,3:4]
        # Cross-fill missing colours from the visible source, never hidden RGB.
        ca = np.where(aa>0,a[...,:3],np.where(ab>0,b[...,:3],0))
        cb = np.where(ab>0,b[...,:3],ca)
        out = np.empty_like(a)
        out[...,3:4] = aa*(1-phase[3])+ab*phase[3]
        out[...,:3] = mix(ca,cb,phase[:3])*out[...,3:4]
    return s.finish(out)
