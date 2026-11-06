"""Editorial structure, shared by the one-line and legacy directors.

Pace vocabulary adapted from blank-page vocabulary.md (MIT; THIRD_PARTY.md).
These are editable editorial defaults, never an aesthetic quality verdict.
"""
from copy import deepcopy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    'calm': dict(asl=6., cv=.12, sizes=['WS','MS','WS'],
                 transitions=['crossfade'], family='dissolve', recipes=['breathe'],
                 moves=['static','drift','static'], aesthetic='mist-veiled natural light', pace='quiet, sustained, gently resolve detail'),
    'kinetic': dict(asl=1.0, cv=.60, sizes=['WS','CU','ECU','MS','CU'],
                    transitions=['gl_burn_through','gl_luminance_melt'], family='energy',
                    recipes=['hook_snap','build','drop','impact'], moves=['static','whip','push'],
                    aesthetic='stadium tungsten hard-light', pace='snappy, accelerate into the payoff'),
    'fresh': dict(asl=2.4, cv=.25, sizes=['WS','MS','CU','WS'],
                  transitions=['crossfade'], family='dissolve', recipes=['breathe','soft_hit','warm_memory'],
                  moves=['drift','static','pull'], aesthetic='Japanese daylight linen', pace='unhurried, breathe between gestures'),
    'precision': dict(asl=3.5, cv=.45, sizes=['ECU','CU','MS','WS'],
                      transitions=['wipe'], family='geometric', recipes=['breathe','hero_glow','outro_settle'],
                      moves=['static','smooth_in','pull'], aesthetic='obsidian macro atelier', pace='measured, linger on the mechanism'),
    'warm': dict(asl=2.5, cv=.35, sizes=['CU','MS','WS','CU'],
                 transitions=['crossfade'], family='dissolve', recipes=['warm_memory','breathe','soft_hit'],
                 moves=['drift','static','pull'], aesthetic='morning-window warm film', pace='gentle, one continuous gesture'),
    'graphic': dict(asl=1.8, cv=.40, sizes=['MS','CU','WS','ECU'],
                    transitions=['wipe'], family='geometric', recipes=['title_pop','build','reveal_subject'],
                    moves=['static','push','pull'], aesthetic='two-ink printed matter', pace='crisp, land each action'),
}


def structure(core, brief=None, profile=None, target=None):
    brief = brief or {}
    authored = ' '.join(str(brief.get(k,'')) for k in ('aesthetic','pace','fence')).lower()
    signals=r'asmr|sleep|meditat|calm|ambient|mist-veiled|睡眠|助眠|冥想|療癒|sport|hype|kinetic|snappy|stadium|運動|熱血|衝擊|快剪|japan|fresh|linen|日系|日式|清新|watch|luxury|precision|atelier|手錶|腕錶|精品|warm|cozy|cafe|coffee|溫暖|咖啡'
    text=authored if re.search(signals,authored) else core.lower()
    if re.search(r'asmr|sleep|meditat|calm|ambient|mist-veiled|睡眠|助眠|冥想|療癒',text):key='calm'
    elif re.search(r'sport|hype|kinetic|snappy|stadium|運動|熱血|衝擊|快剪', text): key='kinetic'
    elif re.search(r'japan|fresh|linen|日系|日式|清新', text): key='fresh'
    elif re.search(r'watch|luxury|precision|atelier|手錶|腕錶|精品', text): key='precision'
    elif re.search(r'warm|cozy|cafe|coffee|溫暖|咖啡', text): key='warm'
    else: key='graphic'
    result=deepcopy(PROFILES[key]); result['profile']=key
    pace=str(brief.get('pace','')).lower()
    if re.search(r'linger|unhurried|gentle|慢|呼吸',pace):result['asl']*=1.15;result['cv']*=.85
    elif re.search(r'rapid|snappy|accelerat|快|加速',pace):result['asl']*=.85;result['cv']=min(.8,result['cv']*1.1)
    defaults=(profile or {}).get('defaults',profile or {})
    density=defaults.get('density',1.)
    if isinstance(density,(int,float)) and density>0: result['asl']/=density
    # Explicit brief editorial fields outrank vocabulary defaults.
    result.update(brief.get('structure',{}))
    target=(target or {}).get('target',target) or {}
    for field in ('asl','cv'):
        if target.get(field) is not None: result[field]=target[field]
    if defaults.get('warm') or defaults.get('color')=='warm':
        result['aesthetic']='morning-window warm film';result['recipes']=['warm_memory','breathe','soft_hit']
    if defaults.get('recipe_family') in ('soft_hit','breathe','warm_memory'):
        result['recipes']=['warm_memory','breathe','soft_hit']
    return result


def stable_choices(design):
    from fx import TRANSITIONS
    from taste_lint import transition_family
    recipes={p.stem:json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'recipes').glob('*.json')}
    result=deepcopy(design)
    result['recipes']=[r for r in result['recipes'] if recipes.get(r,{}).get('status')=='stable']
    selected=[t for t in result['transitions'] if TRANSITIONS.get(t,{}).get('status')=='stable']
    if not selected:
        selected=sorted(t for t,s in TRANSITIONS.items() if s['status']=='stable' and transition_family(t)==result['family'])
    result['transitions']=selected or ['crossfade']
    if not result['recipes']: raise ValueError('No stable recipe for editorial structure')
    return result


def recipe_camera(name):
    data=json.loads((ROOT/'recipes'/f'{name}.json').read_text(encoding='utf-8'))
    return any(layer['ref'] in ('camera_move','zoom_punch','parallax') for layer in data['layers'])
