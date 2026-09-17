import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from repair_edges import repair
class RepairTests(unittest.TestCase):
 def test_preserves_lighting_and_protected_overlap(self):
  a=np.zeros((32,32,4),np.uint8);a[8:24,8:24]=[190,160,175,255];a[12,12]=[55,30,40,255];a[24,13]=[20,130,30,255]
  mask=np.zeros((32,32),np.uint8);mask[24,13]=255;mask[12,12]=255
  protect=np.zeros_like(mask);protect[8:24,8:24]=255
  out,qc=repair(a,mask,protect)
  np.testing.assert_array_equal(out[8:24,8:24],a[8:24,8:24]);self.assertEqual(int(out[24,13,3]),0);self.assertEqual(qc['protectedChangedPixels'],0)
 def test_pixel_mode_removes_without_softening(self):
  a=np.full((8,8,4),255,np.uint8);mask=np.zeros((8,8),np.uint8);mask[0]=255
  out,_=repair(a,mask,smooth=0);self.assertFalse(out[0].any());np.testing.assert_array_equal(out[1:],a[1:])
 def test_reject_mismatched_mask(self):
  with self.assertRaises(ValueError):repair(np.zeros((8,8,4),np.uint8),np.zeros((7,8),np.uint8))
 def test_adjacent_smoothing_preserves_a_thin_attached_line(self):
  a=np.zeros((16,16,4),np.uint8);a[2:6,4:10]=[30,25,20,255];a[6:14,7]=[30,25,20,255];a[9,8]=[70,120,50,255]
  mask=np.zeros((16,16),np.uint8);mask[9,8]=255
  out,_=repair(a,mask,smooth=2)
  self.assertTrue((out[6:14,7,3]>128).all());self.assertEqual(out[9,8,3],0)
