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


@register_transition(name='gl_glitch_memories', status='stable', style_tags=['故障', '搶眼/衝擊'])
def transition(a, b, p, ctx):
    """A crossfade with glitchy, color-shifted blocks."""
    if p <= 0:
        return a
    if p >= 1:
        return b
    s = Shader(a, b, ctx)
    x, y = s.x, s.y
    # Explicit CPU adaptation: pixel-space blocks replace upstream floor(UV/16)
    # (identically zero). One coherent RGBA offset avoids channel/alpha mismatch.
    # Blending commutes with this shared linear sample, so sample only once.
    bx, by = np.meshgrid(np.arange((ctx.width+15)//16),np.arange((ctx.height+15)//16))
    envelope = .045*np.sin(np.pi*p)
    dx = (random_field(bx,by,ctx.seed+int(p*24))-.5)*envelope
    dy = (random_field(bx,by,ctx.seed+41+int(p*24))-.5)*envelope
    # Clamp the translation of the entire block, including partial edge cells.
    # Per-pixel UV clipping repeats the border texel into a streak instead.
    dx = np.clip(dx, -bx*16/ctx.height,
                 (ctx.width-np.minimum((bx+1)*16,ctx.width))/ctx.height)
    dy = np.clip(dy, -by*16/ctx.height,
                 (ctx.height-np.minimum((by+1)*16,ctx.height))/ctx.height)
    ix=np.arange(ctx.width)//16;iy=(ctx.height-1-np.arange(ctx.height))//16
    dx=dx[iy[:,None],ix];dy=dy[iy[:,None],ix]
    out = s.sample(s.blend(p),x+dx/s.ratio,y+dy)
    return s.finish(out, displacement=True)
