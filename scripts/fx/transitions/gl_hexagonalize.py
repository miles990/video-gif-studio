"""Hexagonalize — Both images turn into hexagons, crossfade, then sharpen again

Author: Fernando Kuteken
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/Hexagonalize.glsl
SHA256: abcac2efc147d397875a233ad010d72b03986237f0955ae2b18a214987d75c08
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_hexagonalize', status='stable', style_tags=['幾何', '數位'], steps='steps; GLSL int, default 50', horizontalHexagons='@param Number of hexagons across; GLSL float, default 20')
def transition(a, b, p, ctx, steps=50, horizontalHexagons=20.0):
    """Both images turn into hexagons, crossfade, then sharpen again."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    positive(horizontalHexagons,'horizontalHexagons')
    dist = 2*min(p,1-p)
    if steps>0: dist = np.ceil(dist*steps)/steps
    size = np.sqrt(3)/3*dist/horizontalHexagons
    px, py = (x-.5)/size,(y/s.ratio-.5)/size
    q, r = np.sqrt(3)/3*px-py/3,2*py/3
    z = -q-r
    rq, rr, rz = np.floor(q+.5),np.floor(r+.5),np.floor(z+.5)
    dq, dr, dz = np.abs(rq-q),np.abs(rr-r),np.abs(rz-z)
    mq = (dq>dr)&(dq>dz); mr = (~mq)&(dr>dz)
    rq = np.where(mq,-rr-rz,rq); rr = np.where(mr,-rq-rz,rr)
    u = (np.sqrt(3)*rq+np.sqrt(3)/2*rr)*size+.5
    v = (1.5*rr*size+.5)*s.ratio
    out = s.warped(u,v,u,v,p)
    if steps>0 and 2*min(p,1-p)*steps<1:
        out=mix(s.blend(p),out,2*min(p,1-p)*steps)
    return s.finish(out, displacement=True)
