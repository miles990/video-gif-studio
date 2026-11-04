"""Experimental named moves using Robert Penner BSD easing (see ../easing.py)."""
import cv2
import numpy as np
from ..core import effect, warp, premultiply, straight
from ..easing import EASINGS, spring

MOVES = {
    'crash_in': (100, 'easeOutExpo', 1.35),
    'crash_out': (100, 'easeOutExpo', 1.35),
    'expo_in': (800, 'easeInExpo', 1.3),
    'smooth_in': (1000, 'easeInOutCubic', 1.2),
    'whip': (160, 'easeInOutCubic', 1.0),
    'punch': (200, 'easeOutCubic', 1.18),
    'drift': (2000, 'easeInOutSine', 1.08),
    'spring_in': (700, 'spring', 1.2),
}


def motion(move, elapsed_ms, duration_ms=0, target=0, stiffness=180, damping=18, mass=1):
    if move not in MOVES: raise ValueError('move: choose '+', '.join(MOVES))
    duration, easing, default = MOVES[move]
    duration = duration_ms or duration; target = target or default
    if duration <= 0 or target <= 0: raise ValueError('camera duration and target must be positive')
    p = min(1, max(0, elapsed_ms/duration))
    v = spring(max(0, elapsed_ms)/1000, stiffness, damping, mass) if easing == 'spring' else EASINGS[easing](p)
    if move == 'crash_out':
        # Prepare the zoom from the incoming framing, then reveal. No discontinuity
        # on the first frame; the last 70% is the fast exponential zoom-out.
        amount=EASINGS['easeInOutCubic'](p/.3) if p<.3 else 1-EASINGS['easeOutExpo']((p-.3)/.7)
        return 1+(target-1)*amount, 0
    if move == 'punch': return 1+(target-1)*np.sin(np.pi*p)**2, 0
    if move == 'whip': return 1, 0.0 if p in (0,1) else .85*np.sin(np.pi*p)**2
    if move == 'drift': return 1+(target-1)*v, .04*v
    return 1+(target-1)*v, 0


def whip_peak_ms(duration_ms=0, fps=30):
    """First maximum displacement between delivered frames (audio peak anchor)."""
    duration=duration_ms or MOVES['whip'][0]
    times=np.arange(0,duration+1000/fps,1000/fps)
    shifts=[motion('whip',t,duration)[1] for t in times]
    return float(times[1+int(np.argmax(np.abs(np.diff(shifts))))])


@effect(status='experimental')
def camera_move(frame, t, ctx, move='crash_in', duration_ms=0.0, target=0.0,
                direction='left', anchor='center', stiffness=180.0, damping=18.0, mass=1.0):
    """Named zoom/pan; durations in ms, spring physics in SI seconds."""
    elapsed = t-ctx.effect_start_ms
    scale, shift = motion(move, elapsed, duration_ms, target, stiffness, damping, mass)
    center = (ctx.width/2, ctx.height/2)
    if anchor == 'subject':
        alpha = frame[..., 3]; weight = float(alpha.sum())
        if weight and np.min(alpha) < 1:
            yy, xx = np.indices(alpha.shape)
            center = (float((xx*alpha).sum()/weight), float((yy*alpha).sum()/weight))
    elif anchor != 'center': raise ValueError('anchor: center or subject')
    matrix = cv2.getRotationMatrix2D(center, 0, scale)
    vertical = direction in ('up', 'down'); sign = -1 if direction in ('left', 'up') else 1
    matrix[int(vertical), 2] += sign*shift*(ctx.height if vertical else ctx.width)
    if move=='whip' and shift==0: return frame
    result = (straight(cv2.warpAffine(premultiply(frame),matrix,(ctx.width,ctx.height),
              flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)) if move=='whip' else warp(frame, matrix, ctx))
    if move == 'whip':
        _, before = motion(move, elapsed-1000/ctx.fps, duration_ms, target)
        length = max(1, round(abs(shift-before)*(ctx.height if vertical else ctx.width)*.3))
        if length > 1:
            result = straight(cv2.blur(premultiply(result), (1, length) if vertical else (length, 1)))
    return result
