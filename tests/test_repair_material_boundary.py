import sys,unittest,json,subprocess,tempfile,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from repair_material_boundary import repair
class MaterialBoundaryTests(unittest.TestCase):
 def sample(self):
  src=np.full((100,120,3),[0,230,0],np.uint8);src[10:61,10:110]=[175,165,171]
  old=np.zeros((100,120,4),np.uint8);old[10:61,10:110]=[175,165,171,255];old[50:55,40:50]=0;old[51,60]=[70,61,65,255]
  region={'reviewed':True,'startX':20,'curveY':[60.2]*80,'bandInside':15,'bandOutside':8}
  return src,old,region
 def test_recovers_missing_rgb_keeps_shading_and_gap(self):
  src,old,r=self.sample();out,qc=repair(old,src,r)
  self.assertTrue((out[50:55,40:50,3]==255).all());np.testing.assert_array_equal(out[50,40,:3],src[50,40]);np.testing.assert_array_equal(out[51,60],old[51,60]);self.assertTrue((out[64:68,40:50,3]==0).all());self.assertTrue(0<int(out[60,50,3])<255);np.testing.assert_array_equal(out[:40],old[:40])
 def test_protected_negative_space_and_hidden_rgb(self):
  src,old,r=self.sample();old[50:55,40:50]=[1,2,3,0];mask=np.zeros(old.shape[:2],np.uint8);mask[50:55,40:50]=255;out,_=repair(old,src,r,mask);np.testing.assert_array_equal(out[50:55,40:50],old[50:55,40:50])
 def test_rejects_unreviewed_or_out_of_bounds_curve(self):
  src,old,r=self.sample();r['reviewed']=False
  with self.assertRaises(ValueError):repair(old,src,r)
  r['reviewed']=True;r['curveY']=[2.]*80
  with self.assertRaises(ValueError):repair(old,src,r)
 def test_cli_preserves_unmodified_frames_and_protected_gap(self):
  src,old,r=self.sample()
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);frames=base/'rgba';sources=base/'source';masks=base/'protect';out=base/'candidate'
   for path in [frames,sources,masks]:path.mkdir()
   mask=np.zeros(old.shape[:2],np.uint8);mask[50:55,40:50]=255
   for name in ['0000.png','0001.png']:
    Image.fromarray(old).save(frames/name);Image.fromarray(src).save(sources/name);Image.fromarray(mask).save(masks/name)
   recipe=base/'regions.json';recipe.write_text(json.dumps({'frames':{'0000.png':[r],'0001.png':[]}}))
   command=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/repair_material_boundary.py'),'--frames',str(frames),'--source-frames',str(sources),'--regions',str(recipe),'--protect-masks',str(masks),'--out',str(out)]
   subprocess.run(command,check=True,capture_output=True,text=True)
   np.testing.assert_array_equal(np.array(Image.open(out/'0001.png')),old)
   np.testing.assert_array_equal(np.array(Image.open(out/'0000.png'))[50:55,40:50],old[50:55,40:50])
   report=json.loads((out/'repair-report.json').read_text());self.assertFalse(report['productionAccepted']);self.assertEqual(report['visualReview'],'pending');self.assertEqual(len(report['frames']),2)
   self.assertEqual(report['frames'][0]['inputSha256'],hashlib.sha256((frames/'0000.png').read_bytes()).hexdigest())
   self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
if __name__=='__main__':unittest.main()
