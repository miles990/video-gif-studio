"""BowTieHorizontal — Two triangles grow from the left and right edges into a bow tie that reveals the incoming image

Author: huynx
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/BowTieHorizontal.glsl
SHA256: fcd134626185864b9c9dd0eb7d713f367e63afc445ace442ace6849a4700ec59
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_bow_tie_horizontal', status='stable', style_tags=['幾何', '俐落'])
def transition(a, b, p, ctx):
    """Two triangles grow from the left and right edges into a bow tie that reveals the incoming image."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    dy = np.abs(y-.5)
    left, right = dy+x<=p,dy+1-x<=p
    # Exact distance to either sloping triangle edge (slope +/- 1).
    left_blur = np.clip((p-x-dy)/np.sqrt(2)/.005,0,1)
    right_blur = np.clip((p-(1-x)-dy)/np.sqrt(2)/.005,0,1)
    m = np.where(left,np.where(p<.1,0,np.where(x<.5,left_blur,1)),
                 np.where(right & (x>=.5),right_blur,0))
    out = s.blend(m)
    return s.finish(out)
