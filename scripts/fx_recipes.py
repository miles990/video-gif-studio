"""JSON intent recipes and lossless expansion into the existing plan format."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import sys
from fx import EFFECTS, TRANSITIONS
from fx_calibrate import inverse
from fx_catalog import INTENTS, NEEDS, ROOT


def validate(recipe):
    json.dumps(recipe,allow_nan=False)
    from fx_schema import validate as schema_validate
    schema_validate(recipe,json.loads((ROOT/'references/fx-recipe.schema.json').read_text(encoding='utf-8')))
    required={'name','intent','layers','sfx','perceived_target','gate','status','notes','needs','good_for','avoid_for'}
    if required-set(recipe):raise ValueError('Recipe missing '+str(sorted(required-set(recipe))))
    import re
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',recipe['name']):raise ValueError('Invalid recipe name: '+recipe['name'])
    for field in ('good_for','avoid_for'):
        if not isinstance(recipe[field],list) or not recipe[field] or any(not isinstance(v,str) or not v.strip() for v in recipe[field]):
            raise ValueError('Invalid recipe '+field)
    if recipe['intent'] not in INTENTS:raise ValueError('Unknown recipe intent')
    if set(recipe['needs'])-set(NEEDS):raise ValueError('Unknown recipe needs: '+str(recipe['needs']))
    from sfx import KINDS
    if recipe['sfx'] is not None and recipe['sfx'] not in KINDS:raise ValueError('Unknown recipe sfx: '+str(recipe['sfx']))
    if recipe['status'] not in ('stable','experimental'):raise ValueError('Invalid recipe status')
    if recipe['status']=='stable' and recipe['gate'].get('status')!='stable':raise ValueError('Stable recipe requires a stable technical gate')
    if not 0<recipe['perceived_target']<=1:raise ValueError('Recipe target must be in (0,1]')
    if not recipe['layers']:raise ValueError('Recipe needs layers')
    for layer in recipe['layers']:
        if layer.get('kind') not in ('effect','transition'):raise ValueError('Visual recipe layers must be effects or transitions; pair sound in sfx')
        reg=EFFECTS if layer['kind']=='effect' else TRANSITIONS
        spec=reg.get(layer['ref'])
        if spec is None or spec['status']!='stable':raise ValueError('Recipe ingredient is unknown or experimental (not stable): '+layer['ref'])
        if set(layer['params'])-set(spec['params']):raise ValueError('Unknown recipe parameters: '+layer['ref'])
        knob=layer.get('control','amount')
        if knob not in spec['params'] and not (knob=='mix' and layer['ref']=='cutout_card'):
            raise ValueError(f'{layer["ref"]}: unknown recipe control {knob}')
        for key,v in layer['params'].items():
            expected=spec['params'][key]['type']
            if expected=='number' and (type(v) not in (int,float) or not math.isfinite(v)) or expected=='str' and not isinstance(v,str) or expected=='bool' and type(v) is not bool:
                raise ValueError(f'{layer["ref"]}.{key}: expected {expected}, got {v!r}')
        if layer['offset_ms']<0 or layer['duration_ms']<=0:raise ValueError('Invalid layer time')
        points=layer['envelope']
        if len(points)<2 or any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in points):raise ValueError('Invalid recipe envelope')
        if points[0][0]!=0 or points[-1][0]!=layer['duration_ms'] or any(b[0]<=a[0] for a,b in zip(points,points[1:])):raise ValueError('Recipe envelope must span duration with increasing times')
    return recipe


def load_recipes(directory=None, experimental=False):
    result={}
    dirs=[ROOT/'recipes']
    user=directory or os.environ.get('VIDEO_GIF_RECIPE_HOME')
    if user:dirs.append(Path(user))
    for root in dirs:
        for path in sorted(root.glob('*.json')):
            r={}
            try:
                r=json.loads(path.read_text(encoding='utf-8'))
                validate(r)
            except Exception as exc:
                from fx_diagnostics import excluded
                data=r if isinstance(r,dict) else {}
                refs=[l.get('ref','?') for l in data.get('layers',[]) if isinstance(l,dict)] if isinstance(data.get('layers',[]),list) else []
                excluded(path,data.get('name',path.stem),data.get('status','unknown'),exc,refs+[data.get('intent','?')])
                continue
            if r['name'] in result:print('Recipe override: '+r['name']+' from '+str(path),file=sys.stderr)
            result[r['name']]=r
    return {k:v for k,v in result.items() if experimental or v['status']=='stable'}


def expand(plan, beats, experimental=False):
    result=deepcopy(plan);expanded=[];records=[]
    recipes=load_recipes(experimental=experimental)
    for event in result.get('effects',[]):
        if 'recipe' not in event:
            event=dict(event)
            if 'perceived' in event:
                from fx_calibrate import control
                target=event.pop('perceived');name=event['name'];knob=control(name)
                if knob=='mix':raise ValueError('cutout_card is not addressable via perceived; use native parameters or an explicitly authored recipe mix')
                mode='nearest' if 'nearest' in (event.get('sampling'),result.get('sampling')) else 'linear'
                event[knob]=inverse(name,target,sampling=mode)
            expanded.append(event);continue
        if set(event)-{'recipe','at_beat','at_ms','perceived','review'}:raise ValueError('Unknown recipe event field')
        name=event['recipe']
        if name not in recipes:raise ValueError('Unknown or experimental recipe: '+name+'; use --experimental for review')
        r=recipes[name]
        if 'at_beat' in event:
            index=event['at_beat']
            if type(index) is not int or not 0<=index<len(beats):raise ValueError('Recipe beat out of range')
            at=beats[index]
        else:at=event.get('at_ms',0)
        target=event.get('perceived',r['perceived_target'])
        if not math.isfinite(at) or at<0 or not math.isfinite(target) or not 0<=target<=1:raise ValueError('Invalid recipe time/intensity')
        factor=target/r['perceived_target']
        event_id=f'{name}@{at}:{len(records)}'
        for layer in r['layers']:
            if layer['kind']!='effect':raise ValueError('Transition recipe layers require a scene boundary; use candidates API')
            start=at+layer['offset_ms'];params=deepcopy(layer['params'])
            knob=layer.get('control','amount')
            points=[[start+t,v*factor] for t,v in layer['envelope']]
            if knob=='mix':
                # Plan metadata carries compositing without changing cutout's API.
                params['director_mix']={'keyframes':points}
            else:params[knob]={'keyframes':points}
            expanded.append(dict(name=layer['ref'],start_ms=start,end_ms=start+layer['duration_ms'],recipe_name=name,recipe_event_id=event_id,**params))
        records.append(dict(recipe=name,event_id=event_id,at_ms=at,perceived=target,sfx=r['sfx'],sfx_at_ms=at+r.get('peak_ms',0),sfx_anchor=r.get('sfx_anchor','measured_peak'),gate=r['gate']))
        if r.get('sfx_anchor')=='onset':records[-1]['sfx_at_ms']=at+min(l['offset_ms'] for l in r['layers'])
    result['effects']=expanded
    if records:
        result['recipe_events']=records
        if any(r['sfx'] for r in records):result.setdefault('sfx','auto')
    return result


def apply_recipe(recipe, frame, elapsed_ms, ctx, perceived=None):
    import numpy as np
    from fx.core import floating,premultiply,straight,restore
    factor=(recipe['perceived_target'] if perceived is None else perceived)/recipe['perceived_target']
    result=frame
    for layer in recipe['layers']:
        t=elapsed_ms-layer['offset_ms']
        if not 0<=t<layer['duration_ms']:continue
        points=layer['envelope'];strength=float(np.interp(t,[p[0] for p in points],[p[1] for p in points]))*factor
        params=dict(layer['params']);knob=layer.get('control','amount')
        if knob!='mix':params[knob]=strength
        output=EFFECTS[layer['ref']]['function'](result,elapsed_ms,ctx,**params)
        if knob=='mix':
            output=restore(straight(premultiply(floating(result))*(1-strength)+premultiply(floating(output))*strength),result.dtype)
        result=output
    return result
