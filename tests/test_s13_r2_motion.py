from image_fixtures import ImageCase,ROOT
from image_motion import seam_qa,repair_loop
from PIL import Image,ImageOps
import numpy as np

def bob(path,count,amplitude):
 with Image.open(path) as im: sprite=ImageOps.contain(im.convert('RGBA'),(72,96))
 frames=[]
 for i in range(count):
  frame=Image.new('RGBA',(128,128));frame.alpha_composite(sprite,((128-sprite.width)//2,16+round(amplitude*np.sin(2*np.pi*i/count))))
  frames.append(frame)
 return frames

class MotionRound2(ImageCase):
 def test_clean_bobs_both_live_sets_and_opaque(self):
  for path in (ROOT/'tests/fixtures/live-s13/sprite/cleaned.png',ROOT/'tests/fixtures/live-s13-r2/sprite2/native/image-1.png'):
   for count,amplitude in ((48,6),(48,12),(32,3)):
    frames=bob(path,count,amplitude)
    self.assertEqual(seam_qa(frames)['status'],'PASS',(path,count,seam_qa(frames)))
    opaque=[]
    for f in frames:
     bg=Image.new('RGBA',f.size,'#223344');bg.alpha_composite(f);opaque.append(bg)
    self.assertNotIn('speed_discontinuity',seam_qa(opaque)['issues'])
 def test_midmotion_hold_still_fails(self):
  frames=bob(ROOT/'tests/fixtures/live-s13/sprite/cleaned.png',48,12)
  frames[21:29]=[frames[21]]*8
  self.assertIn('speed_discontinuity',seam_qa(frames)['issues'])
 def test_repair_four_lengths_passes_both_checks(self):
  from PIL import ImageDraw
  for n,ms in ((12,40),(24,40),(24,80),(48,40)):
   paths=[]
   for i in range(n):
    im=Image.new('RGBA',(128,128));ImageDraw.Draw(im).ellipse((8+i,40,24+i,56),fill='orange')
    path=self.path/f'{n}-{ms}-{i}.png';im.save(path);paths.append(path)
   result=repair_loop(paths,[ms]*n,self.path/f'repaired-{n}-{ms}')
   self.assertEqual(result['loop']['status'],'PASS')
   self.assertEqual(result['media_qa_loop']['level'],'PASS')
   self.assertLessEqual(abs(sum(result['durations_ms'])/(n*ms)-1),.1)
