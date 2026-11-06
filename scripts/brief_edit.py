"""Delta/image-feedback grammar adapted from blank-page SKILL.md (MIT).

Copyright (c) 2026 Cekura, Inc.; notice in THIRD_PARTY.md. Unknown targets and
quantities stay explicit questions; the parser never silently edits everything.
"""
from copy import deepcopy
import json
from pathlib import Path
import re

NUMBERS={'一':1,'二':2,'兩':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}


def number(value):return int(value) if value.isdigit() else NUMBERS.get(value)


def parse(draft,previous,image=None):
    shots=previous.get('shots',[])
    if not shots and 'beats' in previous:
        from brief import to_storyboard
        shots=to_storyboard(previous)['shots']
    changes=[];questions=[];text=draft.lower();keep=['all others']
    if re.search('保留顏色|keep.*colo',text):keep=['color','color_script','LUT','all others']
    metadata={}
    if image:
        path=Path(image).with_suffix('.json')
        if not path.is_file():raise ValueError('E_FEEDBACK metadata: contact sheet timestamps are required')
        metadata=json.loads(path.read_text(encoding='utf-8'))
    lines=re.split(r'[\n；;、，]',draft)
    for line in lines:
        if not line.strip() or re.match(r'\s*(keep|保留|其他不動)',line,re.I):continue
        target={};direction=dict(axis='time',sense='forward');magnitude=None;phase='whole shot';change='speed';extra={}
        shot_match=re.search(r'第([一二三四五六七八九十\d]+)鏡|shot\s*(\d+)',line,re.I)
        beat_match=re.search(r'第([一二三四五六七八九十\d]+)拍|beat\s*(\d+)',line,re.I)
        frame_match=re.search(r'第\s*(\d+)\s*格|frame\s*(\d+)',line,re.I)
        if image and frame_match:
            frame=int(next(g for g in frame_match.groups() if g));times=metadata.get('frames_at_s',[])
            if not 1<=frame<=len(times):raise ValueError('E_FEEDBACK frame: outside contact-sheet metadata')
            time=times[frame-1];target['shots']=[s['id'] for s in shots if s['start']<=time<s['end']]
            extra.update(frame=frame,time=time,observation=line.strip())
            if '暗' in line or 'dark' in line.lower():
                import cv2
                import numpy as np
                source=metadata.get('source')
                if not source or not Path(source).is_file():raise ValueError('E_FEEDBACK source: original rendered clip required to quantify luma')
                cap=cv2.VideoCapture(str(source));cap.set(cv2.CAP_PROP_POS_MSEC,time*1000);ok,bgr=cap.read();cap.release()
                if not ok:raise ValueError('E_FEEDBACK source: cannot decode selected frame')
                rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB).astype(float);y=float(np.mean(rgb@np.array([.2126,.7152,.0722])))
                change='brightness';magnitude=max(0.,80-y);direction=dict(axis='luma',sense='increase');extra['quantified']=dict(measured_y=y,target_y=80)
            else:
                current=next((s.get('min_text_px',24) for s in shots if s['id'] in target['shots']),None)
                change='font_size';magnitude=1.25;direction=dict(axis='size',sense='increase');extra['quantified']=dict(current_px_1080=current,target_px_1080=max(24,(current or 24)*1.25))
        elif beat_match:
            target['beat']=number(next(g for g in beat_match.groups() if g));target['shots']=[s['id'] for s in shots if target['beat'] in s.get('beats',[s.get('beat')])]
        elif shot_match:
            index=number(next(g for g in shot_match.groups() if g));target['shot']=index;target['shots']=[shots[index-1]['id']] if index and 1<=index<=len(shots) else []
        elif re.search('final pan',line,re.I):target['shots']=[s['id'] for s in shots if s['motion']=='pan'][-1:];target['element']='pan'
        elif re.search('轉折|the turn',line,re.I):target['shots']=[s['id'] for s in shots if s.get('is_turn')];target['element']='turn'
        elif re.search('拿掉|remove|get rid of',line,re.I):
            target['element']='last title/card';target['shots']=[s['id'] for s in shots if s.get('elements') or s.get('captions') or s.get('recipe',{}).get('name')=='title_pop'][-1:];change='remove'
        if not image:
            if re.search('提前|drop',line,re.I):
                change='time';grid=previous.get('music',{});drop=grid.get('drop_ms');magnitude=drop/1000 if drop is not None else None
                direction=dict(axis='timeline',sense='align to drop')
                if magnitude is None:questions.append('[? reviewed drop time]')
            elif re.search('度|degree',line,re.I):
                change='rotation';match=re.search(r'(\d+(?:\.\d+)?)\s*(?:度|degree)',line);magnitude=float(match[1])
                direction=dict(axis='yaw',sense='screen-right' if re.search('右|right|clockwise',line,re.I) else 'screen-left')
            elif change!='remove':
                match=re.search(r'(\d+(?:\.\d+)?)\s*[x×]',line,re.I);magnitude=float(match[1]) if match else .8 if re.search('慢|slower',line,re.I) else 1.25
                direction=dict(axis='time',sense='slower' if re.search('慢|slower',line,re.I) else 'faster')
                phase='top speed' if re.search('top speed',line,re.I) else 'whole shot'
                if not match:extra['default']='[? '+str(magnitude)+'x]'
            if re.search('other way|另一邊|反過來',line,re.I):
                old=next((s.get('direction') for s in shots if s['id'] in target.get('shots',[])),None)
                absolute={'left-to-right':'right-to-left','right-to-left':'left-to-right','screen-right':'screen-left','screen-left':'screen-right'}
                if old not in absolute:questions.append('[? absolute screen direction]')
                else:direction=dict(axis='x',sense=absolute[old]);change='direction';magnitude=1
        if not target.get('shots'):questions.append('[? target shot / edit pace or camera speed]' if re.search('make it faster',line,re.I) else '[? target shot]')
        changes.append(dict(target=target,change=change,magnitude=magnitude,direction=direction,phase=phase,keep=keep,**extra))
    questions=list(dict.fromkeys(questions))[:1]
    lines=[]
    for c in changes:
        target=','.join(c['target'].get('shots',[])) or '? target'
        lines.append(f'{target}: {c["change"]} {c.get("default",c["magnitude"])} {c["direction"]["sense"]}; keep '+', '.join(c['keep']))
    return dict(version=1,mode='image_feedback' if image else 'delta',mode_reason='contact sheet' if image else 'targeted change',draft=draft,
                changes=changes,questions=questions,prompt='\n'.join(lines),understood='我理解為：'+'; '.join(lines),refs_unchanged=True)


def apply_changes(board,edit):
    if edit.get('questions'):raise ValueError('E_AMBIGUOUS: '+edit['questions'][0])
    b=deepcopy(board);changed=set();notes=[]
    for c in edit['changes']:
        ids=set(c['target']['shots']);changed.update(ids)
        for s in b['shots']:
            if s['id'] not in ids:continue
            if c['change']=='speed':
                if c['phase']=='top speed':s['motion_peak_speed']=c['magnitude']
                else:
                    if b.get('music',{}).get('downbeats_ms'):
                        notes.append('Preserve total length and downstream downbeats; slow only the camera/action inside this shot, shortening its travel.')
                    else:s['duration']=(s['end']-s['start'])/c['magnitude']
                    s['motion_speed']=c['magnitude']
            elif c['change']=='remove':
                s['elements']=[e for e in s.get('elements',[]) if e.get('type') not in ('title','card')];s['captions']=[]
                if s.get('recipe',{}).get('name')=='title_pop':s.pop('recipe')
            elif c['change']=='rotation':
                # Screen yaw is a lateral camera pan, not an in-plane roll.
                s['yaw_degrees']=c['magnitude']*(1 if c['direction']['sense']=='screen-right' else -1)
            elif c['change']=='direction':s['direction']=c['direction']['sense']
            elif c['change']=='brightness':s['brightness_delta']=c['magnitude']
            elif c['change']=='font_size':s['min_text_px']=c['quantified']['target_px_1080']
            elif c['change']=='time':
                idx=b['shots'].index(s);delta=c['magnitude']-s['start']
                if idx==0 or b['shots'][idx-1]['duration']+delta<=0:raise ValueError('E_TIME: cannot move turn without a positive preceding shot')
                if s['duration']-delta<=0:raise ValueError('E_TIME: turn would have no remaining duration')
                b['shots'][idx-1]['duration']+=delta;changed.add(b['shots'][idx-1]['id'])
                s['duration']-=delta
    cursor=0.;grid=b.get('music',{}).get('downbeats_ms',[])
    for s in b['shots']:
        duration=s.get('duration',s['end']-s['start']);s['start']=round(cursor,6);s['end']=round(cursor+duration,6);cursor=s['end']
    b['duration']=cursor
    b['revision']=dict(changed_shots=sorted(changed),keep=sorted({k for c in edit['changes'] for k in c['keep']}),notes=notes)
    # Keep colors and all unaddressed local render fields bit-for-bit.
    return b
