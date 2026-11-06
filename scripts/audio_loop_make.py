"""Search whole-bar source cuts and measured equal-power preroll crossfades.

No provider loop flag is trusted. No padding, repetition, or fade to silence.
The existing verifier is the final authority, including decoded exports.
"""
import numpy as np
from audio_grid import grid
from audio_loop import RATE, bar_samples, features, normalise, check
from image_common import ImageError


def zero_crossing(x, sample, radius=48):
    """Nearest mono crossing within one millisecond of the measured bar line."""
    lo, hi = max(1, round(sample)-radius), min(len(x)-1, round(sample)+radius)
    mono = x[lo-1:hi+1].mean(axis=1)
    crossings = np.flatnonzero(mono[:-1]*mono[1:] <= 0)+lo
    return int(min(crossings, key=lambda i: abs(i-sample))) if len(crossings) else round(sample)


def candidates(x, bpm, meter='4/4', bars=(2,4,8,16), measured_grid=None):
    measured_grid = measured_grid or grid(x, meter)
    bar = bar_samples(bpm, meter)
    beat = RATE*60/bpm
    # Grid phase is carried to the target timebase by the caller after stretching.
    origin = measured_grid['downbeat_sample']
    for count in bars:
        length = round(count*bar)
        for nominal in np.arange(origin, len(x)-length+1, bar):
            start = zero_crossing(x, nominal)
            end = start+length
            if end > len(x):
                continue
            for seconds in (.005,.01,.02,.04,.08,.125,.25,60/bpm):
                width = min(round(seconds*RATE), round(beat))
                if start < width:
                    continue
                y = x[start:end].copy()
                angle = np.linspace(0,np.pi/2,width)[:,None]
                y[-width:] = x[end-width:end]*np.cos(angle)+x[start-width:start]*np.sin(angle)
                a, b = y[-round(bar):].mean(axis=1), y[:round(bar)].mean(axis=1)
                corr = np.fft.irfft(np.fft.rfft(a)*np.conj(np.fft.rfft(b)),n=len(a))
                ids = np.arange(-960,961)
                lag = int(ids[np.argmax(corr[ids%len(a)])])
                spectral = float(np.linalg.norm(features(y[-2048:])-features(y[:2048])))
                rms = lambda z: max(float(np.sqrt(np.mean(z**2))),1e-12)
                level = abs(20*np.log10(rms(y[:19200])/rms(y[-19200:])))
                jump = float(np.max(abs(y[-1]-y[0])))
                record = dict(start_sample=start,end_sample=end,bar_count=count,
                              zero_crossing_offset_samples=start-round(nominal),
                              crossfade_samples=width,correlation_lag_ms=lag/48,
                              spectral_distance=spectral,head_tail_rms_db=level,
                              seam_jump=jump,score=abs(lag)/48+spectral+level+jump*100)
                yield y, record


def make_loop(x, bpm=120, meter='4/4', bars=(2,4,8,16), max_checks=40):
    measured = grid(x,meter)
    original_grid = dict(measured)
    stretch_report = None
    if abs(measured['bpm']-bpm) > .5:
        from audio_variants import stretch
        x, stretch_report = stretch(x,measured['bpm'],bpm)
        measured = grid(x,meter)
    options = sorted(candidates(x,bpm,meter,bars,measured),key=lambda p:p[1]['score'])
    trials = []
    for y, record in options[:max_checks]:
        y, gain = normalise(y)
        qa = check(y,bpm,meter,measured_bpm=measured['bpm'])
        trials.append(dict(record,qa=qa))
        if qa['status'] == 'PASS':
            return y,dict(method='local grid + whole-bar zero-crossing cut + equal-power incoming preroll',
                          source_grid=original_grid,grid=measured,stretch=stretch_report,
                          selected=record,normalization=gain,qa=qa,trials=trials,
                          candidates_searched=len(options))
    raise ImageError('E_LOOP_REPAIR','No measured candidate passed; regenerate needed',
                     source_grid=original_grid,trials=trials,candidates_searched=len(options))
