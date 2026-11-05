"""Transitions are output-clock operations; p=0 and p=1 are exact endpoints."""
import cv2
import numpy as np
from ..core import transition, premultiply, straight, warp
from ..masks import field, reveal
from ..effects.accents import transform


def masked(a,b,mask):
    return straight(premultiply(a)*(1-mask[...,None])+premultiply(b)*mask[...,None])


@transition(status='experimental',shape='circle, diamond, star or heart',softness='Soft edge width in pixels')
def shape_wipe(a,b,p,ctx,shape='circle',softness=0.0):
    """Centered expanding shape; progress measures revealed area, not radius."""
    if p<=0:return a
    if p>=1:return b
    return masked(a,b,reveal(field(ctx.width,ctx.height,shape),p,softness))


@transition(status='experimental',mask='linear, radial, cloud, or grayscale image path',invert='Reverse reveal order')
def luma_wipe(a,b,p,ctx,mask='linear',invert=False,softness=12.0,seed=7.0):
    """Reveal in mask luminance order; procedural masks need no asset files."""
    if p<=0:return a
    if p>=1:return b
    value=field(ctx.width,ctx.height,mask,int(seed));value=-value if invert else value
    return masked(a,b,reveal(value,p,softness))


def moving(a,b,p,ctx,direction,slide=False):
    if p<=0:return a
    if p>=1:return b
    vectors={'left':(-ctx.width,0),'right':(ctx.width,0),'up':(0,-ctx.height),'down':(0,ctx.height)}
    dx,dy=vectors[direction];mode=cv2.INTER_NEAREST if ctx.sampling=='nearest' else cv2.INTER_LINEAR
    left=premultiply(a) if slide else cv2.warpAffine(premultiply(a),np.float32([[1,0,dx*p],[0,1,dy*p]]),(ctx.width,ctx.height),flags=mode)
    right=cv2.warpAffine(premultiply(b),np.float32([[1,0,-dx*(1-p)],[0,1,-dy*(1-p)]]),(ctx.width,ctx.height),flags=mode)
    # Push tiles adjacent shots: their fractional edge coverages are complementary.
    # Alpha-over would attenuate that shared edge twice and leave a transparent seam.
    return straight(right+left*(1-right[...,3:4]) if slide else right+left)


@transition(status='experimental',direction='left, right, up or down')
def push(a,b,p,ctx,direction='left'):
    """Both shots move together across the same straight boundary."""
    return moving(a,b,p,ctx,direction)


@transition(status='experimental',direction='left, right, up or down')
def slide(a,b,p,ctx,direction='left'):
    """Incoming shot covers the stationary outgoing shot."""
    return moving(a,b,p,ctx,direction,True)


@transition(status='stable', style_tags=['旋轉', '衝擊'], turns='Rotation turns at midpoint')
def spin(a,b,p,ctx,turns=.25):
    """Rotate with analytic cover zoom, so corners never sample reflected content."""
    if p<=0:return a
    if p>=1:return b
    angle=360*turns*np.sin(np.pi*p);r=np.deg2rad(angle)
    cover=max(abs(np.cos(r))+ctx.height/ctx.width*abs(np.sin(r)),abs(np.cos(r))+ctx.width/ctx.height*abs(np.sin(r)))
    source=a if p<.5 else b
    scale=max(1+.15*np.sin(np.pi*p),cover+np.sin(np.pi*p)/min(ctx.width,ctx.height)) if np.all(source[...,3]==1) else 1
    matrix=cv2.getRotationMatrix2D(((ctx.width-1)/2,(ctx.height-1)/2),angle,scale)
    return warp(source,matrix,ctx)


@transition(status='experimental',scale='Peak camera scale')
def zoom_through(a,b,p,ctx,scale=1.8):
    """Centered zoom into the cut and back out; reflected edges maintain coverage."""
    if p<=0:return a
    if p>=1:return b
    return transform(a if p<.5 else b,ctx,scale=1+(scale-1)*np.sin(np.pi*p))


@transition(status='experimental',seed='Deterministic animated block pattern',amount='Displacement strength')
def glitch(a,b,p,ctx,seed=7.0,amount=1.0):
    """Brief block displacement and alternating scanlines, with unchanged endpoints."""
    if p<=0:return a
    if p>=1:return b
    rng=np.random.default_rng(int(seed)+ctx.seed+int(p*1000));source=a if p<.5 else b
    y,x=np.indices(source.shape[:2],dtype=np.float32);blocks=rng.integers(-25,26,max(1,ctx.height//8+1))
    x+=blocks[(y//8).astype(int)]*amount*np.sin(np.pi*p)
    out=straight(cv2.remap(premultiply(source),x,y,cv2.INTER_NEAREST,borderMode=cv2.BORDER_WRAP))
    if ctx.sampling!='nearest': out[::2,:,:3]*=1-.2*amount*np.sin(np.pi*p)
    return out
