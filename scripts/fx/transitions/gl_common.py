"""Shared CPU sampling for the stable gl-transitions adaptations.

UVs address pixel centres, with GLSL's bottom-up Y. Texture lookup is bilinear
CLAMP_TO_EDGE (or nearest when requested). All samples and blends are premultiplied.
Distances/rotations use frame-height units, so wide/portrait frames stay isotropic.

Value-noise interpolation: Morgan McGuire @morgan3d, via Rich Harris's
PerlinDissolve and liubailin2020@gmail.com's BurnThrough; hash via gre.
License: MIT, see THIRD_PARTY.md (gl-transitions).
"""
from functools import lru_cache
import cv2
import numpy as np
from ..core import premultiply, straight


def mix(a, b, t):
    if np.ndim(t)==0 and np.shape(a)==np.shape(b) and isinstance(a,np.ndarray):
        return cv2.addWeighted(a,1-float(t),b,float(t),0)
    t = np.asarray(t, dtype=np.float32)
    if isinstance(a,np.ndarray) and np.shape(a)==np.shape(b) and a.ndim==3 and t.shape==a.shape[:2]:
        # OpenCV runs contiguous vector loops; avoid three broadcast temporaries
        # over four-channel 720p frames on the common spatial-mask path.
        weights=cv2.merge([t]*a.shape[2])
        result=cv2.subtract(b,a)
        cv2.multiply(result,weights,dst=result)
        return cv2.add(result,a,dst=result)
    if t.ndim == 2 and np.ndim(a) == 3:
        t = t[..., None]
    return a * (1 - t) + b * t


def smooth(lo, hi, x):
    lo, hi = np.asarray(lo, np.float32), np.asarray(hi, np.float32)
    delta = hi - lo
    t = np.clip((np.asarray(x) - lo) / np.where(delta == 0, 1, delta), 0, 1)
    return np.where(delta == 0, np.asarray(x) >= hi, t * t * (3 - 2 * t)).astype(np.float32)


def fract(x):
    return x - np.floor(x)


def vector(value, count, name):
    v = np.asarray(value, dtype=np.float32)
    if v.shape != (count,) or not np.isfinite(v).all():
        raise ValueError(f'{name}: expected {count} finite components')
    return v


def positive(value, name):
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f'{name}: expected a positive number')
    return value


def direction_vector(value, default=(1, 0)):
    v = vector(value, 2, 'direction')
    norm = np.linalg.norm(v)
    return v / norm if norm else np.asarray(default, np.float32)


def random_field(x, y, seed=0, coefficient=12.9898, reduced=False):
    # float64 avoids platform-dependent float32 amplification by 43758.
    phase = (np.asarray(x, np.float64) + seed * .754877666) * coefficient
    phase = phase + (np.asarray(y, np.float64) + seed * .569840296) * 78.233
    if reduced:
        phase %= 3.14
    return fract(np.sin(phase) * 43758.5453).astype(np.float32)


def noise(x, y, seed=0, coefficient=12.9898, reduced=False):
    ix, iy = np.floor(x), np.floor(y)
    fx, fy = fract(x), fract(y)
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = random_field(ix, iy, seed, coefficient, reduced)
    b = random_field(ix + 1, iy, seed, coefficient, reduced)
    c = random_field(ix, iy + 1, seed, coefficient, reduced)
    d = random_field(ix + 1, iy + 1, seed, coefficient, reduced)
    return mix(a, b, ux) + (c - a) * uy * (1 - ux) + (d - b) * ux * uy


@lru_cache(maxsize=4)
def grid(width, height):
    x, y = np.meshgrid((np.arange(width, dtype=np.float32) + .5) / width,
                       1 - (np.arange(height, dtype=np.float32) + .5) / height)
    x.flags.writeable = y.flags.writeable = False
    return x, y


class Shader:
    def __init__(self, a, b, ctx):
        if a.shape != b.shape or a.shape[:2] != (ctx.height, ctx.width):
            raise ValueError('gl transition: A, B and context dimensions must match')
        self.opaque = bool(np.all(a[...,3]==1) and np.all(b[...,3]==1))
        self.original_a, self.original_b = a, b
        # Public calls already own private input copies. Shader operations never
        # mutate these aliases; the opaque path needs no association/division.
        self.a, self.b = (a,b) if self.opaque else (premultiply(a),premultiply(b))
        self.ctx = ctx
        self.x, self.y = grid(ctx.width, ctx.height)
        self.ratio = ctx.width / ctx.height

    def sample(self, image, x, y):
        if x is self.x and y is self.y:
            return image.copy()
        # Clamp before conversion: even very large finite UVs cannot overflow
        # OpenCV's fixed-point remap coordinates.
        mx = np.ascontiguousarray(np.clip(x * self.ctx.width - .5, 0, self.ctx.width - 1), dtype=np.float32)
        my = np.ascontiguousarray(np.clip((1 - y) * self.ctx.height - .5, 0, self.ctx.height - 1), dtype=np.float32)
        mode = cv2.INTER_NEAREST if self.ctx.sampling == 'nearest' else cv2.INTER_LINEAR
        return cv2.remap(image, mx, my, mode, borderMode=cv2.BORDER_REPLICATE)

    def blend(self, amount):
        return mix(self.a, self.b, amount)

    def warped(self, ax, ay, bx, by, amount):
        return mix(self.sample(self.a, ax, ay), self.sample(self.b, bx, by), amount)

    def finish(self, pm, displacement=False):
        if self.opaque:
            pm[...,3]=1
            return pm  # outer decorator clips RGB once
        return finish(pm,self.original_a,self.original_b,displacement=displacement)


def finish(pm, a, b, displacement=False):
    # Non-geometric reveals retain the original union. Displaced coverage is
    # exempt: clipping it to source coordinates fragments moving subjects.
    pm = np.asarray(pm, dtype=np.float32)
    alpha = np.clip(pm[..., 3:4], 0, 1)
    pm[..., :3] = np.minimum(np.maximum(pm[..., :3], 0), alpha)
    pm[..., 3:4] = alpha
    if not displacement: pm[(a[..., 3] == 0) & (b[..., 3] == 0)] = 0
    return straight(pm)
