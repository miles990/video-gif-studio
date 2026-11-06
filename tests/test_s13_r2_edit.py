from image_fixtures import ImageCase,ROOT
from image_edit import composite
from PIL import Image
import numpy as np

class EditRound2(ImageCase):
 def test_subpixel_translation_and_rotation_bounds(self):
  import cv2
  from image_edit import register
  from image_common import ImageError
  p=ROOT/'tests/fixtures/live-s13/kf/shot-3/keyframe.png'
  with Image.open(p) as im:a=np.array(im.convert('RGBA'))
  region=np.zeros(a.shape[:2],np.uint8)
  transform=np.float32([[1,0,.65],[0,1,-.4]])
  b=cv2.warpAffine(a,transform,(a.shape[1],a.shape[0]),borderMode=cv2.BORDER_REFLECT)
  _,qa=register(a,b,region)
  self.assertLessEqual(qa['residual_px'],1);self.assertEqual(qa['acceptance'],'pass')
  for angle,scale in ((4,.92),(-7,1.08)):
   matrix=cv2.getRotationMatrix2D((a.shape[1]/2,a.shape[0]/2),angle,scale)
   b=cv2.warpAffine(a,matrix,(a.shape[1],a.shape[0]),borderMode=cv2.BORDER_REFLECT)
   _,qa=register(a,b,region);self.assertLessEqual(qa['residual_px'],1)
  for matrix in (cv2.getRotationMatrix2D((a.shape[1]/2,a.shape[0]/2),12,1),np.float32([[1.06,0,0],[0,1,0]])):
   b=cv2.warpAffine(a,matrix,(a.shape[1],a.shape[0]),borderMode=cv2.BORDER_REFLECT)
   with self.assertRaises(ImageError):register(a,b,region)

 def test_both_live_edits_report_subpixel_and_boundary_seam(self):
  for folder,shot in (('live-s13',3),('live-s13-r2',2)):
   p=ROOT/'tests/fixtures'/folder
   with Image.open(p/f'kf/shot-{shot}/keyframe.png') as im:base=im.convert('RGBA')
   with Image.open(p/'edit/regeneration/image-1.png') as im:candidate=im.convert('RGBA')
   with Image.open(p/'edit/mask.png') as im:mask=np.array(im.convert('L').resize(base.size,Image.Resampling.NEAREST))
   result,qa,expanded=composite(base,candidate,mask)
   reg=qa['registration']
   self.assertEqual(reg['residual_tolerance_px'],1)
   self.assertTrue(reg['ecc_attempted'])
   self.assertEqual(reg['acceptance'],'pass' if reg['residual_px']<=1 else 'needs_review')
   self.assertTrue(qa['outside_identical'])
   self.assertIn('boundary_gradient_excess_mean',qa['seam'])
   self.assertIn('boundary_gradient_excess_p95',qa['seam'])
   self.assertGreater(qa['seam']['boundary_edges'],0)
   self.assertTrue(np.array_equal(np.array(result)[expanded==0],np.array(base)[expanded==0]))

 def test_feather_reduces_boundary_jump(self):
  from image_edit import seam_metrics
  a=np.full((100,100,4),255,np.uint8);mask=np.zeros((100,100),np.uint8);mask[20:80,20:80]=255
  hard=a.copy();hard[mask>0,:3]=0
  soft=a.copy();soft[24:76,24:76,:3]=0
  self.assertGreater(seam_metrics(a,hard,mask)['boundary_gradient_excess_mean'],seam_metrics(a,soft,mask)['boundary_gradient_excess_mean'])
