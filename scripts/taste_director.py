"""Opt-in offline treatment builder; legacy plans/rendering never load taste implicitly."""
import argparse
from pathlib import Path
import sys
import re
import numpy as np
from taste_common import read,write,curve_points
from taste_pick import load
from taste_target import plan_timing
from taste_lint import default_tokens,transition_family
from storyboard import lint,shot_table


def brief_curve(core,duration,music=None,brief=None):
    """Authored curve/intent wins; keywords are only a legacy brief fallback."""
    brief=brief or {}
    if brief.get('design_curve') is not None:
        return curve_points(brief['design_curve']).tolist(),'explicit design curve from brief'
    intent=brief.get('design_curve_intent','').strip().lower()
    if intent:
        if intent in ('build','rise','crescendo'):return [[0,.2],[duration,.8]],'rise explicitly requested by brief field'
        if intent in ('calm','level','flat','ambient','sustained'):return [[0,.4],[duration,.4]],'level intensity requested by brief'
        if intent in ('settle','fall','release'):return [[0,.7],[duration,.2]],'settling arc explicitly requested by brief field'
        raise ValueError('Unknown brief design_curve_intent: '+intent)
    text=core.lower()
    # "Build a calm ambience" creates a scene, not an intensity crescendo.
    text=re.sub(r'\bbuild\s+(?:a|an|the)\s+(?=[^.]*\b(?:ambience|ambiance|atmosphere|ambient|meditation)\b)', 'create ', text)
    if re.search(r'\b(build|crescendo|rising)\b',text) or '漸強' in text:
        return [[0,.2],[duration,.8]],'rise explicitly requested by brief'
    if any(word in text for word in ('asmr','meditation','calm','ambient','flat','stillness','meditative','平靜','平坦','安靜','放鬆','冥想','療癒')):
        return [[0,.4],[duration,.4]],'level intensity requested by brief'
    sections=(music or {}).get('sections',[])
    if sections:
        points=[]
        for s in sections:
            t=float(s.get('start',s.get('start_ms',0)/1000))
            if t<duration:points.append([t,float(np.clip(s.get('energy',.5),0,1))])
        points=sorted(dict(points).items())
        if points:
            if points[0][0]>0:points.insert(0,(0,points[0][1]))
            return [list(p) for p in points]+[[duration,points[-1][1]]],'declared/analyzed music section energy'
    if any(word in text for word in ('settle','fade away','減弱')):
        return [[0,.7],[duration,.2]],'settling arc explicitly requested by brief'
    return [[0,.5],[duration,.5]],'level provisional intent; supply music sections or author a design curve'


def treatment(images,duration,core,profile=None,target=None,music=None,brief=None):
    if not images:raise ValueError('Supply at least one user-owned image/footage source')
    profile=profile or load();defaults=profile['defaults']
    from brief_structure import structure,stable_choices,recipe_camera
    editorial=stable_choices(structure(core,brief,profile,target))
    neutral_legacy=brief is None and editorial['profile']=='graphic'
    if neutral_legacy:
        # Preserve the calibrated neutral preview when the caller supplied no
        # aesthetic/pace at all. Expressive briefs and expanded briefs use the
        # new grammar; reference-stat-only callers retain their proven cut readout.
        editorial.update(asl=2.,cv=.5,sizes=['WS','MS','CU'],moves=['static'],recipes=['impact'])
    calibration=target or {};target=calibration.get('target',target) or {k:editorial[k] for k in ('asl','cv')}
    curve,origin=brief_curve(core,duration,music,brief)
    timing=plan_timing(duration,target);shots=[];cursor=0.;density=defaults['density']
    from fx import TRANSITIONS
    scores={name:max([score for item,score in profile.get('item_preferences',{}).items()
                     if item in (name,'transition:'+name) or item.startswith('transition_'+name+'_')],default=0) for name in TRANSITIONS}
    preferred_names=sorted((name for name,score in scores.items() if score>0),key=lambda name:(-scores[name],name))
    cards=read(Path(__file__).resolve().parents[1]/'references/fx-cards.json')
    eligible=[name for name in preferred_names if TRANSITIONS[name]['status']=='stable']
    if editorial['profile'] in ('kinetic','fresh','precision','warm'):
        # Rank user favourites inside the requested editorial family. A global
        # spot-check preference is not a command to make every genre identical.
        eligible=[name for name in eligible if transition_family(name)==editorial['family']]
    family_choices=sorted(name for name,card in TRANSITIONS.items() if card['status']=='stable' and scores[name]>=0 and cards.get('transition:'+name,{}).get('family')==defaults['transition_family'])
    transition=(eligible or (family_choices if neutral_legacy else editorial['transitions']) or ['crossfade'])[0]
    tokens=default_tokens(profile=profile)
    tokens['transitions']['primary']=transition_family(transition)
    count=len(timing['durations']);event_count=max(1,round(count*.3*density))
    ambient=origin=='level intensity requested by brief' or (origin=='explicit design curve from brief' and np.ptp(np.asarray(curve)[:,1])<.02)
    if ambient:event_count=0
    # Spread optional accents across the design; never silently stack them at
    # the end of a level brief. Musical high-energy sections take priority.
    starts=np.r_[0,np.cumsum(timing['durations'])[:-1]]
    energies=np.interp(starts+np.asarray(timing['durations'])/2,*np.asarray(curve).T)
    order=sorted(range(count),key=lambda i:(-energies[i],i)) if np.ptp(energies)>.02 else np.linspace(0,count-1,min(count,event_count),dtype=int).tolist()
    accented=set(order[:event_count])
    for i,duration_s in enumerate(timing['durations']):
        duration_s=round(duration_s*100)/100
        if i==count-1:duration_s=round((duration-cursor)*100)/100
        energy=float(np.interp(cursor+duration_s/2,*np.asarray(curve).T))
        shot=dict(id=f'shot-{i+1}',start=round(cursor,3),end=round(cursor+duration_s,3),size=editorial['sizes'][i%len(editorial['sizes'])],angle=(i%3)*35,
                  lens='standard',motion='static',composition='subject on thirds',direction='neutral',axis='main',lighting='preserve supplied material',
                  color_script='user palette',image=str(Path(images[i%len(images)]).resolve()),action='Show the supplied subject',subject='subject',
                  intent='hold' if np.ptp(np.asarray(curve)[:,1])<.02 else 'follow design',sound=dict(section=f'part-{i+1}',energy=energy),why='Reveal the next detail of the core concept',
                  serves_core='Make the supplied subject and its next detail readable',transition=transition if i else 'cut')
        if i in accented:
            name=editorial['recipes'][i%len(editorial['recipes'])]
            strength=min(.7,energy*.5*defaults['flashiness']) if neutral_legacy else min(.15,energy*.2*defaults['flashiness'])
            shot['recipe']=dict(name=name,perceived=strength,serves_core='Underline the newly revealed detail')
        if not shot.get('recipe') or not recipe_camera(shot['recipe']['name']):
            shot['motion']=editorial['moves'][i%len(editorial['moves'])]
        shots.append(shot);cursor+=duration_s
    board=dict(core=core,fps=30,shots=shots,tokens=tokens,design_curve=curve,design_origin=origin,weights=profile.get('weights',[.35,.25,.30,.10]),
               taste_applied=dict(defaults=defaults,note='According to your taste profile; only recommendations change',choices=len(profile['choices'])),
               target_timing=timing,editorial_structure=editorial)
    board['target_warnings']=[]
    if brief is not None:board['brief']=brief
    if ambient:board['style']='ambient'
    if calibration.get('weights') and not np.allclose(calibration['weights'],board['weights']):
        board['target_warnings'].append('Mismatched reference/user weights; timing can be reused, intensity cannot be compared directly.')
    return board


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('images',type=Path,nargs='+');p.add_argument('--duration',type=float,required=True);p.add_argument('--core',required=True)
    p.add_argument('--profile',type=Path,help='User profile; defaults to VIDEO_GIF_TASTE or references/taste-user.json');p.add_argument('--target',type=Path);p.add_argument('--music',type=Path,help='Music analysis JSON with sections and energy');p.add_argument('--brief',type=Path,help='Director brief JSON: design_curve or design_curve_intent (build, calm, settle)');p.add_argument('--out',type=Path,required=True);a=p.parse_args(argv)
    try:
        b=treatment(a.images,a.duration,a.core,load(a.profile),read(a.target) if a.target else None,read(a.music) if a.music else None,read(a.brief) if a.brief else None)
        write(a.out/'storyboard.json',b);write(a.out/'treatment.json',dict(core=a.core,design_curve=b['design_curve'],taste_applied=b['taste_applied']))
        write(a.out/'tokens.json',b['tokens']);write(a.out/'lint.json',lint(b));(a.out/'storyboard.md').write_text(shot_table(b),encoding='utf-8');return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:print('taste_director: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
