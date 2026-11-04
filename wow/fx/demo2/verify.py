"""Decoded event neighborhoods and timeline QA; no inference and bounded memory."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parents[2]/'scripts'))
from media_runtime import executable
from qa_media import qa


def verify():
    manifest=json.loads((ROOT/'manifest.json').read_text());plan=json.loads((ROOT/'plan.json').read_text(encoding='utf-8'))
    beats=json.loads((ROOT/'beats.json').read_text())['beats_ms'];master=ROOT/json.loads((ROOT/'build-results.json').read_text())['master']
    edges=np.cumsum([0]+manifest['durations_ms']);events=[]
    cuts=[s['start_ms'] for s in manifest['segments'][1:]]
    accents=next(e['trigger_times_ms'] for e in manifest['effects'] if e['name']=='shake')
    for t in cuts:
        events.extend((t+dt,'cut') for dt in range(-120,121,40))
    for t in accents:events.extend((t+dt,'downbeat') for dt in (-40,0,40))
    for t in (beats[18],beats[20]):events.extend((t+dt,'split layout') for dt in (-40,0,40))
    for tr in manifest['transitions']:
        events.extend((tr['start_ms']+p*(tr['end_ms']-tr['start_ms']),tr['name']) for p in (.25,.5,.75))
    events.extend((t,'ramp') for t in (0,1200,2400,2680,2720,2760,2800,2840,2880))
    events.extend((t,'parallax') for t in (beats[24],(beats[24]+beats[32])/2,beats[32]-40))
    for start in (0,beats[8],beats[26],beats[48]):events.extend((start+i*40,'text entrance') for i in range(5))
    events.extend((t,'ending') for t in range(int(edges[-1]-2000),int(edges[-1]),200))
    events=sorted(set((round(t),label) for t,label in events if 0<=t<edges[-1]))
    sheets=[]
    for page in range(0,len(events),24):
        board=Image.new('RGB',(320*3,204*8),(16,20,28));draw=ImageDraw.Draw(board)
        for i,(t,label) in enumerate(events[page:page+24]):
            index=max(0,int(np.searchsorted(edges,t,side='right')-1));im=Image.open(master/'frames'/f'{index:05d}.png').convert('RGB').resize((320,180))
            x,y=i%3*320,i//3*204;board.paste(im,(x,y+24));draw.text((x+8,y+6),f'{t} ms / {label}',fill='white')
        file=ROOT/f'inspection-{page//24+1}.jpg';board.save(file,quality=88);sheets.append(file.name)
    # Decode sequentially to 160px at the encoded 100fps; at most one frame retained.
    proc=subprocess.Popen([executable('ffmpeg'),'-v','error','-i',str(ROOT/'demo.mp4'),'-vf','scale=160:90','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    differences=[];previous=None
    while True:
        raw=proc.stdout.read(160*90*3)
        if len(raw)<160*90*3:break
        frame=np.frombuffer(raw,np.uint8).astype(np.float32)
        differences.append(float(np.abs(frame-previous).mean()) if previous is not None else 0);previous=frame
    proc.wait();alignment=[]
    for t in accents:
        index=round(t/10);lo=max(1,index-12);hi=min(len(differences),index+13)
        peak=lo+int(np.argmax(differences[lo:hi]));alignment.append({'event_ms':t,'peak_ms':peak*10,'error_ms':peak*10-t,'pass':abs(peak*10-t)<=40})
    out=ROOT/'work'/f'qa-{time.time_ns()}';quality=qa(ROOT/'demo.mp4',out,timeline=ROOT/'manifest.json')
    (ROOT/'qa').mkdir(exist_ok=True)
    for file in out.iterdir():
        if file.is_file():shutil.copy2(file,ROOT/'qa'/file.name)
    result={'duration_ms':int(edges[-1]),'downbeat_alignment':alignment,'all_within_one_25fps_frame':all(e['pass'] for e in alignment),'qa_level':quality['level'],'inspection_sheets':sheets,'frames_inspected':len(events)}
    (ROOT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':verify()
