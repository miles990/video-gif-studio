from image_fixtures import ImageCase,ROOT
from image_identity import build,check,controls
from image_common import read
import unittest
from identity_engine import engine

class IdentityRound2(ImageCase):
 @unittest.skipUnless(engine()[0] is not None,'optional DINOv2 model/runtime unavailable')
 def test_pose_varied_frog_references(self):
  p=ROOT/'tests/fixtures/live-s13-r2';ref=self.path/'frog.json'
  result=build('frog',[p/'refA/image-1.png',p/'refB/image-1.png'],ref,negative=[p/'neg/image-1.png'])
  self.assertTrue(result['controls']['valid'])
  self.assertEqual(check(p/'refB/image-1.png',ref)['status'],'pass')
  self.assertNotEqual(check(p/'imp/image-1.png',ref)['status'],'pass')
  for name in ('kf/shot-1','kf/shot-2','kf/shot-3','kfsq/shot-1'):
   self.assertNotEqual(check(p/name/'keyframe.png',ref)['status'],'identity_fail')

 def test_explicit_human_override_recorded(self):
  p=ROOT/'tests/fixtures/live-s13-r2';ref=self.path/'frog.json'
  result=build('frog',[p/'refA/image-1.png',p/'refB/image-1.png'],ref,identity_override='same')
  self.assertEqual(read(ref)['identity_override']['decision'],'same')
  # Refset approval does not assert every generated image has the same identity.
  self.assertEqual(check(p/'imp/image-1.png',ref)['status'],'unassessed')
  verdict=check(p/'imp/image-1.png',ref,identity_override='different')
  self.assertEqual(verdict['status'],'identity_fail')
  self.assertEqual(verdict['identity_override']['decision'],'different')
