import os
import unittest
from unittest.mock import patch
from image_fixtures import ImageCase,ROOT
from image_common import ImageError,write
from image_identity import build,check,load
from identity_engine import verdict,engine

class IdentityRound3(ImageCase):
 @unittest.skipUnless(engine()[0] is not None,'optional DINOv2 model/runtime unavailable')
 def test_model_path_never_runs_orb(self):
  p=ROOT/'tests/fixtures/live-s13';out=self.path/'dino.json'
  with patch('cv2.ORB_create',side_effect=AssertionError('ORB is fallback only')):
   build('fox',[p/'ref1/image-1.png',p/'ref2/image-1.png'],out,negative=[p/'neg/image-1.png'])
   self.assertEqual(check(p/'ref1/image-1.png',out)['status'],'pass')

 @unittest.skipUnless(engine()[0] is not None,'optional DINOv2 model/runtime unavailable')
 def test_held_out_poses_and_impostors(self):
  p=ROOT/'tests/fixtures/live-s13-r3';names=['refFront','refSide','refBack','refAction']
  for held in names:
   ref=self.path/(held+'.json')
   build('Bramble',[p/n/'image-1.png' for n in names if n!=held],ref,negative=[p/'impSpecies/image-1.png',p/'impRecolor/image-1.png'])
   self.assertEqual(check(p/held/'image-1.png',ref)['status'],'pass',held)
   for imp in ['impSpecies','impRecolor']:
    self.assertEqual(check(p/imp/'image-1.png',ref)['status'],'identity_fail',imp)

 @unittest.skipUnless(engine()[0] is not None,'optional DINOv2 model/runtime unavailable')
 def test_rejected_library_is_not_written_and_bad_load_is_clear(self):
  p=ROOT/'tests/fixtures/live-s13-r3';out=self.path/'bad.json'
  with self.assertRaises(ImageError):build('mixed',[p/'refFront/image-1.png',p/'impRecolor/image-1.png'],out,negative=[p/'impSpecies/image-1.png'])
  self.assertFalse(out.exists())
  write(out,{'status':'rejected'})
  with self.assertRaises(ImageError) as cm:load(out)
  self.assertEqual(cm.exception.error['code'],'E_REFSET_INVALID')

 def test_missing_model_is_unassessed_and_overrides_work(self):
  p=ROOT/'tests/fixtures/live-s13';out=self.path/'ref.json'
  with patch.dict(os.environ,{'VGS_DINO_MODEL':str(self.path/'missing.onnx')}):
   build('fox',[p/'ref1/image-1.png',p/'ref2/image-1.png'],out,negative=[p/'neg/image-1.png'])
   result=check(p/'neg/image-1.png',out)
   self.assertEqual(result['status'],'unassessed');self.assertIn('fallback',result['reason'])
   self.assertEqual(check(p/'neg/image-1.png',out,identity_override='different')['status'],'identity_fail')

 def test_axes_are_independent_with_abstention_band(self):
  self.assertEqual(verdict(dict(structure=.95,colour=.4)),'identity_fail')
  self.assertEqual(verdict(dict(structure=.5,colour=.95)),'unassessed')
  self.assertEqual(verdict(dict(structure=.81,colour=.95)),'unassessed')
