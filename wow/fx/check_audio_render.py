"""Encoded synthetic click-track verification (normal venv + FFmpeg only)."""
import json
from pathlib import Path
import sys
import time
import wave
import cv2
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'scripts'))
from fx_render import render
work=ROOT/f'demo/work/audio-check-{time.time_ns()}';work.mkdir(parents=True)
Image.new('RGBA',(32,24),(40,40,40,255)).save(work/'frame.png')
rate=48000;t=np.arange(rate*4)/rate;local=t%.5
x=np.sin(2*np.pi*1000*t)*np.where((t//.5).astype(int)%2==0,.8,.2)*np.exp(-local*100)*(local<.03)
with wave.open(str(work/'click.wav'),'wb') as wav:
 wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes((x*32767).astype('<i2').tobytes())
records=[]
for channel,offset in (('onset',0),('onset',20),('energy',0),('energy',20)):
 plan={'fps':25,'music':{'file':'click.wav','in_ms':offset},'segments':[{'type':'still','image':'frame.png','duration_ms':3800}], 'effects':[{'name':'flash_white','amount':{'on':channel,'decay_ms':140}}]}
 file=work/f'{channel}-{offset}.json';file.write_text(json.dumps(plan));out=work/f'{channel}-{offset}'
 render(file,out,('mp4',))
 cap=cv2.VideoCapture(str(out/'animation.mp4'));fps=cap.get(cv2.CAP_PROP_FPS);luma=[]
 while True:
  ok,frame=cap.read()
  if not ok:break
  luma.append(float(frame.mean()))
 cap.release();events=[]
 for beat in range(0 if offset==0 else 1,8):
  at=beat*500-offset;ids=[i for i in range(len(luma)) if at<=i*1000/fps<=at+30]
  peak=max(ids,key=lambda i:luma[i]);events.append({'beat':beat,'trigger_ms':at,'peak_ms':peak*1000/fps,'luma':luma[peak]})
 loud=min(e['luma'] for e in events if e['beat']%2==0);quiet=max(e['luma'] for e in events if e['beat']%2)
 assert loud-quiet>=30 and min(e['luma'] for e in events)>80
 records.append({'channel':channel,'in_ms':offset,'every_visible_beat_flashes':True,'loud_min':loud,'quiet_max':quiet,'luma_gap':loud-quiet,'events':events})
(ROOT/'audio-render-evidence.json').write_text(json.dumps(records,indent=2));print(json.dumps([{k:v for k,v in r.items() if k!='events'} for r in records],indent=2))
