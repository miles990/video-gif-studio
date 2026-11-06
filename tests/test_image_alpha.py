import numpy as np
from PIL import Image,ImageDraw
from image_fixtures import ImageCase
from image_alpha import alpha_qa,checkerboard,cleanup,matte_uniform,transparent_asset


def sticker():
    im=Image.new('RGBA',(320,320));d=ImageDraw.Draw(im);d.ellipse((40,40,280,280),fill='#c64020')
    return im.resize((160,160),Image.Resampling.BOX)


class AlphaTests(ImageCase):
    def test_alpha_halo_and_speck_controls(self):
        im=sticker();report=alpha_qa(im);self.assertEqual(report['status'],'PASS',report)
        a=np.array(im);semi=(a[...,3]>0)&(a[...,3]<250);a[...,:3][semi]=255;a[2:4,2:4]=[255,255,255,80]
        bad=Image.fromarray(a);self.assertIn('halo',alpha_qa(bad)['issues'])
        cleaned,result=cleanup(bad);self.assertEqual(result['after']['status'],'PASS',result)
        self.assertGreater(result['removed_speck_pixels'],0);self.assertGreater(result['despilled_pixels'],0)
        self.assertGreater(np.sum((np.array(cleaned)[...,3]>0)&(np.array(cleaned)[...,3]<255)),0)

    def test_checkerboard_and_interior_tablecloth_negative(self):
        yy,xx=np.indices((160,160));gray=np.where((xx//16+yy//16)%2,204,255).astype('uint8')
        rgb=np.repeat(gray[...,None],3,axis=2);im=Image.fromarray(rgb)
        self.assertTrue(alpha_qa(im)['fake_transparency'])
        rgb[:20]=[25,60,80];rgb[-20:]=[25,60,80];rgb[:,:20]=[25,60,80];rgb[:,-20:]=[25,60,80]
        self.assertFalse(alpha_qa(Image.fromarray(rgb))['fake_transparency'])

    def test_uniform_matting_and_native_delivery(self):
        im=sticker();background=Image.new('RGBA',im.size,(0,255,0,255));background.alpha_composite(im)
        result=matte_uniform(background,[0,255,0]);self.assertEqual(alpha_qa(result)['status'],'PASS')
        im.save(self.fixture);result=transparent_asset(self.adapter,self.request(),self.path/'asset')
        self.assertEqual(result['alpha_source'],'native');self.assertTrue((self.path/'asset/asset.gif').exists())
