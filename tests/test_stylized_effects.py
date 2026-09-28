import json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from extract_guides import extract
from propose_effect_masks import propose
from render_stylized import render

PINK=[255,80,200]
def plate(root,frames=2):
 d=root/'plate';d.mkdir();e=root/'fx';e.mkdir()
 for i in range(frames):
  a=np.zeros((48,64,4),np.uint8);fx=np.zeros((48,64),np.uint8)
  a[10:34,10:34]=[200,60,40,255];a[10:18,10:34]=[40,60,200,255]
  if i:
   a[38:44,36:60]=PINK+[255];fx[38:44,36:60]=255
   a[26:34,28:40]=PINK+[255];fx[26:34,28:40]=255
  Image.fromarray(a).save(d/f'{i:05d}.png');Image.fromarray(fx).save(e/f'{i:05d}.png')
 m=root/'plate.json';m.write_text(json.dumps({'durations_ms':[40]*frames}))
 return d,m,e

class EffectGuides(unittest.TestCase):
 def test_reviewed_effect_masks_get_their_own_layer_and_palette(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,e=plate(t);extract(d,m,t/'g',colors=2,effect_masks=e,effect_colors=1)
   g=json.loads((t/'g/manifest.json').read_text())
   self.assertEqual(g['effects']['palette'],[PINK]);self.assertNotIn(PINK,g['palette'])
   self.assertEqual(g['frames'][1]['area'],24*24-8*6);self.assertEqual(g['effects']['frames'][1]['area'],6*24+8*12)
   self.assertEqual(g['effects']['frames'][0]['area'],0);self.assertEqual(g['effects']['frames'][0]['rings'],[])
   self.assertIn('not verified',g['effects']['mask_review']);self.assertEqual(len(g['effects']['mask_sha256']),2)
 def test_without_effect_masks_manifest_stays_single_layer(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,_=plate(t);extract(d,m,t/'g',colors=3)
   self.assertIsNone(json.loads((t/'g/manifest.json').read_text())['effects'])
 def test_effect_masks_must_match_plate(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,e=plate(t);(e/'00001.png').unlink()
   with self.assertRaises(ValueError):extract(d,m,t/'g',effect_masks=e)
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,e=plate(t);Image.fromarray(np.zeros((8,8),np.uint8)).save(e/'00001.png')
   with self.assertRaises(ValueError):extract(d,m,t/'g',effect_masks=e)

class EffectRender(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();t=Path(self.t.name);d,m,e=plate(t)
  extract(d,m,t/'g',colors=2,effect_masks=e,effect_colors=1);self.root=t
 def tearDown(self):self.t.cleanup()
 def frame(self,style,name):
  render(self.root/'g',style,self.root/name);return np.array(Image.open(self.root/name/'frames/00001.png')).astype(int)
 def test_effect_keeps_its_color_without_outline_by_default(self):
  a=self.frame({'line':{'width':1}},'r')
  np.testing.assert_array_equal(a[40,50],PINK+[255]);self.assertEqual(a[38,48,3],255);self.assertGreater(a[38,48,0],200)
  self.assertEqual(a[2,2,3],0)
 def test_order_and_opacity(self):
  over=self.frame({'line':{'width':0}},'o');under=self.frame({'line':{'width':0},'effects':{'order':'under'}},'u')
  np.testing.assert_array_equal(over[30,34],PINK+[255])
  # The character layer does not cover reviewed effect pixels, so "under" only differs where layers overlap after smoothing.
  np.testing.assert_array_equal(under[40,50],PINK+[255])
  half=self.frame({'line':{'width':0},'effects':{'opacity':.5}},'h')
  self.assertEqual(half[40,50,3],128);np.testing.assert_array_equal(half[40,50,:3],PINK)
  np.testing.assert_array_equal(half[20,15],over[20,15])
 def test_effect_solid_fill_and_bad_effect_style(self):
  a=self.frame({'effects':{'fill':'#00FF00'}},'s');np.testing.assert_array_equal(a[40,50],[0,255,0,255])
  for bad in ({'effects':{'order':'sideways'}},{'effects':{'opacity':2}},{'effects':{'palette':['#000000','#FFFFFF']}}):
   with self.assertRaises(ValueError):render(self.root/'g',bad,self.root/'bad')
 def test_effect_style_on_single_layer_guides_is_rejected(self):
  t=self.root;d=t/'p2';d.mkdir();a=np.zeros((48,64,4),np.uint8);a[10:34,10:34]=[200,60,40,255]
  Image.fromarray(a).save(d/'00000.png');(t/'p2.json').write_text(json.dumps({'durations_ms':[40]}));extract(d,t/'p2.json',t/'g2',colors=1)
  render(t/'g2',{},t/'ok')
  with self.assertRaises(ValueError):render(t/'g2',{'effects':{'fill':'#00FF00'}},t/'no')

class Proposal(unittest.TestCase):
 def test_proposal_marks_colors_absent_from_reference_frames_and_stays_pending(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,_=plate(t);r=propose(d,m,t/'p',reference_frames=[0],threshold=60,min_area=4)
   k=np.array(Image.open(t/'p/masks/00001.png'))>0;k0=np.array(Image.open(t/'p/masks/00000.png'))>0
   self.assertTrue(k[38:44,36:60].all());self.assertTrue(k[26:34,28:40].all())
   self.assertFalse(k[10:26,10:28].any());self.assertFalse(k0.any())
   man=json.loads((t/'p/manifest.json').read_text());self.assertEqual(man['review'],'pending');self.assertEqual(r['frames'],2)
 def test_rare_reference_colors_and_small_shifts_are_not_proposed(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,_=plate(t,frames=1)
   # A few fringe pixels in the reference must stay known even though they are too rare to form a palette cluster.
   a=np.array(Image.open(d/'00000.png'));a[20,10]=[250,40,250,255];Image.fromarray(a).save(d/'00000.png')
   b=a.copy();b[10:34,10:34,:3]=np.clip(b[10:34,10:34,:3].astype(int)+12,0,255);b[21,10]=[240,50,240,255]
   Image.fromarray(b).save(d/'00001.png');m.write_text(json.dumps({'durations_ms':[40,40]}))
   propose(d,m,t/'p',reference_frames=[0],min_area=1)
   self.assertFalse((np.array(Image.open(t/'p/masks/00001.png'))>0).any())
 def test_proposal_drops_small_speckles_and_refuses_bad_reference(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,_=plate(t);propose(d,m,t/'p',reference_frames=[0],min_area=500)
   self.assertFalse((np.array(Image.open(t/'p/masks/00001.png'))>0).any())
   with self.assertRaises(ValueError):propose(d,m,t/'q',reference_frames=[9])
if __name__=='__main__':unittest.main()
