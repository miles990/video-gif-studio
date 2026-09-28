import json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from extract_guides import extract
from render_stylized import render
from qc_redraw import qc

def guides(root,frames=3):
 d=root/'plate';d.mkdir()
 for i in range(frames):
  a=np.zeros((48,64,4),np.uint8);a[8:40,8:30]=[200,120,60,255];a[8:16,8:30]=[60,90,200,255]
  a[20:26,30:36+4*i]=[200,120,60,255]  # the arm reaches further each frame; the torso is still
  Image.fromarray(a).save(d/f'{i:05d}.png')
 (root/'plate.json').write_text(json.dumps({'durations_ms':[40]*frames}))
 extract(d,root/'plate.json',root/'g',colors=2);return root/'g'

def plugin(root,name,body):
 p=root/f'{name}.py';p.write_text('import numpy as np\n'+body);return str(p)

GRAIN_KEYED='''
def render(ctx):
    out=ctx['base'].copy();h,w=out.shape[:2]
    n=(ctx['noise']({key},(h,w))-.5)*40
    out[...,:3]=np.clip(out[...,:3]+n[...,None],0,255).astype(np.uint8);return out
'''

class Plugins(unittest.TestCase):
 def test_plugin_gets_context_and_is_recorded(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=guides(t)
   p=plugin(t,'probe','''
def render(ctx):
    assert ctx['count']==3 and ctx['canvas']==(64,48) and ctx['params']=={'k':1}
    assert ctx['character']['mask'].shape==(48,64) and ctx['effects'] is None
    out=ctx['base'].copy();out[...,:3]=255-out[...,:3];return out
''')
   render(g,{'plugin':p,'plugin_params':{'k':1}},t/'r');render(g,{},t/'b')
   a=np.array(Image.open(t/'r/frames/00000.png'));b=np.array(Image.open(t/'b/frames/00000.png'))
   np.testing.assert_array_equal(a[...,:3],255-b[...,:3])
   man=json.loads((t/'r/manifest.json').read_text());self.assertEqual(len(man['plugin']['sha256']),64)
 def test_bad_plugin_output_is_refused(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=guides(t)
   for i,body in enumerate(('def render(ctx):\n    return np.zeros((2,2,4),np.uint8)\n','x=1\n')):
    with self.assertRaises(ValueError):render(g,{'plugin':plugin(t,f'bad{i}',body)},t/f'r{i}')
 def test_bundled_paper_cutout_is_deterministic_and_shadowed(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=guides(t);render(g,{'plugin':'paper_cutout'},t/'a');render(g,{'plugin':'paper_cutout'},t/'b')
   for i in range(3):np.testing.assert_array_equal(*(np.array(Image.open(t/d/f'frames/{i:05d}.png')) for d in 'ab'))
   a=np.array(Image.open(t/'a/frames/00000.png'));self.assertTrue(0<a[42,20,3]<128)  # soft shadow below the body

class QC(unittest.TestCase):
 def check(self,t,style):
  g=guides(t);render(g,style,t/'r');return qc(g,style,t/'r')
 def test_builtin_and_canvas_grain_pass(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);r=self.check(t,{});self.assertTrue(r['auto_checks_passed'],r)
   self.assertIn('human',r['review'])
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);r=self.check(t,{'plugin':plugin(t,'grain',GRAIN_KEYED.format(key="'grain'"))});self.assertTrue(r['auto_checks_passed'],r)
 def test_reseeded_texture_fails_unless_boil_is_declared(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);r=self.check(t,{'plugin':plugin(t,'boil',GRAIN_KEYED.format(key="('grain',ctx['index'])"))})
   self.assertFalse(r['checks']['static_interior']['pass']);self.assertEqual(r['checks']['static_interior']['flagged_frames'],[1,2])
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);r=self.check(t,{'plugin':plugin(t,'boil',GRAIN_KEYED.format(key="('grain',ctx['index'])")),'intent':{'boil':True}})
   self.assertTrue(r['auto_checks_passed'],r)
 def test_texture_swimming_on_still_torso_is_caught(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);r=self.check(t,{'plugin':'paper_cutout','plugin_params':{'anchor':'centroid'}})
   self.assertFalse(r['checks']['static_interior']['pass'])
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);r=self.check(t,{'plugin':'paper_cutout'});self.assertTrue(r['auto_checks_passed'],r)
 def test_silhouette_and_determinism_failures(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);r=self.check(t,{'plugin':plugin(t,'empty','def render(ctx):\n    return np.zeros_like(ctx["base"])\n')})
   self.assertFalse(r['checks']['silhouette']['pass']);self.assertEqual(r['checks']['silhouette']['flagged_frames'],[0,1,2])
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);r=self.check(t,{'plugin':plugin(t,'rand','''
def render(ctx):
    out=ctx['base'].copy();out[...,0]=np.random.default_rng().integers(0,255,out.shape[:2]);return out
'''),'intent':{'boil':True}})
   self.assertFalse(r['checks']['deterministic']['pass'])
 def test_declared_silhouette_tolerance_is_respected(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);body='''
def render(ctx):
    out=ctx['base'].copy();out[:,:20]=0;return out
'''
   r=self.check(t,{'plugin':plugin(t,'crop',body)});self.assertFalse(r['checks']['silhouette']['pass'])
   r2=qc(t/'g',{'plugin':str(t/'crop.py'),'intent':{'silhouette_min':.3}},t/'r');self.assertTrue(r2['checks']['silhouette']['pass'])
 def test_opaque_background_does_not_hide_the_figure_from_checks(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);r=self.check(t,{'plugin':'paper_cutout','background':'#E8E0D0'});self.assertTrue(r['auto_checks_passed'],r)
   self.assertTrue(all(n>0 for n in r['checks']['static_interior']['still_pixels'][1:]))
 def test_nothing_still_is_inconclusive_not_passed(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d=t/'plate';d.mkdir()
   for i in range(2):
    a=np.zeros((48,64,4),np.uint8);a[8+6*i:30+6*i,8+10*i:24+10*i]=[200,120,60,255];Image.fromarray(a).save(d/f'{i:05d}.png')
   (t/'plate.json').write_text(json.dumps({'durations_ms':[40,40]}));extract(d,t/'plate.json',t/'g',colors=1)
   render(t/'g',{},t/'r');r=qc(t/'g',{},t/'r')
   self.assertIsNone(r['checks']['static_interior']['pass']);self.assertFalse(r['auto_checks_passed']);self.assertEqual(r['inconclusive'],['static_interior'])
 def test_agent_notes_are_labelled_as_agent_review(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);g=guides(t);render(g,{},t/'r');r=qc(g,{},t/'r',agent_notes='frames 1-2: arm reads clearly')
   self.assertEqual(r['agent_review']['by'],'agent');self.assertIn('arm',r['agent_review']['notes'])
if __name__=='__main__':unittest.main()
