from image_fixtures import ImageCase,ROOT
from image_keyframes import keyframes
from image_common import read
from test_image_keyframes import board
from unittest.mock import patch
class LiveCapTests(ImageCase):
 def test_identity_retry_cap_retains_first(self):
  # Match the requested 9:16 canvas so aspect fitting cannot hide retry reachability.
  self.configure(image=str(self.fixture))
  self.adapter.cap=1;b=board();b['shots']=b['shots'][:1]
  with patch('image_identity.check',return_value=dict(status='identity_fail')) as identity,patch.object(self.adapter,'generate',wraps=self.adapter.generate) as generate:
   result=keyframes(b,self.adapter,self.path/'kf',self.request(refset_path='test-refset'))
  self.assertEqual(generate.call_count,2)
  self.assertIn('identity-retry',str(generate.call_args_list[1].args[1]))
  identity.assert_called_once()
  shot=result['shots'][0]
  self.assertIn('keyframe',shot);self.assertNotIn('keyframe_failure',shot)
  self.assertEqual(shot['keyframe']['status'],'identity_fail')
  manifest=read(shot['keyframe']['gen_manifest'])
  self.assertEqual(manifest['qa']['identity']['retry_error']['code'],'E_CAP')
  self.assertEqual(manifest['qa']['identity']['generation_retained'],'first')
  self.assertEqual(len(self.calls()),1)
