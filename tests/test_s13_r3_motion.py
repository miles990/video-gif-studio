import numpy as np
from PIL import Image,ImageOps
from image_fixtures import ImageCase,ROOT
from image_motion import seam_qa
from test_s13_r2_motion import bob

def breathe(path,n=32):
 from image_alpha import cleanup
 with Image.open(path) as im:sprite=ImageOps.contain(cleanup(im)[0],(448,448),Image.Resampling.LANCZOS)
 sp=Image.new('RGBA',(512,512));sp.alpha_composite(sprite,((512-sprite.width)//2,(512-sprite.height)//2))
 a=np.array(sp);foot=np.where(a[...,3]>8)[0].max();frames=[]
 for i in range(n):
  scale=1+.025*np.sin(2*np.pi*i/n);h=round(512*scale);im=sp.resize((512,h),Image.Resampling.LANCZOS);off=round(foot-foot*scale)
  canvas=Image.new('RGBA',(512,512));canvas.alpha_composite(im.crop((0,max(0,-off),512,min(h,512-off))),(0,max(0,off)));frames.append(canvas)
 return frames

class MotionRound3(ImageCase):
 def test_three_sets_breathe_hold_hysteresis_and_jump(self):
  for folder,src in [('live-s13','sprite/cleaned.png'),('live-s13-r2','sprite2/native/image-1.png'),('live-s13-r3','spRing/native/image-1.png')]:
   frames=breathe(ROOT/'tests/fixtures'/folder/src)
   self.assertEqual(seam_qa(frames)['status'],'PASS',folder)
   held=frames[:8]+[frames[8]]*50+frames[9:]
   self.assertIn('endpoint_hold',seam_qa(held)['issues'],folder)
   middle=frames[:4]+[frames[4]]*10+frames[5:]
   self.assertIn('speed_discontinuity',seam_qa(middle)['issues'],folder)
   jumped=frames.copy();jumped[16]=Image.fromarray(np.roll(np.array(frames[16]),12,axis=0))
   self.assertIn('single_frame_position_jump',seam_qa(jumped)['issues'],folder)
   timed=[40]*32;timed[8]=2000
   self.assertIn('endpoint_hold',seam_qa(frames,timed)['issues'],folder)
