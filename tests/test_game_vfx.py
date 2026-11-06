import sys
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from game_vfx import vfx,vfx_qa,additive_preview,scene_preview
from image_common import ImageError


class VfxTests(unittest.TestCase):
    def test_declared_alpha_scene_does_not_use_additive_blend(self):
        im=Image.new('RGBA',(2,1),(80,120,160,128));im.putpixel((0,0),(0,0,0,0))
        alpha=scene_preview(im,'alpha');add=scene_preview(im,'add')
        expected=Image.alpha_composite(Image.new('RGBA',im.size,(12,18,30,255)),im)
        self.assertEqual(alpha.tobytes(),expected.tobytes());self.assertNotEqual(alpha.tobytes(),add.tobytes())
        self.assertEqual(alpha.getpixel((0,0)),add.getpixel((0,0)))
    def test_soft_alpha_complete_decay_and_additive_zero(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as folder:
            out=Path(folder);m=vfx(out);self.assertEqual(m['qa']['status'],'PASS',m['qa'])
            frames=[Image.open(out/f['file']).convert('RGBA') for f in m['frames']]
            self.assertEqual(vfx_qa(frames[:-3])['status'],'FAIL')
            comp,premult=additive_preview(frames[4]);a=np.array(frames[4]);self.assertTrue(np.all(np.array(premult)[a[...,3]==0]==0))
            self.assertTrue((out/'additive/preview.gif').is_file());self.assertTrue((out/'additive/preview.png').is_file())
    def test_budget_does_not_truncate(self):
        with self.assertRaises(ImageError) as e:vfx(ROOT/'.scratch/not-created',frames=20,pixel=True)
        self.assertEqual(e.exception.error['code'],'E_FRAME_BUDGET')


if __name__=='__main__':unittest.main()
