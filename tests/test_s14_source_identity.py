from image_fixtures import ImageCase
from game_character import sheet
from unittest.mock import patch
from PIL import Image,ImageDraw

class SourceIdentityTests(ImageCase):
    def test_64px_delivery_keeps_full_resolution_identity_evidence(self):
        im=Image.new('RGBA',(256,256));ImageDraw.Draw(im).rectangle((60,30,190,230),fill='orange');im.save(self.fixture)
        result=sheet(self.adapter,self.request(),self.path/'sheet',pixel=64)
        self.assertEqual(result['identity']['measurement_stage'],'source_before_downscale')
        self.assertEqual(result['identity']['source_sizes']['front'],[256,256])
        self.assertEqual(Image.open(self.path/'sheet/views/front.png').size,(64,64))
        self.assertEqual(Image.open(self.path/'sheet/identity/front.png').size,(256,256))
