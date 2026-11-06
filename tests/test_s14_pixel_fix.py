import unittest,sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from game_character import quantize,palette_of
from game_sprite import pixel_qa

class PixelFixTests(unittest.TestCase):
    def test_area_conversion_and_noise_gate(self):
        rng=np.random.default_rng(1405);a=np.zeros((512,512,4),np.uint8)
        a[48:464,100:412,3]=255;a[48:464,100:412,:3]=rng.integers(0,256,(416,312,3),dtype=np.uint8)
        im=Image.fromarray(a);palette=palette_of([im],16)
        old=quantize(im.resize((64,64),Image.Resampling.NEAREST),palette)
        new=quantize(im,palette,(64,64))
        self.assertNotEqual(new.tobytes(),old.tobytes())
        self.assertTrue(any(r['kind']=='pixel_noise' for r in pixel_qa([old],palette,(64,64))['issues']))
        self.assertEqual(pixel_qa([new],palette,(64,64))['status'],'PASS')

    def test_both_live_families_and_frozen_back_holdouts(self):
        from game_character import prepare_subject
        from game_sprite import pixel_noise
        for family in ('rimewick','wolf'):
            for view in ('front','side','back'):
                with Image.open(Path('tests/fixtures/live-s14')/(family+'-'+view+'.png')) as source:
                    im,_=prepare_subject(source.convert('RGBA'),view)
                palette=palette_of([im]);old=quantize(im.resize((64,64),Image.Resampling.NEAREST),palette)
                new=quantize(im,palette,(64,64))
                self.assertGreater(pixel_noise(old),.12,(family,view,'old'))
                self.assertLessEqual(pixel_noise(new),.12,(family,view,'area/median'))
