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


class VgsTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
