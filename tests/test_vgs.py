import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import vgs
from media_runtime import locate


class VgsTests(unittest.TestCase):
    def test_temporal_palette_and_global_table(self):
        colors = [(100, 100, 100), (110, 100, 100), (100, 100, 100), (200, 100, 100)]
        frames = [Image.new('RGBA', (16, 16), (*c, 255)) for c in colors]
        result = vgs.pixel_quantize(frames, 4, 1)
        pixels = [f.getpixel((0, 0)) for f in result]
        self.assertEqual(pixels[0], pixels[1])
        self.assertEqual(pixels[0], pixels[2])
        self.assertNotEqual(pixels[2], pixels[3])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'out.gif'
            vgs.encode_pixel(result, [100]*4, path)
            self.assertEqual(vgs.count_gif_lcts(path), 0)

    def test_flicker_metrics_and_qa(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'out.gif'
            frames = []
            for i in range(5):
                a = np.zeros((48, 48, 4), dtype=np.uint8)
                a[8:40, 8:40] = (80 + 100*(i % 2), 80, 80, 255)
                frames.append(Image.fromarray(a))
            vgs.encode_pixel(frames, [100]*5, path)
            self.assertGreater(vgs.flicker_metrics(path)['quiet_flicker_rate'], .15)
            self.assertEqual(vgs.qa_gif(path), 1)
            clean = []
            for i in range(5):
                a = np.zeros((48, 48, 4), dtype=np.uint8)
                a[10:30, 8+i:28+i] = (80, 80, 80, 255)
                clean.append(Image.fromarray(a))
            vgs.encode_pixel(clean, [100]*5, path)
            metrics = vgs.flicker_metrics(path)
            self.assertLessEqual(metrics['quiet_flicker_rate'], .03)
            self.assertEqual(metrics['lct_count'], 0)

    @unittest.skipUnless(locate('ffmpeg') and locate('ffprobe'), 'FFmpeg/ffprobe required')
    def test_pixel_mp4_crisp(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'frames'; src.mkdir()
            for i in range(4):
                a = np.zeros((32, 32, 4), dtype=np.uint8)
                a[8:24, 8+i:24+i] = (180, 100, 40, 255)
                Image.fromarray(a).save(src / f'{i:05d}.png')
            out = Path(d) / 'out'
            proc = subprocess.run([sys.executable, str(ROOT/'scripts/vgs.py'), 'make', str(src), '--fps', '4', '--out', str(out), '--pixel', '--pixel-width', '32', '--mp4', '--loop-count', '1', '--loop', 'off'], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            manifest = json.loads((out/'manifest.json').read_text())
            scale = manifest['mp4_scale']
            self.assertGreaterEqual(min(manifest['mp4_size']), 576)
            probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=pix_fmt', '-of', 'default=nw=1:nk=1', str(out/'animation.mp4')], capture_output=True, text=True, check=True)
            self.assertEqual(probe.stdout.strip(), 'yuv420p')
            import cv2
            cap = cv2.VideoCapture(str(out/'animation.mp4'))
            ok, frame = cap.read(); cap.release()
            self.assertTrue(ok)
            h, w = frame.shape[:2]
            blocks = frame.reshape(h//scale, scale, w//scale, scale, 3)
            std = blocks.std(axis=(1, 3)).max(axis=2)
            self.assertLess(np.mean(std > 5), .02)

    def test_low_saturation(self):
        key, confidence, flat = vgs.estimate_key([Image.new('RGBA', (32, 32), '#f3eadb')])
        self.assertTrue(flat)
        self.assertGreater(confidence, .95)
        self.assertLess((key.max()-key.min())/key.max(), .35)

    def test_interior_key_choice(self):
        a = np.full((40,40,4), [255,0,255,255], dtype=np.uint8)
        a[5:35,5:35] = [255,255,255,255]
        a[15:25,15:25] = [255,0,255,255]
        removed, info = vgs.apply_key_connected([Image.fromarray(a)], [255,0,255], .2, .18)
        kept, _ = vgs.apply_key_connected([Image.fromarray(a)], [255,0,255], .2, .18, True)
        self.assertGreater(info['max_share'], .001)
        self.assertEqual(np.asarray(removed[0])[20,20,3], 0)
        self.assertEqual(np.asarray(kept[0])[20,20,3], 255)

    def test_pixel_blocks_palette_and_alpha(self):
        rng = np.random.default_rng(5)
        a = rng.integers(0,256,(16,16,4),dtype=np.uint8)
        out = vgs.pixel_quantize([Image.fromarray(a)], 16, 3)[0]
        b = np.asarray(out).reshape(16,3,16,3,4)
        self.assertFalse((b != b[:, :1, :, :1]).any())
        arr = np.asarray(out)
        self.assertLessEqual(len(np.unique(arr[arr[:,:,3]>0,:3], axis=0)), 16)
        self.assertLessEqual(set(np.unique(arr[:,:,3])), {0,255})

    def test_center_magenta_fails(self):
        with tempfile.TemporaryDirectory() as d:
            a = np.zeros((100,100,4),dtype=np.uint8)
            a[10:90,10:90] = [255,0,255,255]
            p = Path(d)/'test.gif'; Image.fromarray(a).save(p)
            ring, share, _ = vgs.key_metrics(p)
            self.assertLessEqual(ring, .01)
            self.assertGreater(share, .10)
            self.assertEqual(vgs.qa_gif(p), 1)

    def test_invalid_flags_human_error(self):
        for flag in (['--key','ZZZZZZ'], ['--colors','bad'], ['--pixel-width','0']):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as d:
                out = Path(d)/'out'
                p = subprocess.run([sys.executable, str(ROOT/'scripts/vgs.py'), 'make', str(ROOT/'examples/chibi-running-dash/source.mp4'), '--out', str(out), *flag], capture_output=True, text=True, env={k:v for k,v in os.environ.items() if k not in ('XAI_API_KEY','FAL_KEY')})
                self.assertEqual(p.returncode,1)
                self.assertNotIn('Traceback',p.stderr)
                self.assertFalse(out.exists())

    def test_robot_no_auto_crossfade(self):
        frames = [Image.new('RGBA',(24,24),(i*10,0,0,255)) for i in range(20)]
        _, info = vgs.loop_select(frames,24,19,20)
        self.assertEqual(info['method'], 'not_found')



    def test_low_saturation_cli_safe_hint(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)/'frames'; src.mkdir()
            for i in range(4):
                a = np.full((64,64,4), [243,234,219,255], dtype=np.uint8)
                a[16:48,16:48] = [40+i*10, 40, 40, 255]
                Image.fromarray(a).save(src/f'{i:05d}.png')
            out = Path(d)/'out'
            p = subprocess.run([sys.executable, str(ROOT/'scripts/vgs.py'), 'make', str(src), '--fps', '12', '--out', str(out)], capture_output=True, text=True, env={k:v for k,v in os.environ.items() if k not in ('XAI_API_KEY','FAL_KEY')})
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn('未去背', p.stdout)
            self.assertNotIn('請加 --key', p.stdout)


    def test_gradual_fade_not_frozen_and_alpha_hysteresis(self):
        # Gradual fade 0..200 in steps of 10 must advance across palette entries
        fade_frames = [Image.fromarray(np.full((8,8,4), [v,v,v,255], dtype=np.uint8)) for v in range(0, 201, 10)]
        q = vgs.pixel_quantize(fade_frames, 16, 1)
        vals = [int(np.asarray(f)[0,0,0]) for f in q]
        self.assertEqual(vals[0], 0)
        self.assertGreater(vals[-1], 150)
        # Alpha hysteresis: 0.55 coverage stays transparent after transparent frame, >=0.62 turns opaque
        a0 = np.zeros((10,10,4), dtype=np.uint8)
        a1 = np.zeros((10,10,4), dtype=np.uint8); a1[:5, :] = [200,200,200,255]; a1[5, :5] = [200,200,200,255]  # 0.55 cov
        a2 = np.zeros((10,10,4), dtype=np.uint8); a2[:7, :] = [200,200,200,255]  # 0.70 cov
        pooled = vgs.pixel_pool_and_stabilize_alpha([Image.fromarray(a0), Image.fromarray(a1), Image.fromarray(a2)], 1, 1)
        self.assertEqual(np.asarray(pooled[0])[0,0,3], 0)
        self.assertEqual(np.asarray(pooled[1])[0,0,3], 0)
        self.assertEqual(np.asarray(pooled[2])[0,0,3], 255)

if __name__ == '__main__':
    unittest.main()
