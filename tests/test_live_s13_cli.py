import contextlib,io,json,sys,subprocess
import numpy as np
from PIL import Image
from image_fixtures import ImageCase,ROOT
from image_common import ImageError,write
from image_route import Adapter
from image_identity import build
from image_alpha import transparent_asset
from test_image_keyframes import board
LIVE=ROOT/'tests/fixtures/live-s13'
class LiveCliTests(ImageCase):
 def cli(self,*args):
  return subprocess.run([sys.executable,str(ROOT/'scripts/imagegen.py'),*map(str,args)],capture_output=True,text=True)
 def test_variants_without_prompt(self):
  self.configure(image=str(LIVE/'kf/shot-2/keyframe.png'));path=self.path/'board.json';write(path,board())
  result=self.cli('variants','--experimental','--storyboard',path,'--n',2,'--out',self.path/'variants','--codex',self.fake,'--state',self.path/'state')
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_auth_and_missing_cli_list_alternatives(self):
  for missing in (False,True):
   self.configure(login='Not logged in')
   adapter=Adapter(self.path/'state',codex='missing-codex-executable' if missing else [sys.executable,str(self.fake)])
   with self.assertRaises(ImageError) as cm:adapter.generate(self.request(),self.path/str(missing))
   self.assertGreaterEqual(len(cm.exception.error['alternatives']),2)
 def test_partial_keyframes_exit_nonzero(self):
  path=self.path/'board.json';b=board();b['shots']=b['shots'][:2];write(path,b)
  self.configure(image=str(LIVE/'kf/shot-2/keyframe.png'))
  result=self.cli('keyframes',path,'--experimental','--out',self.path/'kf','--codex',self.fake,'--state',self.path/'state','--cap',1)
  self.assertEqual(result.returncode,2,result.stdout);data=json.loads(result.stdout);self.assertFalse(data['ok']);self.assertIn('keyframe',data['result']['shots'][0])
 def test_svg_error_is_structured_with_location(self):
  path=self.path/'unsafe.svg';path.write_text('<svg><script/></svg>');plan=self.path/'plan.json';write(plan,dict(segments=[],assets=[dict(image=str(path))]))
  result=subprocess.run([sys.executable,str(ROOT/'scripts/fx_render.py'),str(plan),'--validate','--json','--no-user-fx'],capture_output=True,text=True)
  self.assertEqual(result.returncode,2);data=json.loads(result.stderr);self.assertEqual(data['error']['code'],'E_SVG_UNSAFE');self.assertIn(str(path),data['error']['location'])
 def test_mixed_refs_list_all_suspicious_images(self):
  refs=[LIVE/'ref1/image-1.png',LIVE/'ref2/image-1.png',LIVE/'neg/image-1.png',LIVE/'cafe-matcha.png']
  with self.assertRaises(ImageError) as cm:build('mixed',refs,self.path/'refs.json')
  self.assertEqual(cm.exception.error['suspect_indices'],[1,2,3,4]);self.assertEqual(len(cm.exception.error['suspect_images']),4)
 def test_fake_transparency_record_survives_matting(self):
  with Image.open(LIVE/'sprite/cleaned.png') as im:sprite=im.convert('RGBA').resize((512,512))
  yy,xx=np.indices((512,512));gray=np.where((xx//16+yy//16)%2,204,255).astype('uint8')
  native=Image.fromarray(np.repeat(gray[...,None],3,axis=2)).convert('RGBA');native.alpha_composite(sprite);native.save(self.fixture)
  backing=Image.new('RGBA',sprite.size,(0,255,0,255));backing.alpha_composite(sprite);p=self.path/'backing.png';backing.save(p)
  self.configure(images=[str(self.fixture),str(p)])
  from unittest.mock import patch
  with patch('image_alpha.choose_backing',return_value=([0,255,0],100)):
   report=transparent_asset(self.adapter,self.request(),self.path/'asset')
  self.assertTrue(report['fake_transparency_detected'])
