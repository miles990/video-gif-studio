"""Serial reverse measurements for the feature-flag/reverse slice; no source writes."""
import json
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np
from PIL import Image

sys.path[:0]=['scripts','tests']
from fx_reverse import inspect_frames,sample_frames,media_frames,media_info
from fx_render import validate_plan


def inspect(source):
    source=Path(source);info=media_info(source,25)
    if source.is_dir():
        info['durations']=[v/1000 for v in json.loads((source.parent/'manifest.json').read_text())['durations_ms']]
    # Same detector thumbnails, bounded retained memory; decode one media file at a time.
    def small_frames(source,info):
        for image in media_frames(source,info):yield image.convert('RGB').resize((160,90))
    with patch('fx_reverse.media_frames',small_frames):
        images,times,duration=sample_frames(source,info,25)
    report=inspect_frames(images,times,duration)
    return {'source':str(source),'analysis_samples':len(images),'zoom_count':len(report['zoom_punches']),
            'zooms':report['zoom_punches'],'flash_count':len(report['flashes']),'flashes':report['flashes']}


result={}
for name,source in [('neon','examples/neon-zen-pv/final.mp4'),('demo','wow/fx/demo/demo.mp4'),
                    ('roundtrip','wow/fx/roundtrip/render/frames'),
                    ('roundtrip_mp4','wow/fx/roundtrip-mp4/render/animation.mp4')]:
    result[name]=inspect(source)
    print(name,json.dumps(result[name]),flush=True)
for moving in (False,True):
    rng=np.random.default_rng(19);source=rng.integers(20,220,(90,220,3),dtype=np.uint8)
    images=[Image.fromarray(source[:,i if moving else 0:(i if moving else 0)+160]) for i in range(60)]
    report=inspect_frames(images,np.arange(60)*40,2400)
    result['slow_pan' if moving else 'static']={'zoom_count':len(report['zoom_punches'])}
result['validated_plans']=[]
for path in ('wow/fx/demo/plan.json','wow/fx/demo/plan-b.json','wow/fx/demo2/plan.json'):
    plan,*_=validate_plan(path,('mp4',))
    result['validated_plans'].append({'path':path,'experimental':plan.get('experimental',False)})
Path('wow/fx/slice-reverse-measurements.json').write_text(json.dumps(result,indent=2))
