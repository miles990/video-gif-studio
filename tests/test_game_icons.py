import sys
from pathlib import Path
import unittest
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from game_icons import style_qa


class IconTests(unittest.TestCase):
    def setUp(self):
        self.token=dict(grid=64,outline_hex='#20182A',outline_px=2,light_deg=135,safe_margin=4,palette=['#20182A','#808060'],shading='cel')
    def icon(self,width=2,size=48,color='#808060'):
        im=Image.new('RGBA',(64,64));x=(64-size)//2;d=ImageDraw.Draw(im);d.rectangle((x,x,x+size-1,x+size-1),fill=color,outline='#20182A',width=width);return im
    def test_good_flat_icons_and_indexed_outliers(self):
        icons=[self.icon() for _ in range(8)];self.assertEqual(style_qa(icons,self.token,True)['status'],'PASS')
        icons[3]=self.icon(width=4);icons[6]=self.icon(size=30);icons[7]=self.icon(color='#808010')
        result=style_qa(icons,self.token,True);self.assertTrue({3,6,7}<=set(result['outlier_indices']))
        self.assertTrue(any(i['index']==3 and i['kind']=='outline' for i in result['issues']))


if __name__=='__main__':unittest.main()
