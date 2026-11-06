"""Render storyboard cards/footage through the existing timeline renderer, then measure."""
import argparse
from pathlib import Path
import sys
import wave
import cv2
import numpy as np
from PIL import Image,ImageDraw
from taste_common import read,write,run,executable
from storyboard import validate,lint,design_curve,fingerprint,shot_table


def card(shot,size=(320,180)):
    w,h=size; im=Image.new('RGBA',size,shot.get('background','#556578'));d=ImageDraw.Draw(im)
    scale={'EWS':.08,'WS':.18,'MS':.34,'CU':.65,'ECU':.9}[shot['size']]
    radius=max(2,round(h*scale*.32));cx=w//2;cy=int(h*.46)
    d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill='#18232e')
    d.polygon([(cx-radius,cy+radius),(cx-2*radius,cy+5*radius),(cx+2*radius,cy+5*radius),(cx+radius,cy+radius)],fill='#18232e')
    d.text((7,7),f"{shot['id']} / {shot['size']} / {shot['duration']:.3f}s",fill='white')
    d.text((7,h-18),f"{shot['motion']} {'-->' if shot['motion']!='static' else '-'}",fill='white')
    return np.asarray(im)


def moved(frame,shot,t):
    h,w=frame.shape[:2];motion=shot['motion'];u=np.clip(t/shot['duration'],0,1);zoom=1.;dx=dy=0.
    if motion in ('push','dolly','smooth_in','expo_in','crash_in','spring_in','punch'):zoom=1+.2*u
    elif motion in ('pull','crash_out'):zoom=1.2-.2*u
    elif motion in ('pan','whip'):dx=.12*w*u
    elif motion in ('tilt','crane'):dy=.12*h*u
    elif motion=='drift':dx=.04*w*u;zoom=1+.05*u
    elif motion=='handheld':dx=np.sin(t*5)*w*.008;dy=np.sin(t*7)*h*.008
    matrix=np.array([[zoom,0,(1-zoom)*w/2+dx],[0,zoom,(1-zoom)*h/2+dy]],np.float32)
    return cv2.warpAffine(frame,matrix,(w,h),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)


def source_frame(shot,base,size):
    filename=shot.get('image',shot.get('footage'))
    if not filename:return card(shot,size)
    path=base/filename
    if not path.is_file():
        shot['asset_fallback']=dict(path=str(path),reason='missing footage')
        return card(shot,size)
    try:
        with Image.open(path) as im:return np.array(im.convert('RGBA').resize(size))
    except OSError:
        cap=cv2.VideoCapture(str(path));cap.set(cv2.CAP_PROP_POS_MSEC,shot.get('in_ms',0));ok,bgr=cap.read();cap.release()
        if not ok:
            shot['asset_fallback']=dict(path=str(path),reason='undecodable footage')
            return card(shot,size)
        return cv2.cvtColor(cv2.resize(bgr,size),cv2.COLOR_BGR2RGBA)


def audio_mix(board,base,out,music=None):
    rate=48000;mix=np.zeros((round(board['duration']*rate),2),np.float32);used=False
    def audio(file):
        return np.frombuffer(run([executable('ffmpeg'),'-v','error','-i',str(file),'-vn','-ar',str(rate),'-ac','2','-f','f32le','-']).stdout,'<f4').reshape(-1,2)
    if music:
        x=audio(music);n=min(len(x),len(mix));mix[:n]+=x[:n];used=True
    shots=board['shots']
    for i,s in enumerate(shots):
        sound=s.get('sound',{})
        if not sound.get('file'):continue
        start=s['start']-sound.get('audio_lead_ms',0)/1000;end=s['end']+sound.get('audio_tail_ms',0)/1000
        if i and shots[i-1].get('sound',{}).get('audio_tail_ms'):start+=shots[i-1]['sound']['audio_tail_ms']/1000
        if i+1<len(shots):end-=shots[i+1].get('sound',{}).get('audio_lead_ms',0)/1000
        x=audio(base/sound['file']);a=max(0,round(start*rate));skip=max(0,-round(start*rate));n=min(len(x)-skip,len(mix)-a,max(0,round((end-max(0,start))*rate)))
        if n>0:mix[a:a+n]+=x[skip:skip+n];used=True
    if not used:return None
    file=out/'sound.wav'
    with wave.open(str(file),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate);w.writeframes((np.clip(mix,-1,1)*32767).astype('<i2').tobytes())
    return file


def bounded_effects(plan,duration_ms):
    """Expand before clamping, including envelopes; renderer still validates."""
    from fx_recipes import expand
    plan=expand(plan,[],experimental=True);effects=[];adjustments=[]
    for effect in plan.get('effects',[]):
        start=max(0,effect.get('start_ms',0));end=min(duration_ms,effect.get('end_ms',duration_ms))
        if end<=start:
            adjustments.append(dict(effect=effect['name'],action='omitted beyond film',start_ms=start));continue
        if end!=effect.get('end_ms',end):adjustments.append(dict(effect=effect['name'],action='clamped to film',end_ms=end))
        effect.update(start_ms=start,end_ms=end)
        for key,v in effect.items():
            if isinstance(v,dict) and 'keyframes' in v:
                points=np.asarray(v['keyframes'],float)
                v['keyframes']=[[start,float(np.interp(start,points[:,0],points[:,1]))]]+[[float(t),float(x)] for t,x in points if start<t<end]+[[end,float(np.interp(end,points[:,0],points[:,1]))]]
        effects.append(effect)
    plan['effects']=effects
    for event in plan.get('recipe_events',[]):event['sfx_at_ms']=min(duration_ms,event['sfx_at_ms'])
    return plan,adjustments


def to_plan(board,out,base=Path('.'),size=(320,180),music=None):
    """One converter for proxy and final renders. Frame clocks quantized to 10 ms."""
    b=validate(board);out=Path(out);out.mkdir(parents=True,exist_ok=True);base=Path(base)
    segments=[];effects=[];fallbacks=[]
    for i,s in enumerate(b['shots']):
        frame=source_frame(s,base,size);folder=out/f'shot-{i+1}'/'frames';folder.mkdir(parents=True,exist_ok=True)
        if s.get('asset_fallback'):fallbacks.append(dict(shot=i+1,**s['asset_fallback']))
        # 25 fps card motion is sampled identically by any delivery frame rate.
        edges=np.r_[np.arange(0,round(s['duration']*1000),40),round(s['duration']*1000/10)*10]
        if len(edges)>2 and edges[-1]-edges[-2]<20:edges=np.delete(edges,-2)
        durations=np.diff(edges).astype(int).tolist()
        if min(durations)<20:raise ValueError('Shot too short for the existing timeline (minimum 20 ms)')
        for j,t in enumerate(edges[:-1]):Image.fromarray(moved(frame,s,t/1000)).save(folder/f'{j:05d}.png')
        write(folder.parent/'manifest.json',dict(durations_ms=durations))
        segment=dict(type='animation',manifest=str((folder.parent/'manifest.json').resolve()))
        transition=s.get('transition')
        if i and transition and transition not in ('cut','hard_cut'):
            tr=dict(transition) if isinstance(transition,dict) else dict(name=transition)
            segment['transition']={k:v for k,v in tr.items() if k not in ('serves_core','why','rule_break','family','id')}
            segment['transition'].setdefault('duration_ms',max(40,int(min(.2,s['duration']/2,b['shots'][i-1]['duration']/2)*100)*10))
        segments.append(segment)
        recipe=s.get('recipe')
        if recipe:
            name=recipe.get('name',recipe.get('recipe')) if isinstance(recipe,dict) else recipe
            event=dict(recipe=name,at_ms=round(s['start']*1000))
            if isinstance(recipe,dict) and 'perceived' in recipe:event['perceived']=recipe['perceived']
            elif 'perceived' in s:event['perceived']=s['perceived']
            effects.append(event)
    plan=dict(fps=b['fps'],segments=segments,effects=effects,experimental=True,seed=b.get('seed',0))
    plan,adjustments=bounded_effects(plan,round(b['duration']*1000))
    write(out/'asset-fallbacks.json',fallbacks);write(out/'effect-adjustments.json',adjustments)
    sound=audio_mix(b,base,out,music)
    if sound:plan.update(source_audio=dict(file=str(sound.resolve())),keep_audio=True,loudnorm=True)
    write(out/'plan.json',plan);return plan


def render(board,out,base=Path('.'),music=None,size=(320,180)):
    out=Path(out);b=validate(board);check=lint(b)
    if check['errors']:raise ValueError('Storyboard has unannotated structural errors; inspect storyboard_lint first')
    if out.exists():raise ValueError('Use a new output directory')
    # Persist the automatic/authored treatment before any rendering work.
    write(out/'treatment.json',dict(core=b.get('core',''),design_curve=check['design_curve'],origin=check['design_origin']))
    write(out/'lint.json',check);to_plan(board,out/'assets',base,size,music)
    from fx_render import render as fx_render
    fx_render(out/'assets/plan.json',out/'render',('mp4',),fps=b['fps'],experimental=True)
    files=list((out/'render').glob('*.mp4'))
    if len(files)!=1:raise ValueError('Renderer did not produce one animatic')
    from taste_report import analyze,save_report
    report=analyze(files[0],dict(points=check['design_curve'],bar_seconds=b.get('bar_seconds',2),origin=check['design_origin']),weights=b.get('weights',[.35,.25,.30,.10]),storyboard=b,weight_source='user' if 'weights' in b else 'default')
    save_report(report,out/'taste',files[0])
    import hashlib
    receipt=dict(asset_fallbacks=read(out/'assets/asset-fallbacks.json'),effect_adjustments=read(out/'assets/effect-adjustments.json'),storyboard_sha256=fingerprint(board),movie=str(files[0].resolve()),movie_sha256=hashlib.sha256(files[0].read_bytes()).hexdigest(),duration=b['duration'],cut_times=[s['start'] for s in b['shots'][1:]],
                 predicted_correlation=__import__('taste_common').compare_curve(np.asarray(check['predicted']['times']),np.interp(check['predicted']['times'],report['M15']['times'],report['M15']['values']),
                    [[t,float(v)] for t,v in zip(check['predicted']['times'],check['predicted']['values'])])['correlation'])
    write(out/'receipt.json',receipt);(out/'storyboard.md').write_text(shot_table(b),encoding='utf-8');return receipt


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('storyboard',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--music',type=Path);a=p.parse_args(argv)
    try:render(read(a.storyboard),a.out,a.storyboard.parent,a.music);return 0
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:print('animatic: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
