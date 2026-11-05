"""Shared runtime threshold values. Pending calibration never affects this round.

Uncalibrated C instruments return UNKNOWN, never a quality verdict. Positive and
negative controls are anchors with the corresponding roles (the §5 JSON schema).
"""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re

DEFAULT_PATH = Path(__file__).resolve().parents[1]/'references/thresholds.json'
REQUIRED = {'id','value','class','unit','measures','direction','provenance','history','anchors'}
FIELDS = REQUIRED | {'instrument','scope','bounds','max_step','margin','status'}
ROLES = {'best','benchmark','known_worse','positive_control','negative_control','style_control'}


def finite(value):
    if isinstance(value, dict): return bool(value) and all(finite(v) for v in value.values())
    if isinstance(value, list): return bool(value) and all(finite(v) for v in value)
    return type(value) in (int,float) and math.isfinite(value)


def validate(data):
    if type(data.get('version')) is not int or not isinstance(data.get('thresholds'),list):
        raise ValueError('threshold registry requires version and thresholds')
    ids=set()
    for entry in data['thresholds']:
        ident=entry.get('id','<missing>')
        if REQUIRED-set(entry) or set(entry)-FIELDS:
            raise ValueError(f'{ident}: missing or unknown registry fields')
        if not re.fullmatch(r'[a-z0-9_.-]+',ident) or ident in ids:
            raise ValueError(f'{ident}: invalid or duplicate threshold id')
        ids.add(ident)
        if not all(isinstance(entry[k],str) and entry[k] for k in ('unit','measures')):
            raise ValueError(f'{ident}: nonempty unit and measures required')
        if entry['class'] not in ('F','R','C','U') or not finite(entry['value']):
            raise ValueError(f'{ident}: invalid class or non-finite value')
        if entry['direction'] not in ('min','max','range','equal'):
            raise ValueError(f'{ident}: invalid direction')
        values=entry['value'].values() if isinstance(entry['value'],dict) else [entry['value']]
        for v in values:
            if entry['direction']=='range' and (not isinstance(v,list) or len(v)!=2 or v[0]>v[1]):
                raise ValueError(f'{ident}: range requires [min,max]')
            if entry['direction'] in ('min','max','equal') and not isinstance(v,(int,float)):
                raise ValueError(f'{ident}: scalar boundary required')
        if entry.get('status','active') not in ('active','calibrate_first','instrument_invalid','frozen'):
            raise ValueError(f'{ident}: invalid status')
        provenance=entry['provenance']
        if provenance.get('source_class') not in ('EXT','PHYS','ANCHOR','GUESS') or not provenance.get('ref'):
            raise ValueError(f'{ident}: provenance required')
        if provenance.get('agent_invented') and entry['class']=='F' and entry.get('status')!='calibrate_first':
            raise ValueError(f'{ident}: invented values cannot be active fixed standards')
        anchors=entry['anchors'];seen=set()
        for a in anchors:
            if not {'id','path','role','expected'}<=set(a) or a['role'] not in ROLES or a['expected'] not in ('pass','fail','tie') or a['id'] in seen:
                raise ValueError(f'{ident}: invalid anchor')
            seen.add(a['id'])
            if not isinstance(a['id'],str) or not isinstance(a['path'],str) or not a['path']:
                raise ValueError(f'{ident}: anchor id/path must be strings')
            if 'held_out' in a and type(a['held_out']) is not bool:
                raise ValueError(f'{ident}: held_out must be boolean')
            if 'label_source' in a and a['label_source'] not in ('standard','fixture','review','panel','user'):
                raise ValueError(f'{ident}: invalid anchor label source')
        if entry['class']=='C' and not {'positive_control','negative_control'}<={a['role'] for a in anchors}:
            raise ValueError(f'{ident}: C requires positive and negative controls')
        if 'bounds' in entry and (len(entry['bounds'])!=2 or not finite(entry['bounds']) or entry['bounds'][0]>entry['bounds'][1]):
            raise ValueError(f'{ident}: invalid hard bounds')
        if not isinstance(entry['history'],list): raise ValueError(f'{ident}: history must be an array')
        for h in entry['history']:
            if not {'date','from','to','trigger','approved_by','anchor_decisions'}<=set(h):
                raise ValueError(f'{ident}: incomplete audit history')
        if 'max_step' in entry and (not finite(entry['max_step']) or not 0<entry['max_step']<=1):
            raise ValueError(f'{ident}: max_step must be in (0,1]')
    return data


def load(path=DEFAULT_PATH):
    return validate(json.loads(Path(path).read_text(encoding='utf-8')))


@lru_cache(maxsize=8)
def _cached(path, stamp):
    return load(path)


def registry(path=DEFAULT_PATH):
    path=Path(path).resolve()
    return _cached(str(path),path.stat().st_mtime_ns)


def entry(ident, data=None):
    return next((x for x in (registry() if data is None else data)['thresholds'] if x['id']==ident), None) or _missing(ident)


def _missing(ident): raise ValueError('Unknown threshold: '+ident)


def value(ident, context='default', data=None):
    result=entry(ident,data)['value']
    if isinstance(result,dict): result=result.get(context,result.get('default'))
    if result is None: raise ValueError(f'{ident}: no threshold for context {context}')
    return deepcopy(result)


def default_value(ident, context='default', data=None):
    """A <5-choice U update changes defaults, never the gate boundary."""
    data=registry() if data is None else data
    result=data.get('defaults',{}).get(ident,value(ident,context,data))
    if isinstance(result,dict):result=result.get(context,result.get('default',value(ident,context,data)))
    return deepcopy(result)


def passes(measurement, boundary, direction):
    if not finite(measurement): raise ValueError('Threshold measurement must be finite')
    if direction=='min': return measurement>=boundary
    if direction=='max': return measurement<=boundary
    if direction=='range': return boundary[0]<=measurement<=boundary[1]
    return measurement==boundary


def check(ident, measurement, context='default', data=None, intent=None):
    if not finite(measurement): raise ValueError('Threshold measurement must be finite')
    e=entry(ident,data);boundary=value(ident,context,data)
    exempt=ident.startswith('visibility.') and intent=='texture'
    valid=e.get('status','active')=='active' and not exempt
    return dict(id=ident,value=boundary,measurement=measurement,unit=e['unit'],
        status=e.get('status','active'),context=context,
        decision=('pass' if passes(measurement,boundary,e['direction']) else 'fail') if valid else 'unknown',
        reason='texture intent exemption' if exempt else e['provenance']['ref'])


def snapshot(data=None):
    data=registry() if data is None else data
    return dict(version=data['version'],round=data.get('round',0),
        sha256=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),
        values={e['id']:e['value'] for e in data['thresholds']})


def check_metrics(metrics, context='default', data=None, intent=None):
    """Runtime/QA adapter for measured event, budget, memory and camera channels."""
    return [check(ident,measurement,context,data,intent) for ident,measurement in metrics.items()]
