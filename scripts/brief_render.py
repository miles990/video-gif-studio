"""Stable brief rendering and immutable per-shot cache with transition dependencies."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from brief_refs import validate_assets


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def preflight(board):
    from storyboard import validate,lint,MOVES
    from fx import TRANSITIONS
    b=validate(board);credits=validate_assets(b.get('asset_policy',[]))
    denied={str(Path(p).resolve()).casefold() for p in b.get('reference_paths',[])}
    for i,s in enumerate(b['shots']):
        for field in ('image','footage'):
            if s.get(field) and str(Path(s[field]).resolve()).casefold() in denied:
                raise ValueError(f'E_REF_EMBED shots[{i}].{field}: reference media cannot enter outputs')
        if s.get('asset'):validate_assets([s['asset']])
        recipe=s.get('recipe');name=recipe.get('name') if isinstance(recipe,dict) else recipe
        if name:
            path=Path(__file__).resolve().parents[1]/'recipes'/f'{name}.json'
            if not path.is_file() or json.loads(path.read_text())['status']!='stable':raise ValueError(f'E_STATUS shots[{i}].recipe: stable recipes only')
        if s.get('motion') not in MOVES:raise ValueError(f'E_MOTION shots[{i}]: choose a named camera move')
        transition=s.get('transition','cut');name=transition.get('name') if isinstance(transition,dict) else transition
        if name not in ('cut','hard_cut') and TRANSITIONS.get(name,{}).get('status')!='stable':raise ValueError(f'E_STATUS shots[{i}].transition: stable transitions only')
    if lint(b)['errors']:raise ValueError('E_STORYBOARD: resolve structural storyboard errors before rendering')
    return b,credits


def proxy_size(board):
    width,height=board.get('width',1920),board.get('height',1080)
    if min(width,height)<=0:raise ValueError('E_SIZE: width and height must be positive')
    scale=180/min(width,height)
    return tuple(max(2,round(v*scale/2)*2) for v in (width,height))


def compile_plan(board,out,size=None,music=None):
    from animatic import to_plan
    b,credits=preflight(board);out=Path(out);size=size or proxy_size(b)
    plan=to_plan(b,out,size=size,music=music or b.get('music_source'))
    # Match the incremental renderer's local-shot semantics. An accent does not
    # leak into a later cached shot just because its recipe has a long tail.
    import numpy as np
    ends={event['event_id']:next((round(s['end']*1000) for s in b['shots'] if round(s['start']*1000)==event['at_ms']),round(b['duration']*1000)) for event in plan.get('recipe_events',[])}
    effects=[]
    for effect in plan.get('effects',[]):
        end=min(effect['end_ms'],ends.get(effect.get('recipe_event_id'),effect['end_ms']));start=effect['start_ms']
        if end<=start:continue
        effect['end_ms']=end
        for key,value in effect.items():
            if isinstance(value,dict) and 'keyframes' in value:
                points=np.asarray(value['keyframes'],float)
                value['keyframes']=[[start,float(np.interp(start,points[:,0],points[:,1]))]]+[[float(t),float(v)] for t,v in points if start<t<end]+[[end,float(np.interp(end,points[:,0],points[:,1]))]]
        effects.append(effect)
    plan['effects']=effects
    plan['experimental']=False
    # The general SFX router remains experimental; stable visual-only briefs do
    # not silently opt in. A supplied music track is retained independently.
    if plan.pop('sfx',None):write(out/'sound-policy.json',dict(note='Recipe SFX omitted: SFX routing is experimental; supplied music remains unchanged'))
    plan['assets']=deepcopy(b.get('asset_policy',[]))
    plan['review']=dict(hard_constraints=deepcopy(b.get('hard_constraints',[])),subject=b.get('core',''),status=b.get('status','storyboard'))
    write(out/'credits.json',credits);write(out/'plan.json',plan)
    from fx_render import validate_plan
    validate_plan(out/'plan.json')
    return plan


def render_version(board,out,previous=None,size=None,formats=('png','mp4')):
    """Only changed shot pixels are recalculated; assembly owns boundary blends.

    Hashes exclude absolute timeline position, so retiming an earlier shot does not
    invalidate later local frames. Renderer/source/recipe changes invalidate cache.
    Transition windows depend on both neighbor hashes and are explicitly logged.
    """
    from fx_render import render
    from review_shots import reuse_file
    b,credits=preflight(board);out=Path(out);size=size or proxy_size(b)
    if out.exists():raise ValueError('E_OUTPUT: use a new version directory')
    old={};previous=Path(previous) if previous else None
    if previous:
        old={s['id']:s for s in json.loads((previous/'version.json').read_text(encoding='utf-8'))['shots']}
    scripts=Path(__file__).parent;root=scripts.parent
    code_files=sorted([*scripts.glob('*.py'),*(scripts/'fx').rglob('*.py'),*(root/'recipes').glob('*.json')])
    engine=hashlib.sha256(''.join(digest(p) for p in code_files).encode()).hexdigest()
    records=[];segments=[];out.mkdir(parents=True)
    for i,s in enumerate(b['shots']):
        local=deepcopy(s);duration=round(s['end']-s['start'],6);local.update(start=0.,end=duration,duration=duration,transition='cut')
        for key in ('beat','beats','anchor','refs','why','serves_core'):local.pop(key,None)
        deps={}
        for field in ('image','footage'):
            if s.get(field):deps[field]=digest(s[field]) if Path(s[field]).is_file() else 'missing'
        fingerprint=hashlib.sha256(json.dumps(dict(shot=local,files=deps,size=size,fps=b['fps'],footage_motion=b.get('preserve_footage_motion',False),engine=engine),sort_keys=True).encode()).hexdigest()
        shotdir=out/'shots'/s['id'];cached=old.get(s['id'])
        valid=cached and cached['fingerprint']==fingerprint and len(cached['frames'])==len(cached['sha256']) and cached['frames']
        if valid:valid=all((previous/p).is_file() and digest(previous/p)==h for p,h in zip(cached['frames'],cached['sha256']))
        if valid:
            shutil.copytree(previous/'shots'/s['id'],shotdir,copy_function=reuse_file);status='cache'
        else:
            localboard=dict(core=b['core'],status=b.get('status','storyboard'),hard_constraints=deepcopy(b.get('hard_constraints',[])),fps=b['fps'],shots=[local],preserve_footage_motion=b.get('preserve_footage_motion',False),asset_policy=b.get('asset_policy',[]),reference_paths=b.get('reference_paths',[]))
            compile_plan(localboard,out/'inputs'/s['id'],size)
            render(out/'inputs'/s['id']/'plan.json',shotdir,('png',),fps=b['fps']);status='rendered'
        frames=sorted((shotdir/'frames').glob('*.png'))
        record=dict(id=s['id'],fingerprint=fingerprint,status=status,frames=[p.relative_to(out).as_posix() for p in frames],sha256=[digest(p) for p in frames],start=s['start'],end=s['end'])
        records.append(record)
        segment=dict(type='animation',manifest=str((shotdir/'manifest.json').resolve()))
        tr=s.get('transition','cut')
        if i and tr not in ('cut','hard_cut'):
            segment['transition']=dict(tr) if isinstance(tr,dict) else dict(name=tr,duration_ms=100)
            segment['transition']={k:v for k,v in segment['transition'].items() if k in ('name','duration_ms')}
        segments.append(segment)
    boundaries=[dict(left=records[i-1]['id'],right=r['id'],status='rendered' if r['status']=='rendered' or records[i-1]['status']=='rendered' else 'cache inputs') for i,r in enumerate(records) if i and 'transition' in segments[i]]
    assembly=dict(fps=b['fps'],segments=segments,assets=deepcopy(b.get('asset_policy',[])),review=dict(hard_constraints=deepcopy(b.get('hard_constraints',[])),subject=b['core'],status=b.get('status','storyboard')))
    if b.get('music_source'):assembly['music']=dict(file=b['music_source'])
    write(out/'plan.json',assembly);write(out/'storyboard.json',b);write(out/'credits.json',credits)
    render(out/'plan.json',out/'render',formats,fps=b['fps'])
    movies=list((out/'render').glob('*.mp4'))
    if movies:b['render_source']=str(movies[0].resolve());write(out/'storyboard.json',b)
    report=dict(version=1,shots=records,transitions=boundaries,rerendered_shots=[r['id'] for r in records if r['status']=='rendered'],
                reused_shots=[r['id'] for r in records if r['status']=='cache'],duration=b['duration'],
                no_visible_effect=[r['id'] for r in records if r['status']=='rendered' and r['id'] in old and r['sha256']==old[r['id']]['sha256']],
                note='Local shot frames are immutable; final assembly recomposites transition windows and encodes the delivery.')
    write(out/'version.json',report);return report


def diff(before,after):
    old={s['id']:s for s in before['shots']}
    changed=[s['id'] for s in after['shots'] if s['id'] not in old or s['fingerprint']!=old[s['id']]['fingerprint']]
    return dict(shots=changed,transitions=[t for t in after.get('transitions',[]) if t['left'] in changed or t['right'] in changed])
