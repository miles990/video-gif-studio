#!/usr/bin/env python3
"""Validate, render and inspect explicitly requested post-production effects."""
import argparse
import bisect
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from collections import deque
import numpy as np
from PIL import Image, ImageDraw
from compose_timeline import compose, resolve_plan, export_timeline, FORMATS
from fx import Context, EFFECTS, TRANSITIONS, evaluate
from fx.core import OVERRIDES, catalog, load_directory, validate_envelope, triggers, audio_peaks

TOP = {'segments','beatmap','music','effects','fps','seed','sampling','review','interpolate','rife_model'}
SEGMENT = {'type','manifest','image','previous','frame','duration_ms','in_ms','out_ms','speed','ramp','ending','end_beat','end_downbeat','transition','review'}
META = {'name','start_ms','end_ms','start_beat','end_beat','review','stage'}

def keys(value, allowed, where):
    if not isinstance(value,dict): raise ValueError(f'{where}: expected JSON object; valid keys {sorted(allowed)}')
    unknown = set(value)-allowed
    if unknown: raise ValueError(f'{where}: unknown {sorted(unknown)}; valid keys {sorted(allowed)}')

def number(value, where, minimum=0, maximum=math.inf):
    if type(value) not in (int,float) or not math.isfinite(value) or not minimum<=value<=maximum:
        raise ValueError(f'{where}: {value!r}; expected number in {minimum}..{maximum}')
    return value

def beat_index(index, times, where):
    if type(index) is not int or not 0<=index<len(times):
        raise ValueError(f'{where}: {index!r}; valid beat range 0..{len(times)-1}')
    return times[index]

def validate_entry(entry, registry, ctx, where, metadata):
    if not isinstance(entry,dict): raise ValueError(f'{where}: expected object with name; available {sorted(registry)}')
    name = entry.get('name')
    if name not in registry: raise ValueError(f'{where}: unknown {name!r}; available {sorted(registry)}')
    spec = registry[name]
    keys(entry,set(spec['params'])|metadata,where)
    params = {k:entry.get(k,v['default']) for k,v in spec['params'].items()}
    for k,v in params.items():
        expected = spec['params'][k]['type']
        if isinstance(v,dict) and expected=='number': validate_envelope(v,ctx,where+'.'+k)
        elif expected=='number': number(v,where+'.'+k,-math.inf)
        elif expected=='str' and not isinstance(v,str): raise ValueError(f'{where}.{k}: expected str, got {v!r}')
        elif expected=='bool' and type(v) is not bool: raise ValueError(f'{where}.{k}: expected bool, got {v!r}')
        if k=='sampling' and v not in ('linear','nearest'): raise ValueError(f'{where}.{k}: valid options linear, nearest')
        if k=='direction' and expected=='str' and v not in ('left','right','up','down','horizontal','vertical'): raise ValueError(f'{where}.{k}: valid options left, right, up, down, horizontal, vertical')
        if k in ('bg','color') and v and (len(v.lstrip('#'))!=6 or any(c not in '0123456789abcdefABCDEF' for c in v.lstrip('#'))):
            raise ValueError(f'{where}.{k}: expected 6-digit RGB hex')
    source = Path(spec['source'])
    if name=='shape_wipe' and params['shape'] not in ('circle','diamond','star','heart'):raise ValueError(where+'.shape: circle, diamond, star, heart')
    if name=='text' and params['entrance'] not in ('pop','scale'):raise ValueError(where+'.entrance: pop or scale')
    if name=='text':
        from fx.effects.typography import resolve_font
        params['font']=resolve_font(params['font'])
    if name=='parallax':
        from fx.depth import check_model
        check_model(params['model'])
        if not params['depth']:
            from fx.timewarp import session
            try:session(params['model'])
            except ValueError as exc:raise ValueError(f'{where}: {exc}; .runtime/models/depth-anything-v2-small.onnx; use beat_bounce/zoom_punch instead') from None
    return {'name':name,'params':params,'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}

def validate_plan(plan_path, formats=('png',)):
    path = Path(plan_path).resolve()
    plan = json.loads(path.read_text(encoding='utf-8-sig'))
    if os.environ.get('VIDEO_GIF_INTERPOLATE'):plan['interpolate']=os.environ['VIDEO_GIF_INTERPOLATE']
    keys(plan,TOP,'plan')
    if not isinstance(plan.get('segments'),list) or not plan['segments']: raise ValueError('segments: expected nonempty list')
    fps = number(plan.get('fps',25),'fps',1,50)
    if plan.get('interpolate','flow') not in ('none','blend','flow','rife'): raise ValueError('interpolate: choose none, blend, flow, rife')
    if plan.get('interpolate')=='rife':
        from fx.timewarp import session
        session(plan.get('rife_model',os.environ.get('VIDEO_GIF_RIFE_MODEL','.runtime/models/rife_v4.25_lite.onnx')))
    if plan.get('sampling','linear') not in ('linear','nearest'): raise ValueError('sampling: valid options linear, nearest')
    if type(plan.get('seed',0)) is not int: raise ValueError('seed: expected integer')
    music = plan.get('music',{})
    keys(music,{'file','in_ms','gain_db','fade_in_ms','fade_out_ms'},'music')
    if music:
        if not (path.parent/music.get('file','')).is_file(): raise ValueError('music.file: expected existing audio file')
        for k in ('in_ms','fade_in_ms','fade_out_ms'): number(music.get(k,0),'music.'+k)
        number(music.get('gain_db',0),'music.gain_db',-60,20)
    offset = music.get('in_ms',0)
    beats = json.loads((path.parent/plan['beatmap']).read_text()) if 'beatmap' in plan else {}
    for k in ('beats_ms','downbeats_ms'):
        values = beats.get(k,[])
        if not isinstance(values,list) or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values) or any(b<=a for a,b in zip(values,values[1:])):
            raise ValueError(f'beatmap.{k}: expected strictly increasing finite nonnegative times')
    for t in beats.get('downbeats_ms',[]):
        if not any(abs(t-b)<=1 for b in beats.get('beats_ms',[])):
            raise ValueError(f'beatmap.downbeats_ms: {t} is not in beats_ms (1ms rounding tolerance)')
    ctx = Context(0,0,fps,[v-offset for v in beats.get('beats_ms',[])],seed=plan.get('seed',0),downbeats_ms=[v-offset for v in beats.get('downbeats_ms',[])],sampling=plan.get('sampling','linear'))
    prepared = dict(plan); prepared['segments'] = []
    cursor = 0;extra_source_files=[]
    for i, original in enumerate(plan['segments']):
        where = f'segments[{i}]'; keys(original,SEGMENT,where)
        segment = dict(original)
        if 'speed' in segment:
            speed=segment.pop('speed')
            if isinstance(speed,dict):
                validate_envelope(speed,ctx,where+'.speed')
                values=[v for _,v in speed['keyframes']] if 'keyframes' in speed else [speed.get('min',0),speed.get('max',1)]
                for value in values: number(value,where+'.speed',.001,100)
            else:number(speed,where+'.speed',.001,100)
        if 'ramp' in segment:
            ramp=segment.pop('ramp');keys(ramp,{'into_beat','slow','hit_ms'},where+'.ramp')
            beat_index(ramp.get('into_beat'),ctx.beats_ms,where+'.ramp.into_beat')
            number(ramp.get('slow',.3),where+'.ramp.slow',.001,.999)
            number(ramp.get('hit_ms',200),where+'.ramp.hit_ms',10)
            if 'speed' in original:raise ValueError(where+': choose speed or ramp')
        if 'duration_ms' in segment:
            duration = number(segment['duration_ms'],where+'.duration_ms',10)
            if duration%10: raise ValueError(f'{where}.duration_ms: must be a multiple of 10')
        if 'end_downbeat' in segment:
            if not ctx.downbeats_ms: raise ValueError(f'{where}.end_downbeat: downbeats_ms missing; use --engine beat_this')
            if 'end_beat' in segment or 'duration_ms' in segment: raise ValueError(f'{where}: choose end_downbeat, end_beat or duration_ms')
            segment['duration_ms'] = round(beat_index(segment.pop('end_downbeat'),ctx.downbeats_ms,where+'.end_downbeat')/10)*10-cursor
        if 'end_beat' in segment: beat_index(segment['end_beat'],ctx.beats_ms,where+'.end_beat')
        segment.pop('transition',None)
        # An implicit source out-point follows the output cut at unity speed.
        # Explicit in/out duration-fitting remains the legacy editorial operation.
        if original.get('type')=='animation' and 'out_ms' not in original and 'ramp' not in original and original.get('speed',1)==1:
            data=json.loads((path.parent/original['manifest']).read_text());available=sum(data['durations_ms'])
            target=round(ctx.beats_ms[segment['end_beat']]/10)*10-cursor if 'end_beat' in segment else segment.get('duration_ms',available)
            end=original.get('in_ms',0)+target
            if end<available:segment['out_ms']=end;ctx.source_trimmed=True
        if original.get('type')=='animation' and ('ramp' in original or original.get('speed',1)!=1):
            manifest=path.parent/original['manifest'];data=json.loads(manifest.read_text())
            files=sorted((manifest.parent/'frames').glob('*.png'));available=sum(data['durations_ms'])
            extra_source_files.extend(files)
            if not files or len(files)!=len(data['durations_ms']):raise ValueError(where+': source frames/timing mismatch')
            begin=number(original.get('in_ms',0),where+'.in_ms',0,available)
            finish=number(original.get('out_ms',available),where+'.out_ms',begin+1,available)
            duration=segment.get('duration_ms',finish-begin)
            segment={k:v for k,v in segment.items() if k in ('end_beat','duration_ms','review')}
            segment.update(type='still',image=str(files[0]))
            if 'end_beat' not in segment:segment['duration_ms']=duration
        prepared['segments'].append(segment)
        # Resolve incrementally for exact loop/trim/still semantics and useful location errors.
        try: items, segments = resolve_plan(prepared,path,formats)
        except (ValueError,KeyError,TypeError,OSError) as exc: raise ValueError(f'{where}: {exc}') from None
        cursor = sum(t for _,t in items)
    for i,s in enumerate(segments):
        s['edit']=plan['segments'][i];s['type']=plan['segments'][i]['type']
        if 'ramp' in s['edit']:
            hit=ctx.beats_ms[s['edit']['ramp']['into_beat']]
            if not s['start_ms']<hit<=s['start_ms']+s['duration_ms']:
                raise ValueError(f'segments[{i}].ramp.into_beat: beat must be inside or at segment end')
    size = None
    for file in dict.fromkeys([f for f,_ in items]+extra_source_files):
        with Image.open(file) as im:
            if size is not None and im.size!=size: raise ValueError(f'segments: {file}: all images must share one canvas {size}')
            size = im.size
    ctx.width,ctx.height = size
    for k in ('fade_in_ms','fade_out_ms'):
        if music.get(k,0)>cursor: raise ValueError(f'music.{k}: valid range 0..{cursor}')
    effects, transitions = [], []
    if not isinstance(plan.get('effects',[]),list): raise ValueError('effects: expected list of effect objects')
    for i, entry in enumerate(plan.get('effects',[])):
        where = f'effects[{i}]'
        effect = validate_entry(entry,EFFECTS,ctx,where,META)
        effect['stage'] = entry.get('stage','post')
        if effect['stage'] not in ('source','post'): raise ValueError(f'{where}.stage: valid options source, post')
        for edge,default in [('start',0),('end',cursor)]:
            if edge+'_beat' in entry and edge+'_ms' in entry: raise ValueError(f'{where}: choose {edge}_beat or {edge}_ms')
            value = beat_index(entry[edge+'_beat'],ctx.beats_ms,where+'.'+edge+'_beat') if edge+'_beat' in entry else entry.get(edge+'_ms',default)
            effect[edge+'_ms'] = number(value,where+'.'+edge+'_ms',0,cursor)
        if effect['end_ms']<=effect['start_ms']: raise ValueError(f'{where}: end must follow start')
        if 'sampling' in effect['params'] and 'sampling' not in entry: effect['params']['sampling'] = ctx.sampling
        if effect['params'].get('background'):
            effect['params']['background'] = str((path.parent/effect['params']['background']).resolve())
            if not Path(effect['params']['background']).is_file(): raise ValueError(f'{where}.background: expected existing image')
        for key in ('depth',):
            if effect['params'].get(key):
                effect['params'][key]=str((path.parent/effect['params'][key]).resolve())
                if not Path(effect['params'][key]).is_file():raise ValueError(where+'.'+key+': expected existing image')
        effect['trigger_times_ms'] = sorted(set(t for v in effect['params'].values() if isinstance(v,dict) and v.get('on') in ('beats','downbeats') for t in triggers(v,ctx) if effect['start_ms']<=t<effect['end_ms']))
        effects.append(effect)
    for i, segment in enumerate(plan['segments']):
        if 'transition' not in segment: continue
        where = f'segments[{i}].transition'
        if i==0: raise ValueError(f'{where}: requires a previous segment; valid index 1..{len(segments)-1}')
        entry = segment['transition']
        tr = validate_entry(entry,TRANSITIONS,ctx,where,{'name','duration_ms','review'})
        if tr['name']=='luma_wipe' and tr['params']['mask'] not in ('linear','radial','cloud'):
            tr['params']['mask']=str((path.parent/tr['params']['mask']).resolve())
            if not Path(tr['params']['mask']).is_file():raise ValueError(where+'.mask: expected grayscale image or linear/radial/cloud')
        limit = min(segments[i-1]['duration_ms'],segments[i]['duration_ms'])
        length = number(entry.get('duration_ms',400),where+'.duration_ms',1000/fps,limit)
        if length%10: raise ValueError(f'{where}.duration_ms: must be a multiple of 10')
        if ctx.sampling=='nearest' and (tr['name'] in ('crossfade','whip_pan','flash_cut','glitch') or tr['params'].get('softness',0)):
            warning = f'{where} {tr["name"]} blends colours in nearest/pixel mode'
            tr['warning'] = warning
            print('Warning: '+warning,file=sys.stderr)
        cut = segments[i]['start_ms']
        tr.update(start_ms=cut-length/2,end_ms=cut+length/2,cut_ms=cut,segment_index=i)
        transitions.append(tr)
    for a,b in zip(transitions,transitions[1:]):
        if a['end_ms']>b['start_ms']: raise ValueError('segments: adjacent transition windows overlap; shorten duration_ms')
    needs_audio = any(isinstance(v,dict) and v.get('on') in ('onset','energy') for e in effects+transitions for v in e['params'].values())
    if needs_audio:
        if not music: raise ValueError('effects: onset/energy require music.file for 10ms RMS analysis')
        from music_sync import audio_envelopes
        ctx.audio = audio_envelopes(path.parent/music['file']); ctx.audio['offset_ms'] = offset
        for effect in effects:
            effect['trigger_times_ms'] = sorted(set(effect['trigger_times_ms']+[
                t for value in effect['params'].values() if isinstance(value,dict) and value.get('on') in ('onset','energy')
                for t,_ in audio_peaks(ctx.audio,value['on']) if effect['start_ms']<=t<effect['end_ms']]))
    return plan, items, segments, ctx, effects, transitions

def render(plan_path, out, formats=('gif',), background='000000'):
    out = Path(out); path = Path(plan_path).resolve()
    if out.exists(): raise ValueError('Use a new output directory')
    if not formats or not set(formats)<=FORMATS: raise ValueError(f'formats: valid options {sorted(FORMATS)}')
    plan,items,segments,ctx,effects,transitions = validate_plan(path,formats)
    origins={}
    for s in plan['segments']:
        if s.get('type') in ('animation','loop') and s.get('manifest'):
            manifest=path.parent/s['manifest'];data=json.loads(manifest.read_text());clock=0
            for file,duration in zip(sorted((manifest.parent/'frames').glob('*.png')),data['durations_ms']):
                origins[str(file.resolve())]=clock;clock+=duration
    if not effects and not transitions and not any('end_downbeat' in s or 'ramp' in s or s.get('speed',1)!=1 for s in plan['segments']):
        if ctx.source_trimmed or any('speed' in s for s in plan['segments']):
            # Explicit unity shares the exact legacy frame/exposure path.
            images=[]
            for file,_ in items:
                with Image.open(file) as im:images.append(im.convert('RGBA'))
            result=export_timeline(path,out,formats,background,plan,items,segments,images,[t for _,t in items])
        else:result=compose(path,out,formats,background)
        manifest_path=out/'manifest.json';record=json.loads(manifest_path.read_text());clock=0;record['source_samples']=[]
        for file,duration in items:
            index=max(0,bisect.bisect_right([s['start_ms'] for s in segments],clock)-1)
            record['source_samples'].append({'output_ms':clock,'segment_index':index,'source_ms':origins.get(str(file.resolve()),0),'interpolation':'none','extended_last_frame':False});clock+=duration
        manifest_path.write_text(json.dumps(record,indent=2));return result
    started = time.perf_counter()
    edges = np.cumsum([0]+[t for _,t in items]).tolist(); total = edges[-1]
    # 10ms exposures retain existing exporters, with the mean requested rate.
    events = [s['start_ms'] for s in segments]
    events += [round(t/10)*10 for e in effects for t in e['trigger_times_ms']]
    # Resolve the first decay step too: repeated maximum-white frames otherwise
    # let tiny codec differences move the measured peak several encoded frames.
    events += [round(t/10)*10+10 for e in effects if e['name']=='flash_white' for t in e['trigger_times_ms']]
    events += [tr['cut_ms']+10 for tr in transitions if tr['name']=='flash_cut']
    sample_edges = sorted(set([round(k*1000/ctx.fps/10)*10 for k in range(math.ceil(total*ctx.fps/1000))]+[t for t in events if 0<=t<=total]+[total]))
    if len(sample_edges)>2 and sample_edges[-1]-sample_edges[-2]<20: sample_edges.pop(-2)
    cache = {}
    remaps={}; source_records=[]; flow_cache={}
    from fx.timewarp import source_clock, interpolate, flow_pair
    from fx.core import floating
    from fx.core import restore
    for i,original in enumerate(plan['segments']):
        if original.get('type')=='animation' and ('ramp' in original or original.get('speed',1)!=1):
            manifest=path.parent/original['manifest']; data=json.loads(manifest.read_text())
            files=sorted((manifest.parent/'frames').glob('*.png'))
            remaps[i]=(files,np.cumsum([0]+data['durations_ms']),original)
    def read(file):
        if file not in cache:
            if len(cache)>=12:cache.pop(next(iter(cache)))
            with Image.open(file) as im:cache[file]=np.array(im.convert('RGBA'))
        return cache[file]
    def parameters(effect,t,end=None):
        result = {}
        for key,value in effect['params'].items():
            at = t
            if isinstance(value,dict) and value.get('on') in ('beats','downbeats'):
                candidates = [beat for beat in triggers(value,ctx) if round(beat/10)*10==t]
                if candidates: at = min(candidates,key=lambda beat:abs(beat-t))
            result[key] = evaluate(value,at,ctx)
            if isinstance(value,dict) and value.get('on') in ('onset','energy') and end is not None:
                # Integrate peaks over the exposure; a subframe onset cannot disappear.
                samples = [s-ctx.audio.get('offset_ms',0) for s in ctx.audio['times_ms']
                           if t<=s-ctx.audio.get('offset_ms',0)<end]
                result[key] = max([result[key]]+[evaluate(value,s,ctx) for s in samples])
        return result
    def source(t, index=None):
        index = max(0,bisect.bisect_right([s['start_ms'] for s in segments],t)-1) if index is None else index
        j = max(0,min(len(items)-1,bisect.bisect_right(edges,t)-1))
        if index is not None: j = max(segments[index]['start_frame'],min(segments[index]['end_frame_exclusive']-1,j))
        file = items[j][0]
        frame = read(file)
        previous_segment = ctx.segment
        ctx.segment = dict(segments[index],index=index,end_ms=segments[index]['start_ms']+segments[index]['duration_ms'])
        active_t = max(segments[index]['start_ms'],min(t,segments[index]['start_ms']+segments[index]['duration_ms']-1e-6))
        source_ms=origins.get(str(file.resolve()),0);method='none';extended=False
        if index in remaps:
            files,source_edges,original=remaps[index]
            local=active_t-segments[index]['start_ms'];begin=original.get('in_ms',0)
            requested=begin+source_clock(original,local,ctx)
            limit=original.get('out_ms',int(source_edges[-1]))
            extended=requested>=limit;source_ms=min(requested,limit-1e-5)
            k=max(0,min(len(files)-1,bisect.bisect_right(source_edges,source_ms)-1))
            file=files[k];frame=read(file)
            speed=(source_clock(original,local+1,ctx)-source_clock(original,local,ctx))
            phase=(source_ms-source_edges[k])/(source_edges[k+1]-source_edges[k])
            if speed<1-1e-6 and phase>1e-6 and k+1<len(files) and source_edges[k+1]<limit:
                method=plan.get('interpolate','flow');other=read(files[k+1]);flows=None
                if method=='flow':
                    key=(str(file),str(files[k+1]))
                    if key not in flow_cache:
                        flow_cache.clear();flow_cache[key]=flow_pair(floating(frame),floating(other))
                    flows=flow_cache[key]
                frame=interpolate(frame,other,phase,method,model=plan.get('rife_model',''),flows=flows)
        if t==ctx.t_ms and index==ctx.segment['index']:
            current_source.update(source_ms=round(float(source_ms),3),interpolation=method,extended_last_frame=extended)
        frame=floating(frame)
        for effect in effects:
            if effect['stage']=='source' and effect['start_ms']<=active_t<effect['end_ms']:
                ctx.effect_start_ms=effect['start_ms']
                frame = EFFECTS[effect['name']]['owned'](frame,t,ctx,**parameters(effect,t,end))
        ctx.segment = previous_segment
        return frame,file
    images, output_items = [], []
    history_size=max([EFFECTS[e['name']].get('history',0) for e in effects]+[0])
    history=deque(maxlen=history_size);history_times=deque(maxlen=history_size);previous_index=None
    for t,end in zip(sample_edges,sample_edges[1:]):
        index = max(0,bisect.bisect_right([s['start_ms'] for s in segments],t)-1)
        ctx.t_ms = t; ctx.segment = dict(segments[index],index=index,end_ms=segments[index]['start_ms']+segments[index]['duration_ms'])
        if index!=previous_index:history.clear();history_times.clear()
        previous_index=index;ctx.history=tuple(reversed(history));ctx.history_times_ms=tuple(reversed(history_times))
        current_source={'output_ms':t,'segment_index':index}
        frame,file = source(t)
        source_records.append(current_source.copy())
        for tr in transitions:
            if tr['start_ms']<=t<tr['end_ms']:
                j = tr['segment_index']; a,_ = source(t,j-1); b,_ = source(t,j)
                p = (t-tr['start_ms'])/(tr['end_ms']-tr['start_ms'])
                frame = TRANSITIONS[tr['name']]['owned'](a,b,p,ctx,**parameters(tr,t,end))
        before_effects=frame.copy() if history_size else None
        for effect in effects:
            if effect['stage']=='post' and effect['start_ms']<=t<effect['end_ms']:
                ctx.effect_start_ms=effect['start_ms']
                frame = EFFECTS[effect['name']]['owned'](frame,t,ctx,**parameters(effect,t,end))
        images.append(Image.fromarray(restore(frame,np.uint8))); output_items.append((file,end-t))
        if history_size:history.append(floating(before_effects));history_times.append(t)
    elapsed = time.perf_counter()-started
    extra = {'effects':effects,'transitions':transitions,'fx_overrides':list(OVERRIDES),'render':{'seconds':elapsed,'fps':len(images)/elapsed,'requested_fps':ctx.fps},'semantics':'Centered transitions; source endpoints extended; effect intervals end-exclusive; no motion synthesized.'}
    extra['warnings'] = [tr['warning'] for tr in transitions if 'warning' in tr]
    extra['source_samples']=source_records
    for segment in segments:
        segment['start_frame'] = bisect.bisect_left(sample_edges,segment['start_ms'])
        segment['end_frame_exclusive'] = bisect.bisect_left(sample_edges,segment['start_ms']+segment['duration_ms'])
    return export_timeline(path,out,formats,background,plan,output_items,segments,images,[t for _,t in output_items],extra)

def preview(out, image_path=None):
    if image_path:
        with Image.open(image_path) as im: frame = np.array(im.convert('RGBA').resize((320,180)))
    else:
        yy,xx = np.indices((180,320)); frame = np.empty((180,320,4),np.uint8)
        frame[:,:,:3] = np.stack((30+xx//3,30+yy//2,120+xx//4),axis=2); frame[:,:,3] = 255
        frame[55:125,110:210,:3] = [245,195,100]
    ctx = Context(320,180); other = frame[:,::-1].copy(); other[:,:,:3] = other[:,:,:3][:,:,::-1]
    settings = {'grade':{'sat':.5,'temp':.08,'gain':1.15},'zoom_punch':{'scale':1.18},
                'beat_bounce':{'translate_px':20,'rotation_deg':-5,'scale':1.06},'halation':{'amount':2,'radius':12,'threshold':.35},
                'shake':{'distance':20},'rgb_split':{'distance':14},'radial_blur':{'distance':.5},
                'split_screen':{'panels':4},'film_grain':{'amount':.07},'dust_scratches':{'amount':1,'density':.04},'echo':{'amount':1,'decay':.8},
                'text':{'size':40},'light_leak':{'amount':.6}}
    ctx.history=(np.roll(frame.astype(np.float32)/255,40,axis=1),np.roll(frame.astype(np.float32)/255,80,axis=1))
    tiles = [('original',frame)]
    for name,spec in EFFECTS.items():
        source = frame.copy()
        if name in ('cutout_card','multi_cutout'):
            source[:,:,3]=0; source[35:150,80:240,3]=255
        try:tiles.append((name,spec['function'](source,240,ctx,**settings.get(name,{}))))
        except (ValueError,OSError) as exc:
            unavailable=Image.new('RGBA',(320,180),(28,30,40,255));d=ImageDraw.Draw(unavailable)
            d.text((8,65),'unavailable: '+str(exc)[:38],fill='white');tiles.append((name,np.array(unavailable)))
    tiles += [(f'{name}  p={p}',spec['function'](frame,other,p,ctx)) for name,spec in TRANSITIONS.items() for p in (.25,.5,.75)]
    sheet = Image.new('RGB',(320*3,212*math.ceil(len(tiles)/3)),(18,22,30)); draw = ImageDraw.Draw(sheet)
    for i,(label,arr) in enumerate(tiles):
        x,y = i%3*320,i//3*212
        tile = Image.new('RGBA',(320,180),(55,60,70,255)); tile.alpha_composite(Image.fromarray(arr))
        sheet.paste(tile.convert('RGB'),(x,y+32)); draw.text((x+12,y+9),label,fill='white')
    Path(out).parent.mkdir(parents=True,exist_ok=True); sheet.save(out)

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan',type=Path,nargs='?'); ap.add_argument('--out',type=Path)
    ap.add_argument('--formats',nargs='+',choices=sorted(FORMATS),default=['gif'])
    ap.add_argument('--background',default='000000'); ap.add_argument('--fx-dir',action='append',default=[])
    ap.add_argument('--no-user-fx',action='store_true'); ap.add_argument('--list',action='store_true'); ap.add_argument('--json',action='store_true')
    ap.add_argument('--preview',type=Path); ap.add_argument('--image',type=Path); ap.add_argument('--validate',action='store_true')
    ap.add_argument('--interpolate',choices=['none','blend','flow','rife'])
    a = ap.parse_args(argv)
    try:
        if not a.no_user_fx: load_directory(os.environ.get('VIDEO_GIF_FX_HOME',str(Path.home()/'.video-gif-studio/fx')))
        for directory in a.fx_dir: load_directory(directory)
        if a.list:
            if a.json: print(json.dumps(catalog(),indent=2))
            else:
                for kind,entries in catalog().items():
                    print(kind.upper())
                    for name,spec in entries.items():
                        print(f'  {name}: {spec["doc"]}')
                        for key,param in spec['params'].items(): print(f'    {key}={param["default"]!r} ({param["type"]}): {param["doc"]}')
                        print(f'    source: {spec["source"]}')
            return 0
        if a.preview: preview(a.preview,a.image); return 0
        if not a.plan: raise ValueError('plan required, or use --list / --preview FILE.png')
        if a.validate: validate_plan(a.plan,a.formats); print('Plan valid'); return 0
        if not a.out: raise ValueError('--out required')
        if a.interpolate:
            # Override remains in memory; never rewrite the user's plan.
            os.environ['VIDEO_GIF_INTERPOLATE']=a.interpolate
        print(json.dumps(render(a.plan,a.out,a.formats,a.background))); return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError) as exc:
        print(f'fx_render: {exc}',file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
