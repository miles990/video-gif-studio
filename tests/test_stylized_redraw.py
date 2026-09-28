import hashlib,json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from extract_guides import extract
from render_stylized import render

def plate(root,offsets,size=(64,48),durations=None,hole=True,opaque=False):
 frames=root/'plate';frames.mkdir()
 for i,(dx,dy) in enumerate(offsets):
  a=np.zeros((size[1],size[0],4),np.uint8)
  if opaque:a[...,3]=255
  a[10+dy:34+dy,10+dx:34+dx]=[200,60,40,255]
  a[10+dy:18+dy,10+dx:34+dx]=[40,60,200,255]
  if hole:a[22+dy:28+dy,20+dx:26+dx]=0
  Image.fromarray(a).save(frames/f'{i:05d}.png')
 m=root/'plate.json';m.write_text(json.dumps({'durations_ms':durations or [40]*len(offsets)}))
 return frames,m

def digest(d):return [hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(d).glob('*.png'))]
STYLE={'fill':'palette','line':{'color':'#101010','width':2,'taper':.6},'supersample':4}

class Guides(unittest.TestCase):
 def test_guides_keep_timing_holes_and_report_mask_stability(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);f,m=plate(t,[(0,0),(4,0),(4,0)],durations=[40,80,40])
   r=extract(f,m,t/'g',colors=2);g=json.loads((t/'g/manifest.json').read_text())
   self.assertEqual(r['frames'],3);self.assertEqual(g['durations_ms'],[40,80,40]);self.assertEqual(g['canvas'],[64,48])
   self.assertTrue(any(ring['hole'] for ring in g['frames'][0]['rings']))
   self.assertIsNone(g['frames'][0]['iou_prev']);self.assertLess(g['frames'][1]['iou_prev'],1);self.assertEqual(g['frames'][2]['iou_prev'],1)
   self.assertEqual(len(g['palette']),2);self.assertEqual(g['visual_review'][:8],'required')
 def test_shared_palette_is_deterministic(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);f,m=plate(t,[(0,0),(3,2)])
   extract(f,m,t/'a',colors=2);extract(f,m,t/'b',colors=2)
   ga,gb=(json.loads((t/d/'manifest.json').read_text()) for d in 'ab')
   self.assertEqual(ga['palette'],gb['palette']);self.assertEqual(digest(t/'a/labels'),digest(t/'b/labels'))
   lum=[sum(c) for c in ga['palette']];self.assertEqual(lum,sorted(lum))
 def test_refuses_existing_output_mismatch_and_plate_without_alpha(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);f,m=plate(t,[(0,0)]);(t/'x').mkdir()
   with self.assertRaises(FileExistsError):extract(f,m,t/'x')
   m.write_text(json.dumps({'durations_ms':[40,40]}))
   with self.assertRaises(ValueError):extract(f,m,t/'y')
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);f,m=plate(t,[(0,0)],opaque=True,hole=False)
   with self.assertRaises(ValueError):extract(f,m,t/'g')

class Render(unittest.TestCase):
 def guides(self,t,offsets,**kw):
  f,m=plate(t,offsets,**kw);extract(f,m,t/'g',colors=2);return t/'g'
 def test_render_preserves_canvas_timing_and_hole(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=self.guides(t,[(0,0),(4,0)])
   render(g,STYLE,t/'r');man=json.loads((t/'r/manifest.json').read_text())
   self.assertEqual(man['durations_ms'],[40,40]);self.assertEqual(man['pixels'][:7],'redrawn')
   a=np.array(Image.open(t/'r/frames/00000.png'));self.assertEqual(a.shape,(48,64,4))
   self.assertEqual(a[25,23,3],0);self.assertEqual(a[2,2,3],0);self.assertEqual(a[45,60,3],0)
   self.assertEqual(a[28,15,3],255);self.assertGreater(a[28,15,0],a[28,15,2])
   self.assertEqual(a[13,20,3],255);self.assertGreater(a[13,20,2],a[13,20,0])
   self.assertLess(int(a[22,10,:3].sum()),200)
 def test_render_is_byte_identical_and_translation_coherent(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=self.guides(t,[(0,0),(4,0)])
   render(g,STYLE,t/'a');render(g,STYLE,t/'b');self.assertEqual(digest(t/'a/frames'),digest(t/'b/frames'))
   f0,f1=(np.array(Image.open(t/f'a/frames/0000{i}.png')).astype(int) for i in (0,1))
   self.assertLessEqual(np.abs(f1[:,4:]-f0[:,:-4]).max(),1)
 def test_solid_fill_background_and_empty_frame(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);f,m=plate(t,[(0,0)]);Image.fromarray(np.zeros((48,64,4),np.uint8)).save(f/'00001.png')
   m.write_text(json.dumps({'durations_ms':[40,40]}));extract(f,m,t/'g',colors=2)
   render(t/'g',{'fill':'#F0E0C0','line':{'width':0},'background':'#000000'},t/'r')
   a=np.array(Image.open(t/'r/frames/00000.png'));b=np.array(Image.open(t/'r/frames/00001.png'))
   np.testing.assert_array_equal(a[28,15],[240,224,192,255]);np.testing.assert_array_equal(a[25,23],[0,0,0,255])
   self.assertTrue((b==[0,0,0,255]).all())
 def test_rejects_bad_style(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=self.guides(t,[(0,0)])
   for bad in ({'fill':'plaid'},{'fill':'palette','palette':['#000000']},{'supersample':0}):
    with self.assertRaises(ValueError):render(g,bad,t/'r')
if __name__=='__main__':unittest.main()
