#!/usr/bin/env python3
"""Offline proxy contact sheet with explicit decisions and content-addressed shot reuse.

Independent shots are the unit of caching. Cross-shot transitions/history/reframe
are rejected; their dependencies cannot honestly be called isolated changed shots.
"""
import argparse
import copy
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import numpy as np
from PIL import Image


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as f:
        while block:=f.read(1024*1024): value.update(block)
    return value.hexdigest()


def reuse_file(source, destination):
    """Rendered PNGs are immutable cache artifacts; link when the filesystem allows."""
    if Path(source).suffix.lower()=='.png':
        try:
            os.link(source,destination)
            return destination
        except OSError: pass
    return shutil.copy2(source,destination)


def source_paths(value, base):
    """Resolve file references and collect all image/manifest dependencies."""
    files=[]
    def walk(item):
        if isinstance(item,list): return [walk(v) for v in item]
        if not isinstance(item,dict): return item
        result={}
        for key,v in item.items():
            if key in ('image','manifest','font','depth','background','words','srt','audio','model') and isinstance(v,str) and v:
                file=(base/v).resolve()
                if file.is_file():
                    result[key]=str(file);files.append(file)
                    if key=='manifest': files.extend(sorted((file.parent/'frames').glob('*.png')))
                    continue
            result[key]=walk(v)
        return result
    return walk(value),files


def write_html(root, events):
    cards=[]
    for i,event in enumerate(events):
        shot=event['shot_index']
        placeholder=html.escape('{"segment":{"image":"replacement.png"}}',quote=True)
        cards.append(f'<article><img src="{html.escape(event["thumbnail"],quote=True)}" alt="Event {i+1}"><h2>Shot {shot+1} · {event["time_ms"]:.1f} ms</h2><p>{html.escape(event["label"])}</p><label>Decision <select data-shot="{shot}"><option value="keep">Keep / 保留</option><option value="replace">Replace / 換掉</option></select></label><label>Replacement segment/effects JSON<textarea data-edit="{shot}" placeholder="{placeholder}"></textarea></label></article>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Shot review</title>
<style>body{background:#101722;color:#e7eef8;font:16px system-ui;margin:28px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}article{background:#1c2838;padding:16px;border-radius:12px}img{width:100%;height:220px;object-fit:contain}h2{font-size:18px}label{display:block;margin:12px 0}select,textarea,button{font:inherit;padding:8px}textarea{width:90%;height:70px}button{margin:16px 0}#status{color:#ffd166}</style>
<h1>Review the proxy</h1><p>Keep each shot or replace its source/effects. Save decisions.json, then pass it to --decisions with --previous pointing to this review directory.</p><button id="save">Save decisions.json</button><p id="status" role="status"></p><main>'''+''.join(cards)+'''</main>
<script>
document.querySelectorAll('select').forEach(s=>s.addEventListener('change',()=>{document.querySelectorAll('select').forEach(v=>{if(v.dataset.shot===s.dataset.shot)v.value=s.value})}));
document.querySelectorAll('textarea').forEach(s=>s.addEventListener('input',()=>{document.querySelectorAll('textarea').forEach(v=>{if(v.dataset.edit===s.dataset.edit)v.value=s.value})}));
document.getElementById('save').onclick=()=>{try{const shots={};document.querySelectorAll('select').forEach(s=>{const edit=document.querySelector('textarea[data-edit="'+s.dataset.shot+'"]');const replacement=edit.value.trim()?JSON.parse(edit.value):{};if(s.value==='replace'&&!replacement.segment&&!replacement.effects)throw Error('Provide replacement JSON for shot '+(+s.dataset.shot+1));shots[s.dataset.shot]={action:s.value,...replacement}});const a=document.createElement('a');const url=URL.createObjectURL(new Blob([JSON.stringify({version:1,shots},null,2)],{type:'application/json'}));a.href=url;a.download='decisions.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.getElementById('status').textContent='Decisions saved';}catch(e){document.getElementById('status').textContent=e.message}};
</script></html>'''
    (root/'review.html').write_text(page,encoding='utf-8')


def build(plan_path, out, previous=None, decisions=None, experimental=False, proxy=True):
    from fx_render import validate_plan,render
    from fx import EFFECTS
    path=Path(plan_path).resolve();out=Path(out)
    if out.exists(): raise ValueError('Use a new output directory')
    plan,items,segments,ctx,effects,transitions=validate_plan(path,('mp4',),experimental,proxy=proxy)
    if transitions or plan.get('reframe') or any(EFFECTS[e['name']].get('history',0) for e in effects):
        raise ValueError('Shot cache requires independent shots: remove cross-shot transitions/history/reframe or use normal render')
    if any(s['edit'].get('previous') for s in segments): raise ValueError('Shot cache requires explicit source images, not previous-frame dependencies')
    old={}
    if previous:
        previous=Path(previous).resolve();old=json.loads((previous/'manifest.json').read_text()).get('shots',[])
        old={r['index']:r for r in old}
    choices=json.loads(Path(decisions).read_text()) if decisions else {'shots':{}}
    if set(choices.get('shots',{}))-set(map(str,range(len(segments)))): raise ValueError('Decision references an unknown shot')
    started=time.perf_counter();records=[];all_events=[];clock=0;rerendered=0;reused=0
    out.parent.mkdir(parents=True,exist_ok=True)
    # Renderer and all FX source hashes invalidate stale caches after code changes.
    scripts=Path(__file__).parent
    renderer_hash=hashlib.sha256(''.join(digest(f) for f in sorted([scripts/'fx_render.py',scripts/'captions.py',scripts/'compose_timeline.py',*list((scripts/'fx').rglob('*.py'))])).encode()).hexdigest()
    with tempfile.TemporaryDirectory(dir=out.parent) as temporary:
        stage=Path(temporary)/'review';(stage/'shots').mkdir(parents=True);(stage/'thumbnails').mkdir()
        for i,segment in enumerate(segments):
            start=segment['start_ms'];duration=segment['duration_ms'];choice=choices.get('shots',{}).get(str(i),{'action':'keep'})
            if choice.get('action') not in ('keep','replace'): raise ValueError('Decision action must be keep or replace')
            edit=copy.deepcopy(segment['edit']);edit.pop('end_beat',None);edit.pop('end_downbeat',None);edit['duration_ms']=duration
            if choice['action']=='replace':
                if not choice.get('segment') and 'effects' not in choice: raise ValueError('Replace needs segment or effects')
                edit.update(choice.get('segment',{}));duration=edit['duration_ms']
            local_effects=[]
            for e in effects:
                if e['end_ms']<=start or e['start_ms']>=start+segment['duration_ms']: continue
                entry=dict(name=e['name'],start_ms=max(0,e['start_ms']-start),end_ms=min(duration,e['end_ms']-start),stage=e['stage'])
                for key,value in e['params'].items():
                    if isinstance(value,dict):
                        from fx.core import evaluate
                        # Freeze the global envelope into shot-local samples on the same proxy clock.
                        times=np.arange(0,duration+1,40).tolist()
                        if times[-1]!=duration: times.append(duration)
                        value={'keyframes':[[t,evaluate(value,t+start,ctx)] for t in times]}
                    entry[key]=value
                local_effects.append(entry)
            if choice['action']=='replace' and 'effects' in choice: local_effects=choice['effects']
            local=dict(segments=[edit],effects=local_effects,fps=plan.get('fps',25),seed=plan.get('seed',0),
                       sampling=plan.get('sampling','linear'),experimental=experimental or plan.get('experimental',False))
            if ctx.captions:
                words=[dict(w,start_ms=max(0,w['start_ms']-start),end_ms=min(duration,w['end_ms']-start)) for w in ctx.captions['words'] if w['start_ms']<start+duration and w['end_ms']>start]
                if words: local['captions']=dict(words=words,style=ctx.captions['style'],keywords=ctx.captions['keywords'])
            local,dependencies=source_paths(local,path.parent)
            effect_sources=[(EFFECTS[e.get('name','camera_move')]['source'],digest(EFFECTS[e.get('name','camera_move')]['source']))
                            for e in local_effects if e.get('name','camera_move') in EFFECTS]
            fingerprint=hashlib.sha256(json.dumps(dict(plan=local,proxy=proxy,renderer=renderer_hash,effect_sources=effect_sources,
                                                     files=[(str(f),digest(f)) for f in dependencies]),sort_keys=True).encode()).hexdigest()
            shotdir=stage/'shots'/f'{i:03}'
            cached=old.get(i)
            if cached and cached['fingerprint']==fingerprint and all((previous/p).is_file() and digest(previous/p)==sha for p,sha in zip(cached['frames'],cached['sha256'])):
                shutil.copytree(previous/'shots'/f'{i:03}',shotdir,copy_function=reuse_file);reused+=1
            else:
                # Resize source assets once, before effects: real proxy work, not a full render scaled afterwards.
                source_root=Path(temporary)/f'input-{i}';source_root.mkdir()
                if proxy:
                    for item in local['segments']:
                        if 'image' in item:
                            with Image.open(item['image']) as im:
                                size=tuple(max(2,round(v/3/2)*2) for v in im.size);im.convert('RGBA').resize(size).save(source_root/'still.png')
                            item['image']=str(source_root/'still.png')
                        elif 'manifest' in item:
                            original=Path(item['manifest']);data=json.loads(original.read_text());(source_root/'frames').mkdir()
                            for file in sorted((original.parent/'frames').glob('*.png')):
                                with Image.open(file) as im: im.convert('RGBA').resize(tuple(max(2,round(v/3/2)*2) for v in im.size)).save(source_root/'frames'/file.name)
                            (source_root/'manifest.json').write_text(json.dumps(data));item['manifest']=str(source_root/'manifest.json')
                localpath=source_root/'plan.json';localpath.write_text(json.dumps(local),encoding='utf-8')
                render(localpath,shotdir,('png',),experimental=local['experimental']);rerendered+=1
            manifest=json.loads((shotdir/'manifest.json').read_text());files=sorted((shotdir/'frames').glob('*.png'))
            relative=[f.relative_to(stage).as_posix() for f in files];sha=[digest(f) for f in files]
            records.append(dict(index=i,fingerprint=fingerprint,frames=relative,sha256=sha,durations_ms=manifest['durations_ms'],duration_ms=duration,start_ms=clock))
            event_times=[(0,'Shot start')]
            for e in effects:
                for t in e['trigger_times_ms'] or [e['start_ms']]:
                    if start<=t<start+duration: event_times.append((t-start,e['name']))
            if ctx.captions:
                event_times += [(line['start_ms']-start,'caption') for line in ctx.captions['lines'] if start<=line['start_ms']<start+duration]
            edges=np.cumsum([0]+manifest['durations_ms'])
            for local_time,label in event_times:
                index=min(len(files)-1,max(0,int(np.searchsorted(edges,local_time,side='right')-1)))
                thumb=f'thumbnails/{len(all_events):04}.png';shutil.copy2(files[index],stage/thumb)
                all_events.append(dict(shot_index=i,time_ms=clock+local_time,source_frame=index,source_frame_ms=float(edges[index]),label=label,thumbnail=thumb))
            clock+=duration
        report=dict(shots=records,events=all_events,duration_ms=clock,rerendered_shots=rerendered,reused_shots=reused,
                    proxy=proxy,seconds=time.perf_counter()-started,limitations='Independent shot cache; audio is added only at final delivery. Durations are explicit; beat snapping after length changes is not automatic.')
        assembly=dict(segments=[dict(type='animation',manifest=f'shots/{r["index"]:03}/manifest.json') for r in records])
        (stage/'render-plan.json').write_text(json.dumps(assembly,indent=2),encoding='utf-8')
        (stage/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8');write_html(stage,all_events)
        stage.rename(out)
    return report


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan',type=Path);ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--previous',type=Path);ap.add_argument('--decisions',type=Path);ap.add_argument('--experimental',action='store_true');ap.add_argument('--full',action='store_true')
    a=ap.parse_args(argv)
    try:
        report=build(a.plan,a.out,a.previous,a.decisions,a.experimental,not a.full)
        print(json.dumps({k:report[k] for k in ('rerendered_shots','reused_shots','seconds')}));return 0
    except (OSError,ValueError,KeyError,RuntimeError) as exc:
        print('review_shots: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__': raise SystemExit(main())
