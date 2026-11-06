from image_fixtures import ImageCase,ROOT
from image_motion import loop_keyframes,seam_qa,repair_loop
from PIL import Image,ImageEnhance
import numpy as np
from unittest.mock import patch
LIVE=ROOT/'tests/fixtures/live-s13'
class LiveMotionTests(ImageCase):
 def frames(self):
  return [Image.open(p).convert('RGBA') for p in sorted((LIVE/'sprite_loop').glob('*.png'))]
 def test_live_clipping_is_measured(self):
  qa=seam_qa(self.frames());self.assertGreater(qa['clipped_frames'],0);self.assertEqual(qa['status'],'FAIL')
 def test_colour_seam_and_preloop_pause(self):
  frames=self.frames()
  # Use the same live artwork with isolated colour/timing faults.
  frames=[f.resize((192,192)) for f in frames]
  colour=frames.copy();a=np.array(colour[-1]);a[...,:3]=255-a[...,:3];colour[-1]=Image.fromarray(a)
  self.assertIn('colour_seam',seam_qa(colour)['issues'])
  paused=frames[:-4]+[frames[-5]]*4
  self.assertIn('speed_discontinuity',seam_qa(paused)['issues'])
  timed=seam_qa(frames,[40]*23+[800]);self.assertIn('speed_discontinuity',timed['issues'])
 def test_single_image_sway_has_no_scaling_or_clipping(self):
  with patch('image_motion.deliver',side_effect=lambda frames,durations,out,manifest,*a:dict(frames=frames,manifest=manifest)):
   result=loop_keyframes([LIVE/'sprite/cleaned.png'],self.path/'loop',frames=24,size=(256,256))
  boxes=[f.getbbox() for f in result['frames']]
  widths=[b[2]-b[0] for b in boxes];heights=[b[3]-b[1] for b in boxes]
  self.assertLessEqual(max(widths)-min(widths),2);self.assertLessEqual(max(heights)-min(heights),2)
  self.assertEqual(seam_qa(result['frames'])['clipped_frames'],0)
  self.assertIn('placeholder',result['manifest']['note'])
 def test_repair_duration_within_ten_percent(self):
  paths=sorted((LIVE/'sprite_loop').glob('*.png'))
  with patch('image_motion.deliver',side_effect=lambda frames,durations,*a:dict(duration=sum(durations))):
   result=repair_loop(paths,[80]*len(paths),self.path/'repair')
  self.assertLessEqual(abs(result['duration']/(80*len(paths))-1),.10)

 def test_live_sprite_delivered_sway_and_repair(self):
  result=loop_keyframes([LIVE/'sprite/cleaned.png'],self.path/'sway',frames=24,frame_ms=80,size=(128,128))
  self.assertEqual(result['loop']['status'],'PASS')
  paths=sorted((self.path/'sway/frames').glob('*.png'))[:18]
  repaired=repair_loop(paths,[80]*len(paths),self.path/'repaired')
  self.assertEqual(repaired['loop']['status'],'PASS')
  self.assertEqual(repaired['media_qa_loop']['level'],'PASS')
  self.assertLessEqual(abs(sum(repaired['durations_ms'])/(80*len(paths))-1),.10)
