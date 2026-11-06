"""Offline synthetic/cassette support for slice 13; never invokes a live provider."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from image_route import Adapter,Request
from image_common import read,write

FAKE='''import json,os,sys,time
from pathlib import Path
base=Path(__file__).parent
config=json.loads((base/'fake-config.json').read_text())
if sys.argv[1:]==['login','status']:
 print(config.get('login','Logged in using ChatGPT'));sys.exit(0)
request=sys.stdin.read()
with (base/'calls.jsonl').open('a') as f:f.write(json.dumps(dict(argv=sys.argv[1:],env={k:v for k,v in os.environ.items() if k.startswith(('OPENAI_','CODEX_API_KEY'))},stdin=request))+'\\n')
time.sleep(config.get('delay',0))
if config.get('error'):
 print(config['error']);sys.exit(1)
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':json.dumps({'image_paths':[config['image']]})}}))
'''


class ImageCase(unittest.TestCase):
    def setUp(self):
        (ROOT/'.scratch').mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.scratch',prefix='image-test-')
        self.path=Path(self.tmp.name)
        self.fixture=self.path/'fixture.png'
        im=Image.new('RGB',(90,160),'#3a5a80');d=ImageDraw.Draw(im)
        d.rectangle((25,35,65,140),fill='#c84220');d.ellipse((22,15,68,62),fill='#f5d398');im.save(self.fixture)
        self.fake=self.path/'fake_codex.py';self.fake.write_text(FAKE,encoding='utf-8')
        self.configure()
        self.adapter=Adapter(self.path/'state',codex=[sys.executable,str(self.fake)])
    def tearDown(self):self.tmp.cleanup()
    def configure(self,**kwargs):write(self.path/'fake-config.json',dict(image=str(self.fixture),**kwargs))
    def calls(self):
        path=self.path/'calls.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    def request(self,**kwargs):return Request('Mia with green cup',experimental=True,**kwargs)
