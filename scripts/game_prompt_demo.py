"""One prompt -> generated sources -> measured experimental engine pack.

Nineteen subscription images, no model-video and no manually authored source pack.
Automatic geometric pose guides are explicitly unassessed anatomical evidence.
"""
from dataclasses import replace
from pathlib import Path
import os,subprocess,shutil
import numpy as np
from PIL import Image
from image_common import ImageError,read,write,digest
from game_character import sheet,rgba,prepare_subject,quantize
from game_animation import animate,KEY_POSES
from game_icons import iconset
from game_tiles import texture
from game_engines import export_engines


class ResumeSources:
    """Explicit preprocessing replay; retain original transport refs/receipts.

    A changed prompt is never reused. Changed derived reference pixels are
    allowed only with --resume, so a local crop/matting fix need not regenerate.
    """
    def __init__(self,adapter):self.adapter=adapter
    def __getattr__(self,name):return getattr(self.adapter,name)
    def generate(self,request,out,**kwargs):
        from image_common import key
        record=Path(out)/'gen-manifest.json'
        candidates=([read(record)] if record.exists() else [])+[r for r in reversed(self.adapter.records()) if r.get('event')=='generation' and any(Path(a['path']).parent.resolve()==Path(out).resolve() for a in r.get('assets',[]))]
        for old in candidates:
            if old.get('status')=='ok' and old.get('prompt_sha')==key(request.normalized()['prompt']) and all(Path(r['path']).exists() and digest(r['path'])==r['sha256'] for r in old.get('assets',[])) and old.get('assets'):
                return dict(old,cache_hit=True,subscription_images=0,preprocessing_replay=True,original_refs_sent=old.get('refs_sent',[]))
        return self.adapter.generate(request,out,**kwargs)


def check_godot(out,engine):
    out=Path(out).resolve();userdata=out/'userdata';userdata.mkdir(exist_ok=True)
    env=dict(os.environ,APPDATA=str(userdata),LOCALAPPDATA=str(userdata));logs=[]
    for args in (['--editor','--quit'],['--fixed-fps','120','--script','check_frames.gd']):
        r=subprocess.run([str(engine),'--headless','--path',str(out),*args],capture_output=True,text=True,timeout=90,env=env)
        logs.append(r.stdout+r.stderr)
        if r.returncode or 'SCRIPT ERROR' in r.stderr:raise ImageError('E_GODOT','Engine load failed',log=logs[-1])
    (out/'godot-load.log').write_text('\n'.join(logs),encoding='utf8')
    if 'S14_GODOT_PASS' not in logs[-1]:raise ImageError('E_GODOT','Playback did not finish every frame.')
    return 'tested:'+logs[-1].split('S14_GODOT_PASS ',1)[1].splitlines()[0]


def generated_pose_plan(adapter,request,char,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);contract=read(char/'charsheet.json');palette=read(char/'palette.json')
    refs=[str((char/'identity'/f'{n}.png').resolve()) for n in ('front','three_quarter')];plan={};generations=[]
    for state in ('idle','run','attack','hurt'):
        prompt=(f'{request.prompt}. Reference character identity and clothing unchanged. Four sequential {state} key poses in a 2 columns by 2 rows equal-cell grid. '
                f'Row-major poses: {"; ".join(KEY_POSES[state])}. Each cell has ONE full body, same camera, scale, center and baseline. '
                'Keep full ears, feet and weapons within each cell. Clear transparent gutters, no text, no grid lines, no ground rules. '
                'Idle and attack feet remain planted; run alternates left contact, flight, right contact, flight. Crisp color clusters, no blur.')
        result=adapter.generate(replace(request,prompt=prompt,refs=refs,transparent=True,n=1),out/state/'generation');generations.append(result)
        source=rgba(result['assets'][0]['path']);cells=[]
        for i in range(4):
            x=i%2;y=i//2;cell=source.crop((round(x*source.width/2),round(y*source.height/2),round((x+1)*source.width/2),round((y+1)*source.height/2)))
            cell,subject=prepare_subject(cell);cells.append(cell)
        # ONE camera transform for the entire strip preserves bob/flight/travel.
        boxes=[im.getbbox() for im in cells];left=min(b[0] for b in boxes);right=max(b[2] for b in boxes);top=min(b[1] for b in boxes);bottom=max(b[3] for b in boxes)
        scale=min(52/(bottom-top),58/(right-left));region=(left,top,right,bottom);target=(max(1,round((right-left)*scale)),max(1,round((bottom-top)*scale)))
        keys=[]
        for i,im in enumerate(cells):
            identity_source=out/state/f'source-key-{i}.png';im.save(identity_source)
            crop=quantize(im.crop(region),palette,target);canvas=Image.new('RGBA',(64,64));canvas.paste(crop,((64-target[0])//2,59-target[1]))
            p=out/state/f'key-{i}.png';canvas.save(p);keys.append(dict(image=str(p.resolve()),identity_source=str(identity_source.resolve()),refs_sent=[digest(p) for p in refs]))
        n=8 if state!='attack' else 10;indices=[0,2,4,6] if state in ('idle','run') else [0,3,6,9] if state=='attack' else [0,2,4,7]
        spec=dict(keys=keys,key_indices=indices,frame_count=n,ground_line=58,registration=dict(source_box=region,scale=scale,common_transform=True),
                  foot_boxes={'left':[[12,45,20,16]]*n,'right':[[32,45,20,16]]*n},foot_tracking='screen-side pixel proxy; anatomical identity unassessed')
        if state=='attack':spec['phases']=['anticipation']*3+['swing']*2+['contact']+['follow_through']*2+['recovery']*2
        plan[state]=spec
        write(out/'progress.json',dict(completed_states=list(plan),source_generations=generations))
    return plan,generations


def build(adapter,request,out,vendor=None,godot=None,allow_qa_fail=False,resume=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if request.route not in ('codex','auto'):raise ImageError('E_ROUTE','Prompt demo is subscription-only; no paid fallback.')
    if not request.prompt:raise ImageError('E_PROMPT','Give an original character and style in --prompt.')
    if resume:adapter=ResumeSources(adapter)
    char=out/'charsheet';contract=sheet(adapter,request,char,pixel=64,expression_atlas=True)
    plan,generations=generated_pose_plan(adapter,request,char,out/'pose-sources');write(out/'pose-plan.json',plan)
    anim=animate(adapter,request,char/'charsheet.json',out/'anim',plan=plan)
    palette=read(char/'palette.json');outline=min(palette,key=lambda c:sum(bytes.fromhex(c['hex'][1:])))['hex']
    token=dict(grid=64,outline_hex=outline,outline_px=2,light_deg=135,safe_margin=4,palette=palette,shading='cel')
    icons=iconset(adapter,request,['sword','shield','potion','key','scroll','gem','bow','boot'],token,out/'icons',pixel=True)
    tex=texture(adapter,replace(request,prompt=request.prompt+' Matching blue-grey slate ground texture, no characters or objects.',size='256x256'),out/'tex',256)
    qa=dict(character=contract['qa'],animation={k:v['qa'] for k,v in anim['states'].items()},icons=icons['qa'],texture=tex.get('qa',tex.get('repair',{})),
            human_review='pending; automatic silhouettes and screen-side feet are not semantic tracking')
    write(out/'qa-summary.json',qa)
    all_records=adapter.records();records=[r for r in all_records if r.get('run_id')==adapter.run_id]
    used=sum(r.get('subscription_images',0) for r in records if r.get('event')=='generation' and r.get('status')=='ok' and not r.get('cache_hit'))
    source_records=[r for r in all_records if r.get('event')=='generation' and r.get('status')=='ok' and not r.get('cache_hit') and any(Path(a['path']).resolve().is_relative_to(out.resolve()) for a in r.get('assets',[]))]
    total=sum(r.get('subscription_images',0) for r in source_records)
    manifest=dict(status='experimental_preview',prompt=request.prompt,generated_this_run=used,subscription_images=total,cost_usd=0,ai_video_calls=0,
                  source_generation_ledger=source_records,includes_rejected_sources=True,
                  allow_qa_fail=allow_qa_fail,qa='qa-summary.json',generation_ledger=records,source_pack_required=False,engine_load={'godot4':'untested'})
    write(out/'gen-manifest.json',manifest)
    failures=any(m['qa']['status']=='FAIL' for m in anim['states'].values()) or contract['qa']['status']=='FAIL' or icons['qa']['status']=='FAIL' or tex['qa']['status']=='FAIL'
    if failures and not allow_qa_fail:raise ImageError('E_QA_FAIL','Demo QA failed; sources and reports retained. Repair or explicitly use --allow-qa-fail for a labelled preview.',report=str(out/'qa-summary.json'))
    if resume and (out/'export').exists():
        import uuid
        source=(out/'export').resolve();history=(out/'export-history'/uuid.uuid4().hex).resolve()
        if not source.is_relative_to(out.resolve()) or not history.is_relative_to(out.resolve()):
            raise ImageError('E_OUTPUT_PATH','Resume export paths must remain within the requested output directory.')
        history.parent.mkdir(exist_ok=True);source.rename(history)
    packed=export_engines(sorted((out/'anim').glob('*/anim.json')),out/'export',['godot4','unity','phaser-hash','phaser-array','pixi','aseprite'],pixel=True,allow_qa_fail=allow_qa_fail)
    from game_demo import browser_demo
    browser_demo(out/'phaser-demo',packed,vendor)
    if godot:
        manifest['engine_load']['godot4']=check_godot(out/'export',godot)
        packed['engines']['godot4']['engine_load']=manifest['engine_load']['godot4'];write(out/'export/sprites.json',packed)
    manifest['measured_qa_status']='FAIL' if failures else 'unassessed';write(out/'gen-manifest.json',manifest)
    (out/'README.md').write_text('Experimental preview. Open export/project.godot. Read qa-summary.json before use.\nIdentity, expression fidelity, anatomical foot tracking and physical motion need human review.\nQA FAIL overrides are recorded; engine loading is not artistic acceptance.\n',encoding='utf8')
    return manifest
