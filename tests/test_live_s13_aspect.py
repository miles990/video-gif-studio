from image_fixtures import ImageCase,ROOT
from image_keyframes import fit_image,frame_qa,keyframes
from image_common import ImageError
from PIL import Image,ImageDraw
from test_image_keyframes import board
LIVE=ROOT/'tests/fixtures/live-s13'
class LiveAspectTests(ImageCase):
 def test_large_mismatch_is_not_successful_padding(self):
  with Image.open(LIVE/'sprite/native/image-1.png') as im:
   with self.assertRaises(ImageError) as cm:fit_image(im,(1080,1920))
  self.assertEqual(cm.exception.error['code'],'E_ASPECT_UNFIXABLE')
 def test_small_mismatch_is_cropped(self):
  with Image.open(LIVE/'kf/shot-2/keyframe.png') as im:source=im.resize((1088,1920))
  result,qa=fit_image(source,(1080,1920))
  self.assertEqual(result.size,(1080,1920));self.assertEqual(qa['method'],'uniform_crop');self.assertEqual(qa['padding_fraction'],0)
 def test_lower_edge_subject_is_measurable(self):
  im=Image.new('RGB',(180,320),'#444444');ImageDraw.Draw(im).rectangle((50,90,130,319),fill='orange');im.save(self.fixture)
  self.assertEqual(frame_qa(self.fixture,dict(size='MS'))['size_status'],'pass')
  report=frame_qa(LIVE/'kf/shot-2/keyframe.png',dict(size='MS'))
  self.assertNotEqual(report['size_status'],'unassessed')
 def test_large_mismatch_marked_on_shot(self):
  self.configure(image=str(LIVE/'sprite/native/image-1.png'));b=board();b['shots']=b['shots'][:1]
  shot=keyframes(b,self.adapter,self.path/'kf',self.request())['shots'][0]
  self.assertNotIn('keyframe',shot);self.assertEqual(shot['keyframe_failure']['status'],'aspect_unfixable')
