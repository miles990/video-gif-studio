from image_fixtures import ImageCase,ROOT
from image_alpha import cleanup,alpha_qa
from PIL import Image,ImageDraw
import numpy as np
LIVE=ROOT/'tests/fixtures/live-s13'
class LiveAlphaTests(ImageCase):
 def test_live_probe_negative_space_and_specks(self):
  with Image.open(LIVE/'sprite/native/image-1.png') as im:
   result,report=cleanup(im)
  self.assertEqual(report['after']['status'],'PASS',report)
  self.assertGreater(report['removed_speck_pixels'],0)
  self.assertGreater(report['after']['designed_negative_space_pixels'],0)
 def test_small_and_semitransparent_holes_still_fail(self):
  with Image.open(LIVE/'sprite/native/image-1.png') as im:base,_=cleanup(im)
  a=np.array(base);ys,xs=np.where(a[...,3]>=250);cy,cx=int(np.median(ys)),int(np.median(xs))
  for alpha in (0,120):
   b=a.copy();b[cy-8:cy+8,cx-8:cx+8,3]=alpha
   qa=alpha_qa(Image.fromarray(b));self.assertGreater(qa['interior_hole_ratio'],0)
 def test_large_clear_gap_is_preserved(self):
  im=Image.new('RGBA',(200,200));d=ImageDraw.Draw(im);d.rectangle((20,20,180,180),fill='orange');d.rectangle((70,70,130,130),fill=(0,0,0,0))
  qa=alpha_qa(im);self.assertNotIn('interior_holes',qa['issues']);self.assertGreater(qa['designed_negative_space_pixels'],3000)

 def test_original_probe_also_passes_cleanup(self):
  with Image.open(LIVE/'probe-alpha.png') as im:_,report=cleanup(im)
  self.assertEqual(report['after']['status'],'PASS',report)
  self.assertGreater(report['removed_speck_pixels'],0)
