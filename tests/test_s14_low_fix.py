from image_fixtures import ImageCase
from image_common import read
from game_video import estimate
from game_tiles import tileset

class LowFixTests(ImageCase):
    def test_estimates_survive_other_route_and_request(self):
        a=estimate(self.fixture,self.fixture,[],'grok',self.path/'est')
        b=estimate(self.fixture,self.fixture,[],'fal',self.path/'est')
        c=estimate(self.fixture,self.fixture,[],'grok',self.path/'est',duration=6)
        self.assertEqual(estimate(self.fixture,self.fixture,[],'grok',self.path/'est')['estimate_id'],a['estimate_id'])
        self.assertEqual(len(list((self.path/'est/estimates').glob('*.json'))),3)
        self.assertNotEqual(a['estimate_id'],b['estimate_id'])

    def test_tiles_follow_color_prompt(self):
        r=tileset(self.path/'tiles',prompt='violet rock and turquoise moss #663399 #40E0D0')
        self.assertEqual(r['palette'],['#663399','#40E0D0'])
        self.assertEqual(r['qa']['status'],'PASS')
