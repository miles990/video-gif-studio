import json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from extract_guides import extract,load_flow,layer_weights
from render_stylized import render
from qc_redraw import qc

def textured_plate(root,shift=3,frames=4,still=False):
 # A textured block sliding right; texture lets optical flow lock on.
 rng=np.random.default_rng(7);tex=rng.integers(40,220,(40,40,3)).astype(np.uint8)
 tex=np.array(Image.fromarray(tex).resize((40,40),Image.NEAREST).filter(__import__('PIL.ImageFilter',fromlist=['x']).GaussianBlur(1)))
 d=root/'plate';d.mkdir()
 for i in range(frames):
  a=np.zeros((64,96,4),np.uint8);x=8+(0 if still else shift*i)
  a[12:52,x:x+40,:3]=tex;a[12:52,x:x+40,3]=255
  Image.fromarray(a).save(d/f'{i:05d}.png')
 (root/'plate.json').write_text(json.dumps({'durations_ms':[40]*frames}))
 return d,root/'plate.json'

class FlowGuides(unittest.TestCase):
 def test_flow_measures_translation_and_uv_follows_the_surface(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m=textured_plate(t);extract(d,m,t/'g',colors=3,flow=True)
   g=json.loads((t/'g/manifest.json').read_text());self.assertTrue(g['flow']['enabled'])
   f=load_flow(t/'g',g,2);bw=f['backward'];valid=f['valid']
   core=np.zeros(valid.shape,bool);core[20:44,24:44]=True
   self.assertLess(np.abs(np.median(bw[core&valid][:,0])+3),.5)  # pixel at t came from 3px to the left
   uv=f['uv'];self.assertLess(np.abs(uv[32,34]-(uv[32,34-3]+[3,0])).max(),50)
   # the same surface point keeps its texture coordinate as it moves: (x,y) at frame 2 == (x-6,y) at frame 0
   uv0=load_flow(t/'g',g,0)['uv'];np.testing.assert_allclose(uv[32,40],uv0[32,34],atol=.75)
   self.assertIsNone(load_flow(t/'g',g,0)['backward'])
 def test_without_flow_manifest_says_so(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m=textured_plate(t,frames=2);extract(d,m,t/'g',colors=2)
   self.assertFalse(json.loads((t/'g/manifest.json').read_text())['flow']['enabled'])

class Layers(unittest.TestCase):
 def test_weights_sum_to_one_and_vanish_at_wrap(self):
  ph=np.linspace(0,3,301).astype(np.float32);w0,w1=layer_weights(ph)
  np.testing.assert_allclose(w0+w1,1,atol=1e-6);self.assertEqual(w0[0],0);self.assertEqual(w1[50],0)
 def test_zero_travel_keeps_one_layer_and_rigid_motion_has_no_distortion(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m=textured_plate(t,frames=4);extract(d,m,t/'g',colors=3,flow=True,uv_clock=0)
   g=json.loads((t/'g/manifest.json').read_text());self.assertEqual(len(load_flow(t/'g',g,3)['uv_layers']),1)
   extract(d,m,t/'g2',colors=3,flow=True);g2=json.loads((t/'g2/manifest.json').read_text())
   self.assertEqual(len(load_flow(t/'g2',g2,3)['uv_layers']),2);self.assertLess(max(g2['flow']['uv_distortion']),.02)
   render(t/'g2',{},t/'r');c=qc(t/'g2',{},t/'r')['checks']['texture_distortion'];self.assertTrue(c['pass'],c)
   self.assertFalse(qc(t/'g2',{'intent':{'uv_distortion_max':-1}},t/'r')['checks']['texture_distortion']['pass'])
 def test_rigid_motion_survives_reanchoring_so_layers_never_crossfade(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m=textured_plate(t,shift=2,frames=9);extract(d,m,t/'g',colors=3,flow=True,uv_clock=.5)
   g=json.loads((t/'g/manifest.json').read_text());f=load_flow(t/'g',g,8)
   (a,_),(b,_)=f['uv_layers'];core=np.zeros(a.shape[:2],bool);core[22:42,34:52]=True
   self.assertLess(np.abs(a[core]-b[core]).max(),.3)                     # both layers agree on the rigid block
   uv0=load_flow(t/'g',g,0)['uv'];np.testing.assert_allclose(a[32,40],uv0[32,24],atol=1)  # still glued after resets
 def test_still_and_rigid_points_never_change_weight_while_deformed_points_cycle(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);dd=t/'plate';dd.mkdir();rng=np.random.default_rng(3)
   tex=np.array(Image.fromarray((rng.random((30,30,3))*180+40).astype(np.uint8)).resize((30,30)))
   for i in range(8):
    a=np.zeros((80,200,4),np.uint8);a[4:34,4:34,:3]=tex;a[4:34,4:34,3]=255              # still block
    x=40+3*i;a[4:34,x:x+30,:3]=tex;a[4:34,x:x+30,3]=255                                 # rigidly moving block
    wid=30+6*i;a[44:74,100:100+wid,:3]=np.array(Image.fromarray(tex).resize((wid,30)));a[44:74,100:100+wid,3]=255  # stretching block
    Image.fromarray(a).save(dd/f'{i:05d}.png')
   (t/'p.json').write_text(json.dumps({'durations_ms':[40]*8}));extract(dd,t/'p.json',t/'g',colors=3,flow=True,uv_clock=.3)
   g=json.loads((t/'g/manifest.json').read_text());ws=[load_flow(t/'g',g,i)['uv_layers'][0][1] for i in range(8)]
   still=np.zeros((80,200),bool);still[10:28,10:28]=True
   for w in ws[1:]:np.testing.assert_allclose(w[still],ws[0][still],atol=1e-3)
   self.assertGreater(float(np.abs(ws[7][50:68,110:130]-ws[0][50:68,110:130]).max()),.2)

GRAIN='''
import cv2
import numpy as np
def render(ctx):
    out=ctx['base'].copy();h,w=out.shape[:2]
    field=cv2.GaussianBlur(ctx['noise']('g',(256,256)).astype(np.float32),(0,0),2)
    field=(field-field.mean())/field.std()*20
    if {anchored}:
        mx,my=ctx['uv'][...,0],ctx['uv'][...,1]
    else:
        my,mx=np.mgrid[:h,:w].astype(np.float32)
    n=cv2.remap(field,mx.astype(np.float32),my.astype(np.float32),cv2.INTER_LINEAR,borderMode=cv2.BORDER_WRAP)
    out[...,:3]=np.clip(out[...,:3]+n[...,None],0,255).astype(np.uint8);return out
'''
class MotionCoherence(unittest.TestCase):
 def run_qc(self,t,anchored,**kw):
  d,m=textured_plate(t,**kw);extract(d,m,t/'g',colors=3,flow=True)
  p=t/'grain.py';p.write_text(GRAIN.format(anchored=anchored));style={'plugin':str(p)}
  render(t/'g',style,t/'r');return qc(t/'g',style,t/'r')
 def test_canvas_texture_slides_over_moving_body_and_is_flagged(self):
  with tempfile.TemporaryDirectory() as t:
   r=self.run_qc(Path(t),False);c=r['checks']['motion_coherence']
   self.assertFalse(c['pass']);self.assertTrue(c['flagged_frames'])
 def test_uv_anchored_texture_moves_with_body_and_passes(self):
  with tempfile.TemporaryDirectory() as t:
   r=self.run_qc(Path(t),True);c=r['checks']['motion_coherence'];self.assertTrue(c['pass'],c)
 def test_declared_sliding_texture_is_allowed(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m=textured_plate(t);extract(d,m,t/'g',colors=3,flow=True)
   p=t/'grain.py';p.write_text(GRAIN.format(anchored=False));style={'plugin':str(p),'intent':{'texture_slides':True}}
   render(t/'g',style,t/'r');self.assertTrue(qc(t/'g',style,t/'r')['checks']['motion_coherence']['pass'])
 def test_no_motion_is_inconclusive_and_no_flow_skips(self):
  with tempfile.TemporaryDirectory() as t:
   r=self.run_qc(Path(t),True,still=True);self.assertIsNone(r['checks']['motion_coherence']['pass'])
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m=textured_plate(t,frames=2);extract(d,m,t/'g',colors=2);render(t/'g',{},t/'r')
   r=qc(t/'g',{},t/'r');self.assertNotIn('motion_coherence',r['checks']);self.assertIn('motion_coherence',r['not_run'])
if __name__=='__main__':unittest.main()
