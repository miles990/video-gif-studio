import numpy as np
from PIL import Image
from image_fixtures import ImageCase, ROOT
from image_edit import composite
from image_common import ImageError
LIVE=ROOT/'tests/fixtures/live-s13'
class LiveEditTests(ImageCase):
 def test_live_size_changed_regeneration(self):
  with Image.open(LIVE/'kf/shot-3/keyframe.png') as im:base=im.convert('RGBA')
  with Image.open(LIVE/'edit/regeneration/image-1.png') as im:candidate=im.convert('RGBA')
  with Image.open(LIVE/'edit/mask.png') as im:mask=np.array(im.resize(base.size).convert('L'))
  self.assertNotEqual(base.size,candidate.size)
  result,qa,region=composite(base,candidate,mask)
  self.assertTrue(np.array_equal(np.array(result)[region==0],np.array(base)[region==0]))
  self.assertEqual(qa['registration']['residual_tolerance_px'],1)
  self.assertEqual(qa['acceptance'],'pass' if qa['registration']['residual_px']<=1 else 'needs_review')
  self.assertIn('boundary_gradient_excess_mean',qa['seam'])
  self.assertGreaterEqual(qa['registration']['inliers'],8)
 def test_unrelated_regeneration_refused(self):
  with Image.open(LIVE/'kf/shot-3/keyframe.png') as im:base=im.convert('RGBA')
  with Image.open(LIVE/'neg/image-1.png') as im:candidate=im.convert('RGBA')
  mask=np.zeros((base.height,base.width),np.uint8);mask[200:300,100:200]=255
  with self.assertRaises(ImageError) as cm:composite(base,candidate,mask)
  self.assertEqual(cm.exception.error['code'],'E_REGISTRATION')

 def test_live_regeneration_at_original_canvas_dimensions(self):
  with Image.open(LIVE/'kf/shot-3/keyframe.png') as im:base=im.convert('RGBA').resize((1080,1920))
  with Image.open(LIVE/'edit/regeneration/image-1.png') as im:candidate=im.convert('RGBA').resize((916,1717))
  with Image.open(LIVE/'edit/mask.png') as im:mask=np.array(im.convert('L').resize(base.size,Image.Resampling.NEAREST))
  result,qa,region=composite(base,candidate,mask)
  self.assertTrue(np.array_equal(np.array(result)[region==0],np.array(base)[region==0]))
  self.assertEqual(qa['registration']['residual_tolerance_px'],1)
  self.assertEqual(qa['acceptance'],'pass' if qa['registration']['residual_px']<=1 else 'needs_review')
  self.assertGreaterEqual(qa['registration']['inlier_fraction'],.25)
