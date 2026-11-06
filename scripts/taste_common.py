"""Offline taste instruments. Seconds throughout; no aesthetic pass/fail score."""
import json
from pathlib import Path
import subprocess
import numpy as np
from media_runtime import executable
from threshold_registry import value

ROOT = Path(__file__).resolve().parents[1]


def peaks(x, distance=1, prominence=0):
    """Deterministic local peaks, including a flat plateau's first sample."""
    x=np.asarray(x,float)
    candidates=np.flatnonzero((x>np.r_[-np.inf,x[:-1]]) & (x>=np.r_[x[1:],-np.inf]))
    accepted=[]
    for i in sorted(candidates,key=lambda i:(-x[i],i)):
        lo=max(0,i-distance);hi=min(len(x),i+distance+1)
        if x[i]-float(np.min(x[lo:hi]))>=prominence and all(abs(i-j)>=distance for j in accepted):accepted.append(int(i))
    return np.array(sorted(accepted),int)


def read(path):
    def invalid(s):
        raise ValueError('Non-finite JSON: '+s)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_constant=invalid)


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True,
                               allow_nan=False)+'\n', encoding='utf-8')


def run(args):
    p = subprocess.run(args, capture_output=True)
    if p.returncode:
        raise ValueError(p.stderr.decode('utf-8', errors='replace')[-1800:])
    return p


def probe(path):
    if not Path(path).is_file():
        raise ValueError('Input does not exist: '+str(path))
    data = json.loads(run([executable('ffprobe'), '-v', 'error', '-show_streams',
                           '-show_format', '-of', 'json', str(path)]).stdout)
    video = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if video is None:
        raise ValueError('Input has no video stream')
    a, b = map(float, video['avg_frame_rate'].split('/'))
    if b == 0 or a <= 0:
        raise ValueError('Video has no usable frame rate')
    return dict(fps=a/b, width=video['width'], height=video['height'],
                duration=float(data['format'].get('duration', video.get('duration', 0))),
                audio=any(s['codec_type'] == 'audio' for s in data['streams']))


def zscore(x):
    x = np.asarray(x, float)
    return (x-x.mean())/x.std() if x.size and x.std() > 1e-9 else np.zeros_like(x)


def smooth(x, hz=10):
    """Centered box, edge replication, 2 seconds; even kernel biased 1/2 sample left."""
    x = np.asarray(x, float)
    n = max(1, int(round(value('taste.smooth.seconds')*hz)))
    return np.convolve(np.pad(x, (n//2, n-1-n//2), mode='edge'), np.ones(n)/n, 'valid')


def curve_points(design):
    points = design.get('points', design.get('design_curve')) if isinstance(design, dict) else design
    points = np.asarray(points, float)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2 or not np.isfinite(points).all():
        raise ValueError('design_curve needs finite [seconds, intensity] points')
    if np.any(np.diff(points[:, 0]) <= 0) or points[0, 0] < 0 or np.any((points[:, 1] < 0) | (points[:, 1] > 1)):
        raise ValueError('Curve times must increase and intensity must be 0..1')
    return points


def align_proxy(measured, target):
    """Affine P5/P95 alignment of the already-smoothed proxy; never time-warp it.

    Use full ranges when either quantile span is degenerate (sparse accents).
    A constant proxy maps to the design minimum: it has no evidenced build.
    This estimates relative shape on planning units, not absolute arousal.
    """
    y = np.asarray(measured, float)
    source = np.percentile(y, [5, 95])
    destination = np.percentile(target, [5, 95])
    method = 'affine P5/P95 of smoothed proxy and sampled design'
    if np.ptp(source) < 1e-9 or np.ptp(destination) < 1e-9:
        source = np.array([y.min(), y.max()])
        destination = np.array([target.min(), target.max()])
        method = 'affine min/max fallback for degenerate P5/P95 span'
    aligned = ((y-source[0])*np.ptp(destination)/np.ptp(source)+destination[0]
               if np.ptp(source) > 1e-9 else np.full_like(y, target.min()))
    return aligned, dict(method=method, source_anchors=source.tolist(),
                         design_anchors=destination.tolist(), constant_proxy=bool(np.ptp(source)<1e-9))


def noise_sigma(values):
    """Robust sample noise from second differences, rejecting linear trends.

    MAD / sqrt(6) estimates independent sample sigma. With smoothed proxies
    this describes remaining local jitter, not absolute measurement accuracy.
    """
    delta = np.diff(np.asarray(values, float), n=2)
    return float(1.4826*np.median(abs(delta-np.median(delta)))/np.sqrt(6)) if len(delta) else 0.


def peak_center(times, values):
    """Mass centre above a three-sigma noise band around the first maximum.

    Only its contiguous lobe participates; separated peaks cannot cancel a
    timing error by averaging across a valley. A constant curve has no peak.
    """
    y = np.asarray(values, float)
    if np.ptp(y) < 1e-9:
        return None
    # A short, sharply alternating signal can contaminate even robust MAD.
    # Keep the upper half of the range so its baseline cannot join two lobes.
    band = max(min(3*noise_sigma(y), .5*np.ptp(y)), 1e-12)
    floor = y.max()-band
    top = y >= floor
    left = right = int(np.argmax(y))
    while left > 0 and top[left-1]: left -= 1
    while right+1 < len(y) and top[right+1]: right += 1
    weights = np.maximum(y[left:right+1]-floor, 1e-15)
    return float(np.average(np.asarray(times)[left:right+1], weights=weights))


def peak_intervals(points):
    """Exact authored maximum intervals, including isolated point peaks."""
    intervals = []
    previous_top = False
    for t, y in points:
        if abs(y-points[:, 1].max()) <= 1e-12:
            if intervals and previous_top:
                intervals[-1][1] = float(t)
            else:
                intervals.append([float(t), float(t)])
            previous_top = True
        else:
            previous_top = False
    return intervals


def compare_curve(times, measured, design, bar_seconds=2, proxy=False, absolute=None):
    points = curve_points(design)
    target = np.interp(times, points[:, 0], points[:, 1])
    y = np.asarray(measured, float)
    # A nearly level intention has no meaningful peak or correlation. Never
    # manufacture a crescendo by normalizing its tiny fluctuations to unit SD.
    flat = float(target.std()) < .02
    if flat and proxy:
        # A z-score has discarded amplitude. Its variance cannot tell a quiet
        # ambient plate from a loud montage. Only physical-unit evidence can.
        limits = dict(lra=5., short_term_range_lu=5., luminance_range_y=25., motion_range_px=3.)
        evidence = {k: dict(value=float(v), limit=limits[k]) for k,v in (absolute or {}).items()
                    if k in limits and v is not None}
        excess = [k for k,v in evidence.items() if v['value'] > v['limit']]
        return dict(design=target.tolist(), correlation=None, peak_offset_bars=None,
                    correlation_reason='Level design: standardized shape is not an absolute dynamics measure',
                    metric='absolute_dynamics', absolute_dynamics=evidence, revise=bool(excess),
                    measured_domain='physical units; no absolute intended intensity calibration',
                    reason='Review excess variation: '+', '.join(excess) if excess else
                           'Level intent retained; absolute dynamics within review limits' if evidence else
                           'Absolute dynamics unavailable; no revision inferred from normalized proxy',
                    deviations=[])
    alignment = None
    if proxy:
        y, alignment = align_proxy(y, target)
    r = float(np.corrcoef(target, y)[0, 1]) if not flat and y.std() > 1e-9 else None
    measured_peak, design_peak = peak_center(times, y), peak_center(times, target)
    intervals = peak_intervals(points)
    shift = None
    if not flat and measured_peak is not None and design_peak is not None:
        # Preserve sampled point-peak timing (e.g. a ramp ending between
        # samples); sustained maxima instead admit the entire authored hold.
        distance = (min(max(a-measured_peak, measured_peak-b, 0.) for a,b in intervals)
                    if any(b>a for a,b in intervals) else abs(measured_peak-design_peak))
        shift = distance/bar_seconds
    # Planning predictions already share units; measured films use aligned units.
    residual = target-y
    rms = float(np.sqrt(np.mean(residual**2)))
    limit = .15 if not proxy else .3
    n = max(1, round(value('taste.weak.seconds')/(times[1]-times[0]))) if len(times) > 1 else 1
    windows = np.convolve(abs(residual), np.ones(min(n, len(y)))/min(n, len(y)), 'valid')
    selected = []
    # Deficits first for shaped designs, so an over-measured designed dip cannot
    # hide a missed climax. Level planning comparisons still report excesses.
    priority = windows if flat else np.convolve(np.maximum(residual,0), np.ones(min(n,len(y)))/min(n,len(y)), 'valid')
    tolerance = value('taste.curve.residual.max') if proxy else 1e-9
    for i in np.argsort(-priority, kind='stable'):
        deficit = float(residual[i:i+n].mean())
        if priority[i] <= tolerance+1e-12 or (not flat and deficit <= tolerance+1e-12):
            continue
        start = float(times[i])
        if all(abs(start-w['start']) >= value('taste.weak.seconds') for w in selected):
            end=min(start+value('taste.weak.seconds'),float(times[-1])+(float(times[1]-times[0]) if len(times)>1 else .1))
            selected.append(dict(start=round(start, 3), end=round(end, 3),
                                 design=float(target[i:i+n].mean()), measured=float(y[i:i+n].mean()),
                                 deficit=deficit, deviation=float(windows[i]),
                                 kind='exceeds design' if deficit < 0 else 'missing',
                                 suggestion=('Reduce motion or soften an accent to restore the intended level.' if residual[i:i+n].mean()<0 else
                                             'Restore the planned action or audio accent here; retain this rest if intentional.')))
        if len(selected) == 3:
            break
    return dict(design=target.tolist(), correlation=r, correlation_reason=None if r is not None else 'Low-variance design or constant measurement; correlation not used for level designs',
                metric='rms_deviation' if flat else 'correlation', rms_deviation=rms, rms_limit=limit,
                measured_domain='proxy aligned to planning intensity; relative shape only' if proxy else 'planning intensity',
                measured=y.tolist(), alignment=alignment, residual_tolerance=tolerance,
                peak_method='mass centre of contiguous maximum lobe above three-sigma second-difference MAD band; distance to nearest authored maximum interval',
                peak_noise_sigma=noise_sigma(y), design_peak_intervals=intervals,
                measured_peak_seconds=measured_peak, design_peak_seconds=design_peak,
                peak_offset_bars=shift, revise=rms>limit if flat else r is None or r < value('taste.curve.correlation.min') or (shift is not None and shift > value('taste.curve.peak_bars.max')+1e-9),
                reason=f'RMS deviation {rms:.3f} (limit {limit})' if flat else f'Peak offset {shift} bars; correlation {r}', deviations=selected)


def plot_curve(path, times, measured, design=None, peaks=(), valley=None, bar_seconds=None):
    # Pillow avoids backend/font caches, timestamps and nondeterministic PNG metadata.
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (1000, 420), '#101722'); d = ImageDraw.Draw(im)
    arrays = [np.asarray(measured, float)] + ([np.asarray(design, float)] if design is not None else [])
    lo = min(float(a.min()) for a in arrays); hi = max(float(a.max()) for a in arrays)
    end = max(float(times[-1]), .001)
    def point(t, y):
        return 55+int(t/end*910), 350-int((y-lo)/max(hi-lo, 1e-9)*285)
    d.line((55, 55, 55, 350, 965, 350), fill='white', width=1)
    for a, color in zip(arrays, ('#39d9ef', '#ffab51')):
        d.line([point(float(t), float(y)) for t, y in zip(times, a)], fill=color, width=3)
    d.text((55, 15), 'Measured arousal proxy (cyan) / design (orange)' if design is not None else 'Measured arousal proxy / no design curve', fill='white')
    for i in peaks:
        x, y = point(times[i], measured[i]); d.ellipse((x-4, y-4, x+4, y+4), fill='#ffffff')
        d.text((max(55, min(x, 880)), max(35, y-18)), f'peak {times[i]:.3f}s', fill='white')
    if valley is not None:
        x, y = point(times[valley], measured[valley]); d.text((min(x, 850), min(y+8, 330)), f'valley {times[valley]:.3f}s', fill='white')
    for t in np.linspace(0, end, 6):
        x, _ = point(t, lo); d.text((x-20, 365), f'{t:.2f}s', fill='white')
        if bar_seconds: d.text((x-20, 385), f'bar {1+t/bar_seconds:.1f}', fill='white')
    Path(path).parent.mkdir(parents=True, exist_ok=True); im.save(path)
