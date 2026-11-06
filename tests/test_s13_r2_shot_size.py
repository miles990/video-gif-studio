from image_fixtures import ImageCase,ROOT
from image_keyframes import frame_qa
from PIL import Image
import numpy as np

class ShotSizeRound2(ImageCase):
 def test_seven_live_scene_frames_are_unassessed(self):
  old=ROOT/'tests/fixtures/live-s13';new=ROOT/'tests/fixtures/live-s13-r2'
  paths=[new/f'kf/shot-{i}/keyframe.png' for i in (1,2,3)]+[new/'kfsq/shot-1/keyframe.png',old/'kf/shot-1/keyframe.png',old/'kf/shot-2/keyframe.png',old/'cafe-keyframe.png']
  for p in paths:
   for size in ('WS','MS','CU'):
    self.assertEqual(frame_qa(p,dict(size=size))['size_status'],'unassessed',(p,size))
 def test_full_frame_matte_cannot_establish_subject(self):
  mask=np.ones((160,90),np.uint8)
  self.assertEqual(frame_qa(self.fixture,dict(size='CU'),subject_mask=mask)['size_status'],'unassessed')
  mask[:]=0;mask[20:70,30:60]=1
  self.assertEqual(frame_qa(self.fixture,dict(size='WS'),subject_mask=mask)['size_status'],'pass')
