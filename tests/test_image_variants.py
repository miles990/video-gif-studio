from PIL import Image,ImageDraw
from image_fixtures import ImageCase
from image_common import ImageError,read,write
from image_variants import variants,pick
from test_image_keyframes import board


class VariantTests(ImageCase):
    def setUp(self):
        super().setUp();paths=[]
        for i in range(3):
            im=Image.new('RGB',(90,160),'#234655');d=ImageDraw.Draw(im)
            if i==0:d.ellipse((5,10,65,70),fill='gold');d.rectangle((40,105,80,155),fill='red')
            if i==1:d.polygon([(5,140),(85,140),(75,10)],fill='gold');d.ellipse((5,10,35,40),fill='red')
            if i==2:d.rectangle((5,20,35,145),fill='gold');d.rectangle((50,60,85,90),fill='red')
            path=self.path/f'v{i}.png';im.save(path);paths.append(str(path))
        self.configure(images=paths)

    def test_different_moving_candidates_cache_and_user_pick(self):
        out=self.path/'variants';result=variants(self.adapter,self.request(n=3),out,shot='2',board=board())
        self.assertTrue(result['distinct'],result['pairwise']);self.assertIsNone(result['user_pick'])
        for c in result['candidates']:
            with Image.open(out/c['preview']) as im:self.assertGreater(im.n_frames,1)
        page=(out/'pick.html').read_text(encoding='utf-8');self.assertNotIn('https://',page);self.assertIn('keydown',page);self.assertIn('picks.json',page)
        variants(self.adapter,self.request(n=3),self.path/'again',shot='2',board=board());self.assertEqual(len(self.calls()),3)
        selection=pick(out,'v2');self.assertEqual(selection['chooser'],'user')
        chosen=read(selection['storyboard']);self.assertEqual(chosen['shots'][1]['keyframe']['sha256'],result['candidates'][1]['sha256'])
        self.assertNotIn('keyframe',chosen['shots'][0]);self.assertEqual(len(read(out/'picks.json')),1)

    def test_invalid_counts_no_calls_and_duplicate_detection(self):
        for n in (1,9):
            with self.assertRaises(ImageError):variants(self.adapter,self.request(n=n),self.path/str(n))
        self.assertEqual(self.calls(),[])
        self.configure();result=variants(self.adapter,self.request(n=2),self.path/'same')
        self.assertFalse(result['distinct']);self.assertEqual(result['technical_status'],'variants_not_distinct')
