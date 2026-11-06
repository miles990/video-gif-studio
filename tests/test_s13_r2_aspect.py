from image_fixtures import ImageCase,ROOT
from image_keyframes import fit_image
from image_common import ImageError
from PIL import Image,ImageDraw,ImageOps

class AspectRound2(ImageCase):
 def test_two_three_crops_when_subject_fits(self):
  for p in (ROOT/'tests/fixtures/live-s13/sprite/cleaned.png',ROOT/'tests/fixtures/live-s13-r2/sprite2/native/image-1.png'):
   with Image.open(p) as im:subject=ImageOps.contain(im.convert('RGBA'),(120,240))
   source=Image.new('RGBA',(240,360));source.alpha_composite(subject,((240-subject.width)//2,60))
   result,qa=fit_image(source,(180,320))
   self.assertEqual(qa['method'],'subject_safe_crop');self.assertEqual(qa['padding_fraction'],0)
   self.assertIsNotNone(result.getbbox())
 def test_two_three_scene_or_wide_subject_refused(self):
  im=Image.new('RGBA',(240,360));ImageDraw.Draw(im).rectangle((2,20,238,340),fill='orange')
  with self.assertRaises(ImageError):fit_image(im,(180,320))
  for p in (ROOT/'tests/fixtures/live-s13/cafe-keyframe.png',ROOT/'tests/fixtures/live-s13-r2/kfsq/shot-1/keyframe.png'):
   with Image.open(p) as im:scene=im.resize((240,360))
   with self.assertRaises(ImageError):fit_image(scene,(180,320))
