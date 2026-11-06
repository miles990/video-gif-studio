import sys,unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from game_sprite import alpha_contract
from game_character import prepare_subject
from image_common import read,write,ImageError
from test_game_engines import EngineTests
from game_engines import export_engines

class AlphaFixTests(unittest.TestCase):
    def test_original_pixel_highlights_are_not_outside_halo(self):
        from game_character import palette_of,quantize
        with Image.open('tests/fixtures/live-s14/rimewick-side.png') as raw:im,_=prepare_subject(raw.convert('RGBA'),'side')
        im=quantize(im,palette_of([im]),(64,64))
        self.assertNotIn('opaque_rim_halo',alpha_contract(im)['issues'])

    def test_opaque_rim_halo(self):
        yy,xx=np.mgrid[:256,:256];d=np.hypot(xx-128,yy-128)
        a=np.zeros((256,256,4),np.uint8);a[...,:3]=(224,122,46);a[...,3]=np.rint(np.clip((90-d)/2+.5,0,1)*255);a[a[...,3]==0]=0
        self.assertEqual(alpha_contract(Image.fromarray(a))['status'],'PASS')
        band=(a[...,3]>0)&(d>87.5);a[band,:3]=np.rint(a[band,:3]*.2+255*.8)
        self.assertIn('opaque_rim_halo',alpha_contract(Image.fromarray(a))['issues'])

    def test_white_backing_takes_matting_route(self):
        im=Image.new('RGB',(128,128),'white');ImageDraw.Draw(im).rectangle((40,20,88,110),fill='orange')
        result,report=prepare_subject(im.convert('RGBA'))
        self.assertEqual(report['alpha_source'],'matted')
        self.assertEqual(result.getpixel((0,0))[3],0)
        self.assertEqual(result.getpixel((64,60))[3],255)

class RestoreTests(EngineTests):
    def test_chinese_state_and_explicit_trim_restore(self):
        m=read(self.manifests[1]);m['state']='攻擊';r=m['frames'][0];p=self.manifests[1].parent/r['file']
        with Image.open(p) as im:crop=im.crop((4,3,28,30))
        crop.save(p);r['trim_offset']=[4,3];write(self.manifests[1],m)
        out=self.path/'restored';packed=export_engines(self.manifests,out)
        self.assertIn('attack',packed['states']);self.assertEqual(packed['states']['attack']['original_state'],'攻擊')
        restored=Image.open(out/'frames/00003.png').convert('RGBA')
        self.assertEqual(restored.size,(32,32));self.assertEqual(restored.getpixel((6,5)),(190,100,50,255))

    def test_missing_trim_offset_names_bad_file(self):
        p=self.manifests[0].parent/'1.png';Image.new('RGBA',(20,20)).save(p)
        with self.assertRaises(ImageError) as e:export_engines(self.manifests,self.path/'bad')
        self.assertIn('1.png',e.exception.error['message'])
