import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import sys
import unittest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
spec = importlib.util.spec_from_file_location('video',Path(__file__).resolve().parents[1]/'scripts/video_export.py')
video = importlib.util.module_from_spec(spec);spec.loader.exec_module(video)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class VideoTests(unittest.TestCase):
    def test_actual_alpha_and_variable_timing_both_containers(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'frames').mkdir()
            for i in range(2):
                im=Image.new('RGBA',(16,16),(20,50,90,0))
                for x in range(4,12):
                    for y in range(4,12): im.putpixel((x,y),(100,120,160,127 if i==0 else 255))
                im.save(p/'frames'/f'{i:05d}.png')
            (p/'manifest.json').write_text(json.dumps({'durations_ms':[30,70]}))
            for ext in ['mov','webm','mp4']:
                with self.subTest(ext=ext):
                    r=video.export(p/'frames',p/'manifest.json',p/f'out.{ext}')
                    self.assertEqual(r['encoded_frames'],10)
                    self.assertEqual(r['transparent'], ext != 'mp4')
                    if ext == 'mp4': self.assertEqual(r['background'], '000000')
                    self.assertLessEqual(r['alpha_max_error_255'],2)
                    self.assertAlmostEqual(r['container_duration_ms'],100,delta=10.01)
                    with self.assertRaises(FileExistsError):video.export(p/'frames',p/'manifest.json',p/f'out.{ext}')
