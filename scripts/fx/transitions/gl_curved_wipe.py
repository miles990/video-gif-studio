"""CurvedWipe — The outgoing image is pulled away by its middle: the wipe edge bulges into a smooth curve that leads the way, then flattens as it reaches the far side

Author: gre
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/CurvedWipe.glsl
SHA256: cd20a2628f20c0e5b889146d4caa6315dbc99e903331f4edffc628bcd78678ff
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_curved_wipe', status='experimental', direction='@param Direction the edge moves toward; GLSL vec2, default vec2(0.0, 1.0)', curvature='@range(0, 1) How far the middle of the edge leads its sides; GLSL float, default 0.6', smoothness='@range(0, 0.2) Softness of the edge; GLSL float, default 0.02', shadow='@color Color of the soft shadow the lifted edge casts on the incoming image (its alpha is its strength; 0 for none); GLSL vec4, default vec4(0.0, 0.0, 0.0, 0.4)')
def transition(a, b, p, ctx, direction=(0.0, 1.0), curvature=0.6, smoothness=0.02, shadow=(0.0, 0.0, 0.0, 0.4)):
    """The outgoing image is pulled away by its middle: the wipe edge bulges into a smooth curve that leads the way, then flattens as it reaches the far side."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    v = direction_vector(direction,(0,1)); color = vector(shadow,4,'shadow')
    dx,dy = (x-.5)*s.ratio,y-.5
    e = .5*(abs(v[0])*s.ratio+abs(v[1])); w = .5*(abs(v[1])*s.ratio+abs(v[0]))
    d = dx*v[0]+dy*v[1]; across = np.clip((-dx*v[1]+dy*v[0])/w,-1,1)
    soft = max(smoothness,.001)
    k = np.clip(curvature,0,1)*min(1,w/e)*(1-across*across)
    t = p+k*p*(1-p)
    ease = lambda t: .5*(t+t*t*(3-2*t))
    edge = -e-soft+2*(e+soft)*ease(t)
    side = -e-soft+2*(e+soft)*ease(p)
    m = 1-smooth(-soft,soft,d-edge)
    caster = s.sample(s.a,(dx+(edge-d)*v[0])/s.ratio+.5,dy+(edge-d)*v[1]+.5)
    sh = color[3]*np.sin(np.pi*p)*np.exp(-np.maximum(edge-d,0)/(.012+.25*(edge-side)))*m*caster[...,3]*s.b[...,3]
    to = s.b.copy(); to[...,:3] = mix(to[...,:3],color[:3]*to[...,3:4],sh)
    out = mix(s.a,to,m)
    return finish(out, a, b)
