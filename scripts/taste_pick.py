"""Persist only the user's choices, with bounded U-class steps and P-USER agreement."""
import argparse
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import shutil
import sys
import warnings
import numpy as np
from taste_common import ROOT, read, write, value


def factory():
    return dict(version=1,axis='user_taste',threshold_class='U',defaults=dict(density=1.,color=1.,flashiness=1.,caption_scale=1.,caption_style='clean',transition_family='dissolve'),
                weights=[.35,.25,.30,.10],choices=[],history=[],family_votes={},item_preferences={},agreement=dict(n=0,status='directional'))


def profile_path():
    return Path(os.environ.get('VIDEO_GIF_TASTE',str(ROOT/'references/taste-user.json'))).expanduser()


def load(path=None):
    path=Path(path) if path else profile_path()
    if not path.exists():return factory()
    try:
        data=read(path)
        if data.get('version')!=1 or data.get('threshold_class')!='U' or not isinstance(data.get('choices'),list) or not {'defaults','history','family_votes','item_preferences'}<=set(data):raise ValueError('missing profile fields')
        for key in ('density','color','flashiness','caption_scale'):
            if not np.isfinite(data['defaults'][key]) or data['defaults'][key]<=0:raise ValueError('invalid profile value')
        weights=np.asarray(data.setdefault('weights',[.35,.25,.30,.10]),float)
        if weights.shape!=(4,) or not np.isfinite(weights).all() or np.any(weights<0) or weights.sum()<=0:raise ValueError('invalid profile weights')
        # Validate supplied weights without rewriting them. Consumers
        # normalize weights when measuring; even unit sums can drift in float.
        return data
    except (OSError,ValueError,KeyError,TypeError) as exc:
        warnings.warn('Invalid taste profile; using factory defaults and preserving original: '+str(exc))
        return factory()


def agreement(choices):
    pairs=[c for c in choices if c.get('judge') in ('A','B') and not c.get('control_negative')]
    n=len(pairs);k=sum(c.get('choice')==c['judge'] for c in pairs)
    if not n:return dict(n=0,matches=0,rate=None,wilson_lower=None,status='directional',reason='No comparable non-tie judge votes')
    p=k/n;z=value('taste.profile.wilson.z');lower=(p+z*z/(2*n)-z*np.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)
    status='valid' if lower>=value('taste.profile.wilson.min') else 'invalid' if p<.5 else 'directional'
    return dict(n=n,matches=k,rate=p,wilson_lower=float(lower),status=status,axis='appeal only; cannot delete effects')


def ingest(profile, choices, context='default'):
    if context!='default':
        result=deepcopy(profile);sub=result.get('contexts',{}).get(context,factory())
        result.setdefault('contexts',{})[context]=ingest(sub,choices)
        for c in result['contexts'][context]['choices']:c['context']=context
        return result
    result=deepcopy(profile); seen={c['id'] for c in result['choices']};step=value('taste.profile.step.max')
    for choice in choices:
        if choice.get('choice') not in ('A','B','tie') or not choice.get('id') or not choice.get('date') or not choice.get('source'):
            raise ValueError('Choice requires id, date, source and choice A/B/tie')
        if choice['id'] in seen:continue
        seen.add(choice['id']);before=deepcopy(result['defaults']);dimension=choice.get('dimension')
        if choice['choice']!='tie':
            option=choice.get('options',{}).get(choice['choice'],{})
            if dimension in ('density','color','flashiness','caption_scale') and dimension in option:
                target=float(option[dimension]);old=before[dimension]
                if not np.isfinite(target) or target<=0:raise ValueError('Preference targets must be finite and positive')
                result['defaults'][dimension]=float(np.clip(target,old*(1-step),old*(1+step)))
            if dimension=='transition_family' and option.get('transition_family'):
                family=option['transition_family'];votes=result['family_votes'];votes[family]=votes.get(family,0)+1
                if votes[family]>=2:result['defaults']['transition_family']=family
            if dimension=='caption_style' and option.get('caption_style'):
                style=option['caption_style'];votes=result['family_votes'];ident='caption:'+style;votes[ident]=votes.get(ident,0)+1
                if votes[ident]>=2:result['defaults']['caption_style']=style
            if choice.get('item'):
                candidate=choice.get('candidate','A');result['item_preferences'][choice['item']]=1 if choice['choice']==candidate else -1
        result['choices'].append(dict(choice,context=context))
        result['history'].append(dict(id=choice['id'],date=choice['date'],before=before,after=deepcopy(result['defaults']),trigger='user_choice',approved_by='user',max_relative_step=step))
    result['agreement']=agreement(result['choices'])
    result['gate_updates']=False
    result['note']='User choices adjust recommendations only; technical acceptance is unchanged.'
    return result


def spotcheck(answers, key):
    result=[];translate={'左':'A','右':'B','一樣':'tie'}
    from taste_lint import transition_family
    cards=read(ROOT/'references/fx-cards.json')
    for row in key:
        raw=answers['answers'].get(str(row['n']))
        if raw not in translate:continue
        candidate='A' if row['candidate_side']=='left' else 'B'; role=row['role']
        judge=(candidate if role=='gate: stable' else ('B' if candidate=='A' else 'A') if role=='gate: delete' else 'tie')
        name=next((k.split(':',1)[1] for k in cards if k.startswith('transition:') and row['id'].startswith(k.replace(':','_')+'_')),None)
        options={candidate:{'transition_family':transition_family(name)}} if name else {}
        result.append(dict(id='spotcheck-1-'+str(row['n']),date=answers['date'],source='wow/fx/gate/spotcheck-1-answers.json',
                           item=row['id'],dimension='transition_family',choice=translate[raw],raw_answer=raw,candidate=candidate,judge=judge,
                           control_negative='control-broken' in role,control='control-' in role,options=options))
    # Do not invent density or color votes from a transition comparison.
    return result


def persist(path,data):
    path=Path(path)
    if path.exists():
        try:old=read(path);valid=old.get('version')==1 and 'defaults' in old and 'choices' in old
        except (ValueError,TypeError):valid=False
        if not valid:
            shutil.copy2(path,path.with_suffix(path.suffix+'.bak'))
            recovery=path.with_suffix(path.suffix+'.recovered.json');write(recovery,data)
            warnings.warn('Corrupt original retained; recovered profile saved to '+str(recovery));return recovery
    write(path,data);return path


def prepare_pairs(pairs,out):
    """Package user-supplied moving comparisons, keeping control keys off the page."""
    import html
    from taste_common import probe
    if len(pairs)<value('taste.profile.pairs.min'):raise ValueError('P-USER requires at least eight moving pairs')
    roles={p.get('role') for p in pairs}
    if not {'positive_control','negative_control'}<=roles:raise ValueError('Include one hidden positive and negative control')
    ids=set();public=[];blocks=[]
    for pair in pairs:
        if pair.get('dimension') not in ('density','color','caption_scale','caption_style','transition_family','flashiness'):raise ValueError('Each pair must declare one supported taste dimension')
        if not pair.get('id') or pair['id'] in ids:raise ValueError('Unique pair IDs required')
        ids.add(pair['id']);clips={}
        for side in ('A','B'):
            clip=Path(pair[side]).resolve();probe(clip);clips[side]=str(clip)
        public.append(dict(id=pair['id'],**clips,question='Would you use this today, or adjust it?',choice=None))
        blocks.append('<section><h2>'+html.escape(str(len(public)))+'</h2>'+''.join('<label>'+side+'<video controls loop preload="metadata" src="'+html.escape(Path(clips[side]).as_uri(),quote=True)+'"></video></label>' for side in ('A','B'))+'<p>Keep A / replace with B / either</p></section>')
    out=Path(out)
    if out.exists():raise ValueError('Use a new pair output directory')
    write(out/'pairs.json',public);write(out/'private-key.json',pairs)
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Your taste choices</title><style>body{background:#131b25;color:#fff;font:18px sans-serif;margin:32px}section{margin:36px 0}video{width:42%;vertical-align:middle;margin:8px}label{display:inline}</style><h1>Would you use this today, or adjust it?</h1>'+''.join(blocks),encoding='utf-8')
    return public


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['show','reset','ingest','spotcheck','prepare']);p.add_argument('--out',type=Path,default=profile_path())
    p.add_argument('--choices',type=Path);p.add_argument('--context',default='default');p.add_argument('--answers',type=Path,default=ROOT/'wow/fx/gate/spotcheck-1-answers.json');p.add_argument('--key',type=Path,default=ROOT/'wow/fx/gate/spotcheck-1-key.json')
    a=p.parse_args(argv)
    try:
        if a.command=='prepare':prepare_pairs(read(a.choices),a.out);return 0
        if a.command=='show':print(__import__('json').dumps(load(a.out),ensure_ascii=False,indent=2));return 0
        if a.command=='reset':data=factory()
        else:data=ingest(load(a.out),spotcheck(read(a.answers),read(a.key)) if a.command=='spotcheck' else read(a.choices),a.context)
        print(persist(a.out,data));return 0
    except (ValueError,OSError,TypeError,KeyError) as exc:print('taste_pick: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
