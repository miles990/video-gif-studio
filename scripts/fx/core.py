"""Pure RGBA effects: same dtype out (uint8 or float32), straight alpha at boundary."""
from dataclasses import dataclass, field
from pathlib import Path
import functools
import hashlib
import importlib.util
import inspect
import math
import sys
import warnings
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
    history: tuple = ()
    history_times_ms: tuple = ()
    effect_start_ms: float = 0
    source_trimmed: bool = False

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
    a = np.clip(a, 0, 1, out=a)
    return cv2.convertScaleAbs(a,alpha=255) if dtype == np.uint8 else a.astype(np.float32,copy=False)

def premultiply(a):
    channels=cv2.split(a)
    return cv2.merge([cv2.multiply(c,channels[3]) for c in channels[:3]]+[channels[3]])

def straight(a):
    channels=cv2.split(a); alpha=channels[3]
    divisor=cv2.max(alpha,1e-8)
    return cv2.merge([cv2.divide(c,divisor) for c in channels[:3]]+[alpha])

def over(a, b):
    return straight(premultiply(a)+premultiply(b)*(1-a[..., 3:4]))

def warp(a, matrix, ctx, sampling=None):
    mode = cv2.INTER_NEAREST if (sampling or ctx.sampling)=='nearest' else cv2.INTER_LINEAR
    if np.min(a[...,3])>=1:
        # Opaque camera moves extend the edge, avoiding transparent wedges and
        # unnecessary premultiply/divide passes. Transparent assets keep coverage.
        return cv2.warpAffine(a,matrix,(ctx.width,ctx.height),flags=mode,borderMode=cv2.BORDER_REFLECT_101)
    return straight(cv2.warpAffine(premultiply(a), matrix, (ctx.width, ctx.height), flags=mode, borderMode=cv2.BORDER_CONSTANT))

def register(registry, name=None, status='stable', style_tags=None, **docs):
    if status not in ('stable', 'experimental'):
        raise ValueError('FX status must be stable or experimental')
    if style_tags is not None and (not isinstance(style_tags,(list,tuple)) or
                                   any(not isinstance(tag,str) or not tag.strip() for tag in style_tags)):
        raise ValueError('style_tags must be a list of nonempty strings')
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
            if registry is TRANSITIONS:
                progress = args[1] if len(args)>1 else kwargs.get('p')
                if not isinstance(progress,(int,float,np.number)) or not np.isfinite(progress):
                    raise ValueError(f'{key}: p must be finite')
                context=args[2] if len(args)>2 else kwargs.get('ctx')
                if key.startswith('gl_') and context is not None and context.sampling=='nearest':
                    warnings.warn(f'{key} blends colours in nearest/pixel mode',UserWarning,stacklevel=2)
                if converted: converted[0] = floating(converted[0])
                else: kwargs = dict(kwargs,b=floating(kwargs['b']))
            return restore(fn(floating(a), *converted, **kwargs), a.dtype)
        source = str(Path(inspect.getfile(fn)).resolve())
        if key in registry:
            event = {'name':key,'previous':registry[key]['source'],'source':source}
            OVERRIDES.append(event); print('FX override: '+str(event), file=sys.stderr)
        def owned(*args,**kwargs):
            if registry is TRANSITIONS:
                progress=args[2] if len(args)>2 else kwargs.get('p')
                if not isinstance(progress,(int,float,np.number)) or not np.isfinite(progress):
                    raise ValueError(f'{key}: p must be finite')
            result=fn(*args,**kwargs)
            return np.clip(result,0,1,out=result)
        registry[key] = {'function':wrapped,'owned':owned,'status':status,'params':params,'doc':inspect.getdoc(fn) or key,'source':source,'history':int(docs.get('history',0))}
        if registry is TRANSITIONS or style_tags is not None:
            registry[key]['style_tags'] = list(style_tags or [])
        return wrapped
    return decorate

def effect(name=None, **docs): return register(EFFECTS, name, **docs)
def transition(name=None, **docs): return register(TRANSITIONS, name, **docs)

ENVELOPE_KEYS = {'on','attack_ms','decay_ms','curve','beats','indices','every','keyframes','min','max'}

def triggers(value, ctx):
    times = ctx.downbeats_ms if value.get('on')=='downbeats' else ctx.beats_ms
    indices = value.get('indices',value.get('beats',range(0,len(times),value.get('every',1))))
    return [times[i] for i in indices]

def audio_peaks(data, channel):
    """Local maxima on the analysis clock, including the first audio hop."""
    v = np.asarray(data[channel])
    ids = np.flatnonzero((v > 0) & (v >= np.r_[-1, v[:-1]]) & (v > np.r_[v[1:], -1]))
    return [(data['times_ms'][i]-data.get('offset_ms',0), float(v[i])) for i in ids]

def evaluate(value, t_ms, ctx):
    if not isinstance(value,dict): return value
    if 'keyframes' in value:
        points = np.asarray(value['keyframes'])
        return float(np.interp(t_ms, points[:,0], points[:,1]))
    on = value['on']
    if on in ('energy','onset'):
        data = ctx.audio
        if on not in data: raise ValueError('Missing 10ms '+on+' analysis; provide music.file')
        if on=='onset':
            decay = value.get('decay_ms',120)
            result = max((strength*max(0,1-(t_ms-t)/decay) if decay else strength*float(t_ms==t)
                          for t,strength in audio_peaks(data,on) if t<=t_ms),default=0.)
            if value.get('curve')=='ease_out': result = result**3
            elif value.get('curve')=='smooth': result = result*result*(3-2*result)
        else:
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
        saved_effects, saved_transitions, saved_overrides = dict(EFFECTS), dict(TRANSITIONS), list(OVERRIDES)
        try:
            spec = importlib.util.spec_from_file_location('vgs_fx_'+hashlib.sha256(str(file).encode()).hexdigest(),file)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        except Exception as exc:
            EFFECTS.clear(); EFFECTS.update(saved_effects)
            TRANSITIONS.clear(); TRANSITIONS.update(saved_transitions)
            OVERRIDES[:] = saved_overrides
            print(f'Warning: skipped FX library {file}:{getattr(exc,"lineno", "?")}: {exc}',file=sys.stderr)

def catalog(experimental=False):
    return {kind:{name:{k:v for k,v in item.items() if k not in ('function','owned')}
                  for name,item in reg.items() if experimental or item['status']=='stable'}
            for kind,reg in [('effects',EFFECTS),('transitions',TRANSITIONS)]}
