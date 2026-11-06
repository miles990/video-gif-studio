from image_fixtures import ImageCase
from game_icons import iconset,style_qa
from PIL import Image,ImageDraw

class IconFixTests(ImageCase):
    def test_first_icon_has_generated_style_anchor(self):
        im=Image.new('RGBA',(64,64));ImageDraw.Draw(im).rectangle((10,6,53,57),fill='#808060',outline='#20182A',width=2);im.save(self.fixture)
        token=dict(grid=64,outline_hex='#20182A',outline_px=2,light_deg=135,safe_margin=4,palette=['#20182A','#808060'],shading='flat')
        result=iconset(self.adapter,self.request(),['shield','key'],token,self.path/'icons',pixel=True)
        self.assertTrue(result['records'][0]['refs_sent'])
        self.assertTrue(result['records'][1]['refs_sent'])
        self.assertIn('set_drift',result['qa'])
        self.assertEqual(result['style_anchor']['source'],'generated')

    def test_whole_set_outline_drift(self):
        im=Image.new('RGBA',(64,64));ImageDraw.Draw(im).rectangle((10,6,53,57),fill='#808060',outline='#20182A',width=4)
        token=dict(grid=64,outline_hex='#20182A',outline_px=2,light_deg=135,safe_margin=4,palette=[],shading='flat')
        q=style_qa([im,im],token)
        self.assertGreater(q['set_drift']['outline_px'],1)
