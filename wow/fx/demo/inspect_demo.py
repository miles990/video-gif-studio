"""Decoded beat measurements, inspection sheets and a smaller GIF preview."""
import json
from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,'scripts')
from gif_pipeline import encode,verify

root=Path(__file__).resolve().parent
reports={}
for tag in ('a','b'):
    master=root/f'master-{tag}';m=json.loads((master/'manifest.json').read_text())
    cap=cv2.VideoCapture(str(root/('demo.mp4' if tag=='a' else 'demo-b.mp4')))
    fps=cap.get(cv2.CAP_PROP_FPS);means=[];frames=[]
    while True:
        ok,im=cap.read()
        if not ok:break
        rgb=cv2.cvtColor(im,cv2.COLOR_BGR2RGB)
        means.append(float((rgb@np.array([.2126,.7152,.0722])).mean()));frames.append(rgb)
    cap.release();events=[]
    for effect in m['effects']:
        if effect['name']!='flash_white':continue
        for t in effect['trigger_times_ms']:
            k=round(t*fps/1000);lo=max(0,k-3);hi=min(len(means),k+4)
            peak=lo+int(np.argmax(means[lo:hi]));rise=means[peak]-means[max(0,k-3)]
            events.append({'trigger_ms':t,'peak_ms':peak*1000/fps,'error_ms':peak*1000/fps-t,
                           'rise_over_3_encoded_frames':rise,'pass':abs(peak*1000/fps-t)<=1000/fps and rise>=40})
    # 480px compatibility previews, keeping exact frame exposures and decoded QC.
    preview=[]
    for file in sorted((master/'frames').glob('*.png')):
        with Image.open(file) as im:preview.append(im.convert('RGBA').resize((480,270),Image.Resampling.LANCZOS))
    gif=root/('demo.gif' if tag=='a' else 'demo-b.gif')
    encode(preview,m['durations_ms'],gif);qc=verify(gif,preview,m['durations_ms'])
    reports[tag]={'encoded_fps':fps,'flash_peaks':events,'render':m['render'],'duration_ms':m['duration_ms'],
                  'gif_bytes':gif.stat().st_size,'gif_qc':qc,'transitions':[{'cut_ms':t['cut_ms'],'midpoint_ms':(t['start_ms']+t['end_ms'])/2} for t in m['transitions']]}
    targets=[0,2800,2890,2930,2970,3050,3500,4300,4390,4480,5720,5810,5850,5890,5970,6200,7200,8700]
    # Include +/-3 native rendered frames at every edit plus the hold endpoints.
    targets=sorted(set(targets+[round(t['cut_ms']+j*40) for t in m['transitions'] for j in range(-3,4)]))
    board=Image.new('RGB',(3*320,((len(targets)+2)//3)*204),(18,22,30));draw=ImageDraw.Draw(board)
    for j,t in enumerate(targets):
        idx=min(len(frames)-1,round(t*fps/1000));im=Image.fromarray(frames[idx]).resize((320,180))
        x,y=j%3*320,j//3*204;board.paste(im,(x,y+24));draw.text((x+8,y+6),f'{t/1000:.3f}s',fill='white')
    board.save(root/f'inspection-final-{tag}.jpg')
(root/'timings.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports,indent=2))
