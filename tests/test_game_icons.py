import sys
from pathlib import Path
import unittest
from PIL import Image,ImageDraw
import numpy as np
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

    def test_light_direction_uses_cartesian_upper_left(self):
        im=self.icon();a=np.array(im)
        yy,xx=np.indices(a.shape[:2]);inside=(xx>=10)&(xx<54)&(yy>=10)&(yy<54)
        brightness=210-xx-yy;a[...,:3][inside]=brightness[inside,None]
        result=style_qa([Image.fromarray(a)],self.token)
        self.assertAlmostEqual(result['icons'][0]['light'],135,delta=1)
        self.assertFalse(any(i['kind']=='light' for i in result['issues']))
        a[...,:3][inside]=(255-brightness[inside])[:,None]
        self.assertTrue(any(i['kind']=='light' for i in style_qa([Image.fromarray(a)],self.token)['issues']))


if __name__=='__main__':unittest.main()
