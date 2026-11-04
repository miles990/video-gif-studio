"""Round-2 delivery regressions: real CLI publication, independently measured audio.

Fixtures follow acceptance-5 literally; optional variants are named explicitly.
All media lives in automatically cleaned OS temporary directories. Run serially.
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import wave

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from delivery import probe, run
from media_runtime import executable, locate


def wav(path, x):
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1 if x.ndim == 1 else x.shape[1])
        stream.setsampwidth(2)
        stream.setframerate(48000)
        stream.writeframes((np.clip(x, -1, 1)*32767).astype('<i2').tobytes())


def speech(seconds, mask, scale=1):
    t = np.arange(48000*seconds)/48000
    spectrum = np.fft.rfft(np.random.default_rng(4).normal(size=len(t)))
    frequencies = np.fft.rfftfreq(len(t), 1/48000)
    spectrum[(frequencies < 300) | (frequencies > 3400)] = 0
    return scale*.3*np.fft.irfft(spectrum, len(t))*(.6+.4*np.sin(2*np.pi*4*t))*mask(t)


def ebu(path):
    # Read the published file through the acceptance EBU command, not qc.json.
    result = subprocess.run([executable('ffmpeg'), '-nostats', '-i', str(path),
                             '-filter_complex', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True)
    if result.returncode: raise RuntimeError(result.stderr.decode(errors='replace'))
    summary = result.stderr.decode(errors='replace').split('Summary:')[-1]
    return dict(lufs=float(re.search(r'I:\s+(-?[\d.]+) LUFS', summary)[1]),
                true_peak_dbtp=float(re.search(r'True peak:\s+Peak:\s+(-?[\d.]+) dBFS', summary)[1]))


def pcm(path, seconds=None):
    data = subprocess.check_output([executable('ffmpeg'), '-v', 'error', '-i', str(path),
                                    *(['-t', str(seconds)] if seconds else []),
                                    '-vn', '-ac', '2', '-ar', '48000', '-f', 'f32le', '-'])
    return np.frombuffer(data, '<f4').reshape(-1, 2)


@unittest.skipUnless(locate('ffmpeg') and locate('ffprobe'), 'FFmpeg/ffprobe required')
class AudioCLITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='vgs-p0-fix2-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        Image.new('RGB', (32, 32), 'gray').save(cls.root/'gray.png')
        t = np.arange(20*48000)/48000
        phase = t % .5
        music = .25*np.sin(2*np.pi*110*t)+.05*np.sin(2*np.pi*6000*t)
        music += .15*np.sin(2*np.pi*60*phase)*np.exp(-phase*35)
        wav(cls.root/'MUS.wav', np.column_stack((music, music)))
        wav(cls.root/'HOT.wav', np.column_stack((music*4, music*4)))
        voice = speech(20, lambda t: ((t >= 4) & (t < 8)) | ((t >= 12) & (t < 16)))
        wav(cls.root/'SPEECH.wav', voice)
        wav(cls.root/'SPEECH-quiet.wav', voice*.1)
        # A separate stereo variant, without changing the literal MUS fixture.
        right = .25*np.sin(2*np.pi*220*t)+.05*np.sin(2*np.pi*6000*t)
        wav(cls.root/'MUS-LR.wav', np.column_stack((music, right)))
        t = np.arange(10*48000)/48000
        clip = 10**(-30/20)*np.sin(2*np.pi*440*t)
        clip += 10**(-12/20)*np.sin(2*np.pi*1000*t)*((np.arange(len(t)) % 48000) < 480)
        wav(cls.root/'CLIP-A.wav', clip)
        run(['-v', 'error', '-filter_threads', '1', '-f', 'lavfi', '-i',
             "color=gray:s=1080x1920:r=30:d=10,drawbox=width=iw:height=ih:color=white:t=fill:enable='eq(mod(n,30),0)'",
             '-i', str(cls.root/'CLIP-A.wav'), '-c:v', 'libx264', '-preset', 'ultrafast',
             '-threads', '2', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k', str(cls.root/'CLIP-A.mp4')])

    def publish(self, name, source, music=None, seconds=20, platform=True):
        plan = dict(segments=[dict(type='still', image='gray.png', duration_ms=seconds*1000)],
                    source_audio=source)
        if music: plan['music'] = dict(file=music)
        plan_file = self.root/(name+'.json')
        plan_file.write_text(json.dumps(plan))
        out = self.root/name
        command = [sys.executable, str(ROOT/'scripts/fx_render.py'), str(plan_file),
                   '--out', str(out), '--formats', 'mp4', '--keep-audio']
        if platform: command += ['--platform', 'tiktok']
        # No duck, loudnorm, gain, fps, proxy or limiter overrides.
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stderr)
        movie = out/'animation.mp4'
        self.assertTrue(movie.is_file(), 'Delivery must be PUBLISHED at the final path')
        self.assertFalse(list(out.glob('*.partial*')))
        report = json.loads((out/'manifest.json').read_text())
        self.assertFalse(any(c['level'] == 'FAIL' for c in report['audio']['checks']))
        measured = ebu(movie)
        self.assertAlmostEqual(measured['lufs'], -14, delta=1)
        self.assertLessEqual(measured['true_peak_dbtp'], -1)
        streams = probe(movie)['streams']
        self.assertEqual(next(s for s in streams if s['codec_type'] == 'audio')['channels'], 2)
        video = next(s for s in streams if s['codec_type'] == 'video')
        self.assertEqual(video['r_frame_rate'], '30/1')
        self.assertEqual(video['avg_frame_rate'], '30/1')
        if platform: self.assertEqual((video['width'], video['height']), (1080, 1920))
        print('P0_FIX2 '+json.dumps(dict(case=name, status='PUBLISHED', **measured)), flush=True)
        return movie, report['audio']

    def test_literal_mus_clip_a_defaults_publish(self):
        _, audio = self.publish('MUS-CLIP-A', 'CLIP-A.mp4', 'MUS.wav')
        self.assertEqual(audio['ducking']['presence_intervals'], [])

    def test_literal_hot_clip_a_defaults_publish(self):
        self.publish('HOT-CLIP-A', 'CLIP-A.mp4', 'HOT.wav')

    def test_literal_speech_only_defaults_publish(self):
        self.publish('SPEECH-only', 'SPEECH.wav')

    def test_peak_limiter_handles_gain_above_peak_headroom(self):
        # Separate transient variant proves the limiter actually engages.
        voice = speech(20, lambda t: ((t >= 4) & (t < 8)) | ((t >= 12) & (t < 16)))
        for at in (2, 9, 17): voice[at*48000] = .95
        wav(self.root/'SPEECH-peaks.wav', voice)
        _, audio = self.publish('peak-limiter', 'SPEECH-peaks.wav', platform=False)
        unlimited_peak = float(audio['first_pass']['input_tp'])+audio['second_pass']['gain_db']
        self.assertGreater(unlimited_peak, -1)
        print('P0_FIX2 '+json.dumps(dict(case='limiter-engaged', unlimited_peak_dbtp=unlimited_peak,
                                       limiter=audio['second_pass']['limiter'])), flush=True)

    def test_stereo_channels_survive_mono_source(self):
        movie, audio = self.publish('stereo-LR', 'CLIP-A.mp4', 'MUS-LR.wav', platform=False)
        x = pcm(movie, 3)[48000:]
        t = np.arange(len(x))/48000
        amplitude = lambda hz: abs(np.mean(x*np.exp(-2j*np.pi*hz*t)[:, None], axis=0))
        left, right = amplitude(110), amplitude(220)
        separation = [float(20*np.log10(left[0]/max(left[1], 1e-12))),
                      float(20*np.log10(right[1]/max(right[0], 1e-12)))]
        self.assertGreater(min(separation), 20)
        self.assertEqual(audio['ducking']['presence_intervals'], [])
        print('P0_FIX2 '+json.dumps(dict(case='stereo-separation', db=separation)), flush=True)

    def test_steady_ambient_is_not_speech(self):
        noise = np.random.default_rng(12).normal(0, .02, 48000*20)
        wav(self.root/'ambient.wav', noise)
        _, audio = self.publish('ambient', 'ambient.wav', 'MUS.wav', platform=False)
        self.assertEqual(audio['ducking']['presence_intervals'], [])

    def test_three_minutes_360_speech_segments_publish(self):
        # Generate in 1 s blocks: two distinct 120 ms utterances per second.
        one = speech(1, lambda t: ((t >= .1) & (t < .22)) | ((t >= .6) & (t < .72)))
        with wave.open(str(self.root/'long.wav'), 'wb') as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(48000)
            block = (one*32767).astype('<i2').tobytes()
            for _ in range(180): stream.writeframes(block)
        # Music must run for the full three minutes too.
        with wave.open(str(self.root/'MUS.wav'), 'rb') as stream:
            block = stream.readframes(48000*20)
        with wave.open(str(self.root/'long-MUS.wav'), 'wb') as stream:
            stream.setnchannels(2); stream.setsampwidth(2); stream.setframerate(48000)
            for _ in range(9): stream.writeframes(block)
        _, audio = self.publish('long-360', 'long.wav', 'long-MUS.wav', 180, platform=False)
        intervals = audio['ducking']['presence_intervals']
        self.assertEqual(len(intervals), 360)
        self.assertIn('PCM', audio['ducking']['envelope'])
        print('P0_FIX2 '+json.dumps(dict(case='long-envelope', seconds=180, segments=len(intervals))), flush=True)

    def test_default_ducking_both_speech_levels(self):
        for source, name in [('SPEECH.wav', 'duck-normal'), ('SPEECH-quiet.wav', 'duck-quiet')]:
            movie, _ = self.publish(name, source, 'MUS.wav', platform=False)
            x = pcm(movie).mean(axis=1)
            def level(a, b):
                samples = x[round(a*48000):round(b*48000)]
                t = np.arange(len(samples))/48000
                return 20*np.log10(abs(np.mean(samples*np.exp(-2j*np.pi*110*t))))
            baseline = np.mean([level(a, b) for a, b in [(1, 3), (9, 11), (17, 19)]])
            depths = [float(baseline-level(a, b)) for a, b in [(4.5, 7.5), (12.5, 15.5)]]
            for depth in depths: self.assertAlmostEqual(depth, 10, delta=2)
            print('P0_FIX2 '+json.dumps(dict(case=name, duck_db=depths)), flush=True)


if __name__ == '__main__': unittest.main()
