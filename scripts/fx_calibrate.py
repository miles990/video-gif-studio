"""Reproducible perceived-intensity lookup and serialized 720p timing."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import cv2
import numpy as np
from fx import EFFECTS, TRANSITIONS, Context
from fx.core import load_directory
from fx_measure import standard, measures
from threshold_registry import value

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT/'references/fx-calibration.json'


def cpu_load():
    """Sample system utilization without adding a dependency to the shared venv."""
    if os.name=='nt':
        import ctypes
        def sample():
            idle,kernel,user=(ctypes.c_ulonglong() for _ in range(3))
            if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle),ctypes.byref(kernel),ctypes.byref(user)):
                raise OSError('GetSystemTimes failed')
            return idle.value,kernel.value+user.value
        a=sample();time.sleep(.1);b=sample();elapsed=b[1]-a[1]
        return 100*(elapsed-(b[0]-a[0]))/elapsed if elapsed else 0.
    try:
        import psutil
        return psutil.cpu_percent(interval=.1)
    except ImportError:return None


def revision():
    return subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'rev-parse','HEAD'], cwd=ROOT, text=True).strip()


def fingerprint(spec):
    return hashlib.sha256(Path(spec['source']).read_bytes()).hexdigest()


def engine_fingerprint():
    return hashlib.sha256((ROOT/'scripts/fx/core.py').read_bytes()+(ROOT/'scripts/fx_measure.py').read_bytes()).hexdigest()


def control(name):
    # cutout_card.amount means opacity (zero is NOT identity). Its director
    # control is identity-to-default compositing on STD-A; legacy pixels stay unchanged.
    return {'grade':'temp', 'cutout_card':'mix'}.get(name, 'amount')


def apply(name, frame, amount, t_ms=1000, ctx=None, params=None):
    ctx = ctx or Context(frame.shape[1],frame.shape[0],fps=30,beats_ms=[1000],t_ms=t_ms,seed=6)
    p = dict(params or {})
    knob = control(name)
    if knob == 'mix':
        out = EFFECTS[name]['function'](frame,t_ms,ctx,**p)
        # Composite comparison in premultiplied space, preserving straight alpha.
        from fx.core import floating, premultiply, straight, restore
        result = straight(premultiply(floating(frame))*(1-amount)+premultiply(floating(out))*amount)
        return restore(result,frame.dtype)
    p[knob] = amount
    return EFFECTS[name]['function'](frame,t_ms,ctx,**p)


def load_table(path=None):
    path = Path(path or os.environ.get('VIDEO_GIF_FX_CALIBRATION', TABLE))
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {'version':1,'effects':{},'costs':{}}


def calibration_entry(name, table=None, sampling='linear', resolution=None):
    if sampling not in ('linear','nearest'):raise ValueError('Unknown calibration sampling: '+sampling)
    if resolution is not None and min(resolution)<32:
        raise ValueError('Perceived calibration unsupported below 32 pixels on either axis; use native controls')
    table = table or load_table()
    entries = table['effects'] if sampling=='linear' else table.get('sampling_modes',{}).get(sampling,{}).get('effects',{})
    e = entries.get(name)
    if e is None:raise ValueError(f'Uncalibrated effect: {name} ({sampling}); run fx_calibrate.py --sampling {sampling}')
    return e


def interpolate(name, amount, table=None, sampling='linear', resolution=None):
    e = calibration_entry(name,table,sampling,resolution)
    if e is None: raise ValueError('Uncalibrated effect: '+name+'; run fx_calibrate.py --fx-dir DIR')
    rows = e['rows']
    if not np.isfinite(amount) or amount < rows[0]['amount'] or amount > rows[-1]['amount']:
        raise ValueError(name+': intensity outside calibrated domain')
    return float(np.interp(amount,[r['amount'] for r in rows],[r['perceived'] for r in rows]))


def inverse(name, target, table=None, sampling='linear', resolution=None):
    if name=='cutout_card':raise ValueError('cutout_card is not addressable via perceived; use native parameters (measured mix max 0.0211)')
    e = calibration_entry(name,table,sampling,resolution)
    if e is None: raise ValueError('Uncalibrated effect: '+name)
    if not np.isfinite(target) or target<0 or target>e['max_perceived']:
        raise ValueError(f'{name}: perceived {target} unreachable; max_perceived={e["max_perceived"]:.6f}')
    rows = e['rows']
    values = np.array([r['perceived'] for r in rows])
    if np.any(np.diff(values)<-value('calibration.monotonic.tolerance')):
        raise ValueError(name+': nonmonotonic calibration cannot be inverted')
    return float(np.interp(target,np.maximum.accumulate(values),[r['amount'] for r in rows]))


def calibrate(path=TABLE, names=None, costs=True, force=False, sampling='linear'):
    if sampling not in ('linear','nearest'):raise ValueError('Unknown calibration sampling: '+sampling)
    cv2.setNumThreads(1)
    result = load_table(path)
    result.update(version=1, material='STD-P/A6-1 seed=6 noise-after-subject', background='#808080',
                  date=datetime.now(timezone.utc).date().isoformat(),commit=revision(),
                  formula='clip(max(dY/64, ssim_loss, disp/24, flash_area),0,1)',
                  threshold_registry='references/thresholds.json', resolution=[1280,720],
                  method='public uint8 function; t_ms=1000; seed=6; 3 warmups, median of 20 frames',
                  machine=dict(host=platform.node(),cpu=platform.processor(),numpy=np.__version__,opencv=cv2.__version__,threads=1))
    result['machine']['cpu_load_percent']=cpu_load()
    from media_runtime import executable
    result['machine']['ffmpeg']=subprocess.check_output([executable('ffmpeg'),'-version'],text=True).splitlines()[0]
    entries = result['effects'] if sampling=='linear' else result.setdefault('sampling_modes',{}).setdefault(sampling,{}).setdefault('effects',{})
    ctx=Context(1280,720,fps=30,beats_ms=[1000],t_ms=1000,seed=6,sampling=sampling)
    for name,spec in sorted(EFFECTS.items()):
        if names is not None and name not in names: continue
        if names is None and spec['status']!='stable': continue
        if 'amount' not in spec['params'] and name!='grade': continue
        existing=entries.get(name,{})
        if not force and existing.get('source_sha256')==fingerprint(spec) and existing.get('sampling')==sampling and existing.get('engine_sha256')==engine_fingerprint(): continue
        material='STD-A' if name=='cutout_card' else 'STD-P'
        source=standard(material)
        rows=[]
        for amount in np.linspace(0,1,int(value('calibration.grid.points'))):
            output=apply(name,source,float(amount),ctx=ctx)
            rows.append(dict(amount=float(amount),**measures(source,output)))
        default=0 if name=='grade' else spec['params'].get('amount',{}).get('default',1)
        entries[name]=dict(control=control(name),material=material,rows=rows,sampling=sampling,resolution=[1280,720],
            perceived_addressable=name!='cutout_card',
            source_sha256=fingerprint(spec),engine_sha256=engine_fingerprint(),max_perceived=max(r['perceived'] for r in rows),
            default_perceived=float(np.interp(default,[r['amount'] for r in rows],[r['perceived'] for r in rows])),
            identity='premultiplied mix=0' if name=='cutout_card' else control(name)+'=0',
            monotonic=all(b['perceived']>=a['perceived']-value('calibration.monotonic.tolerance') for a,b in zip(rows,rows[1:])))
        print('calibrated '+name,file=sys.stderr,flush=True)
    if costs:
        source=standard();other=np.flip(source,axis=1).copy()
        for kind,registry in [('effect',EFFECTS),('transition',TRANSITIONS)]:
            for name,spec in sorted(registry.items()):
                if (names is not None and name not in names) or (names is None and spec['status']!='stable'):continue
                fn=spec['function']
                samples=[]
                for i in range(23):
                    start=time.perf_counter()
                    fn(source,1000,ctx) if kind=='effect' else fn(source,other,.5,ctx)
                    if i>=3:samples.append((time.perf_counter()-start)*1000)
                result['costs'][kind+':'+name]=dict(ms_per_frame=float(np.median(samples)),samples=20,
                    source_sha256=fingerprint(spec),date=result['date'],machine=result['machine'])
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=TABLE);ap.add_argument('--fx-dir',action='append',default=[])
    ap.add_argument('--effect',action='append');ap.add_argument('--force',action='store_true');ap.add_argument('--no-costs',action='store_true')
    ap.add_argument('--perceived',type=float)
    ap.add_argument('--sampling',choices=['linear','nearest'],default='linear')
    a=ap.parse_args(argv)
    try:
        for directory in a.fx_dir:load_directory(directory)
        if a.effect and set(a.effect)-set(EFFECTS)-set(TRANSITIONS):raise ValueError('Unknown calibration item')
        if a.perceived is not None:
            if not a.effect or len(a.effect)!=1:raise ValueError('--perceived requires one --effect')
            if not np.isfinite(a.perceived) or not 0<=a.perceived<=1:raise ValueError('perceived must be finite and in 0..1')
            table=load_table(a.out)
            try:calibration_entry(a.effect[0],table,a.sampling)
            except ValueError:table=calibrate(a.out,a.effect,not a.no_costs,a.force,a.sampling)
            print(json.dumps({'effect':a.effect[0],'sampling':a.sampling,'control':calibration_entry(a.effect[0],table,a.sampling)['control'],'value':inverse(a.effect[0],a.perceived,table,a.sampling)}))
        else:
            table=calibrate(a.out,a.effect,not a.no_costs,a.force,a.sampling)
            print(json.dumps({'table':str(a.out),'effects':len(table['effects']),'costs':len(table['costs'])}))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('fx_calibrate: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
