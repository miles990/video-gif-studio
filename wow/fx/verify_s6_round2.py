"""Serial decoded evidence; persistent --out folder, never installed-skill writes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from fx_check import check_video,decoded
from fx_measure import standard
from fx_previews import render_preview
from fx_recipes import load_recipes
from sfx import read_audio
from qa_media import qa,analyse_audio


def audio_onset(movie):
    audio=read_audio(movie)
    return float(np.flatnonzero(np.max(np.abs(audio),axis=1)>.01)[0]*1000/48000)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--review-root',type=Path,default=ROOT.parent/'vgs-fx-private/reviews')
    ap.add_argument('--resume',action='store_true',help='Reuse completed QA in this unchanged-instrument run')
    args=ap.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    record=dict(source_revision=subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'rev-parse','HEAD'],text=True).strip(),
                uncommitted=True,artifact_root=str(out),flash={},recipes={})
    paths=list((args.review_root/'review-s6/work/flash').glob('*.mp4'))
    paths+=list((args.review_root/'review-s6-2/work/flash').glob('P_pan*.mp4'))
    paths+=[ROOT/'examples/neon-zen-pv/segment-01/generation/source.mp4']
    for p in paths:
        cap=cv2.VideoCapture(str(p));fps=cap.get(cv2.CAP_PROP_FPS);cap.release()
        saved=out/('qa-'+p.stem)/'report.json'
        q=json.loads(saved.read_text(encoding='utf-8')) if args.resume and saved.is_file() else qa(p,saved.parent,fps=fps)
        wcag=next(c for c in q['checks'] if c['name']=='WCAG 2.3.1')
        r=wcag['measurement']
        record['flash'][p.name]=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),counter=r,qa_level=wcag['level'])
        expected='harsh' if p.stem in ('FL4','H8_every9_3.33ps','H8_alt78_4ps','H9_red_125ms') else 'ok'
        assert r['status']==expected,(p,r)
        assert wcag['level']==('FAIL' if expected=='harsh' else 'PASS')
        if p.stem=='H8_every10_3ps':assert r['general_max']==3
        print('flash',p.name,r['general_max'],r['red_max'],wcag['level'],flush=True)
    for name in ('hook_snap','freeze_card'):
        recipe=load_recipes(experimental=True)[name];cases=[]
        for at,loudnorm in ((500,'on'),(1000,'off')):
            case=out/f'{name}-{at}';case.mkdir(exist_ok=args.resume)
            Image.fromarray(standard('STD-A' if name=='freeze_card' else 'STD-P',160,90)).save(case/'source.png')
            plan={'segments':[{'type':'still','image':'source.png','duration_ms':3000}],'effects':[{'recipe':name,'at_ms':at}],'fps':30}
            (case/'plan.json').write_text(json.dumps(plan))
            command=[sys.executable,'-B',str(ROOT/'scripts/fx_render.py'),str(case/'plan.json'),'--out',str(case/'delivery'),
                     '--formats','mp4','--no-user-fx','--experimental','--loudnorm',loudnorm]
            destination=case/'delivery/animation.mp4'
            result=subprocess.CompletedProcess(command,0,'reused completed render','') if args.resume and destination.is_file() else subprocess.run(command,capture_output=True,text=True)
            (case/'render.log').write_text(result.stdout+'\n'+result.stderr)
            assert result.returncode==0,result.stderr
            movie=case/'delivery/animation.mp4';frames=list(decoded(movie));baseline=frames[0].astype(float)
            changes=[np.mean(np.abs(f.astype(float)-baseline)) for f in frames]
            visual=next(i for i,d in enumerate(changes) if d>max(changes[:round(at*30/1000)])+1)*1000/30
            onset=audio_onset(movie);checks=analyse_audio(movie,{'audio':True},[0,3])
            assert abs(onset-visual)<=1000/30,(name,onset,visual)
            assert not any(c['level']=='FAIL' for c in checks),checks
            cases.append(dict(rc=result.returncode,command=command,movie=str(movie),at_ms=at,loudnorm=loudnorm,
                              decoded_visual_onset_ms=visual,decoded_audio_onset_ms=onset,skew_ms=abs(onset-visual),audio=checks))
        folder=out/(name+'-preview');folder.mkdir(exist_ok=args.resume)
        preview=render_preview(name,'recipe',folder,recipe=recipe,seconds=3,at_ms=500)
        onset=audio_onset(folder/preview['preview']['video'])
        # Preview has a bed; isolate click by comparing the decoded high-frequency
        # energy (bed is 220/330 Hz; the click has broad energy including 2.4 kHz).
        audio=read_audio(folder/preview['preview']['video']).mean(axis=1)
        high=audio-cv2.GaussianBlur(audio.reshape(-1,1),(1,0),5).ravel()
        peaks=np.array([np.sqrt(np.mean(high[i:i+48]**2)) for i in range(0,len(high),48)])
        click=float(np.flatnonzero(peaks>max(.01,float(np.max(peaks[:450]))*5))[0])
        expected=preview['events'][0]['peak_ms']
        if recipe.get('sfx_anchor')=='onset':
            residual=[float(np.abs(a.astype(float)-b.astype(float)).mean()) for a,b in zip(
                decoded(folder/preview['preview']['video']),decoded(folder/('recipe-'+name+'-reference.mp4')))]
            expected=next(i for i,d in enumerate(residual) if d>max(residual[:15])+1)*1000/30
        assert abs(click-expected)<=1000/30,(name,click,expected)
        record['recipes'][name]=dict(status='pass',cases=cases,preview=dict(path=str(folder),decoded_click_ms=click,
            visual_anchor_ms=expected,anchor='paired decoded visible card onset' if name=='freeze_card' else 'decoded MEAS peak',skew_ms=abs(click-expected)))
        print('recipe',name,'PASS',click,expected,flush=True)
    # Additional controls use fresh media, with no reviewer labels or fixtures.
    from fx_gate_kit import source_frames
    from fx_measure import moving
    from delivery import encode_frames,settings
    extra=out/'extra';extra.mkdir(exist_ok=True)
    smooth=render_preview('gl_overexposure','transition',extra/'smooth')
    assert smooth['wcag']['max_flashes_per_s']==1,smooth['wcag']
    source=source_frames(ROOT/'examples/neon-zen-pv/segment-01/generation/source.mp4',(480,270))
    pan=extra/'real-pan.mp4'
    encode_frames((Image.fromarray(moving(f,i*6/(4*480/1280))) for i,f in enumerate(source)),pan,settings((480,270),24))
    q=qa(pan,extra/'real-pan-qa',fps=24)
    flash=next(c for c in q['checks'] if c['name']=='WCAG 2.3.1')
    assert flash['level']=='PASS',flash
    record['additional_controls']=dict(gradual_overexposure=smooth['wcag'],real_footage_pan=flash,artifact_root=str(extra))
    target=ROOT/'wow/fx/s6-round2-regressions.json'
    target.write_text(json.dumps(record,indent=2)+'\n')
    print(target,flush=True)


if __name__=='__main__':main()
