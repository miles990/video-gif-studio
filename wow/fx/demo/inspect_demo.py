"""Stream decoded movies into beat/transition sheets and quantitative evidence."""
import json
from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageSequence
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[2]/'scripts'))
from fx import Context, EFFECTS


def sheet(pictures, target, columns=3):
    board=Image.new('RGB',(columns*320,((len(pictures)+columns-1)//columns)*204),(18,22,30))
    draw=ImageDraw.Draw(board)
    for j,(label,im) in enumerate(pictures):
        x,y=j%columns*320,j//columns*204
        board.paste(im.convert('RGB').resize((320,180)),(x,y+24))
        draw.text((x+8,y+6),label,fill='white')
    board.save(target)


def inspect():
    reports={}
    for tag in ('a','b'):
        m=json.loads((ROOT/f'manifest-{tag}.json').read_text())
        beats=json.loads((ROOT/'beats.json').read_text())['beats_ms']
        targets={0,m['duration_ms']-40}
        for t in beats:
            if t<m['duration_ms']:targets.update(max(0,min(m['duration_ms']-10,t+j)) for j in (-40,0,120,280))
        for tr in m['transitions']:
            targets.update(round(tr['cut_ms']+j*40) for j in range(-3,4))
            targets.update(round(tr['start_ms']+p*(tr['end_ms']-tr['start_ms'])) for p in (.25,.5,.75))
        name='demo' if tag=='a' else 'demo-b'
        cap=cv2.VideoCapture(str(ROOT/f'{name}.mp4'));fps=cap.get(cv2.CAP_PROP_FPS)
        wanted={round(t*fps/1000):t for t in sorted(targets)};pictures=[];means=[];i=0
        while True:
            ok,im=cap.read()
            if not ok:break
            rgb=cv2.cvtColor(im,cv2.COLOR_BGR2RGB)
            means.append(float((rgb@np.array([.2126,.7152,.0722],np.float32)).mean()))
            if i in wanted:pictures.append((f'{i*1000/fps:.0f} ms',Image.fromarray(rgb).resize((320,180))))
            i+=1
        cap.release()
        sheet(pictures,ROOT/f'inspection-final-{tag}.jpg')
        for start in range(0,len(pictures),18):
            sheet(pictures[start:start+18],ROOT/f'inspection-{tag}-{start//18+1}.jpg')
        events=[]
        for effect in m['effects']:
            if effect['name']!='flash_white':continue
            for t in effect['trigger_times_ms']:
                k=round(t*fps/1000);lo=max(0,k-4);hi=min(len(means),k+5)
                peak=lo+int(np.argmax(means[lo:hi]));rise=means[peak]-means[max(0,k-round(.12*fps))]
                events.append({'trigger_ms':t,'peak_ms':peak*1000/fps,'error_ms':peak*1000/fps-t,'rise_luma':rise})
        with Image.open(ROOT/f'work/round1/card-{tag}.png') as im:card=np.array(im.convert('RGBA'))
        effect=next(e for e in m['effects'] if e['name']=='beat_bounce');ctx=Context(640,360)
        def shape(amount):
            params=dict(effect['params'],amount=amount)
            a=EFFECTS['beat_bounce']['function'](card,0,ctx,**params)[:,:,3].astype(float)
            yy,xx=np.indices(a.shape);box=Image.fromarray((a>10).astype('uint8')*255).getbbox()
            return {'centroid_y':float((a*yy).sum()/a.sum()),'height_px':box[3]-box[1]}
        rest,peak=shape(0),shape(1)
        with Image.open(ROOT/f'{name}.gif') as gif:delays=[f.info['duration'] for f in ImageSequence.Iterator(gif)]
        reports[tag]={'duration_ms':len(means)*1000/fps,'gif_duration_ms':sum(delays),'gif_min_delay_ms':min(delays),
            'gif_bytes':(ROOT/f'{name}.gif').stat().st_size,'flash_peaks':events,'freeze_beats_ms':effect['trigger_times_ms'],
            'card_rest':rest,'card_peak':peak,'bounce_displacement_px':rest['centroid_y']-peak['centroid_y'],
            'freeze_luma_mean':float(np.mean(means[round(3.1*fps):round(5.6*fps)])),
            'transitions':[{'name':t['name'],'cut_ms':t['cut_ms'],'midpoint_ms':(t['start_ms']+t['end_ms'])/2} for t in m['transitions']],
            'last_accent_ms':max(t for e in m['effects'] for t in e['trigger_times_ms']), 'render':m['render']}
    (ROOT/'timings.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports,indent=2))

if __name__=='__main__':inspect()
