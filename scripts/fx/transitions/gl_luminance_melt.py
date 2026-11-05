"""LuminanceMelt — The outgoing image melts away in noisy vertical streaks, depending on its brightness

Author: 0gust1
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/LuminanceMelt.glsl
SHA256: 3980732a493577b250f8c5ff5fe38b3aad7af6fda8c2d67ef5abf974affa99a0
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_luminance_melt', status='stable', style_tags=['故障', '有機'], direction='@param Direction of the melt (false: up, true: down); GLSL bool, default true', l_threshold='@range(0, 1) Luminance threshold; GLSL float, default 0.8', above='@param Melt the parts above the threshold instead of below; GLSL bool, default false')
def transition(a, b, p, ctx, direction=True, l_threshold=0.8, above=False):
    """The outgoing image melts away in noisy vertical streaks, depending on its brightness."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    # Ashima Arts / Ian McEwan's MIT 2D simplex function, evaluated at (x, 0).
    # Copyright (c) 2011 Ashima Arts. Based also on pthrasher's Crosshatch.
    c1, c2, c3, c4 = .211324865405187, .366025403784439, -.577350269189626, .024390243902439
    # The shader's noise is a function of x only. Evaluate one row and broadcast;
    # this is exact, and avoids repeating the simplex calculation for every row.
    vx = x[:1] + ctx.seed*.754877666
    ix, iy = np.floor(vx+vx*c2), np.floor(vx*c2)
    x0, y0 = vx-ix+(ix+iy)*c1, -iy+(ix+iy)*c1
    i1x = (x0>y0).astype(np.float32); i1y = 1-i1x
    def permute(t):
        return (((t*34)+1)*t)%289
    n = np.zeros_like(vx)
    for ox, oy, gx, gy in ((0,0,x0,y0),(i1x,i1y,x0+c1-i1x,y0+c1-i1y),(1,1,x0+c3,y0+c3)):
        hsh = permute(permute(iy%289+oy)+ix%289+ox)
        grad = 2*fract(hsh*c4)-1
        h = np.abs(grad)-.5; a0 = grad-np.floor(grad+.5)
        m = np.maximum(.5-gx*gx-gy*gy, 0)**4
        m *= 1.79284291400159-.85373472095314*(a0*a0+h*h)
        n += m*(a0*gx+h*gy)
    dist = np.hypot((1-x)*s.ratio, float(direction)-y)-p*np.exp(130*n)
    r = p-random_field(x[:1],.1,ctx.seed)
    luma = s.a[..., :3]@np.array([.299,.587,.114],np.float32)
    eligible = luma>l_threshold if above else luma<l_threshold
    out = s.blend(np.where((dist<=r)&eligible, 1, p**3))
    return s.finish(out)
