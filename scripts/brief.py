#!/usr/bin/env python3
"""Offline one-liner → director brief → storyboard → existing renderer.

Method/templates adapted from blank-page SKILL.md (MIT), Blake Shao / Stewdio.
Copyright (c) 2026 Cekura, Inc.; notice in THIRD_PARTY.md. Creative text may be
authored by the calling agent with --content; this program never calls a model.
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import sys
import numpy as np
from brief_refs import ground, validate_assets, CassetteProvider, HANDLES
from brief_structure import structure, stable_choices, recipe_camera
from brief_lint import lint

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    text=Path(path).read_text(encoding='utf-8-sig')
    if Path(path).suffix=='.md':
        match=re.search(r'<!-- brief-json\n(.*?)\n-->',text,re.S)
        if not match: raise ValueError('E_SCHEMA markdown: use the canonical Markdown emitted by brief.py')
        data=json.loads(match[1]);visible=re.search(r'```text\n(.*?)\n```',text,re.S)
        if not visible or visible[1]!=prompt(data):raise ValueError('E_SCHEMA markdown: visible prompt differs from canonical brief; edit JSON and regenerate')
        return data
    return json.loads(text)


def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def classify(draft,image=None,previous=None):
    if image:return 'image_feedback','attached contact sheet'
    # New creative text can mention an export, a shot or a repair as its subject.
    edit_context=bool(previous and (previous.get('shots') or previous.get('beats')))
    if edit_context and re.search(r'check the render|\bexport\b|\brename\b|匯出|輸出成|改檔名',draft,re.I):return 'housekeeping','export/rename/check render'
    primary=re.split(r'[，,；;]\s*(?:也|順便|also\b)',draft,flags=re.I)[0]
    if re.search(r'variations|versions|不同的版本|個版本|不同版本|create\s+\d+\s+comps',primary,re.I) and not re.search(r'不急|no rush',primary,re.I):return 'batch','variations / multiple versions'
    if edit_context and re.search(r'保留|其他不動|拿掉|慢一點|往右|提前|make .*faster|make .*more|make .*less|get rid of|\bfix\b|move to|改成|另一邊|反過來|other way|第[一二三四五六七八九十\d]+[鏡拍]|\bshot\s*\d+|\bmake\s+\d+\b',draft,re.I):
        return 'delta','targeted change / keep clause'
    if re.search(r'\bat\s+\d+(?:\.\d+)?\s*s|after .*exits|在\s*\d+(?:\.\d+)?\s*秒',draft,re.I):return 'sequence','timeline anchor / after exit'
    return 'brief','new scene / composition'


def music_grid(source):
    """Read reviewed beat JSON, or return labelled local PCM candidates.

    RMS candidates do not claim general musical downbeat recognition. Sustained
    energy change across a bar locates a drop; onset periodicity supplies the grid.
    """
    if source is None:return {}
    if isinstance(source,dict):return deepcopy(source)
    if Path(source).suffix=='.json':return read(source)
    from music_sync import audio_envelopes
    env=audio_envelopes(source);energy=np.asarray(env['energy']);onset=np.asarray(env['onset'])
    scores=[]
    for lag in range(30,101):
        if lag<len(onset):scores.append((float(np.dot(onset[lag:],onset[:-lag])),lag))
    if not scores:return dict(review='No usable periodicity',downbeats_ms=[])
    lag=max(scores,key=lambda p:(p[0],-p[1]))[1]
    # Beginning of the leading onset, not its RMS maximum.
    first=int(np.argmax(onset[:lag]));offset=max(0,first-1)*10
    if offset<=30:offset=0
    beat_ms=lag*10;down=np.arange(offset,len(energy)*10,beat_ms*4).tolist()
    changes=[]
    for t in down:
        idx=round(t/10)
        if idx<20 or idx+20>len(energy):continue
        before=float(np.mean(energy[max(0,idx-lag*2):idx]));after=float(np.mean(energy[idx:min(len(energy),idx+lag*2)]))
        changes.append((after-before,t))
    drop=max(changes)[1] if changes and max(changes)[0]>.10 else None
    return dict(beats_ms=np.arange(offset,len(energy)*10,beat_ms).tolist(),downbeats_ms=down,drop_ms=drop,
                duration_ms=len(energy)*10,method='local RMS periodicity; 4/4 assumption',review='unreviewed candidates; supply beat JSON for authored meter')


def load_project(project):
    if not project:return []
    if isinstance(project,list):return deepcopy(project)
    project=Path(project)
    candidates=[project] if project.is_file() else [project/n for n in ('shot-cards.json','shots.json','project.json')]
    file=next((p for p in candidates if p.is_file()),None)
    if not file:return []
    data=read(file);cards=data if isinstance(data,list) else data.get('shots',data.get('cards',[]))
    for card in cards:
        path=card.get('path',card.get('file',card.get('footage',card.get('image'))))
        if path:card['path']=str((file.parent/path).resolve())
        card.setdefault('time',card.get('in_ms',0)/1000)
    return cards


def creative(draft,design):
    """Recorded, editable starting treatments; agent text overrides each slot."""
    text=draft.lower();zh=bool(re.search('[\u3400-\u9fff]',draft));aesthetic=design['aesthetic'];fence=''
    subject='the subject';turn='the camera pulls out to reveal the subject inside a larger working assembly'
    if re.search(r'coffee|cafe|咖啡|菜單',text):
        subject='菜單紙' if zh else 'the menu sheet';turn='杯緣掠過紙面，揭露底下對應的新飲品' if zh else 'the cup rim sweeps across the paper to reveal the matching new drink underneath'
    elif 'payment' in text:
        subject='the request';turn='the request leaves the code and comes back as a payment confirmed'
    elif '10,000' in text:
        subject='the user counter';turn='the camera pulls out to reveal 10,000 marks forming the user count'
    elif 'pricing' in text:
        subject='the frosted-glass field';turn='the glass folds through itself to reveal a clear pocket behind the cards'
    elif re.search(r'note-taking|search',text):
        subject='the search strip';turn='the strip unfolds to reveal matching documents, slack and email on one plane'
    elif 'calendar' in text:
        subject='the settings tiles';turn='the messy old settings page snaps into clean grouped sections'
    elif re.search(r'app',text):
        subject='the app card';turn='the camera pulls out to reveal the card as one working part of the app'
    elif design['profile']=='kinetic':
        subject='the athlete';turn='the camera pulls out to reveal the finish line as the athlete breaks the tape'
    elif design['profile']=='precision':
        subject='the watch crown';turn='the camera pulls out to reveal the crown driving the complete watch mechanism'
    if 'stripe' in text:aesthetic='stripe-gradient dark';fence='stripe’s style'
    elif 'apple' in text:aesthetic='apple frosted-glass light';fence='apple’s website'
    elif 'clean and minimal' in text:aesthetic='Swiss white typographic grid';fence='clean and minimal'
    elif re.search(r'溫暖|warm|cozy',text):
        aesthetic='晨光底片暖調' if zh else 'morning-window warm film';fence='溫暖' if zh else 'warm and cozy'
    elif 'riso' in text:aesthetic='two-ink riso stock';fence='riso'
    return dict(aesthetic=aesthetic,fence=fence,subject=subject,turn=turn,
                pace=design['pace'],zh=zh,background=bool(re.search(r'background|背景',text)))


def expand(draft,project=None,taste=None,refstat=None,music=None,platform=None,offline=False,
           provider=None,library=(),content=None,image=None,previous=None):
    mode,reason=classify(draft,image,previous)
    if mode=='housekeeping':
        checking='check' in draft.lower();filename=re.search(r'(?:檔名|filename)\s*([\w-]+)',draft,re.I)
        target=dict(format='mp4',codec='H.264',platform=platform or 'ig_reels',width=1080,height=1920)
        if filename:target['filename']=filename[1]+'.mp4'
        text=draft if checking else draft+'; '+target.get('filename','mp4')+', 1080×1920, H.264'
        return dict(version=1,mode=mode,mode_reason=reason,draft=draft,prompt=text,command='qa_media.py' if checking else 'export',target=target)
    if mode in ('delta','image_feedback'):
        from brief_edit import parse
        return parse(draft,previous or {},image=image)
    from taste_pick import load as load_taste
    content=deepcopy(content or {});taste=load_taste() if taste is None else taste;cards=load_project(project);grid=music_grid(music)
    design=stable_choices(structure(draft,content,taste,refstat));copy=creative(draft,design);copy.update({k:v for k,v in content.items() if k in copy})
    grounded_look=next((c.get('aesthetic_tag') for c in cards if c.get('aesthetic_tag')),None)
    if grounded_look and not content.get('aesthetic'):copy['aesthetic']=grounded_look
    # Grounding precedes beat construction. Attachment slots never go to web.
    refs,meta=ground(copy['aesthetic'],cards,taste,refstat,library,provider,offline)
    match=re.search(r'(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s\b|秒)',draft,re.I)
    duration=float(content.get('duration',match[1] if match else 5))
    if mode=='sequence':
        cap=re.search(r'(\d+(?:\.\d+)?)\s*秒前結束|ends? (?:at|by)\s*(\d+(?:\.\d+)?)',draft,re.I)
        duration=float(next(g for g in cap.groups() if g)) if cap else max(10.,duration+3)
    if not math.isfinite(duration) or not .2<=duration<=600:raise ValueError('E_SCHEMA duration: choose 0.2..600 seconds')
    fps=content.get('fps',30);design.update(content.get('structure',{}))
    from taste_target import plan_timing
    if grid.get('downbeats_ms'):
        edges=sorted(set([0.,duration]+[round(t/1000*fps)/fps for t in grid['downbeats_ms'] if 0<t/1000<duration]))
        drop=grid.get('drop_ms')
        if drop is None:
            drop=next((s.get('start_ms',s.get('start',0)*1000) for s in grid.get('sections',[]) if s.get('label',s.get('name','')).lower()=='drop'),None)
        turn_time=min(edges[:-1],key=lambda t:abs(t-(drop/1000 if drop is not None else duration*.6)))
        anchor='downbeat';shot_groups=[]
        for a,b in zip(edges,edges[1:]):shot_groups.append(plan_timing(b-a,dict(asl=design['asl'],cv=design['cv']))['durations'])
    elif mode=='sequence':
        anchor_match=re.search(r'(?:at\s*|在\s*)(\d+(?:\.\d+)?)\s*(?:s|秒)',draft,re.I)
        start=float(anchor_match[1]) if anchor_match else 0.
        if start>=duration:raise ValueError('E_TIME sequence: duration cap must follow the start anchor')
        edges=sorted(set([0.,start,start+(duration-start)*.45,duration]));turn_time=edges[-2]
        shot_groups=[[b-a] for a,b in zip(edges,edges[1:])];anchor='authored sequence time'
    else:
        timing=plan_timing(duration,dict(asl=design['asl'],cv=design['cv']))['durations']
        if len(timing)<3:
            weights=[.28,.46,.26] if design['profile']=='precision' else [.25,.40,.35]
            timing=[duration*w for w in weights]
        groups=np.array_split(np.arange(len(timing)),min(4,len(timing)))
        shot_groups=[[timing[int(i)] for i in group] for group in groups]
        edges=[0.]
        for group in shot_groups:edges.append(edges[-1]+sum(group))
        edges[-1]=duration;turn_time=edges[-2] if len(edges)==4 else edges[2];anchor='authored phrase'
    turn_index=min(range(len(edges)-1),key=lambda i:abs(edges[i]-turn_time))
    assignments={h:(turn_index if h in ('a4','m2') else len(edges)-2 if h=='m3' else 0 if h in ('a1','a2','a3','m1') else max(0,turn_index-1)) for h in HANDLES}
    beats=[]
    for i,(start,end) in enumerate(zip(edges,edges[1:])):
        handles=[h for h in HANDLES if assignments[h]==i];is_turn=i==turn_index
        if is_turn:body=copy['turn']
        elif i==0:body=(copy['subject']+'從畫面下緣滑入，紙邊順著手勢展開') if copy['zh'] else copy['subject']+' slides from the lower edge; its working parts settle into place'
        else:body=(copy['subject']+'沿原方向繼續運動，細節保持清楚') if copy['zh'] else copy['subject']+' continues along the same axis; keep its detail readable'
        body+=' ('+', '.join(handles)+')' if handles else ''
        beats.append(dict(id=i+1,t_start=round(start,6),t_end=round(end,6),text=body,is_turn=is_turn,anchor=anchor,
                          refs=handles,hero_height=.5,min_text_px=24,action=True,perceived=.15 if is_turn else .04,
                          shot_durations=shot_groups[i],mechanism='pull' if is_turn else 'drift'))
    if mode=='sequence' and edges[1]>0:
        beats[0]['text']='keep the existing timeline unchanged before the insertion ('+', '.join(beats[0]['refs'])+')'
        beats[0]['preserve_existing']=True
    # A vetted motion reference supplies its mechanism, not its look. Authored
    # transformation verbs retain priority and are never replaced by a metaphor.
    for r in refs:
        if r['handle'].startswith('m') and r.get('mechanism'):
            index=assignments[r['handle']];beats[index]['mechanism']=r['mechanism']
            if not content.get('beats') and not re.search('comes back as|snaps into',draft,re.I):
                if r.get('beat_text'):beats[index]['text']=r['beat_text']+' ('+', '.join(beats[index]['refs'])+')'
    if content.get('beats'):beats=deepcopy(content['beats'])
    for r in refs:
        r['cited_by']=[b['id'] for b in beats if re.search(r'(?<!\w)'+r['handle']+r'(?!\w)',b['text'])]
        role=r['role'];b=r['cited_by'][0] if r['cited_by'] else 1
        takes={'look':'overall finish and ground','palette':'warm ink and shadow colours','material':'paper grain on the surface',
               'composition':'hero centred with breathing room','detail':'legible small mark on subject','main mechanic':'lower-edge entrance, subject swapped',
               'turn':'pull out to expose the larger whole, subject swapped','exit':'continuous drift to the final pose, subject swapped'}
        r['use']=f'beat {b}: '+r.get('take',takes[role])
        if r['handle'].startswith('m'):
            r.setdefault('time_range',[0.,1.6]);r.setdefault('speed_scale',1.)
            r['use']+=f'; {r["time_range"][0]:g}–{r["time_range"][1]:g} s at {r["speed_scale"]:g}x'
        if r['handle']=='m2':r['is_turn']=True;r['use']+=' (the turn)'
    vertical=platform in ('ig_reels','tiktok','shorts') or bool(re.search(r'直式|vertical|9:16',draft,re.I))
    assets=[dict(path=c['path'],licence=c.get('licence','user-owned'),owned=c.get('owned',True),role='asset',title=c.get('id','user footage')) for c in cards if c.get('path')]
    assets+=deepcopy(content.get('assets',[]))
    result=dict(version=1,mode=mode,mode_reason=reason,draft=draft,aesthetic=copy['aesthetic'],fence=copy['fence'],
                subject=copy['subject'],pace=copy['pace'],duration=duration,fps=fps,width=1080,height=1920 if vertical else 1080,
                beats=beats,refs=refs,assets=assets,structure=design,taste=taste,refstat=refstat or {},music=grid,
                end_hold=0.,hero_height=.5,min_text_px=24,forks=content.get('forks',[]),
                camera=content.get('camera','拉遠：減速落在完整主體' if copy['zh'] else 'pull: ease out into the full assembly'),meta=meta,
                contact_sheets='.scratch/brief-refs/',text_origin='agent-authored' if content else 'editable recorded starting treatment')
    if not cards:result['missing_asset']='未提供真實素材；預覽使用剪影卡片。' if copy['zh'] else 'Real subject media is missing; the preview uses silhouette cards.'
    if copy['zh'] and not content.get('pace'):result['pace']='動作連續，轉折前留呼吸，細節清楚落定'
    if isinstance(music,(str,Path)) and Path(music).suffix!='.json':result['music_source']=str(Path(music).resolve())
    if copy['background']:
        result['rule_break']=dict(rule='hero_size',why='Background field behind plan cards intentionally has no hero subject')
        for b in result['beats']:b['hero_height']=0
    if mode=='batch':
        n=re.search(r'(\d+)\s*(?:個|different|variations|versions)',draft,re.I);n=int(n[1]) if n else 3
        if not 2<=n<=30:raise ValueError('E_SCHEMA batch: choose 2..30 items')
        mechanics=['pull','pan','tilt','push','crane','dolly']
        result['items']=[dict(id=i+1,mechanic=mechanics[i%6],layout=['centred','thirds','diagonal'][i//6%3],treatment=['paper','glass'][i//18],
                              text=f'{mechanics[i%6]} to expose the subject; composition {i//6+1}') for i in range(n)]
        result['dedupe']='Change mechanism, layout or material; reverse direction and mirror alone are not variations.'
    result['prompt']=prompt(result);return result


def prompt(brief):
    if brief.get('mode') in ('housekeeping','delta','image_feedback'):return brief.get('prompt',brief.get('draft',''))
    zh=bool(re.search('[\u3400-\u9fff]',brief.get('draft','')))
    lines=[('以' if zh else 'in ')+brief['aesthetic']+('：' if zh else ':')]
    for b in brief['beats']:lines.append(f'{b["id"]}. {b["t_start"]:g}–{b["t_end"]:g}s: {b["text"]}')
    lines.append(brief['pace']+'; '+brief['camera'])
    lines.append(f'{brief["width"]}:{brief["height"]}; ~{brief["duration"]:g}s')
    for f in brief.get('forks',[]):lines.append('[? '+f['choice_made']+' / '+f['alternative']+']')
    lines.append('refs:')
    for r in brief['refs']:
        provenance=r.get('source_url',r.get('path',r.get('origin_handle',r.get('placeholder','local statistics'))))
        lines.append(f'- {r["handle"]} {provenance}: {r["role"]}, {r["use"]}')
    lines.append('assets:')
    for a in brief.get('assets',[]):lines.append(f'- {a.get("path",a.get("source_url",""))}: use as-is; {a.get("licence","unknown")}')
    if not brief.get('assets'):lines.append('- silhouette stand-in; replace with the real subject')
    return '\n'.join(lines)


def markdown(brief):
    lead=brief.get('missing_asset','')
    text=(lead+'\n' if lead else '')+'```text\n'+prompt(brief)+'\n```\n'
    if brief.get('mode') in ('housekeeping','delta','image_feedback'):
        if brief.get('questions'):text+='fill-ins: '+'; '.join(brief['questions'])+'\n'
        return text+'<!-- brief-json\n'+json.dumps(brief,ensure_ascii=False,sort_keys=True).replace('-->','--\\u003e')+'\n-->\n'
    text+='fill-ins: '+('; '.join(f['choice_made']+' / '+f['alternative'] for f in brief.get('forks',[])) or 'none')+'\n'
    missing=[r for r in brief.get('refs',[]) if r.get('placeholder')]
    if missing:text+='unfilled refs: '+', '.join(r['handle']+' ('+'; '.join(r['queries_tried'])+')' for r in missing)+'\n'
    text+='contact sheets: '+brief.get('contact_sheets','.scratch/brief-refs/')+'\n'
    # Round-trip data; never copied into a renderer plan.
    return text+'<!-- brief-json\n'+json.dumps(brief,ensure_ascii=False,sort_keys=True).replace('-->','--\\u003e')+'\n-->\n'


def to_storyboard(brief,variant=1):
    check=lint(dict(brief,prompt=prompt(brief)))
    if check['errors']:raise ValueError('E_BRIEF '+json.dumps([f for f in check['findings'] if f['severity']=='error'],ensure_ascii=False))
    from fx import TRANSITIONS
    for name in brief.get('structure',{}).get('recipes',[]):
        file=ROOT/'recipes'/f'{name}.json'
        if not file.is_file() or read(file).get('status')!='stable':raise ValueError('E_STATUS structure.recipes: use stable recipes only; '+str(name))
    for name in brief.get('structure',{}).get('transitions',[]):
        if name not in ('cut','hard_cut') and TRANSITIONS.get(name,{}).get('status')!='stable':raise ValueError('E_STATUS structure.transitions: use a stable transition; '+str(name))
    credits=validate_assets(brief.get('assets',[]));design=stable_choices(structure(brief['draft'],brief,brief.get('taste'),brief.get('refstat')))
    from storyboard import validate
    from taste_lint import default_tokens,transition_family
    tokens=default_tokens(profile=brief.get('taste'));tokens['transitions']['primary']=transition_family(design['transitions'][0]);tokens['motion']=design['moves']+['pull','static']
    assets=brief.get('assets',[]);shots=[];curve=[];warnings=[]
    refs={r['handle']:r for r in brief['refs']}
    item=None
    if brief.get('mode')=='batch':
        if not 1<=variant<=len(brief['items']):raise ValueError('E_VARIANT: choose a registered batch item')
        item=brief['items'][variant-1]
    for beat in brief['beats']:
        duration=beat['t_end']-beat['t_start'];lengths=beat.get('shot_durations',[duration]);lengths=np.array(lengths,float);lengths*=duration/lengths.sum()
        cursor=beat['t_start'];curve.append([cursor,.8 if beat['is_turn'] else .25])
        for j,length in enumerate(lengths):
            i=len(shots);turn=beat['is_turn'] and j==0;name=design['recipes'][(i+1)%len(design['recipes'])]
            if turn:name={'kinetic':'drop','precision':'hero_glow','graphic':'reveal_subject','warm':'soft_hit','fresh':'soft_hit'}[design['profile']]
            move=item['mechanic'] if item else beat.get('mechanism',design['moves'][i%len(design['moves'])])
            from storyboard import MOVES
            why='Beat '+str(beat['id'])+': '+beat['text']
            if move not in MOVES:
                warning=f'beat {beat["id"]}: mechanism {move} has no stable implementation; using pull reveal'
                warnings.append(warning);why+='; '+warning;move='pull';name='breathe'
            if recipe_camera(name):move='static';why+='; the recipe owns the single camera movement'
            end=beat['t_end'] if j==len(lengths)-1 else round(cursor+float(length),6)
            handles=beat.get('refs',[r['handle'] for r in brief['refs'] if beat['id'] in r['cited_by']])
            shot=dict(id=f'shot-{i+1}',start=round(cursor,6),end=end,duration=round(end-cursor,6),beat=beat['id'],beats=[beat['id']],
                      size=design['sizes'][i%len(design['sizes'])],angle=(i%3)*35,lens='telephoto' if design['profile']=='precision' else 'standard',
                      motion=move,composition=(item['layout']+'; ' if item else '')+refs['a4']['use']+' (a4)',direction='neutral',axis='main',
                      lighting=refs['a3']['use']+' (a3)',color_script=refs['a2']['use']+' (a2)',
                      action=beat['text'],subject=brief.get('subject','subject'),is_turn=turn,refs=handles,
                      hero_height=beat.get('hero_height',.5),min_text_px=beat.get('min_text_px',24),
                      intent='reveal_subject' if turn else 'breathe',perceived=.15 if turn else .04,
                      recipe=dict(name=name,perceived=.15 if turn else .04,serves_core='Make this beat legible in the chosen aesthetic'),
                      transition='cut' if i==0 or turn else design['transitions'][i%len(design['transitions'])],
                      transition_serves_core='Join the same gesture across framings',sound=dict(section='drop' if turn else 'phrase',energy=.8 if turn else .25),
                      why=why+'; '+refs['a5']['use']+' (a5)',serves_core='Give the subject its specific action and payoff',
                      background='#d2ad7f' if design['profile']=='warm' else '#dce7de' if design['profile']=='fresh' else '#263444')
            for field in ('elements','captions','min_text_px'):
                if field in beat:shot[field]=deepcopy(beat[field])
            if assets:
                preferred='a4' if turn else 'a3' if beat['id']<next(x['id'] for x in brief['beats'] if x['is_turn']) else 'a5'
                source=refs[preferred].get('path') if refs[preferred].get('source')=='user' else None
                asset=next((a for a in assets if source and a.get('path')==source),assets[i%len(assets)])
                if asset.get('path'):shot['image']=asset['path'];shot['asset']=asset
            shots.append(shot);cursor=end
    curve.append([brief['duration'],curve[-1][1]])
    board=dict(version=1,core=brief['draft'],fps=brief['fps'],width=brief['width'],height=brief['height'],duration=brief['duration'],shots=shots,tokens=tokens,
               design_curve=curve,design_origin='authored brief beats',editorial_structure=design,warnings=warnings,credits=credits,
               reference_policy='Read references for mechanisms and statistics; render only assets or silhouette cards',
               brief_ref_uses=[dict(handle=r['handle'],use=r['use'],cited_by=r['cited_by']) for r in brief['refs']],
               preserve_footage_motion=True,asset_policy=brief.get('assets',[]),music=brief.get('music',{}),reference_paths=[r['path'] for r in brief['refs'] if r.get('path') and r.get('source')!='user'])
    if brief.get('music_source'):board['music_source']=brief['music_source']
    return validate(board)


class BriefParser(argparse.ArgumentParser):
    def error(self,message):
        print(json.dumps(dict(ok=False,error=dict(code='E_ARGUMENT',location='arguments',message=message,suggestion='Use brief.py --help for supported arguments'))))
        raise SystemExit(2)


def previous_document(value,project=None):
    if not value:
        candidate=Path(project)/'storyboard.json' if project else None
        return read(candidate) if candidate and candidate.is_file() else None
    path=Path(value)
    if not path.exists() and project:path=Path(project)/value
    if path.is_dir():path=path/'storyboard.json'
    return read(path)


def main(argv=None):
    parser=BriefParser(description=__doc__)
    parser.add_argument('command',nargs='?',default='expand',choices=['expand','lint','to-storyboard','plan','render','apply','schema'])
    parser.add_argument('input',nargs='?');parser.add_argument('--draft');parser.add_argument('--project');parser.add_argument('--music');parser.add_argument('--platform')
    parser.add_argument('--taste');parser.add_argument('--ref');parser.add_argument('--content');parser.add_argument('--library');parser.add_argument('--cassette')
    parser.add_argument('--offline',action='store_true');parser.add_argument('--json',action='store_true');parser.add_argument('--out');parser.add_argument('--previous');parser.add_argument('--image')
    parser.add_argument('--variant',type=int,default=1)
    a=parser.parse_args(argv)
    try:
        if a.command=='schema':data=read(ROOT/'references/brief.schema.json')
        elif a.command=='lint':data=lint(read(a.input))
        elif a.command=='to-storyboard':data=to_storyboard(read(a.input),a.variant)
        elif a.command in ('plan','render'):
            from brief_render import compile_plan,render_version
            b=read(a.input);board=to_storyboard(b) if 'beats' in b else b
            if not a.out:raise ValueError('E_ARGUMENT --out: required')
            data=compile_plan(board,Path(a.out)) if a.command=='plan' else render_version(board,Path(a.out),a.previous)
        elif a.command=='apply':
            from brief_edit import apply_changes,parse
            previous=read(a.input);data=apply_changes(previous,parse(a.draft,previous,image=a.image))
        else:
            if not a.draft:raise ValueError('E_ARGUMENT --draft: required')
            target=read(a.ref) if a.ref and Path(a.ref).suffix=='.json' else None
            if a.ref and target is None:
                from taste_target import calibrate
                target=calibrate([a.ref])
            data=expand(a.draft,project=a.project,taste=read(a.taste) if a.taste else None,refstat=target,music=a.music,platform=a.platform,
                        content=read(a.content) if a.content else None,library=read(a.library) if a.library else (),
                        provider=CassetteProvider(read(a.cassette)) if a.cassette else None,offline=a.offline,image=a.image,previous=previous_document(a.previous,a.project))
        if a.out and a.command not in ('plan','render'):
            if Path(a.out).suffix=='.md':Path(a.out).write_text(markdown(data),encoding='utf-8')
            else:write(a.out,data)
        if a.json or a.command!='expand':print(json.dumps(data,ensure_ascii=False,allow_nan=False))
        else:print(markdown(data).split('<!-- brief-json')[0])
        return 2 if a.command=='lint' and data['errors'] else 0
    except (ValueError,OSError,KeyError,TypeError,RuntimeError,IndexError) as exc:
        error=dict(code=str(exc).split()[0] if str(exc).startswith('E_') else 'E_BRIEF',location=a.input or a.command,
                   message=str(exc),suggestion='Inspect the named field; use schema and brief lint before conversion')
        print(json.dumps(dict(ok=False,error=error),ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main())
