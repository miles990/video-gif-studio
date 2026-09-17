import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from recover_chroma_detail import recover

class ChromaRecoveryTest(unittest.TestCase):
    def test_recovers_a_clipped_neutral_strand_without_changing_protected_light(self):
        key=np.array([4,239,2],dtype=np.float32);fg=np.array([40,40,40]);src=np.tile(key,(7,7,1));src[2:6,3]=fg*.7+key*.3
        rgba=np.zeros((7,7,4),dtype=np.uint8);rgba[2,3]=[100,80,70,255];mask=np.ones((7,7),dtype=np.uint8)*255;protect=np.zeros((7,7),dtype=np.uint8);protect[2,3]=255
        out,qc=recover(rgba,src,mask,key,protect)
        np.testing.assert_array_equal(out[2,3],rgba[2,3]);self.assertGreater(out[4,3,3],160)
        np.testing.assert_allclose(out[4,3,:3],fg,atol=2);self.assertEqual(out[0,0,3],0);self.assertEqual(qc['protectedChangedPixels'],0)
    def test_review_mask_is_a_hard_boundary(self):
        a=np.full((4,4,4),100,dtype=np.uint8);rgb=np.full((4,4,3),30,dtype=np.uint8);mask=np.zeros((4,4),dtype=np.uint8);mask[1,1]=255
        out,_=recover(a,rgb,mask,[4,239,2]);np.testing.assert_array_equal(out[mask==0],a[mask==0])
    def test_rejects_non_green_key_and_misaligned_source(self):
        a=np.zeros((4,4,4),dtype=np.uint8);mask=np.zeros((4,4),dtype=np.uint8)
        with self.assertRaises(ValueError):recover(a,a[:,:,:3],mask,[100,100,100])
        with self.assertRaises(ValueError):recover(a,np.zeros((3,4,3)),mask,[0,240,0])
if __name__=='__main__':unittest.main()
