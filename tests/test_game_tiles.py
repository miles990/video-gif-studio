import sys
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from game_tiles import tile_qa,repair_periodic,tileset,tileset_qa,variants


class TileTests(unittest.TestCase):
    def test_periodic_noise_and_seam_gradient_controls(self):
        rng=np.random.default_rng(21);a=rng.integers(70,130,(128,128,3),dtype=np.uint8);im=Image.fromarray(a)
        q=tile_qa(im);self.assertEqual(q['status'],'PASS',q)
        broken=a.copy();broken[:,-2:]=245
        self.assertTrue(any(i['kind']=='wrap_seam' for i in tile_qa(Image.fromarray(broken))['issues']))
        gradient=np.clip(a.astype(float)+np.arange(128)[None,:,None]*.5,0,255).astype(np.uint8)
        fixed,report=repair_periodic(Image.fromarray(gradient));self.assertGreaterEqual(report['high_frequency_retained'],.85)
        self.assertLessEqual(report['after']['half_luma_difference']['x'],3)

    def test_all_declared_families_and_every_compatible_edge(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as folder:
            for kind,count in [('wang16',16),('blob47',47),('min13',13)]:
                out=Path(folder)/kind;m=tileset(out,16,kind);self.assertEqual(len(m['variants']),count);self.assertEqual(m['qa']['status'],'PASS',m['qa'])
                images=[Image.open(out/r['file']).convert('RGBA') for r in m['variants']]
                self.assertEqual(tileset_qa(images[:-1],m['variants'][:-1],kind,16)['status'],'FAIL')


if __name__=='__main__':unittest.main()
