from image_fixtures import ImageCase, ROOT,intended_gaps
from image_alpha import cleanup, alpha_qa
from PIL import Image, ImageDraw
import numpy as np

LIVE=ROOT/'tests/fixtures/live-s13-r2'

class AlphaRound2(ImageCase):
 def test_live_body_holes_are_flagged(self):
  import cv2
  for p in (ROOT/'tests/fixtures/live-s13/sprite/native/image-1.png',LIVE/'sprite/native/image-1.png',LIVE/'key/native/image-1.png'):
   with Image.open(p) as im:base,_=cleanup(im)
   a=np.array(base);depth=cv2.distanceTransform((a[...,3]>=250).astype('uint8'),cv2.DIST_L2,5)
   cy,cx=np.unravel_index(depth.argmax(),depth.shape)
   for fraction in (.2,.35,.5):
    b=a.copy();mask=np.zeros(depth.shape,np.uint8)
    cv2.circle(mask,(int(cx),int(cy)),int(depth[cy,cx]*fraction),255,-1)
    b[...,3][mask>0]=0
    self.assertIn('interior_holes',alpha_qa(Image.fromarray(b))['issues'],(p,fraction))

 def test_native_akimbo_and_ring(self):
  for name in ('sprite','sprite2','key'):
   with Image.open(LIVE/name/'native/image-1.png') as im: result,qa=cleanup(im,judge=intended_gaps)
   self.assertEqual(qa['after']['status'],'PASS',(name,qa))
   self.assertGreater(qa['after']['designed_negative_space_pixels'],0)
   a=np.array(result)[...,3]
   import cv2
   distance=cv2.distanceTransform((a<250).astype('uint8'),cv2.DIST_L2,5)
   self.assertFalse(np.any((a>0)&(a<=10)&(distance>2)))

 def test_body_holes_are_not_designed_by_area(self):
  for radius in (8,24):
   im=Image.new('RGBA',(240,240));d=ImageDraw.Draw(im)
   d.rectangle((20,20,220,220),fill='orange')
   d.ellipse((120-radius,120-radius,120+radius,120+radius),fill=(0,0,0,0))
   self.assertIn('interior_holes',alpha_qa(im)['issues'])

 def test_true_adjacent_soft_edge_survives(self):
  im=Image.new('RGBA',(100,100));a=np.array(im);a[30:70,30:70]=[200,80,40,255]
  a[29,30:70]=[200,80,40,5];a[5:10,5:10]=[200,80,40,5]
  result,qa=cleanup(Image.fromarray(a))
  self.assertTrue(np.all(np.array(result)[29,32:68,3]>0))
  self.assertTrue(np.all(np.array(result)[5:10,5:10,3]==0))
