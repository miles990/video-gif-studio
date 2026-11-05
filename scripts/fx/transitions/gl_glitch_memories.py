"""GlitchMemories — A crossfade with glitchy, color-shifted blocks

Author: Gunnar Roth
License: MIT; full notice and author list: THIRD_PARTY.md, gl-transitions.
Source: gl-transitions/transitions/GlitchMemories.glsl
SHA256: 95ac53da9e6db7efc350ea26cbfb71e9ee7ec2a23d68b044cb9fa41c1118b407
CPU adaptations: see references/fx.md (P2b gl-transitions).
"""
import numpy as np
from ..core import transition as register_transition
from .gl_common import (Shader, finish, mix, smooth, fract, vector, positive,
                        direction_vector, random_field, noise)


@register_transition(name='gl_glitch_memories', status='experimental')
def transition(a, b, p, ctx):
    """A crossfade with glitchy, color-shifted blocks."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    # Keep the shader's normalized block / 16 formula, not a guessed pixel-space fix.
    bx, by = np.floor(x/16)/64, np.floor(y/16)/64
    dx = (fract(bx+np.floor(p*1200)/64)-.5)*.3*(1-p)
    dy = (fract(by+np.floor(p*3500)/64)-.5)*.3*(1-p)
    out = s.warped(x+dx*.3,y+dy*.3,x+dx*.3,y+dy*.3,p)
    red = s.warped(x+dx*.2,y+dy*.2,x+dx*.2,y+dy*.2,p)
    blue = s.warped(x+dx*.5,y+dy*.5,x+dx*.5,y+dy*.5,p)
    # Samples remain premultiplied; never divide using a different channel's alpha.
    out[...,0] = red[...,0]; out[...,2] = blue[...,2]
    return finish(out, a, b)
