from image_fixtures import ImageCase,ROOT
from image_identity import build
from image_keyframes import keyframes
from image_common import read
from test_image_keyframes import board
from PIL import Image
import unittest
from identity_engine import engine

class RetryRound3(ImageCase):
 @unittest.skipUnless(engine()[0] is not None,'optional DINOv2 model/runtime unavailable')
 def test_real_two_axis_character_fail_reaches_retry(self):
  p=ROOT/'tests/fixtures/live-s13-r3';ref=self.path/'bramble.json'
  build('Bramble',[p/n/'image-1.png' for n in ['refFront','refSide','refBack','refAction']],ref,negative=[p/'impSpecies/image-1.png',p/'impRecolor/image-1.png'])
  # Match the returned image's aspect rather than invoking a crop refusal.
  src=p/'impRecolor/image-1.png'
  with Image.open(src) as im:w,h=im.size
  b=board();b.update(width=w,height=h);b['shots']=b['shots'][:1]
  self.configure(image=str(src));result=keyframes(b,self.adapter,self.path/'kf',self.request(refset_path=str(ref)))
  self.assertEqual(len(self.calls()),2);self.assertIn('Identity correction',self.calls()[1]['stdin'])
  shot=result['shots'][0];self.assertNotIn('keyframe_failure',shot);self.assertEqual(shot['keyframe']['status'],'identity_fail')
  self.assertEqual(read(shot['keyframe']['gen_manifest'])['qa']['identity']['status'],'identity_fail')

 def test_real_scene_unassessed_does_not_retry(self):
  p=ROOT/'tests/fixtures/live-s13-r3';ref=self.path/'bramble.json'
  build('Bramble',[p/n/'image-1.png' for n in ['refFront','refSide','refBack','refAction']],ref,negative=[p/'impSpecies/image-1.png'])
  src=p/'kf/shot-1/keyframe.png';b=board();b['shots']=b['shots'][:1]
  self.configure(image=str(src));result=keyframes(b,self.adapter,self.path/'kf',self.request(refset_path=str(ref)))
  self.assertEqual(len(self.calls()),1);shot=result['shots'][0];self.assertIn('keyframe',shot)
  self.assertEqual(read(shot['keyframe']['gen_manifest'])['qa']['identity']['status'],'unassessed')
