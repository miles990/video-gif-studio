"""Serial P1b evidence; temporary media never enters the repository."""
import json
import math
import os
from pathlib import Path
import sys
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import captions
from fx_render import render
from fx.effects.camera import motion
from qa_media import qa
from delivery import settings
from sfx import events_from_plan
from test_p1b import mixed_words, camera_clip


def decode(movie, times):
    capture=cv2.VideoCapture(str(movie));frames=[]
    try:
        for t in times:
            capture.set(cv2.CAP_PROP_POS_FRAMES,round(t*30/1000))
            ok,frame=capture.read()
            if not ok:raise RuntimeError(f'Cannot decode {movie} at {t}')
            frames.append(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)))
    finally:capture.release()
    return frames


def main():
    out=ROOT/'wow/fx';measurements={};tiles=[]
    with tempfile.TemporaryDirectory(prefix='p1b-evidence-') as tmp:
        root=Path(tmp)
        yy,xx=np.indices((960,540))
        checker=np.where(((xx//16+yy//16)%2)[...,None],[235,225,190],[55,80,110]).astype('uint8')
        Image.fromarray(checker).save(root/'busy.png')
        times=[400,600,900,1367,1600,1833]
        columns=[];reports={}
        for preset in captions.PRESETS:
            path=root/f'{preset}.json'
            path.write_text(json.dumps(dict(experimental=True,segments=[dict(type='still',image='busy.png',duration_ms=2100)],
                captions=dict(words=mixed_words(),language='zh',style=preset))),encoding='utf-8')
            render(path,root/preset,('mp4',),fps=30,platform='tiktok')
            movie=next((root/preset).glob('*.mp4'))
            manifest=root/preset/'manifest.json'
            report=qa(movie,root/f'qa-{preset}',timeline=manifest)
            reports[preset]={c['name']:dict(level=c['level'],events=c['events']) for c in report['checks']}
            columns.append(decode(movie,times))
            record=json.loads(manifest.read_text());data=record['captions']
            measurements[preset]=dict(size=record['size'],words=len(data['words']),lines=len(data['lines']),dropped=data['dropped_codepoints'],
                pop_events_ms=[e['at_ms'] for e in events_from_plan({},[],[],[],data)],
                line_text=[line['text'] for line in data['lines']])
        for row,t in enumerate(times):
            tiles.extend((columns[col][row],f'{preset} / {round(t*30/1000)/30:.3f}s') for col,preset in enumerate(captions.PRESETS))
        for language in ('en','zh'):
            words=json.loads((ROOT/f'tests/fixtures/live/whisper-raw-{language}.json').read_text(encoding='utf-8'))['words']
            for preset in ('pop','clean'):
                data=captions.prepare(dict(words=words,language=language,style=preset),ROOT,True)
                cfg=settings((540,960),platform='tiktok')
                renderer=captions.CaptionRenderer(data,cfg['size'],cfg['safe_zone'])
                t=4300 if language=='en' else 4133.333333
                tiles.append((renderer.overlay(Image.fromarray(checker).convert('RGBA').resize(cfg['size']),t).convert('RGB'),f'live {language} / {preset} / {t/1000:.3f}s'))
        camera=root/'camera';camera.mkdir();report=camera_clip(camera)
        measurements['camera_qa']=report
        measurements['caption_qa']=reports
        measurements['crash_out']={str(fps):float(max(abs(np.diff([motion('crash_out',t)[0] for t in np.arange(0,650,1000/fps)])))) for fps in (24,25,30,60)}
        fixtures=[mixed_words()]+[json.loads((ROOT/f'tests/fixtures/live/whisper-raw-{lang}.json').read_text(encoding='utf-8'))['words'] for lang in ('en','zh')]
        words=[w for corpus in fixtures for w in captions.validate_words(corpus)]
        measurements['word_onsets']=dict(words=len(words),presets=4,checks=len(words)*4,
            max_delay_ms=max(math.ceil(w['start_ms']*30/1000-1e-9)*1000/30-w['start_ms'] for w in words),fps=30)
        sheet=Image.new('RGB',(1080,math.ceil(len(tiles)/4)*508),(18,23,31))
        draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
        for i,(frame,label) in enumerate(tiles):
            x=(i%4)*270;y=(i//4)*508
            draw.text((x+8,y+5),label,font=font,fill='white')
            sheet.paste(frame.resize((270,480),Image.Resampling.LANCZOS),(x,y+28))
        sheet.save(out/'p1b-contact.jpg',quality=88)
        measurements['contact_bytes']=(out/'p1b-contact.jpg').stat().st_size
        assert measurements['contact_bytes']<=2_000_000
        (out/'measurements-p1b.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in measurements.items() if k not in ('camera_qa','caption_qa')},ensure_ascii=True,indent=2))
        print('Camera rhythm:',report['cut_to_downbeat_median_ms'],'ms; flash:',next(c['level'] for c in report['checks'] if c['name']=='flashes'))


if __name__=='__main__':main()
