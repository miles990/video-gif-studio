"""Moving catalog and recipe proxies. Paths are relative to the catalog folder."""
import json
from pathlib import Path
import shutil
import tempfile
import time
import cv2
import numpy as np
from PIL import Image
from fx import EFFECTS,TRANSITIONS,Context
from fx.core import catalog
from fx_catalog import output_root, write_html
from fx_measure import standard,moving,measures,rgb,LUMA,visibility_family
from fx_recipes import apply_recipe,load_recipes
from fx_director import recipe_cards
from fx_check import check_video
from delivery import encode_frames,settings,audio_delivery


def render_preview(name,kind,folder,width=480,height=270,recipe=None,source_frames=None,seconds=2,at_ms=500):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    stem=kind+'-'+name;movie=folder/(stem+'.mp4');thumbnail=folder/(stem+'.jpg')
    reference=folder/(stem+'-reference.mp4')
    fps=30;count=round(seconds*fps);ctx=Context(width,height,fps=fps,beats_ms=[at_ms],t_ms=0,seed=6)
    source=standard('STD-A' if name=='cutout_card' or recipe and 'alpha' in recipe['needs'] else 'STD-P',width,height)
    if kind=='transition':
        # A lower-frequency demonstration plate avoids turning the calibration
        # board's checker pattern into incidental flashing during fast rotation.
        # This is declared preview material, never a gate/calibration substitute.
        source=cv2.GaussianBlur(source,(0,0),max(1,width/40))
        source[...,:3]=(source[...,:3].astype(np.float32)*.45+128*.55).round().astype(np.uint8)
    other=source[:,::-1].copy();other[...,:3]=other[...,:3][...,[2,1,0]]
    peak=-1.;peak_ms=0.;peak_frame=None;raw=[]
    def inputs(i):
        return source_frames(i) if source_frames else moving(source,i)
    def outputs():
        nonlocal peak,peak_ms,peak_frame
        for i in range(count):
            t=i*1000/fps;ctx.t_ms=t;frame=inputs(i)
            if recipe:
                output=apply_recipe(recipe,frame,t-at_ms,ctx)
            elif kind=='transition':
                p=float(np.clip((t-400)/1200,0,1))
                # Offset the native seed clock to demonstrate one fixed block
                # field; preserve the port's upstream parameter contract.
                if name=='gl_glitch_memories':ctx.seed=6-int(p*24)
                output=TRANSITIONS[name]['function'](frame,other,p,ctx)
            else:
                params={'temp':.15} if name=='grade' else {}
                effected=EFFECTS[name]['function'](frame,t,ctx,**params)
                # A smooth sliding before/after view makes static treatments
                # inspectable without falsely relabeling camera motion as FX.
                boundary=round(width*np.clip((t-200)/1400,0,1))
                output=frame.copy();output[:,:boundary]=effected[:,:boundary]
            change=float(np.abs((rgb(output)-rgb(frame))@LUMA).mean())
            if change>peak:peak=change;peak_ms=t;peak_frame=output.copy()
            yield Image.fromarray(output)
    started=time.perf_counter()
    config=settings((width,height),fps)
    encode_frames(outputs(),movie,config,background='808080')
    encode_frames((Image.fromarray(inputs(i)) for i in range(count)),reference,config,background='808080')
    Image.fromarray((rgb(peak_frame)*255).round().astype(np.uint8)).save(thumbnail,quality=90)
    event=dict(name=name,start_ms=at_ms if recipe else 0,end_ms=seconds*1000,intent=recipe['intent'] if recipe else 'texture' if name=='grade' else 'hit',kind=kind)
    if recipe:event['family']=visibility_family(recipe['layers'][0]['ref'])
    report=check_video(movie,reference,[event],fps)
    peak_ms=report['events'][0]['peak_ms']
    cap=cv2.VideoCapture(str(movie))
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES,round(peak_ms*fps/1000));ok,decoded=cap.read()
        if not ok:raise ValueError('Cannot decode the measured peak thumbnail')
        Image.fromarray(cv2.cvtColor(decoded,cv2.COLOR_BGR2RGB)).save(thumbnail,quality=90)
    finally:cap.release()
    # SFX onset at the measured decoded MEAS maximum (riser ends there).
    sound=[]
    if recipe and recipe['sfx']:
        from sfx import render_track,write_wav
        with tempfile.TemporaryDirectory(prefix='vgs-sfx-') as temp:
            track=Path(temp)/'sfx.wav'
            anchor=at_ms+min(l['offset_ms'] for l in recipe['layers']) if recipe.get('sfx_anchor')=='onset' else peak_ms
            sound=render_track([dict(kind=recipe['sfx'],event=name,at_ms=anchor)],seconds*1000,track)
            # A quiet procedural music bed is the documented soundtrack for
            # recipe previews. Very short clicks alone cannot always reach an
            # integrated programme loudness target below a fixed peak ceiling.
            clock=np.arange(round(seconds*48000))/48000
            bed=.025*(np.sin(2*np.pi*220*clock)+.4*np.sin(2*np.pi*330*clock))
            bed*=np.minimum(1,clock/.02)*np.minimum(1,(seconds-clock)/.02)
            bed_path=Path(temp)/'bed.wav';write_wav(bed_path,np.repeat(bed[:,None],2,axis=1))
            audio_delivery(movie,seconds*1000,music={'file':str(bed_path)},sfx={'file':str(track)},normalize=True)
    report.update(name=name,kind=kind,preview={'video':movie.name,'thumbnail':thumbnail.name,'duration_ms':seconds*1000},
                  render_seconds=time.perf_counter()-started,sfx=sound,source='source timeline' if source_frames else 'low-frequency demonstration plate' if kind=='transition' else 'STD-MOV',
                  default_override=preview_override(name))
    if recipe and recipe['sfx']:report['soundtrack']='quiet procedural 220/330 Hz bed plus paired SFX; programme loudness and true peak gated'
    # Keep the matched reference for independent measurement; catalogs can be
    # copied with only their videos/thumbnails when a smaller bundle is needed.
    (folder/(stem+'.json')).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


def preview_override(name):
    # Fixed spatial block field with a smooth amplitude envelope. Avoid the
    # original 24 random changes compressed into a 1.2-second catalog loop.
    if name=='grade':return {'temp':.15}
    return {'context_seed':'6 - floor(24 * progress)'} if name=='gl_glitch_memories' else {}


def build_catalog(target=None,experimental=False):
    cv2.setNumThreads(1)
    target=Path(target or output_root()/'catalog.html');folder=target.parent
    cards=[]
    for kind,entries in catalog(experimental).items():
        for name,card in entries.items():
            if card.get('card') in ('missing','incomplete'):continue
            # Unsupported optional-model plugins fail clearly instead of
            # rendering a placeholder and pretending it is their preview.
            report=render_preview(name,kind[:-1],folder)
            cards.append(dict(card,name=name,kind=kind[:-1],preview=dict(card['preview'],**report['preview'])))
            print('preview '+name,flush=True)
    recipes=load_recipes(experimental=experimental)
    for card in recipe_cards(experimental):
        r=recipes[card['name']]
        report=render_preview(card['name'],'recipe',folder,recipe=r,seconds=3,at_ms=500)
        cards.append(dict(card,preview=report['preview'],snippet={'recipe':card['name'],'at_beat':4,'perceived':r['perceived_target']}))
    write_html(cards,target)
    from fx_catalog import coverage
    (folder/'catalog.json').write_text(json.dumps(cards,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (folder/'coverage.json').write_text(json.dumps(coverage(catalog(experimental)),indent=2)+'\n',encoding='utf-8')
    return str(target)
