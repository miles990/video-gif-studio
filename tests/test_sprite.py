import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

spec = importlib.util.spec_from_file_location('sprite', Path(__file__).resolve().parents[1]/'scripts/sprite_export.py')
sprite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sprite)


class SpriteTests(unittest.TestCase):
    def test_multipage_rgba_timing_and_padding(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); (p/'in').mkdir()
            for i in range(5):
                im = Image.new('RGBA', (4, 4), (12+i, 60, 90, 127)); im.putpixel((0, 0), (90, 40, 10, 0)); im.save(p/'in'/f'{i:05d}.png')
            (p/'m.json').write_text(json.dumps({'durations_ms': [20,30,40,50,60], 'source_indices': [0,1,3,4,5]}))
            r = sprite.export(p/'in', p/'m.json', p/'out', max_size=12, padding=1, pivot=(2,3))
            self.assertEqual(len(r['pages']), 2)
            self.assertEqual(r['duration_ms'], 200)
            self.assertEqual(r['frames'][-1]['source_index'], 5)
            with Image.open(p/'out/sheet-000.png') as im:
                self.assertEqual(im.getpixel((2,2)), (12,60,90,127))
                self.assertEqual(im.getpixel((0,0)), (0,0,0,0))
                self.assertEqual(im.getpixel((1,1)), (90,40,10,0))
            with self.assertRaises(FileExistsError):
                sprite.export(p/'in', p/'m.json', p/'out')

    def test_invalid_timing_creates_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); (p/'in').mkdir(); Image.new('RGBA',(2,2)).save(p/'in/00000.png')
            (p/'m.json').write_text('{"durations_ms": []}')
            with self.assertRaises(ValueError):
                sprite.export(p/'in',p/'m.json',p/'out')
            self.assertFalse((p/'out').exists())
