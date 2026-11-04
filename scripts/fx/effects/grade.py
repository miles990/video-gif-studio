import numpy as np
from ..core import effect

@effect(temp='Warmth: red +temp, blue -temp', sat='Saturation multiplier')
def grade(frame, t_ms, ctx, lift=0.0, gamma=1.0, gain=1.0, sat=1.0, temp=0.0):
    """Lift/gamma/gain, luminance saturation and restrained warmth."""
    rgb = np.maximum(frame[..., :3]+lift,0)**(1/max(gamma,.001))*gain
    gray = rgb @ np.array([.2126,.7152,.0722],np.float32)
    frame[..., :3] = gray[...,None]+(rgb-gray[...,None])*sat+np.array([temp,0,-temp],np.float32)
    return frame
