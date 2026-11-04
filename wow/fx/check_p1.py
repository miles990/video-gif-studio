"""Serial, offline P1 measurements. Temporary media outside the repository.

Outputs only the requested JSON and a small caption contact sheet. No model,
download, paid service, or optional backend is invoked.
"""
import argparse
import json
from pathlib import Path
import platform
import sys
import tempfile
import time
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from captions import prepare,CaptionRenderer
from delivery import settings
from beat_layers import layers
from music_fit import candidates,join_audio
from reframe import plan_path
from review_shots import build
from fx.easing import EASINGS


def run(out):
    report=dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,network_calls=0,model_calls=0,
                methodology='Synthetic offline measurements, not independent acceptance or quality-gate review')
    bounds=[0,8000,24000,40000,48000,60000,64000]
    beatmap=dict(duration_ms=64000,beats_ms=list(range(0,64000,500)),downbeats_ms=list(range(0,64000,2000)),
                 sections=[dict(start_ms=a,end_ms=b,label=str(i)) for i,(a,b) in enumerate(zip(bounds,bounds[1:]))])
    report['S58']={density:len(layers(beatmap,cut_density=density)['cuts_ms']) for density in ('low','mid','high')}
    t=np.arange(64*48000)/48000
    mono=.2*np.sin(2*np.pi*(110*t+.008*t*t))+.04*np.sin(2*np.pi*173*t)
    audio=np.column_stack((mono,mono*.8));baseline=float(np.percentile(abs(np.diff(audio,axis=0)),99.9));measure=[]
    for spans in candidates(beatmap,30000):
        result,joins=join_audio(audio,spans);peaks=[];hf=[]
        def high_energy(block):
            fft=np.fft.rfft(block[:,0]*np.hanning(len(block)))
            frequencies=np.fft.rfftfreq(len(block),1/48000)
            return float(np.sum(abs(fft[frequencies>8000])**2)/len(block)**2)
        for join in joins:
            index=round(join['output_ms']*48)
            peaks.append(float(np.max(abs(np.diff(result[index-960:index+960],axis=0)))))
            center=high_energy(result[index-480:index+480])
            # Identical window lengths avoid comparing different Hann leakage
            # floors. Average 20ms windows in the preceding/following 200ms.
            neighborhoods=[result[at:at+960] for at in range(index-9600,index-960,960)]
            neighborhoods += [result[at:at+960] for at in range(index+960,index+9600,960)]
            neighbors=float(np.mean([high_energy(block) for block in neighborhoods]))
            hf.append(float(10*np.log10(max(center,1e-30)/max(neighbors,1e-30))))
        measure.append(dict(duration_ms=len(result)/48,spans=spans,joins=joins,max_join_derivative=max(peaks),
                            derivative_ratio=max(peaks)/baseline,tail_50ms_dbfs=float(20*np.log10(np.sqrt(np.mean(result[-2400:]**2)))),
                            join_hf_vs_neighbors_db=hf))
    report['S59']=dict(source_derivative_p999=baseline,candidates=measure)
    boxes=[[400+i*2,180,560+i*2,750] for i in range(120)]
    tracking=plan_path(boxes,(1920,1080));scale=1920/tracking['path'][0]['crop'][3]
    centers=np.array([p['crop'][:2] for p in tracking['path']])*scale
    report['S61']=dict(frames=120,max_step_px=float(np.linalg.norm(np.diff(centers,axis=0),axis=1).max()),
                      max_acceleration_px=float(np.linalg.norm(np.diff(centers,n=2,axis=0),axis=1).max()),
                      needs_review=sum(p['needs_review'] for p in tracking['path']),
                      min_headroom_ratio=min(p['subject_bbox'][1]/(p['subject_bbox'][3]-p['subject_bbox'][1]) for p in tracking['path']))
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);segments=[]
        yy,xx=np.indices((360,640));texture=np.empty((360,640,4),np.uint8)
        for i in range(8):
            texture[...,:3]=np.stack(((xx+i*35)%256,(yy*2+i*17)%256,(xx+yy+i*29)%256),axis=-1);texture[...,3]=255
            Image.fromarray(texture).save(root/f'{i}.png');segments.append(dict(type='still',image=f'{i}.png',duration_ms=1200))
        plan=dict(segments=segments,effects=[dict(name='grade',sat=.8)],experimental=True)
        path=root/'plan.json';path.write_text(json.dumps(plan));start=time.perf_counter()
        first=build(path,root/'first',experimental=True);first_wall=time.perf_counter()-start
        decisions=root/'decisions.json';decisions.write_text(json.dumps(dict(shots={str(i):dict(action='replace',effects=[dict(name='grade',sat=0,gain=.6)]) for i in (2,5)})))
        start=time.perf_counter();second=build(path,root/'second',root/'first',decisions,True);second_wall=time.perf_counter()-start
        changes=[]
        for i,(a,b) in enumerate(zip(first['shots'],second['shots'])):
            with Image.open(root/'first'/a['frames'][0]) as im: aa=np.array(im).astype(float)
            with Image.open(root/'second'/b['frames'][0]) as im: bb=np.array(im).astype(float)
            changes.append(dict(shot=i,all_png_hashes_equal=a['sha256']==b['sha256'],pixel_mad=float(np.mean(abs(aa-bb)))/255))
        report['S62']=dict(full_seconds=first_wall,changed_seconds=second_wall,wall_ratio=second_wall/first_wall,
                          rerendered=second['rerendered_shots'],reused=second['reused_shots'],shots=changes,
                          thumbnail_count=len(second['events']),browser_console='not executed; coordinator can open generated review HTML')
    cfg=settings((1080,1920),platform='tiktok',proxy=True);sheet=Image.new('RGB',(4*360,640),(25,30,38));metrics=[]
    for i,preset in enumerate(('pop','typewriter','bounce','clean')):
        words=[dict(text='台北市政府',start_ms=0,end_ms=500),dict(text='真的嗎？',start_ms=500,end_ms=1000)]
        p=prepare(dict(words=words,style=preset),Path('.'),True);renderer=CaptionRenderer(p,cfg['size'],cfg['safe_zone'])
        base=Image.new('RGBA',cfg['size'],(90,110,140,255));image=renderer.overlay(base,90)
        ink=renderer.overlay(Image.new('RGBA',cfg['size']),90).getbbox()
        sheet.paste(image.convert('RGB'),(i*360,0));ImageDraw.Draw(sheet).text((i*360+15,30),preset,fill='white')
        metrics.append(dict(preset=preset,bbox_at_90ms=ink,safe_bounds=renderer.bounds))
    sheet_path=Path(out).with_name('p1-caption-contact.png');sheet.save(sheet_path)
    report['S56']=dict(preview_size=cfg['size'],presets=metrics,contact_sheet=sheet_path.name,quality_gate='pending independent reviewers')
    Path(out).write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    print(json.dumps(run(args.out),indent=2))
