import json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from extract_guides import extract
from render_stylized import render
from qc_redraw import qc
from test_flow_guides import textured_plate
try:
 from js_style_host import find_browser;find_browser();BROWSER=True
except RuntimeError:BROWSER=False

@unittest.skipUnless(BROWSER,'no headless Chromium available')
class JSPlugins(unittest.TestCase):
 def guides(self,t,**kw):
  d,m=textured_plate(t,**kw);extract(d,m,t/'g',colors=3,flow=True);return t/'g'
 def js(self,t,name,body):
  p=t/f'{name}.js';p.write_text(body);return str(p)
 def test_js_plugin_draws_on_canvas_and_is_recorded(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=self.guides(t,frames=2)
   p=self.js(t,'invert','''function render(ctx, api){
     const d=ctx.base.data;for(let i=0;i<d.length;i+=4){d[i]=255-d[i];d[i+1]=255-d[i+1];d[i+2]=255-d[i+2];}
     if(ctx.params.k!==1||!ctx.uv||ctx.uvWidth!==48) throw new Error('bad ctx');return ctx.base;}''')
   render(g,{'plugin':p,'plugin_params':{'k':1}},t/'r');render(g,{},t/'b')
   a=np.array(Image.open(t/'r/frames/00001.png')).astype(int);b=np.array(Image.open(t/'b/frames/00001.png')).astype(int)
   on=b[...,3]==255;np.testing.assert_array_equal(a[on][:,:3],255-b[on][:,:3])
   rec=json.loads((t/'r/manifest.json').read_text())['plugin'];self.assertIn('Chrom',rec['browser']);self.assertEqual(len(rec['sha256']),64)
 def test_math_random_and_wrong_size_are_refused(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=self.guides(t,frames=1)
   with self.assertRaises(ValueError):render(g,{'plugin':self.js(t,'rnd','function render(ctx){Math.random();return ctx.base;}')},t/'a')
   with self.assertRaises(ValueError):render(g,{'plugin':self.js(t,'size','function render(ctx){return new OffscreenCanvas(3,3);}')},t/'b')
 def test_api_noise_is_reproducible(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=self.guides(t,frames=1)
   p=self.js(t,'n','''function render(ctx,api){const r=api.noise('x');const d=ctx.base.data;
     for(let i=0;i<d.length;i+=4){d[i]=Math.floor(r()*255);d[i+3]=255;}return ctx.base;}''')
   render(g,{'plugin':p},t/'a');render(g,{'plugin':p},t/'b')
   np.testing.assert_array_equal(np.array(Image.open(t/'a/frames/00000.png')),np.array(Image.open(t/'b/frames/00000.png')))
 def test_manga_action_speed_lines_only_where_motion_was_measured(self):
  # Compare with the reference render so its own outline is not mistaken for added strokes.
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=self.guides(t,shift=4,frames=3);style={'plugin':'manga_action','intent':{'silhouette_min':.8}}
   render(g,style,t/'r');render(g,{},t/'b')
   a=np.array(Image.open(t/'r/frames/00002.png'));b=np.array(Image.open(t/'b/frames/00002.png'))
   added=(a[...,3]>0)&(b[...,3]==0)
   self.assertGreater(int(added[12:52,:16].sum()),10)   # trails left of a block moving right
   self.assertEqual(int(added[:,40:].sum()),0)          # nothing ahead of the motion
   r=qc(g,style,t/'r');self.assertTrue(r['checks']['deterministic']['pass']);self.assertTrue(r['checks']['silhouette']['pass'],r['checks']['silhouette'])
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=self.guides(t,still=True,frames=3);render(g,{'plugin':'manga_action'},t/'r');render(g,{},t/'b')
   a=np.array(Image.open(t/'r/frames/00002.png'));b=np.array(Image.open(t/'b/frames/00002.png'))
   self.assertEqual(int(((a[...,3]>0)&(b[...,3]==0)).sum()),0)
if __name__=='__main__':unittest.main()
