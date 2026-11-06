import unittest
from image_fixtures import ImageCase,ROOT
from image_identity import build,check
from identity_engine import verdict,engine


class IdentityRound4(ImageCase):
 def test_fixed_axes_reviewer_measurements(self):
  for structure,colour,expected in [(0.761,.8585,'unassessed'),(.552,.7147,'unassessed'),(.878,.068,'identity_fail'),(.324,.490,'identity_fail'),(.740,.465,'identity_fail'),(.805,.815,'unassessed'),(.88,.88,'pass')]:
   self.assertEqual(verdict(dict(structure=structure,colour=colour)),expected)

 @unittest.skipUnless(engine()[0] is not None,'optional DINOv2 model/runtime unavailable')
 def test_real_action_and_prop_abstain_without_impostor_pass(self):
  p=ROOT/'tests/fixtures/live-s13-r4';ref=self.path/'tinroot.json'
  build('Tinroot',[p/n/'image-1.png' for n in ['refFront','refSide','refBack']],ref,negative=[p/'impRecolor/image-1.png',p/'impPalette/image-1.png'])
  for path in [p/'refAction/image-1.png',p/'spHose/asset.png']:
   result=check(path,ref)
   self.assertEqual(result['status'],'unassessed',result)
   self.assertEqual(result['reason'],'pose_or_prop_change')
  for n in ['impRecolor','impPalette','impSilhouette','impTwin']:
   self.assertNotEqual(check(p/n/'image-1.png',ref)['status'],'pass',n)
