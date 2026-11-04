"""Small deterministic accents; random state is derived from seed and output time."""
import cv2
import numpy as np
from ..core import effect, premultiply, straight, evaluate


def transform(frame,ctx,angle=0,scale=1,dx=0,dy=0):
    matrix=cv2.getRotationMatrix2D(((ctx.width-1)/2,(ctx.height-1)/2),angle,scale)
    matrix[:,2]+=(dx,dy)
    return straight(cv2.warpAffine(premultiply(frame),matrix,(ctx.width,ctx.height),
        flags=cv2.INTER_NEAREST if ctx.sampling=='nearest' else cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101))


@effect(amount='Strength; built-in 220ms beat decay',distance='Peak translation px',seed='Stable shake seed')
def shake(frame,t,ctx,amount=1.0,distance=9.0,seed=7.0):
    """Beat-decaying camera shake, doubled on downbeats; reflected edges fill canvas."""
    pulse=evaluate({'on':'beats','decay_ms':220},t,ctx) if ctx.beats_ms else 1
    strong=2 if any(0<=t-b<220 for b in ctx.downbeats_ms) else 1
    # Keep one direction through each decay: frame-random directions can create
    # a larger secondary impact after the beat instead of on the beat itself.
    phase=max(0,sum(b<=t for b in ctx.beats_ms)-1) if ctx.beats_ms else int(t*ctx.fps/1000)
    rng=np.random.default_rng(int(seed)+ctx.seed+phase)
    angle=rng.uniform(0,2*np.pi);d=distance*amount*pulse*strong
    return transform(frame,ctx,dx=d*np.cos(angle),dy=d*np.sin(angle))


@effect(distance='R +distance, B -distance in pixels',direction='Degrees: 0 horizontal, 90 vertical')
def rgb_split(frame,t,ctx,amount=1.0,distance=6.0,direction=0.0):
    """Chromatic offset; original alpha and green retained; hidden RGB excluded."""
    if amount==0:return frame
    dx,dy=np.cos(np.deg2rad(direction))*distance*amount,np.sin(np.deg2rad(direction))*distance*amount
    rgba=premultiply(frame);out=frame.copy()
    for channel,sign in ((0,1),(2,-1)):
        shifted=cv2.warpAffine(rgba,np.float32([[1,0,dx*sign],[0,1,dy*sign]]),(ctx.width,ctx.height),borderMode=cv2.BORDER_REFLECT_101)
        color=cv2.divide(shifted[...,channel],cv2.max(shifted[...,3],1e-8))
        out[...,channel]=np.where(shifted[...,3]>.001,color,frame[...,channel])
    return out


@effect(distance='Radial integration length, fraction of radius',samples='Integration samples')
def radial_blur(frame,t,ctx,amount=1.0,distance=.22,samples=12.0):
    """Zoom-direction blur preserves spokes and softens concentric rings."""
    if amount==0:return frame
    result=np.zeros_like(frame);source=premultiply(frame);count=max(2,round(samples))
    for scale in np.linspace(1-distance*amount/2,1+distance*amount/2,max(2,round(samples))):
        matrix=cv2.getRotationMatrix2D(((ctx.width-1)/2,(ctx.height-1)/2),0,scale)
        moved=cv2.warpAffine(source,matrix,(ctx.width,ctx.height),flags=cv2.INTER_NEAREST if ctx.sampling=='nearest' else cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
        cv2.addWeighted(result,1,moved,1/count,0,dst=result)
    result=straight(result);cy,cx=ctx.height//2,ctx.width//2
    result[cy-1:cy+2,cx-1:cx+2]=frame[cy-1:cy+2,cx-1:cx+2]
    return result


@effect(history=4,decay='Older echoes decay geometrically',amount='Trail strength')
def echo(frame,t,ctx,amount=.65,decay=.55):
    """Lighten premultiplied trails, newest first, without dimming current pixels."""
    result=premultiply(frame)
    for age,old in enumerate(ctx.history[:4]):
        ghost=premultiply(old)*amount*decay**age
        result=np.maximum(result,ghost)
    return straight(result)
