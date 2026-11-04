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
import numpy as np
from PIL import Image, ImageDraw
from compose_timeline import compose, resolve_plan, export_timeline, FORMATS
from fx import Context, EFFECTS, TRANSITIONS, evaluate
from fx.core import OVERRIDES, catalog, load_directory, validate_envelope, triggers, audio_peaks

TOP = {'segments','beatmap','music','effects','fps','seed','sampling','review'}
SEGMENT = {'type','manifest','image','previous','frame','duration_ms','in_ms','out_ms','speed','ending','end_beat','end_downbeat','transition','review'}
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
        if k=='direction' and v not in ('left','right'): raise ValueError(f'{where}.{k}: valid options left, right')
        if k in ('bg','color') and v and (len(v.lstrip('#'))!=6 or any(c not in '0123456789abcdefABCDEF' for c in v.lstrip('#'))):
            raise ValueError(f'{where}.{k}: expected 6-digit RGB hex')
    source = Path(spec['source'])
    return {'name':name,'params':params,'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}

def validate_plan(plan_path, formats=('png',)):
    path = Path(plan_path).resolve()
    plan = json.loads(path.read_text(encoding='utf-8-sig'))
    keys(plan,TOP,'plan')
    if not isinstance(plan.get('segments'),list) or not plan['segments']: raise ValueError('segments: expected nonempty list')
    fps = number(plan.get('fps',25),'fps',1,50)
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
    cursor = 0
    for i, original in enumerate(plan['segments']):
        where = f'segments[{i}]'; keys(original,SEGMENT,where)
        segment = dict(original)
        if 'duration_ms' in segment:
            duration = number(segment['duration_ms'],where+'.duration_ms',10)
            if duration%10: raise ValueError(f'{where}.duration_ms: must be a multiple of 10')
        if 'end_downbeat' in segment:
            if not ctx.downbeats_ms: raise ValueError(f'{where}.end_downbeat: downbeats_ms missing; use --engine beat_this')
            if 'end_beat' in segment or 'duration_ms' in segment: raise ValueError(f'{where}: choose end_downbeat, end_beat or duration_ms')
            segment['duration_ms'] = round(beat_index(segment.pop('end_downbeat'),ctx.downbeats_ms,where+'.end_downbeat')/10)*10-cursor
        if 'end_beat' in segment: beat_index(segment['end_beat'],ctx.beats_ms,where+'.end_beat')
        segment.pop('transition',None)
        prepared['segments'].append(segment)
        # Resolve incrementally for exact loop/trim/still semantics and useful location errors.
        try: items, segments = resolve_plan(prepared,path,formats)
        except (ValueError,KeyError,TypeError,OSError) as exc: raise ValueError(f'{where}: {exc}') from None
        cursor = sum(t for _,t in items)
    size = None
    for file in dict.fromkeys(f for f,_ in items):
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
        effect['trigger_times_ms'] = sorted(set(t for v in effect['params'].values() if isinstance(v,dict) and v.get('on') in ('beats','downbeats') for t in triggers(v,ctx) if effect['start_ms']<=t<effect['end_ms']))
        effects.append(effect)
    for i, segment in enumerate(plan['segments']):
        if 'transition' not in segment: continue
        where = f'segments[{i}].transition'
        if i==0: raise ValueError(f'{where}: requires a previous segment; valid index 1..{len(segments)-1}')
        entry = segment['transition']
        tr = validate_entry(entry,TRANSITIONS,ctx,where,{'name','duration_ms','review'})
        limit = min(segments[i-1]['duration_ms'],segments[i]['duration_ms'])
        length = number(entry.get('duration_ms',400),where+'.duration_ms',1000/fps,limit)
        if ctx.sampling=='nearest' and tr['name'] in ('crossfade','whip_pan','flash_cut'):
            print(f'Warning: {where} {tr["name"]} blends colours in nearest/pixel mode',file=sys.stderr)
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
    if not effects and not transitions and not any('end_downbeat' in s for s in plan['segments']):
        return compose(path,out,formats,background)
    started = time.perf_counter()
    edges = np.cumsum([0]+[t for _,t in items]).tolist(); total = edges[-1]
    # 10ms exposures retain existing exporters, with the mean requested rate.
    events = [s['start_ms'] for s in segments]
    events += [round(t/10)*10 for e in effects for t in e['trigger_times_ms']]
    sample_edges = sorted(set([round(k*1000/ctx.fps/10)*10 for k in range(math.ceil(total*ctx.fps/1000))]+[t for t in events if 0<=t<=total]+[total]))
    if len(sample_edges)>2 and sample_edges[-1]-sample_edges[-2]<20: sample_edges.pop(-2)
    cache = {}
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
        if file not in cache:
            with Image.open(file) as im: cache[file] = np.array(im.convert('RGBA'))
        frame = cache[file]
        previous_segment = ctx.segment
        ctx.segment = dict(segments[index],index=index,end_ms=segments[index]['start_ms']+segments[index]['duration_ms'])
        active_t = max(segments[index]['start_ms'],min(t,segments[index]['start_ms']+segments[index]['duration_ms']-1e-6))
        for effect in effects:
            if effect['stage']=='source' and effect['start_ms']<=active_t<effect['end_ms']:
                frame = EFFECTS[effect['name']]['function'](frame,t,ctx,**parameters(effect,t,end))
        ctx.segment = previous_segment
        return frame,file
    images, output_items = [], []
    for t,end in zip(sample_edges,sample_edges[1:]):
        index = max(0,bisect.bisect_right([s['start_ms'] for s in segments],t)-1)
        ctx.t_ms = t; ctx.segment = dict(segments[index],index=index,end_ms=segments[index]['start_ms']+segments[index]['duration_ms'])
        frame,file = source(t)
        for tr in transitions:
            if tr['start_ms']<=t<tr['end_ms']:
                j = tr['segment_index']; a,_ = source(t,j-1); b,_ = source(t,j)
                p = (t-tr['start_ms'])/(tr['end_ms']-tr['start_ms'])
                frame = TRANSITIONS[tr['name']]['function'](a,b,p,ctx,**parameters(tr,t,end))
        for effect in effects:
            if effect['stage']=='post' and effect['start_ms']<=t<effect['end_ms']:
                frame = EFFECTS[effect['name']]['function'](frame,t,ctx,**parameters(effect,t,end))
        images.append(Image.fromarray(frame)); output_items.append((file,end-t))
    elapsed = time.perf_counter()-started
    extra = {'effects':effects,'transitions':transitions,'fx_overrides':list(OVERRIDES),'render':{'seconds':elapsed,'fps':len(images)/elapsed,'requested_fps':ctx.fps},'semantics':'Centered transitions; source endpoints extended; effect intervals end-exclusive; no motion synthesized.'}
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
                'beat_bounce':{'translate_px':20,'rotation_deg':-5,'scale':1.06},'halation':{'amount':1,'radius':9}}
    tiles = [('original',frame)]
    for name,spec in EFFECTS.items():
        source = frame.copy()
        if name=='cutout_card':
            source[:,:,3]=0; source[35:150,80:240,3]=255
        tiles.append((name,spec['function'](source,0,ctx,**settings.get(name,{}))))
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
        print(json.dumps(render(a.plan,a.out,a.formats,a.background))); return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError) as exc:
        print(f'fx_render: {exc}',file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
