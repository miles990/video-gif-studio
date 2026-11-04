"""Procedural texture and graphic treatments, with no external bitmap dependencies."""
import cv2
import numpy as np
from ..core import effect, premultiply, straight, over, warp
from .cutout_card import cutout_card


def grid(ctx):
    return np.indices((ctx.height,ctx.width),dtype=np.float32)


@effect(status='experimental',amount='Noise standard deviation in 0..1',seed='Stable seed')
def film_grain(frame,t,ctx,amount=.025,seed=17.0):
    """Zero-mean moving monochrome film grain; exact original alpha."""
    rng=np.random.default_rng(int(seed)+ctx.seed+int(t*ctx.fps/1000))
    noise=rng.standard_normal(frame.shape[:2],dtype=np.float32)*amount
    frame[...,:3]+=noise[...,None]*(frame[...,3:4]>0)
    return frame


@effect(status='experimental',amount='Corner darkness')
def vignette(frame,t,ctx,amount=.55):
    """Smooth radial falloff with untouched image center."""
    y,x=grid(ctx);r=((x-(ctx.width-1)/2)/(ctx.width/2))**2+((y-(ctx.height-1)/2)/(ctx.height/2))**2
    frame[...,:3]*=(1-amount*np.clip((r-.1)/1.9,0,1))[...,None]
    return frame


@effect(status='experimental',amount='Warm edge exposure gain',seed='Drift phase')
def light_leak(frame,t,ctx,amount=.4,seed=3.0):
    """A broad amber edge leak drifting on a seconds clock."""
    y,x=grid(ctx);phase=t/1000+seed*.3
    center=.78+.2*np.sin(phase);light=np.exp(-((x/ctx.width-center)/.3)**2-((y/ctx.height-(.5+.3*np.cos(phase)))/.85)**2)
    frame[...,:3]+=light[...,None]*np.float32([1,.32,.05])*amount
    return frame


@effect(status='experimental',amount='Scratch opacity',seed='Moving pattern seed',density='Dust coverage fraction, capped below five percent')
def dust_scratches(frame,t,ctx,amount=.5,seed=29.0,density=.02):
    """Sparse dust flecks and fine scratches covering less than five percent."""
    rng=np.random.default_rng(int(seed)+ctx.seed+int(t*ctx.fps/1000));mask=(rng.random(frame.shape[:2],dtype=np.float32)<min(.04,max(0,density))).astype(np.float32)
    for _ in range(12):
        x,y=rng.integers(0,ctx.width),rng.integers(0,ctx.height)
        cv2.circle(mask,(int(x),int(y)),1,1,-1)
    x=int(rng.integers(ctx.width));mask[:,x]=.5
    frame[...,:3]+=(1-frame[...,:3])*mask[...,None]*amount
    return frame


@effect(status='experimental')
def invert_flash(frame,t,ctx,amount=1.0):
    """Beat-driven photographic negative with unchanged coverage."""
    frame[...,:3]+=(1-2*frame[...,:3])*amount
    return frame


@effect(status='experimental')
def black_flash(frame,t,ctx,amount=1.0):
    """Beat-driven dip to black with unchanged coverage."""
    frame[...,:3]*=1-amount
    return frame


@effect(status='experimental',panels='0: automatic 1,2,4 on successive beats; or 1,2,4',amount='0 identity, positive enables layout')
def split_screen(frame,t,ctx,amount=1.0,panels=0.0):
    """Resize the entire source into two columns or four synchronized quadrants."""
    if amount==0:return frame
    count=round(panels) or (1,2,4)[min(2,max(0,sum(b<=t for b in ctx.beats_ms)-1))]
    if count<=1:return frame
    cols,rows=2,2 if count>=4 else 1
    small=cv2.resize(premultiply(frame),(ctx.width//cols,ctx.height//rows),interpolation=cv2.INTER_NEAREST if ctx.sampling=='nearest' else cv2.INTER_LINEAR)
    return straight(cv2.resize(np.tile(small,(rows,cols,1)),(ctx.width,ctx.height),interpolation=cv2.INTER_NEAREST))


@effect(status='experimental',direction='horizontal or vertical',amount='0 identity, positive enables reflection')
def mirror(frame,t,ctx,amount=1.0,direction='horizontal'):
    """Reflect the left or upper half into the other half."""
    if amount==0:return frame
    if direction=='horizontal':frame[:,ctx.width//2:]=frame[:,:ctx.width-ctx.width//2][:,::-1]
    else:frame[ctx.height//2:]=frame[:ctx.height-ctx.height//2][::-1]
    return frame


@effect(status='experimental',sectors='Rotational sectors',amount='0 identity, positive enables geometry')
def kaleidoscope(frame,t,ctx,amount=1.0,sectors=6.0):
    """Fold polar angles into repeating mirrored wedges."""
    if amount==0:return frame
    y,x=grid(ctx);x-=(ctx.width-1)/2;y-=(ctx.height-1)/2
    r=np.hypot(x,y);period=2*np.pi/max(2,round(sectors));angle=np.abs((np.arctan2(y,x)+period/2)%period-period/2)
    mx=(ctx.width-1)/2+r*np.cos(angle);my=(ctx.height-1)/2+r*np.sin(angle)
    return straight(cv2.remap(premultiply(frame),mx,my,cv2.INTER_NEAREST if ctx.sampling=='nearest' else cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101))


@effect(status='experimental',levels='Quantization levels per channel')
def posterize(frame,t,ctx,amount=1.0,levels=4.0):
    """Discrete color platforms, blended by amount."""
    n=max(2,round(levels))-1;frame[...,:3]+=(np.rint(frame[...,:3]*n)/n-frame[...,:3])*amount
    return frame


@effect(status='experimental',size='Ordered screen cell size in pixels')
def halftone(frame,t,ctx,amount=1.0,size=8.0):
    """Clustered-dot monochrome screen preserving local mean luminance."""
    y,x=grid(ctx);s=max(2,round(size));r=((x%s+.5)/s-.5)**2+((y%s+.5)/s-.5)**2
    order=np.argsort(np.argsort(r[:s,:s].ravel())).reshape(s,s)/(s*s)
    threshold=np.tile(order,(int(np.ceil(ctx.height/s)),int(np.ceil(ctx.width/s))))[:ctx.height,:ctx.width]
    gray=cv2.cvtColor(frame[...,:3],cv2.COLOR_RGB2GRAY);ink=(gray>threshold).astype(np.float32)
    frame[...,:3]+=(ink[...,None]-frame[...,:3])*amount
    return frame


@effect(status='experimental',distance='Separation between the three overlapping silhouette cards')
def multi_cutout(frame,t,ctx,amount=1.0,distance=65.0,border_px=6.0):
    """Three explicitly overlapping white-outline cards; the original is in front."""
    if amount==0:return frame
    card=premultiply(cutout_card(frame,t,ctx,border_px=border_px));result=np.zeros_like(frame)
    for dx,dy in ((-distance,8),(distance,-8),(0,0)):
        moved=cv2.warpAffine(card,np.float32([[1,0,dx*amount],[0,1,dy*amount]]),(ctx.width,ctx.height),flags=cv2.INTER_NEAREST if ctx.sampling=='nearest' else cv2.INTER_LINEAR)
        channels=cv2.split(result);alpha=1-moved[...,3]
        result=cv2.add(moved,cv2.merge([cv2.multiply(c,alpha) for c in channels]))
    return straight(result)
