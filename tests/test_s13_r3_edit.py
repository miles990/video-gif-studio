import contextlib,io,json
from unittest.mock import patch
import numpy as np,cv2
from PIL import Image
from image_fixtures import ImageCase,ROOT
from image_edit import composite,register,region_mask,edit
from image_edit_seam import ghosting,graphcut_weights

class EditRound3(ImageCase):
 def test_reviewer_hedgehog_ghosts_are_detected(self):
  p=ROOT/'tests/fixtures/live-s13-r3'
  with Image.open(p/'kf/shot-1/keyframe.png') as im:a=np.array(im.convert('RGBA'))
  with Image.open(p/'edit/regeneration/image-1.png') as im:b=np.array(im.convert('RGBA'))
  with Image.open(p/'edit/mask.png') as im:mask=np.array(im.resize((a.shape[1],a.shape[0]),Image.Resampling.NEAREST).convert('L'))
  expanded=cv2.dilate(mask,np.ones((15,15),np.uint8));aligned,_=register(a,b,expanded)
  band=(expanded>0)&(cv2.erode(mask,np.ones((15,15),np.uint8))==0)
  self.assertTrue(ghosting(a,aligned,band)['flagged'])
  result,qa,region=composite(Image.fromarray(a),Image.fromarray(b),mask)
  self.assertLessEqual(qa['feather_px'],3)
  self.assertTrue(np.array_equal(np.array(result)[region==0],a[region==0]))
  if qa['registration']['residual_px']>1 or qa['seam']['ghosting']['flagged']:self.assertEqual(qa['acceptance'],'needs_review')

 def test_seam_uses_low_mismatch_corridor_and_flags_double_edges(self):
  a=np.full((160,160,4),255,np.uint8);b=a.copy();mask=np.zeros((160,160),np.uint8);mask[50:110,50:110]=255
  b[40:120,40:120,:3]=100;expanded=cv2.dilate(mask,np.ones((41,41),np.uint8))
  w,q=graphcut_weights(a,b,mask,expanded,8)
  self.assertEqual(q['feather_px'],3);self.assertTrue(np.all(w[expanded==0]==0));self.assertTrue(np.all(w[mask>0]==1))
  a[20:140,30:33,:3]=0;b=a.copy();b[20:140,30:33,:3]=255;b[20:140,34:37,:3]=0
  band=np.ones(mask.shape,bool)
  self.assertTrue(ghosting(a,b,band)['flagged']);self.assertFalse(ghosting(a,a,band)['flagged'])

 def test_review_filename_and_cli_exit_three(self):
  from imagegen import main
  from image_common import read
  base=Image.new('RGBA',(160,240),'orange');p=self.path/'source.png';base.save(p)
  candidate=Image.new('RGBA',(114,129),'blue');candidate.save(self.fixture)
  qa=dict(acceptance='needs_review',registration={'residual_px':2},outside_identical=True)
  local=Image.new('RGBA',(114,129),'blue');region=np.zeros((129,114),np.uint8);region[32:97,32:82]=255
  with patch('image_edit.composite',return_value=(local,qa,region)):
   result=edit(self.adapter,self.request(),p,self.path/'edit','blue',region=[53,128,50,65])
  self.assertTrue(result['path'].endswith('.needs-review.png'));self.assertFalse(result['ok']);self.assertFalse((self.path/'edit/edited.png').exists())
  sent=self.calls()[0]['stdin'];self.assertIn('reference-crop.png',sent);self.assertIn('SAME framing',sent)
  with patch('image_edit.edit',return_value=result),contextlib.redirect_stdout(io.StringIO()) as stdout:
   rc=main(['edit','--image',str(p),'--instruction','blue','--region','53,128,50,65','--out',str(self.path/'cli'),'--experimental'])
  self.assertEqual(rc,3);self.assertFalse(json.loads(stdout.getvalue())['ok'])
