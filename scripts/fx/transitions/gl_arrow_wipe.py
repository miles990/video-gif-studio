"""ArrowWipe — A notched arrowhead window onto the incoming image flies in from the edge behind it (or appears at the center), then swells until it fills the frame

Author: gre
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/ArrowWipe.glsl
SHA256: 6050006ea0ef726fffb05171a29f227bfb87dd662717a7e232217959ccfa4423
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_arrow_wipe', status='stable', style_tags=['幾何', '搶眼'], direction='@param Direction the arrow points and flies toward; GLSL vec2, default vec2(1.0, 0.0)', notch='@range(0, 0.9) Depth of the notch at the back of the arrowhead (0 for a plain triangle); GLSL float, default 0.4', width="@range(20, 160) Opening angle of the arrowhead's tip, in degrees; GLSL float, default 80.0", count='@range(1, 3, 1) Number of nested chevrons flying in a row; GLSL int, default 1', origin='@param Grow the arrow from the center of the frame instead of flying it in; GLSL bool, default false', smoothness="@range(0, 0.1) Softness of the arrow's edges; GLSL float, default 0.004")
def transition(a, b, p, ctx, direction=(1.0, 0.0), notch=0.4, width=80.0, count=1, origin=False, smoothness=0.004):
    """A notched arrowhead window onto the incoming image flies in from the edge behind it (or appears at the center), then swells until it fills the frame."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    v = direction_vector(direction); across = np.array([-v[1],v[0]])
    dx,dy = (x-.5)*s.ratio,y-.5
    qx,qy = dx*v[0]+dy*v[1],np.abs(dx*across[0]+dy*across[1])
    soft = max(smoothness,.001); n = np.clip(notch,0,.9)
    h = np.deg2rad(.5*np.clip(width,20,160)); cot = np.cos(h)/np.sin(h)
    notch_len = np.hypot(1,n*cot); pad = soft/np.sin(h)
    c1,c2 = np.array([s.ratio*.5,.5]),np.array([s.ratio*.5,-.5])
    k1,k2 = (abs(c1@v),abs(c1@across)),(abs(c2@v),abs(c2@across))
    e = max(k1[0],k2[0]); r = .5/max(abs(v[0])/s.ratio,abs(v[1]))
    tip = max(k1[0]+k1[1]*cot,k2[0]+k2[1]*cot)+pad
    back = min(n*cot*k1[1]-k1[0],n*cot*k2[1]-k2[0],-r)-soft*notch_len
    body = .5*(1-n); cover = max(tip,-back)/body
    if origin:
        o,l = 0,cover*p*(.4+.6*p)
    else:
        l0 = .92*min(1,s.ratio)/max(1,2*np.tan(h))
        fly = 1-(1-np.clip(p/.65,0,1))**3; grow = np.clip((p-.3)/.7,0,1)
        o = (-e-2*pad-body*l0)*(1-fly); l = mix(l0,cover,grow*grow*(2-grow))
    def arrow(mid):
        return np.maximum((qx-mid-body*l)*np.sin(h)+qy*np.cos(h),
                          ((mid-body*l-qx)-qy*n*cot)/notch_len)
    d = arrow(o)
    for index in range(1, min(max(int(count),1),3)):
        d = np.minimum(d,arrow(o-index*(1-n)*1.35*l))
    out = s.blend(1-smooth(-soft,soft,d+2*soft*(1-p)))
    return s.finish(out)
