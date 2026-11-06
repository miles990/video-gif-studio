"""Librosa-free spectral-flux beat grid; bar phase is an estimate, not a label."""
import numpy as np
from audio_loop import RATE


def grid(x, meter='4/4'):
    x = np.asarray(x)
    if x.ndim != 2 or len(x) < RATE * 2 or not np.isfinite(x).all():
        raise ValueError('Need at least two seconds of finite stereo audio')
    hop, window = 240, 2048
    frames = np.lib.stride_tricks.sliding_window_view(x.mean(axis=1), window)[::hop]
    spectrum = np.abs(np.fft.rfft(frames * np.hanning(window), axis=1))
    flux = np.maximum(np.diff(np.log1p(spectrum), axis=0), 0).sum(axis=1)
    centered = flux - flux.mean()
    size = 1 << (2 * len(flux) - 1).bit_length()
    corr = np.fft.irfft(abs(np.fft.rfft(centered, size)) ** 2, size)[:len(flux)]
    peaks = [i for i in range(60, min(200, len(corr)-1))
             if corr[i] > corr[i-1] and corr[i] >= corr[i+1]]
    if not peaks or max(corr[i] for i in peaks) <= 1e-9:
        raise ValueError('No measurable beat periodicity')
    ranked = sorted(peaks, key=lambda i: corr[i], reverse=True)
    lag = ranked[0]
    a, b, c = corr[lag-1:lag+2]
    offset = np.clip(.5*(a-c)/(a-2*b+c), -.5, .5)
    period = float(lag+offset)
    # Search phase against every pulse, then compare metrical accent classes.
    def strength(phase, step):
        positions = np.arange(phase, len(flux)-1, step)
        return float(np.mean(np.interp(positions, np.arange(len(flux)), flux)))
    phases = np.arange(0, period, .1)
    phase = float(max(phases, key=lambda p: strength(p, period)))
    beats = int(meter.split('/')[0])
    accents = [strength(phase+i*period, beats*period) for i in range(beats)]
    bar_phase = phase + int(np.argmax(accents))*period
    return dict(bpm=60*RATE/(hop*period), beat_samples=hop*period,
                downbeat_sample=round(bar_phase*hop+window/2+hop),
                beat_phase_sample=round(phase*hop+window/2+hop),
                bar_samples=hop*period*beats, meter=meter,
                method='5ms log spectral flux autocorrelation + metrical accent phase',
                downbeat_source='local_estimate', listening_review='pending',
                tempo_candidates=[dict(bpm=12000/i, strength=float(corr[i])) for i in ranked[:5]],
                accent_strength=accents)
