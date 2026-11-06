import sys
from pathlib import Path
import unittest
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from game_character import originality,palette_of,quantize,expressions_qa
from image_common import ImageError


class CharacterTests(unittest.TestCase):
    def test_originality_accepts_originals_offers_different_design(self):
        for prompt in ['ice sword fox','16-bit JRPG scout','moth knight','blue axolotl','amber owl','銀河惡魔城風的手繪','拿冰劍的狐狸劍士','brass beetle','snow rabbit','clockwork deer']:
            self.assertEqual(originality(prompt)['action'],'proceed')
        for prompt in ['make Sonic','皮卡丘','identical to my favourite game character']:
            with self.assertRaises(ImageError) as e:originality(prompt)
            self.assertEqual(e.exception.error['originality']['action'],'offered_original')
            self.assertGreaterEqual(len(e.exception.error['design_changes']),3)

    def test_palette_and_quantize_preserve_known_colors(self):
        im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im)
        colors=['#E07A2E','#F4EDE4','#2BB5B0','#9FE3FF','#FF2BD6']
        for i,c in enumerate(colors):d.rectangle((8+i*9,8,15+i*9,55),fill=c)
        pal=palette_of([im]);self.assertEqual(set(colors),{c['hex'] for c in pal})
        self.assertEqual(quantize(im,pal).tobytes(),im.tobytes())
        enlarged=quantize(im,pal,(128,128));self.assertEqual(set(map(tuple,np.array(enlarged).reshape(-1,4))),set(map(tuple,np.array(im).reshape(-1,4))))

    def test_expression_qa_detects_copies_and_costume_changes(self):
        im=Image.new('RGBA',(64,64),'orange');other=im.copy();ImageDraw.Draw(other).rectangle((0,50,63,63),fill='blue')
        r=expressions_qa(im,{'a':im,'b':other},(10,10,20,20))
        self.assertEqual(r['status'],'fail');self.assertFalse(r['outside'][1]['pass_outside']);self.assertFalse(r['face_pairs'][0]['different'])


if __name__=='__main__':unittest.main()
