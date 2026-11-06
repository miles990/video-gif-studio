import sys
from pathlib import Path
import unittest
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from game_sprite import clean_sprite,alpha_contract,pixel_qa
from game_character import palette_of


class SpriteQualityTests(unittest.TestCase):
    def test_specks_clean_without_contour_loss(self):
        im=Image.new('RGBA',(128,128));d=ImageDraw.Draw(im);d.rectangle((40,30,90,100),fill='#C08040')
        for i in range(17):d.point((3+i*7,5),fill=(255,255,255,60))
        self.assertIn('isolated_specks',alpha_contract(im)['issues'])
        cleaned,r=clean_sprite(im);self.assertEqual(r['removed_speck_pixels'],17);self.assertEqual(r['opaque_pixel_change_ratio'],0)
        self.assertEqual(alpha_contract(cleaned)['status'],'PASS')

    def test_false_straight_premultiplication(self):
        im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im)
        d.rectangle((10,10,53,53),fill=(200,100,50,255));d.rectangle((9,9,54,54),outline=(100,50,25,128))
        self.assertIn('premultiplied_declared_straight',alpha_contract(im)['issues'])
        self.assertEqual(alpha_contract(im,'premultiplied')['status'],'PASS')

    def test_bilinear_rejected_nearest_preserves_palette(self):
        im=Image.new('RGBA',(64,64));ImageDraw.Draw(im).polygon([(8,55),(30,6),(55,55)],fill='#AA5511')
        pal=palette_of([im]);nearest=im.resize((192,192),Image.Resampling.NEAREST);blur=im.resize((192,192),Image.Resampling.BILINEAR)
        self.assertEqual(pixel_qa([nearest],pal,(64,64),3)['status'],'PASS')
        self.assertEqual(pixel_qa([blur],pal,(64,64),3)['status'],'FAIL')


if __name__=='__main__':unittest.main()
