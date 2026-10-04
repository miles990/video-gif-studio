import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from motion_pack import verify, encode

class MotionPackTests(unittest.TestCase):
    def pack(self, path, corrupt=False, unsafe=False):
        data=io.BytesIO();Image.new('RGB',(32,32),'white').save(data,format='PNG');raw=data.getvalue()
        records=[{'path':f'control/frame-{i+1:04d}.png','atSec':i/2,'sha256':hashlib.sha256(raw).hexdigest()} for i in range(2)]
        m={'schema':'laceframe.motion-pack.v1','clip':{'fps':2,'frames':2,'durationSec':1},'controlFrames':{'records':records}}
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('pack.json',json.dumps(m))
            for r in records:z.writestr(r['path'],b'bad' if corrupt else raw)
            if unsafe:z.writestr('../escape','bad')
    def test_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'pack.zip';self.pack(p);self.assertEqual(len(verify(p)[1]),2)
            out=Path(d)/'control.mp4';self.assertEqual(encode(p,out)['frames'],2)
            with self.assertRaises(ValueError):encode(p,out)
    def test_tamper_and_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'pack.zip'
            for kwargs in ({'corrupt':True},{'unsafe':True}):
                self.pack(p,**kwargs)
                with self.assertRaises(ValueError):verify(p)

class WhiteModelPackTests(unittest.TestCase):
    def pack(self, path, mutate=lambda m: None):
        image = io.BytesIO()
        Image.new('RGB', (32, 32), 'gray').save(image, format='PNG')
        data = image.getvalue()
        scene = b'{"schema":"laceframe.white-model.v1"}'
        records = [{'index': i, 'file': f'frames/frame-{i:04d}.png', 'timeSec': i/12,
                    'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for i in range(12)]
        m = {'schema': 'laceframe.white-model.frame-pack.v1', 'pass': 'depth',
             'fps': 12, 'frameCount': 12, 'durationSec': 1, 'width': 32, 'height': 32,
             'scene': {'file': 'scene.json', 'sha256': hashlib.sha256(scene).hexdigest()}, 'frames': records}
        mutate(m)
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('manifest.json', json.dumps(m))
            z.writestr('scene.json', scene)
            for i in range(12): z.writestr(f'frames/frame-{i:04d}.png', data)

    def test_white_model_encode_preserves_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'white.zip'
            self.pack(p)
            report = encode(p, Path(d)/'depth-preview.mp4')
            self.assertEqual(report['frames'], 12)
            self.assertEqual(report['pass'], 'depth')
            self.assertEqual(report['sourceSchema'], 'laceframe.white-model.frame-pack.v1')
            self.assertIn('not for quantitative depth', report['encoding'])
            self.assertEqual(report['creativeApproval'], 'pending')

    def test_rejects_corrupt_white_model_contract(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'white.zip'
            for mutate in [lambda m: m['scene'].update(sha256='bad'),
                           lambda m: m.update(durationSec=1.01),
                           lambda m: m.update(width=34),
                           lambda m: m['frames'][0].update(timeSec=float('nan')),
                           lambda m: m['frames'][0].update(index=True),
                           lambda m: m['frames'][0].update(bytes=1),
                           lambda m: m['frames'][0].update(file='../outside.png')]:
                self.pack(p, mutate)
                with self.assertRaises(ValueError): verify(p)
