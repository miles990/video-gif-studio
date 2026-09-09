import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pipeline', ROOT/'scripts/gif_pipeline.py')
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class ExportTests(unittest.TestCase):
    def test_opaque_skin_and_magenta_are_not_transparency(self):
        frames = []
        for offset in (0, 1, 2):
            a = np.zeros((40, 40, 4), dtype='uint8')
            a[5:35,5:35] = [240,180,185,255]
            a[10:15,10:15] = [255,0,255,255]
            a[20:23,15+offset:25+offset] = [80,35,60,255]
            a[6,6] = [250,220,210,127]
            a[6,7] = [250,220,210,128]
            frames.append(Image.fromarray(a))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'a.gif'
            pipeline.encode(frames,[40,50,40],p)
            qc=pipeline.verify(p,frames,[40,50,40])
            self.assertEqual(qc['alpha_mismatch_pixels'],0)
            self.assertLess(qc['mean_visible_rgb_error'],3)

    def test_duplicate_frames_preserve_timeline(self):
        a=Image.new('RGBA',(12,12),(20,40,60,255))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'same.gif'
            pipeline.encode([a,a,a],[40,40,50],p)
            self.assertEqual(pipeline.verify(p,[a,a,a],[40,40,50])['duration_ms'],130)

    def test_retiming_keeps_pauses_and_speeds_motion(self):
        ids,ms=pipeline.timing(240,24,[{'start':2,'end':4,'speed':2,'ramp':0}])
        self.assertEqual(sum(ms),9000)
        self.assertTrue(all(t>=20 for t in ms))
        self.assertEqual(ids,sorted(set(ids)))
        with self.assertRaises(ValueError):
            pipeline.timing(240,24,[{'start':2,'end':4,'speed':2},{'start':3,'end':5,'speed':2}])

    def test_key_preserves_skin_and_internal_background_gap(self):
        with tempfile.TemporaryDirectory() as d:
            a=np.full((30,30,4),[255,0,255,255],dtype='uint8')
            a[5:25,5:25]=[245,210,195,255]
            a[12:17,12:17]=[255,0,255,255]
            Image.fromarray(a).save(Path(d)/'000.png')
            frames,_=pipeline.load_frames(Path(d),24,640,(255,0,255),.15,.12)
            arr=np.array(frames[0])
            self.assertEqual(arr[10,10,3],255)
            self.assertEqual(arr[14,14,3],0)


class ProviderTests(unittest.TestCase):
    def test_submit_record_and_resume_without_second_submission(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'fake.py').write_text('''API="test-api"
def _fresh_oauth_session(): return {"token":"never-log-this"}
def _data_uri(path): return "data:image/png;base64,mock"
def _request(url,token,method="GET",body=None):
 if method=="POST": return {"request_id":"test-job"}
 return {"status":"pending","progress":20}
''')
            (p/'image.png').write_bytes(b'fake image for transport mock')
            (p/'prompt.txt').write_text('A moving original object.')
            cmd=[sys.executable,str(ROOT/'scripts/grok_video.py'),'--adapter',str(p/'fake.py'),'--out',str(p/'run')]
            r=subprocess.run(cmd+['--submit','--image',str(p/'image.png'),'--prompt',str(p/'prompt.txt')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run(cmd+['--resume'],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertNotIn('never-log-this',r.stdout+r.stderr+(p/'run/job.json').read_text())
            self.assertEqual(json.loads((p/'run/job.json').read_text())['request_id'],'test-job')
            r=subprocess.run(cmd+['--submit','--image',str(p/'image.png'),'--prompt',str(p/'prompt.txt')],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)


if __name__=='__main__':
    unittest.main()
