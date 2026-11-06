from PIL import Image
from image_fixtures import ImageCase,ROOT
from image_identity import controls,build,check
from unittest.mock import patch
import unittest
from identity_engine import engine
LIVE=ROOT/'tests/fixtures/live-s13'
class LiveIdentityTests(ImageCase):
 def test_failed_controls_are_unassessed(self):
  a=LIVE/'ref1/image-1.png';b=LIVE/'ref2/image-1.png'
  prior=controls(a,b,b)
  self.assertFalse(prior['valid'])
  self.assertFalse(controls(a,a,LIVE/'neg/image-1.png')['valid'])
  ref=self.path/'refs.json';build('live',[a,b],ref,negative=[b])
  self.assertEqual(check(LIVE/'kf/shot-2/keyframe.png',ref)['status'],'unassessed')
 @unittest.skipUnless(engine()[0] is not None,'optional DINOv2 model/runtime unavailable')
 def test_live_controls_have_margin(self):
  prior=controls(LIVE/'ref1/image-1.png',LIVE/'ref2/image-1.png',LIVE/'neg/image-1.png')
  self.assertTrue(prior['valid'],prior)
  self.assertGreater(min(p['colour'] for p in prior['positive']),max(p['colour'] for p in prior['negative']))
 def test_scene_features_use_subject_region(self):
  from image_identity import subject_region
  import numpy as np
  with Image.open(LIVE/'kf/shot-2/keyframe.png') as im:mask,method=subject_region(np.array(im.convert('RGBA')))
  self.assertGreater(mask.mean(),.01);self.assertLess(mask.mean(),.95)
  self.assertIn(method,('alpha','uniform_background','saliency'))
 def test_unassessed_does_not_regenerate(self):
  from image_keyframes import keyframes
  from test_image_keyframes import board
  a=LIVE/'ref1/image-1.png';b=LIVE/'ref2/image-1.png';ref=self.path/'refs.json'
  build('live',[a,b],ref,negative=[b]);self.configure(image=str(LIVE/'kf/shot-2/keyframe.png'))
  one=board();one['shots']=one['shots'][:1]
  result=keyframes(one,self.adapter,self.path/'kf',self.request(refset_path=str(ref)))
  self.assertEqual(len(self.calls()),1);self.assertIn('keyframe',result['shots'][0])

 def test_live_scene_keyframes_are_not_false_identity_failures(self):
  ref=self.path/'refs.json';build('live',[LIVE/'ref1/image-1.png',LIVE/'ref2/image-1.png'],ref,negative=[LIVE/'neg/image-1.png'])
  for path in sorted((LIVE/'kf').glob('*/generation/image-1.png')):
   self.assertEqual(check(path,ref)['status'],'unassessed',str(path))
