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
