from image_fixtures import ImageCase,ROOT
from image_keyframes import keyframes
from image_common import read
from test_image_keyframes import board
from unittest.mock import patch
class LiveCapTests(ImageCase):
 def test_identity_retry_cap_retains_first(self):
  self.configure(image=str(ROOT/'tests/fixtures/live-s13/kf/shot-4/generation/image-1.png'))
  self.adapter.cap=1;b=board();b['shots']=b['shots'][:1]
  with patch('image_identity.check',return_value=dict(status='identity_fail')):
   result=keyframes(b,self.adapter,self.path/'kf',self.request(refset_path='test-refset'))
  shot=result['shots'][0]
  self.assertIn('keyframe',shot);self.assertNotIn('keyframe_failure',shot)
  self.assertEqual(shot['keyframe']['status'],'identity_fail')
  manifest=read(shot['keyframe']['gen_manifest'])
  self.assertEqual(manifest['qa']['identity']['retry_error']['code'],'E_CAP')
  self.assertEqual(manifest['qa']['identity']['generation_retained'],'first')
  self.assertEqual(len(self.calls()),1)
