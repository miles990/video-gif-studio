"""Production-local last-frame + consistency-reference adapter; preserves safe job handling."""
import sys,base64,json,hashlib
from pathlib import Path
SKILL=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(SKILL/'scripts'))
from grok_client import GrokClient
from grok_video import main
p=Path(__file__).parent;n=int(sys.argv[1]);segment=p/f'segment-{n:02d}'
class Consistent(GrokClient):
 def submit(self,image,prompt,model,duration,resolution):
  enc=lambda f:{'url':'data:image/png;base64,'+base64.b64encode(f.read_bytes()).decode()}
  return self.request('/videos/generations',{'model':model,'prompt':prompt,'image':enc(image),'reference_images':[enc(p/'identity.png')],'duration':duration,'aspect_ratio':'16:9','resolution':resolution})
if '--submit' in sys.argv:
 segment.mkdir(exist_ok=True)
 (segment/'references.json').write_text(json.dumps({'mode':'last-frame plus fixed consistency reference','first_frame':{'path':'start.png','sha256':hashlib.sha256((segment/'start.png').read_bytes()).hexdigest(),'role':'actual previous decoded endpoint' if n>1 else 'generated opening image'},'consistency':{'path':'../identity.png','sha256':hashlib.sha256((p/'identity.png').read_bytes()).hexdigest(),'role':'fixed fish design and visual palette, not forced starting scene'},'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'provider_route':'/videos/generations with image+reference_images; not video extension'},indent=2)+'\n')
main(['--image',str(segment/'start.png'),'--prompt',str(segment/'prompt.txt'),'--duration','6','--resolution','720p','--out',str(segment/'generation'),*sys.argv[2:]],client=Consistent())
