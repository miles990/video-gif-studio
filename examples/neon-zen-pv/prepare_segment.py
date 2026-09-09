import sys,subprocess,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=Path(__file__).parent;n=int(sys.argv[1]);s=p/f'segment-{n:02d}';skill=Path(__file__).resolve().parents[2]
subprocess.run([str(skill/'.venv/bin/python'),str(skill/'scripts/gif_pipeline.py'),str(s/'generation/source.mp4'),'--out',str(s/'prepared'),'--width','960'],check=True)
# Optional editorial typography is applied before final video encoding. All scene VFX remain Grok generated.
a=json.loads((s/'prepared/manifest.json').read_text());a['source_video']='../generation/source.mp4';a['source_video_sha256']=__import__('hashlib').sha256((s/'generation/source.mp4').read_bytes()).hexdigest();(s/'prepared/manifest.json').write_text(json.dumps(a,indent=2)+'\n')
