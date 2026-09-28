import json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from apply_mask_edits import apply_edits
from extract_guides import extract
from render_stylized import render

GLOW=[80,220,255]
RAMP=np.linspace(255,32,24).round().astype(np.uint8)
def plate(root):
 d=root/'plate';d.mkdir();k=root/'fx';k.mkdir()
 a=np.zeros((48,64,4),np.uint8);a[8:30,8:30]=[200,60,40,255]
 a[36:44,20:44,:3]=GLOW;a[36:44,20:44,3]=RAMP[None]
 m=np.zeros((48,64),np.uint8);m[36:44,20:44]=255
 Image.fromarray(a).save(d/'00000.png');Image.fromarray(m).save(k/'00000.png')
 man=root/'plate.json';man.write_text(json.dumps({'durations_ms':[40]}))
 return d,man,k

class SoftAlpha(unittest.TestCase):
 def test_binary_mode_keeps_previous_threshold_behavior(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t);extract(d,m,t/'g',colors=1,effect_masks=k,effect_colors=1)
   fx=json.loads((t/'g/manifest.json').read_text())['effects']
   self.assertEqual(fx['alpha'],'binary');self.assertEqual(fx['frames'][0]['area'],8*int((RAMP>=128).sum()))
   self.assertNotIn('alpha',fx['frames'][0])
 def test_plate_mode_keeps_soft_pixels_and_stores_measured_alpha(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t);extract(d,m,t/'g',colors=1,effect_masks=k,effect_colors=1,effect_alpha='plate',effect_alpha_floor=1)
   g=json.loads((t/'g/manifest.json').read_text());fx=g['effects']
   self.assertEqual(fx['alpha'],'plate');self.assertEqual(fx['frames'][0]['area'],8*24)
   al=np.array(Image.open(t/'g'/fx['frames'][0]['alpha']));np.testing.assert_array_equal(al[40,20:44],RAMP)
   self.assertEqual(al[20,20],0);self.assertEqual(g['palette'],[[200,60,40]]);self.assertEqual(fx['palette'],[GLOW])
 def test_render_multiplies_coverage_by_measured_alpha_unless_solid(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t);extract(d,m,t/'g',colors=1,effect_masks=k,effect_colors=1,effect_alpha='plate',effect_alpha_floor=1)
   render(t/'g',{'line':{'width':0}},t/'r');a=np.array(Image.open(t/'r/frames/00000.png')).astype(int)
   self.assertLessEqual(np.abs(a[40,21:43,3]-RAMP[1:23]).max(),1);np.testing.assert_array_equal(a[40,30,:3],GLOW)
   man=json.loads((t/'r/manifest.json').read_text());self.assertIn('measured',man['effect_layer']['alpha'])
   render(t/'g',{'line':{'width':0},'effects':{'alpha':'solid'}},t/'s')
   self.assertEqual(np.array(Image.open(t/'s/frames/00000.png'))[40,40,3],255)
 def test_plate_alpha_style_needs_alpha_guides(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t);extract(d,m,t/'g',colors=1,effect_masks=k,effect_colors=1)
   with self.assertRaises(ValueError):render(t/'g',{'effects':{'alpha':'plate'}},t/'r')
   with self.assertRaises(ValueError):extract(d,m,t/'x',effect_masks=k,effect_alpha='soft')
 def test_mask_edits_can_reach_low_alpha_pixels_when_asked(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t);Image.fromarray(np.zeros((48,64),np.uint8)).save(k/'00000.png')
   apply_edits(d,m,k,[{'op':'add','frames':'all','rect':[0,32,64,16]}],t/'hi')
   apply_edits(d,m,k,[{'op':'add','frames':'all','rect':[0,32,64,16]}],t/'lo',alpha_threshold=1)
   hi,lo=(np.array(Image.open(t/n/'masks/00000.png'))>0 for n in ('hi','lo'))
   self.assertEqual(hi.sum(),8*int((RAMP>=128).sum()));self.assertEqual(lo.sum(),8*24)
if __name__=='__main__':unittest.main()
