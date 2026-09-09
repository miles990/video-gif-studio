import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from compose_timeline import compose


class TimelineTests(unittest.TestCase):
    def test_insert_tail_hold_then_next_first_and_animation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'a/frames').mkdir(parents=True)
            for i,color in enumerate([(255,0,0,127),(0,0,255,255)]):Image.new('RGBA',(8,8),color).save(p/'a/frames'/f'{i:05d}.png')
            (p/'a/manifest.json').write_text(json.dumps({'durations_ms':[30,70]}))
            (p/'plan.json').write_text(json.dumps({'segments':[{'type':'animation','manifest':'a/manifest.json'},{'type':'still','previous':'last','duration_ms':2000},{'type':'still','manifest':'a/manifest.json','frame':'first','duration_ms':500},{'type':'animation','manifest':'a/manifest.json'}]}))
            r=compose(p/'plan.json',p/'out',('gif','apng','sprite'))
            self.assertEqual(r['duration_ms'],2700)
            with Image.open(p/'out/frames/00002.png') as im:self.assertEqual(im.getpixel((0,0)),(0,0,255,255))
            with Image.open(p/'out/frames/00003.png') as im:self.assertEqual(im.getpixel((0,0)),(255,0,0,127))
            self.assertEqual(json.loads((p/'out/manifest.json').read_text())['durations_ms'],[30,70,2000,500,30,70])

    def test_invalid_first_previous_creates_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'plan.json').write_text(json.dumps({'segments':[{'type':'still','previous':'last','duration_ms':2000}]}))
            with self.assertRaises(ValueError):compose(p/'plan.json',p/'out')
            self.assertFalse((p/'out').exists())

    def test_one_still_apng(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);Image.new('RGBA',(8,8),(1,2,3,255)).save(p/'still.png')
            (p/'plan.json').write_text(json.dumps({'segments':[{'type':'still','image':'still.png','duration_ms':2000}]}))
            compose(p/'plan.json',p/'out',('gif','apng'))
