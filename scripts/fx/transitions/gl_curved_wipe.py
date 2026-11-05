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


@register_transition(name='gl_curved_wipe', status='stable', style_tags=['幾何', '含蓄/柔和'], direction='@param Direction the edge moves toward; GLSL vec2, default vec2(0.0, 1.0)', curvature='@range(0, 1) How far the middle of the edge leads its sides; GLSL float, default 0.6', smoothness='@range(0, 0.2) Softness of the edge; GLSL float, default 0.02', shadow='@color Color of the soft shadow the lifted edge casts on the incoming image (its alpha is its strength; 0 for none); GLSL vec4, default vec4(0.0, 0.0, 0.0, 0.4)')
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
    out = s.blend(m)
    distance = np.maximum(edge-d,0)
    falloff = .012+.25*(edge-side)
    # Below 1/65535 contribution is less than a uint8 level. Only the shading
    # band needs an exponential, a caster lookup and a three-channel tint.
    band = (m>0) & (distance<11.1*falloff) & (s.b[...,3]>0)
    if color[3] and np.any(band):
        caster_alpha=1
        if not s.opaque:
            u=((dx+(edge-d)*v[0])/s.ratio+.5)[band]
            vmap=(dy+(edge-d)*v[1]+.5)[band]
            count=len(u);pad=(-count)%1024
            u=np.pad(u,(0,pad),mode='edge').reshape(-1,1024)
            vmap=np.pad(vmap,(0,pad),mode='edge').reshape(-1,1024)
            caster_alpha=s.sample(s.a,u,vmap)[...,3].ravel()[:count]
        sh=color[3]*np.sin(np.pi*p)*np.exp(-distance[band]/falloff[band])*m[band]*caster_alpha*s.b[...,3][band]
        # out already includes B*m; add only the shadow's associated-color delta.
        out[band,:3] += (color[:3]*s.b[band,3:4]-s.b[band,:3])*(sh*m[band])[:,None]
    return s.finish(out)
