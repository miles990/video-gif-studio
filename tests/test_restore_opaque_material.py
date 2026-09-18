import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from restore_opaque_material import restore

class OpaqueRestore(unittest.TestCase):
 def test_explicit_rgb_damage_can_fix_opaque_artifact_but_protection_wins(self):
  a=np.full((8,8,4),(220,215,210,255),np.uint8);a[3,3,:3]=0;a[4,4,:3]=0
  s=np.full((8,8,3),(221,216,211),np.uint8);mask=np.ones((8,8),bool)
  damage=np.zeros((8,8),bool);damage[3,3]=damage[4,4]=True
  protect=np.zeros((8,8),bool);protect[4,4]=True
  out,r=restore(a,s,mask,protect,rgb_damage=damage)
  np.testing.assert_array_equal(out[3,3],[221,216,211,255])
  np.testing.assert_array_equal(out[4,4],a[4,4])
  self.assertEqual(r['alreadyOpaqueRgbChangedPixels'],1)
  np.testing.assert_array_equal(out[~damage],a[~damage])
  mask[3,3]=False
  with self.assertRaises(ValueError):restore(a,s,mask,rgb_damage=damage)
 def test_damaged_nonzero_rgb_needs_separately_reviewed_source_recovery(self):
  a=np.full((8,8,4),(220,215,210,255),np.uint8);a[3,3]=[0,0,0,1]
  s=np.full((8,8,3),(221,216,211),np.uint8)
  mask=np.zeros((8,8),bool);mask[3,3]=True
  out,_=restore(a,s,mask,rgb_policy='source')
  np.testing.assert_array_equal(out[3,3],[221,216,211,255])
  np.testing.assert_array_equal(out[~mask],a[~mask])
 def test_alpha_only_recovery_preserves_despill_and_source_is_explicit(self):
  a=np.full((4,4,4),(192,195,191,100),np.uint8);a[1,1]=0
  s=np.full((4,4,3),(185,211,184),np.uint8);mask=np.ones((4,4),bool)
  out,r=restore(a,s,mask)
  np.testing.assert_array_equal(out[0,0],[192,195,191,255])
  np.testing.assert_array_equal(out[1,1],[185,211,184,255])
  self.assertEqual(r['sourceRgbRecoveredPixels'],1)
  out,_=restore(a,s,mask,rgb_policy='source')
  np.testing.assert_array_equal(out[0,0],[185,211,184,255])
 def test_source_shading_preserved_without_filling_protected_gaps(self):
  a=np.zeros((16,16,4),np.uint8);a[0,0]=[20,30,40,255]
  s=np.full((16,16,3),(170,185,160),np.uint8);mask=np.ones((16,16),bool);protect=np.zeros((16,16),bool);protect[:,8]=True
  out,r=restore(a,s,mask,protect)
  np.testing.assert_array_equal(out[0,0],a[0,0]);np.testing.assert_array_equal(out[:,8],a[:,8])
  np.testing.assert_array_equal(out[2,2],[170,185,160,255]);self.assertEqual(r['alreadyOpaqueRgbChangedPixels'],0)
 def test_unreviewed_graded_contour_is_exactly_unchanged(self):
  a=np.full((16,16,4),120,np.uint8);s=np.full((16,16,3),190,np.uint8);mask=np.zeros((16,16),np.uint8);mask[4:12,4:12]=255
  out,_=restore(a,s,mask);np.testing.assert_array_equal(out[mask==0],a[mask==0])
 def test_refuse_alpha_as_review_mask_or_mismatched_source(self):
  a=np.zeros((16,16,4),np.uint8);s=np.zeros((16,16,3),np.uint8)
  with self.assertRaises(ValueError):restore(a,s,np.full((16,16),128,np.uint8))
  with self.assertRaises(ValueError):restore(a,s[:8],np.ones((16,16),bool))
if __name__=='__main__':unittest.main()
