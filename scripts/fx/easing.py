"""Normalized Robert Penner easing equations, Copyright (c) 2001 Robert Penner.

BSD-3-Clause; https://robertpenner.com/easing_terms_of_use.html
Redistribution in source/binary forms, with or without modification, is permitted
provided source retains this notice, conditions and disclaimer; binary distributions
reproduce them in documentation/materials; neither author nor contributors' names
endorse derived products without prior written permission.
THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT EXPRESS OR IMPLIED WARRANTIES,
INCLUDING MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE. IN NO EVENT SHALL
THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE LIABLE FOR DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY OR CONSEQUENTIAL DAMAGES (INCLUDING SUBSTITUTE GOODS/SERVICES,
LOSS OF USE, DATA, PROFITS OR BUSINESS INTERRUPTION), HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER CONTRACT, STRICT LIABILITY OR TORT (INCLUDING
NEGLIGENCE), ARISING IN ANY WAY OUT OF USE, EVEN IF ADVISED OF SUCH DAMAGE.

The physical spring below is an original analytic damped-oscillator implementation.
"""
import math


def easeInExpo(t):
    return 0.0 if t == 0 else 2.0**(10*(t-1))


def easeOutExpo(t):
    return 1.0 if t == 1 else 1-2.0**(-10*t)


def easeInOutCubic(t):
    return 4*t**3 if t < .5 else 1-(-2*t+2)**3/2


def easeOutCubic(t):
    return 1-(1-t)**3


def easeInOutSine(t):
    return (1-math.cos(math.pi*t))/2


EASINGS = {fn.__name__: fn for fn in
           (easeInExpo, easeOutExpo, easeInOutCubic, easeOutCubic, easeInOutSine)}


def spring(seconds, stiffness=180.0, damping=18.0, mass=1.0):
    """Unit step response, initially at rest. Time is seconds, no endpoint clipping."""
    if not all(math.isfinite(v) for v in (seconds, stiffness, damping, mass)) or min(stiffness, mass) <= 0 or damping < 0:
        raise ValueError('spring requires finite stiffness/mass > 0, damping >= 0')
    t = max(0, seconds); w = math.sqrt(stiffness/mass); a = damping/(2*mass)
    if abs(a-w) < 1e-9:
        return 1-math.exp(-w*t)*(1+w*t)
    if a < w:
        b = math.sqrt(w*w-a*a)
        return 1-math.exp(-a*t)*(math.cos(b*t)+a/b*math.sin(b*t))
    b = math.sqrt(a*a-w*w); r1, r2 = -a+b, -a-b
    return 1-(r2*math.exp(r1*t)-r1*math.exp(r2*t))/(r2-r1)
