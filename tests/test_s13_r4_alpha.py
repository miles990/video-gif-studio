import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
from PIL import Image, ImageDraw
from image_fixtures import ImageCase, ROOT, intended_gaps
from image_alpha import alpha_qa, enclosed_regions
from image_hole_judge import prepare_inputs, SubscriptionHoleJudge


class AlphaRound4(ImageCase):
 def test_tinroot_claw_gaps_keep_context_and_cannot_auto_fail(self):
  path=ROOT/'tests/fixtures/live-s13-r4/spHipsClean/asset.png';seen=[]
  def judge(path,regions):
   manifest=json.loads(Path(path).with_suffix('.inputs.json').read_text())
   self.assertIn('clamp hands',manifest['description'])
   self.assertEqual(len(manifest['crops']),len(regions));seen.append(manifest)
   return intended_gaps(path,regions)
  with Image.open(path) as im:
   result=alpha_qa(im,judge=judge,overlay_path=self.path/'claws.png',description='Tinroot robot with clamp hands on hips; designed gaps between claws and arms.')
  self.assertEqual(result['status'],'PASS',result)
  self.assertGreaterEqual(len(result['hole_review']['regions']),2)
  self.assertEqual(len(seen),2)
  self.assertTrue(all(r['classification']=='intended_gap' for r in result['hole_review']['answers']))

 def art(self):
  im=Image.new('RGBA',(160,160));d=ImageDraw.Draw(im)
  d.rectangle((20,20,140,140),fill='orange')
  d.ellipse((47,47,53,53),fill=(0,0,0,0));d.rectangle((90,80,105,110),fill=(0,0,0,0))
  return im

 def test_tiny_core_is_unobscured_and_crops_preserve_pixels(self):
  im=self.art();labels,regions=enclosed_regions(np.array(im)[...,3])
  manifest=prepare_inputs(im,labels,regions,self.path/'full.png','Robot with claws and nozzle')
  with Image.open(manifest['full_view']) as view:rgb=np.array(view)
  self.assertTrue(np.all(rgb[:160,72:232][labels>0]==[192,210,222]))
  self.assertEqual(len(manifest['crops']),len(regions))
  for crop in manifest['crops']:
   x0,y0,x1,y1=crop['bbox'];box=crop['context_box']
   self.assertEqual(box,[x0-(x1-x0),y0-(y1-y0),x1+(x1-x0),y1+(y1-y0)])
   with Image.open(crop['path']) as zoom:
    self.assertGreaterEqual(min(zoom.width,zoom.height-28),256)
    pixels=np.array(zoom)[28:];scale=crop['scale']
    self.assertTrue(np.array_equal(pixels,np.repeat(np.repeat(pixels[::scale,::scale],scale,0),scale,1)))
  self.assertIn('Robot with claws and nozzle',manifest['prompt'])

 def test_shuffled_ids_are_mapped_back_and_disagreement_abstains(self):
  seen=[]
  def judge(path,regions):
   seen.append([(r['id'],r['label']) for r in regions])
   return {'regions':[dict(id=r['id'],classification='body_hole' if r['label']==1 else 'intended_gap',reason='known test label') for r in regions]}
  result=alpha_qa(self.art(),judge=judge,overlay_path=self.path/'mapped.png')
  self.assertEqual(result['status'],'FAIL');self.assertEqual(len(seen),2);self.assertNotEqual(seen[0],seen[1])
  self.assertEqual([r['classification'] for r in result['hole_review']['answers']],['body_hole','intended_gap'])
  calls=[]
  def disagree(path,regions):
   calls.append(path)
   return {'regions':[dict(id=r['id'],classification='body_hole' if len(calls)==1 else 'intended_gap',reason='conflicting fake') for r in regions]}
  self.assertEqual(alpha_qa(self.art(),judge=disagree,overlay_path=self.path/'disagree.png')['status'],'needs_review')

 def test_second_failure_and_invalid_ids_cannot_pass(self):
  for failure in ('unavailable','missing'):
   calls=[]
   def judge(path,regions):
    calls.append(path)
    if len(calls)==1:return intended_gaps(path,regions)
    if failure=='unavailable':raise OSError('offline')
    return {'regions':[]}
   result=alpha_qa(self.art(),judge=judge,overlay_path=self.path/(failure+'.png'))
   self.assertEqual(result['status'],'needs_review')

 def test_adapter_sends_full_view_and_every_crop_with_exact_prompt(self):
  im=self.art();labels,regions=enclosed_regions(np.array(im)[...,3]);path=self.path/'full.png'
  manifest=prepare_inputs(im,labels,regions,path,'Tinroot with designed claw gaps')
  answer=intended_gaps(path,regions)
  response=SimpleNamespace(returncode=0,stderr='',stdout=json.dumps({'type':'item.completed','item':{'type':'agent_message','text':json.dumps(answer)}}))
  adapter=Mock(state=self.path/'state');adapter.command.return_value=response
  self.assertEqual(SubscriptionHoleJudge(adapter)(path,regions),answer)
  args,env,prompt=adapter.command.call_args.args
  self.assertEqual([args[i+1] for i,arg in enumerate(args) if arg=='--image'],[str(path),*[r['path'] for r in manifest['crops']]])
  self.assertEqual(prompt,manifest['prompt'])
