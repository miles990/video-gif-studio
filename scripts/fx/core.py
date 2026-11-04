"""Pure RGBA effects: same dtype out (uint8 or float32), straight alpha at boundary."""
from dataclasses import dataclass, field
from pathlib import Path
import functools
import hashlib
import importlib.util
import inspect
import math
import sys
import numpy as np
import cv2

EFFECTS, TRANSITIONS, OVERRIDES = {}, {}, []

@dataclass
class Context:
    width: int
    height: int
    fps: float = 25
    beats_ms: list = field(default_factory=list)
    t_ms: float = 0
    segment: dict = field(default_factory=dict)
    seed: int = 0
    downbeats_ms: list = field(default_factory=list)
    audio: dict = field(default_factory=dict)
    sampling: str = 'linear'

    @property
    def since_previous_beat(self):
        return self.t_ms-max((t for t in self.beats_ms if t <= self.t_ms), default=-math.inf)

    @property
    def until_next_beat(self):
        return min((t for t in self.beats_ms if t > self.t_ms), default=math.inf)-self.t_ms

    @property
    def rng(self):
        return np.random.default_rng(self.seed)

def floating(a):
    result = a.astype(np.float32)
    if a.dtype == np.uint8: result *= np.float32(1/255)
    return result

def restore(a, dtype):
    a = np.clip(a, 0, 1)
    return np.rint(a*255).astype(np.uint8) if dtype == np.uint8 else a.astype(np.float32)

def premultiply(a):
    a = a.copy(); a[..., :3] *= a[..., 3:4]
    return a

def straight(a):
    a = a.copy()
    a[..., :3] = np.divide(a[..., :3], a[..., 3:4], out=np.zeros_like(a[..., :3]), where=a[..., 3:4]>1e-8)
    return a

def over(a, b):
    return straight(premultiply(a)+premultiply(b)*(1-a[..., 3:4]))

def warp(a, matrix, ctx, sampling=None):
    mode = cv2.INTER_NEAREST if (sampling or ctx.sampling)=='nearest' else cv2.INTER_LINEAR
    return straight(cv2.warpAffine(premultiply(a), matrix, (ctx.width, ctx.height), flags=mode, borderMode=cv2.BORDER_CONSTANT))

def register(registry, name=None, **docs):
    def decorate(fn):
        key = name or fn.__name__
        params = {}
        for k, p in inspect.signature(fn).parameters.items():
            if p.default is not inspect.Parameter.empty:
                params[k] = {'default':p.default, 'type': ('number' if isinstance(p.default,(int,float)) and not isinstance(p.default,bool) else type(p.default).__name__), 'doc': docs.get(k,k.replace('_',' '))}
        @functools.wraps(fn)
        def wrapped(a, *args, **kwargs):
            if a.ndim != 3 or a.shape[2]!=4 or a.dtype not in (np.uint8,np.float32):
                raise ValueError('frame must be HxWx4 uint8 or float32')
            converted = list(args)
            if registry is TRANSITIONS: converted[0] = floating(converted[0])
            return restore(fn(floating(a), *converted, **kwargs), a.dtype)
        source = str(Path(inspect.getfile(fn)).resolve())
        if key in registry:
            event = {'name':key,'previous':registry[key]['source'],'source':source}
            OVERRIDES.append(event); print('FX override: '+str(event), file=sys.stderr)
        registry[key] = {'function':wrapped,'params':params,'doc':inspect.getdoc(fn) or key,'source':source}
        return wrapped
    return decorate

def effect(name=None, **docs): return register(EFFECTS, name, **docs)
def transition(name=None, **docs): return register(TRANSITIONS, name, **docs)

ENVELOPE_KEYS = {'on','attack_ms','decay_ms','curve','beats','indices','every','keyframes','min','max'}

def triggers(value, ctx):
    times = ctx.downbeats_ms if value.get('on')=='downbeats' else ctx.beats_ms
    indices = value.get('indices',value.get('beats',range(0,len(times),value.get('every',1))))
    return [times[i] for i in indices]

def evaluate(value, t_ms, ctx):
    if not isinstance(value,dict): return value
    if 'keyframes' in value:
        points = np.asarray(value['keyframes'])
        return float(np.interp(t_ms, points[:,0], points[:,1]))
    on = value['on']
    if on in ('energy','onset'):
        data = ctx.audio
        if on not in data: raise ValueError('Missing 10ms '+on+' analysis; provide music.file')
        result = float(np.interp(t_ms+data.get('offset_ms',0), data['times_ms'], data[on]))
    else:
        attack, decay = value.get('attack_ms',0), value.get('decay_ms',200)
        result = 0.
        for beat in triggers(value, ctx):
            dt = t_ms-beat
            v = 1+dt/attack if attack and -attack<=dt<0 else (max(0,1-dt/decay) if 0<=dt and decay else float(dt==0))
            result = max(result,v)
        if value.get('curve','linear')=='ease_out': result = result**3
        elif value.get('curve')=='smooth': result = result*result*(3-2*result)
    return value.get('min',0)+(value.get('max',1)-value.get('min',0))*result

def validate_envelope(value, ctx, where):
    unknown = set(value)-ENVELOPE_KEYS
    if unknown: raise ValueError(f'{where}: unknown {sorted(unknown)}; envelope keys {sorted(ENVELOPE_KEYS)}')
    if 'keyframes' in value:
        p = np.asarray(value['keyframes'],dtype=float)
        if p.ndim!=2 or p.shape[1]!=2 or not len(p) or not np.isfinite(p).all() or np.any(np.diff(p[:,0])<=0):
            raise ValueError(f'{where}: keyframes require increasing finite [ms,value] pairs')
        return
    if value.get('on') not in ('beats','downbeats','energy','onset'):
        raise ValueError(f'{where}: on must be beats, downbeats, energy, onset')
    if value['on']=='downbeats' and not ctx.downbeats_ms: raise ValueError(f'{where}: downbeats_ms required; use music_sync.py --engine beat_this')
    if value['on']=='beats' and not ctx.beats_ms: raise ValueError(f'{where}: beats_ms required; provide beatmap or use keyframes')
    for key in ('attack_ms','decay_ms','min','max'):
        if key in value and (type(value[key]) not in (int,float) or not math.isfinite(value[key]) or (key.endswith('_ms') and value[key]<0)):
            raise ValueError(f'{where}.{key}: expected finite nonnegative milliseconds or numeric bounds')
    if value.get('curve','linear') not in ('linear','ease_out','smooth'): raise ValueError(f'{where}: curve options linear, ease_out, smooth')
    if type(value.get('every',1)) is not int or value.get('every',1)<1: raise ValueError(f'{where}.every: positive integer required')
    times = ctx.downbeats_ms if value['on']=='downbeats' else ctx.beats_ms
    for i in value.get('indices',value.get('beats',[])):
        if type(i) is not int or not 0<=i<len(times): raise ValueError(f'{where}: beat {i}, valid range 0..{len(times)-1}')

def load_directory(directory):
    path = Path(directory).expanduser()
    if not path.exists(): return
    for file in sorted(path.glob('*.py')):
        try:
            spec = importlib.util.spec_from_file_location('vgs_fx_'+hashlib.sha256(str(file).encode()).hexdigest(),file)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        except Exception as exc:
            raise ValueError(f'FX library {file}:{getattr(exc,"lineno", "?")}: {exc}') from None

def catalog():
    return {kind:{name:{k:v for k,v in item.items() if k!='function'} for name,item in reg.items()} for kind,reg in [('effects',EFFECTS),('transitions',TRANSITIONS)]}
