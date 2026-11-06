import os,unittest
from unittest.mock import patch
import cv2,numpy as np
from PIL import Image,ImageDraw
from image_fixtures import ImageCase,ROOT,intended_gaps
from image_alpha import alpha_qa,cleanup
from image_hole_judge import validate,SubscriptionHoleJudge

class AlphaRound3(ImageCase):
 def art(self):
  im=Image.new('RGBA',(240,240));d=ImageDraw.Draw(im);d.ellipse((30,30,210,210),fill='orange');d.ellipse((40,60,180,190),fill=(0,0,0,0));return im

 def test_geometry_cannot_pass_even_a_thin_ring(self):
  r=alpha_qa(self.art(),overlay_path=self.path/'overlay.png')
  self.assertEqual(r['status'],'needs_review');self.assertTrue(Path(r['hole_review']['overlay_path']).is_file())
  self.assertFalse(r['hole_geometry'][0]['designed'])

 def test_translucent_channel_cannot_hide_enclosed_clear_core(self):
  a=np.zeros((100,100,4),np.uint8);a[10:90,10:90]=[200,80,40,255]
  a[45:55,45:55,3]=0;a[48:52,10:45,3]=128
  result=alpha_qa(Image.fromarray(a),overlay_path=self.path/'channel.png')
  self.assertEqual(result['status'],'needs_review')
  self.assertEqual(len(result['hole_review']['regions']),1)

 def test_fake_judge_is_strict_and_three_way(self):
  im=self.art()
  self.assertEqual(alpha_qa(im,judge=intended_gaps)['status'],'PASS')
  def body(path,regions):return {'regions':[dict(id=r['id'],classification='body_hole',reason='body material') for r in regions]}
  self.assertEqual(alpha_qa(im,judge=body)['status'],'FAIL')
  for answer in ({'regions':[]},{'regions':[{'id':True,'classification':'intended_gap','reason':'x'}]}, {'regions':[], 'ok':True}):
   self.assertEqual(alpha_qa(im,judge=lambda *_,a=answer:a)['status'],'needs_review')
  def unavailable(*_):raise RuntimeError('offline')
  self.assertEqual(alpha_qa(im,judge=unavailable)['status'],'needs_review')

 def test_all_live_designed_gaps_require_judge(self):
  for path in ['live-s13/sprite/native/image-1.png','live-s13-r2/key/native/image-1.png','live-s13-r3/spRing/native/image-1.png','live-s13-r3/spLegs/native/image-1.png','live-s13-r3/icon/native/image-1.png']:
   with Image.open(ROOT/'tests/fixtures'/path) as im:
    clean,report=cleanup(im)
    self.assertIn(report['after']['status'],('needs_review','PASS'),path)
    if report['after']['hole_review']['regions']:self.assertEqual(report['after']['status'],'needs_review')
    r=alpha_qa(clean,judge=intended_gaps)
    self.assertEqual(r['status'],'PASS',(path,r))

 @unittest.skipUnless(os.environ.get('VGS_LIVE_HOLE_JUDGE')=='1','opt-in subscription vision test')
 def test_live_subscription_judge(self):
  from image_route import Adapter
  p=ROOT/'tests/fixtures/live-s13-r3/icon/native/image-1.png'
  with Image.open(p) as im:clean,_=cleanup(im)
  result=alpha_qa(clean,judge=SubscriptionHoleJudge(Adapter(self.path/'live-state')),overlay_path=self.path/'live-overlay.png')
  self.assertEqual(result['status'],'PASS',result)

from pathlib import Path
