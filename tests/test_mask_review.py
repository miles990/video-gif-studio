import json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageSequence
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from apply_mask_edits import apply_edits
from extract_guides import extract
from review_masks import review

WHITE=[250,250,250]
def plate(root,n=4):
 d=root/'plate';d.mkdir();k=root/'masks';k.mkdir()
 for i in range(n):
  a=np.zeros((40,60,4),np.uint8);a[8:32,8:28]=[200,60,40,255];a[30:34,30:56]=WHITE+[255];m=np.zeros((40,60),np.uint8)
  if i in (1,2):m[30:34,30:56]=255
  if i==3:m[2:4,2:4]=255
  Image.fromarray(a).save(d/f'{i:05d}.png');Image.fromarray(m).save(k/f'{i:05d}.png')
 man=root/'plate.json';man.write_text(json.dumps({'durations_ms':[50]*n}))
 return d,man,k

def load(d,i):return np.array(Image.open(Path(d)/f'{i:05d}.png'))>0

class Review(unittest.TestCase):
 def test_review_exports_overlay_contact_sheet_and_stability_report(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t);r=review(d,m,k,t/'rv')
   rep=json.loads((t/'rv/report.json').read_text())
   self.assertEqual(rep['areas'],[0,104,104,4]);self.assertEqual(rep['frames_with_mask'],[1,2,3])
   self.assertEqual(rep['isolated_frames'],[3]);self.assertIn(3,rep['area_jump_frames'])
   self.assertEqual(rep['review'],'pending');self.assertEqual(r['frames'],4)
   im=Image.open(t/'rv/overlay.png');self.assertEqual(im.size,(120,40))
   # Pillow merges identical consecutive APNG frames; total playback time must still match the plate.
   self.assertEqual(sum(f.info['duration'] for f in ImageSequence.Iterator(im)),200)
   self.assertTrue((t/'rv/contact.png').exists());self.assertEqual(len(list((t/'rv/frames').glob('*.png'))),4)
   # left half is the untouched plate; the right half tints masked pixels
   f1=np.array(Image.open(t/'rv/frames/00001.png').convert('RGB')).astype(int)
   self.assertFalse((f1[31,40]==f1[31,100]).all())
 def test_review_refuses_mismatched_masks(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t);(k/'00003.png').unlink()
   with self.assertRaises(ValueError):review(d,m,k,t/'rv')

class Edits(unittest.TestCase):
 def test_ops_apply_in_order_within_foreground(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t)
   ops=[{'op':'clear','frames':[3,3]},
        {'op':'add','frames':[0,0],'rect':[0,0,60,40],'color':'#FAFAFA','tolerance':8},
        {'op':'remove','frames':'all','polygon':[[50,28],[59,28],[59,39],[50,39]]}]
   r=apply_edits(d,m,k,ops,t/'e')
   self.assertFalse(load(t/'e/masks',3).any())
   e0=load(t/'e/masks',0);self.assertTrue(e0[31,40]);self.assertFalse(e0[20,20]);self.assertFalse(e0[31,52])
   self.assertTrue(load(t/'e/masks',1)[31,40]);self.assertFalse(load(t/'e/masks',1)[31,52])
   man=json.loads((t/'e/manifest.json').read_text());self.assertEqual(man['review'],'pending');self.assertEqual(len(man['ops']),3)
   self.assertEqual(len(man['source_mask_sha256']),4);self.assertEqual(r['review'],'pending')
 def test_add_never_leaves_plate_foreground(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t);apply_edits(d,m,k,[{'op':'add','frames':'all','rect':[0,0,60,40]}],t/'e')
   self.assertFalse(load(t/'e/masks',0)[0,0]);self.assertTrue(load(t/'e/masks',0)[20,20])
 def test_reviewed_by_is_recorded_not_inferred(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t);apply_edits(d,m,k,[],t/'e',reviewed_by='art lead')
   man=json.loads((t/'e/manifest.json').read_text())
   self.assertEqual(man['review'],'reviewed');self.assertEqual(man['reviewed_by'],'art lead')
 def test_bad_ops_are_refused(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t)
   for i,bad in enumerate(([{'op':'grow','frames':'all'}],[{'op':'add','frames':[0,9],'rect':[0,0,1,1]}],
                           [{'op':'add','frames':'all'}],[{'op':'remove','frames':[2,1],'rect':[0,0,1,1]}])):
    with self.assertRaises(ValueError):apply_edits(d,m,k,bad,t/f'bad{i}')
   (t/'x').mkdir()
   with self.assertRaises(FileExistsError):apply_edits(d,m,k,[],t/'x')

class ExtractRecordsReview(unittest.TestCase):
 def test_extract_carries_mask_manifest_review_status(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d,m,k=plate(t);apply_edits(d,m,k,[],t/'e',reviewed_by='art lead')
   extract(d,m,t/'g',colors=1,effect_masks=t/'e/masks',effect_colors=1)
   fx=json.loads((t/'g/manifest.json').read_text())['effects']
   self.assertEqual(fx['mask_manifest']['review'],'reviewed');self.assertEqual(fx['mask_manifest']['reviewed_by'],'art lead')
   extract(d,m,t/'g2',colors=1,effect_masks=k,effect_colors=1)
   self.assertIsNone(json.loads((t/'g2/manifest.json').read_text())['effects']['mask_manifest'])
if __name__=='__main__':unittest.main()
