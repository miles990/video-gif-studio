import json,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from image_fixtures import ImageCase,ROOT,intended_gaps
from image_alpha import alpha_qa
from image_motion import seam_qa
from image_identity import build
from identity_engine import engine
from test_s13_r3_motion import breathe
import test_s13_r4_alpha


class LowRound4(ImageCase):
 def test_default_review_uses_system_temp_and_explicit_path_is_honoured(self):
  im=test_s13_r4_alpha.AlphaRound4.art(self)
  with patch('tempfile.gettempdir',return_value=str(self.path)):
   result=alpha_qa(im,judge=intended_gaps)
  target=Path(result['hole_review']['overlay_path'])
  self.assertEqual(target.parent.parent,self.path)
  self.assertTrue(target.is_file())
  result=alpha_qa(im,judge=intended_gaps,overlay_path=self.path/'output/holes.png')
  self.assertEqual(Path(result['hole_review']['overlay_path']),self.path/'output/holes.png')

 @unittest.skipUnless(engine()[0] is not None,'optional DINOv2 model/runtime unavailable')
 def test_rustbud_reference_warns_with_and_without_negative_controls(self):
  p=ROOT/'tests/fixtures/live-s13-r4'
  for negatives in ([],[p/'impRecolor/image-1.png',p/'impPalette/image-1.png']):
   result=build('mixed twin',[p/n/'image-1.png' for n in ['refFront','refSide','refBack','refAction','impTwin']],self.path/'refs.json',negative=negatives)
   warning=next(w for w in result['warnings'] if w['code']=='W_REFSET_AMBIGUOUS')
   self.assertIn(5,[c['index'] for c in warning['candidates']])

 def test_two_frame_jumps_four_sets_and_wrap(self):
  sources=['live-s13/sprite/cleaned.png','live-s13-r2/sprite2/native/image-1.png','live-s13-r3/spRing/native/image-1.png','live-s13-r4/spHose/asset.png']
  for source in sources:
   frames=breathe(ROOT/'tests/fixtures'/source)
   self.assertEqual(seam_qa(frames)['status'],'PASS',source)
   for px in (6,12):
    for axis in (0,1):
     for start in (16,31):
      jumped=frames.copy()
      for i in (start,(start+1)%len(frames)):jumped[i]=Image.fromarray(np.roll(np.array(frames[i]),px,axis=axis))
      result=seam_qa(jumped)
      self.assertIn('short_position_jump',result['issues'],(source,px,axis,start,result))
