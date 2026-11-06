"""Small deterministic encoded films for the visible taste scenarios.

No recorded reports or held-out fixtures. RGB frames and PCM are generated here,
then H.264/AAC encoded and decoded by the production analyzer. All paths are
provided by the caller (the scenario suite uses only .scratch).
"""
from pathlib import Path
import subprocess
import wave

import cv2
import numpy as np
from media_runtime import executable

FPS = 30
SIZE = (96, 64)


def encode(path, frames, audio=None, crf=18):
    path = Path(path)
    frames = list(frames)
    height, width = frames[0].shape[:2]
    args = [executable('ffmpeg'), '-v', 'error', '-y', '-f', 'rawvideo',
            '-pixel_format', 'rgb24', '-video_size', f'{width}x{height}',
            '-framerate', str(FPS), '-i', 'pipe:0']
    if audio is not None:
        wav = path.with_suffix('.wav')
        with wave.open(str(wav), 'wb') as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(48000)
            stream.writeframes((np.clip(audio, -1, 1)*32767).astype('<i2').tobytes())
        args += ['-i', str(wav), '-c:a', 'aac', '-b:a', '128k']
    args += ['-c:v', 'libx264', '-threads', '1', '-preset', 'fast', '-crf', str(crf),
             '-pix_fmt', 'yuv420p', str(path)]
    subprocess.run(args, input=b''.join(f.tobytes() for f in frames), check=True, capture_output=True)
    return path


def tone(duration, db):
    t = np.arange(round(duration*48000))/48000
    level = db(t) if callable(db) else db
    return 10**(np.asarray(level)/20)*np.sin(2*np.pi*440*t)


def texture(seed=71):
    rng = np.random.default_rng(seed)
    # Corners large enough for stable subpixel LK at this fixture resolution.
    small = rng.integers(30, 210, (16, 24, 3), dtype=np.uint8)
    return cv2.resize(small, SIZE, interpolation=cv2.INTER_NEAREST)


def arc_film(path, duration, points, freezes=(), seed=71, crf=18, jitter=0.):
    """Motion speed and dB level follow intensity; a defect freezes and drops audio.

    Design intensity is never injected into the report. The production decoder,
    optical flow, EBU meter, smoothing and comparison must recover its shape.
    """
    points = np.asarray(points)
    # Slow random jitter survives the production two-second smoothing, unlike
    # independent frame noise. Amplitude is a fraction of the design range.
    knots = np.arange(0, duration+1, .5)
    noise = np.random.default_rng(seed+1000).uniform(-1, 1, len(knots))
    energy = lambda t: (np.interp(t, points[:, 0], points[:, 1])+
                        jitter*np.ptp(points[:, 1])*np.interp(t, knots, noise))
    plate = texture(seed); frames = []; offset = 0.; held = None
    for i in range(round(duration*FPS)):
        t = i/FPS
        frozen = any(a <= t < b for a, b in freezes)
        if not frozen or held is None:
            offset += .25+3*energy(t)
            held = cv2.warpAffine(plate, np.float32([[1, 0, offset % SIZE[0]], [0, 1, 0]]),
                                  SIZE, borderMode=cv2.BORDER_WRAP)
        frames.append(held)
    def db(t):
        levels = -36+22*energy(t)
        for a, b in freezes: levels = np.where((t >= a)&(t < b), -45., levels)
        return levels
    return encode(path, frames, tone(duration, db), crf=crf)


def ambient_film(path, variant, duration=12):
    rng = np.random.default_rng(103)
    plate = texture() if variant in ('texture', 'amb13-like') else np.full((64, 96, 3), 90, np.uint8)
    frames = []
    for i in range(round(duration*FPS)):
        f = plate.astype(float)
        if variant == 'noise': f += rng.normal(0, 3, f.shape)
        if variant == 'breathing': f += 2*np.sin(2*np.pi*i/(FPS*duration))
        if variant == 'amb13-like':
            f = cv2.warpAffine(plate, np.float32([[1,0,.15*np.sin(i/FPS)],[0,1,0]]),
                               SIZE, borderMode=cv2.BORDER_WRAP).astype(float)
            f += rng.normal(0, 1, f.shape)+np.sin(2*np.pi*i/(FPS*duration))
        frames.append(np.clip(f, 0, 255).astype('uint8'))
    db = (lambda t: -24+.4*np.sin(2*np.pi*t/duration)) if variant in ('breathing','amb13-like') else -24
    return encode(path, frames, None if variant == 'texture' else tone(duration, db), crf=23)


def noisy_bars(path, size=(80,60), border=10):
    rng = np.random.default_rng(103)
    frames = []
    width,height=size
    for i in range(90):
        y = np.full((height,width),16.,float)
        u = np.full((height//2,width//2),128,np.uint8); v = u.copy()
        if i >= 30:
            y[border:height-border]=100
            u[border//2:(height-border)//2]=90; v[border//2:(height-border)//2]=170
        y = np.clip(y+rng.normal(0,3,y.shape),0,255).astype('uint8')
        frames.append(y.tobytes()+u.tobytes()+v.tobytes())
    subprocess.run([executable('ffmpeg'),'-v','error','-y','-f','rawvideo',
                    '-pixel_format','yuv420p','-video_size',f'{width}x{height}','-framerate','30',
                    '-i','pipe:0','-c:v','libx264','-threads','1','-crf','12',str(path)],
                   input=b''.join(frames),check=True,capture_output=True)
    return path


def flash_film(path, blowout=False):
    a = np.full((64, 96, 3), 80, np.uint8)
    return encode(path, [a]*30+[np.full_like(a, 255)]*(30 if blowout else 1)+[a]*60, crf=12)
