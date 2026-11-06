"""Pre-registered two-axis before/after harness; never invents human judgments."""
import argparse
from datetime import datetime,timezone
import hashlib
import html
import json
import math
from pathlib import Path
import secrets
import shutil

QUESTION='哪一支你會直接用？'


def canonical(data):return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def sha(data):return hashlib.sha256(canonical(data)).hexdigest()
def write_new(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)


def register(topics,out):
    if not 6<=len(topics)<=10:raise ValueError('Register 6–10 fixed topics')
    if len({t['id'] for t in topics})!=len(topics):raise ValueError('Duplicate topic IDs')
    if sum(bool(t.get('held_out')) for t in topics)<2:raise ValueError('At least two evaluator-supplied held-out topics required')
    if any(not t.get('draft') for t in topics):raise ValueError('Held-out drafts must be supplied before registration')
    data=dict(version=1,benchmark='director-brief-s135',topics=topics,topics_sha256=sha(topics),registered_at=datetime.now(timezone.utc).isoformat(),
              technical=dict(automatic='Both arms must pass decoded defect checks',panel='Expanded arm must not significantly lose defect comparisons'),
              appeal=dict(question=QUESTION,pairs_min=8,controls=['positive_control','negative_control'],decision='User preference Wilson 95% lower bound > 0.5; controls must be valid'),
              fairness=['agent','model','effort','assets_sha256','music_sha256','platform','renderer_sha256'],
              commit_status='pending: builder is explicitly forbidden to commit',status='registered_uncommitted')
    write_new(out,data);return data


def prepare(registration,pairs,out):
    """Pairs come from the same pipeline; raw agent/model/effort receipts mandatory.

    This does not run an agent or claim held-out prompts. Each clip is decoded to
    verify motion. Keys and labels stay in a separate private file.
    """
    if sha(registration['topics'])!=registration['topics_sha256']:raise ValueError('Registered topics changed')
    if len(pairs)<8 or not {'positive_control','negative_control'}<={p.get('role') for p in pairs}:raise ValueError('Need 8 moving pairs including both controls')
    ids={t['id'] for t in registration['topics']}
    if {p['id'] for p in pairs if p.get('role','topic')=='topic'}!=ids:raise ValueError('Every registered topic must be present exactly once')
    if len({p['id'] for p in pairs})!=len(pairs):raise ValueError('Duplicate pair IDs')
    from brief_guard import frames
    out=Path(out)
    if out.exists():raise ValueError('Use a fresh comparison directory; never reblind the same run')
    out.mkdir(parents=True);public=[];key=[]
    for p in pairs:
        if p.get('role','topic')=='topic':
            for field in registration['fairness']:
                if not p.get('context_A',{}).get(field) or p['context_A'][field]!=p.get('context_B',{}).get(field):raise ValueError('Unequal/missing arm context: '+field)
        token=secrets.token_hex(6);swap=bool(secrets.randbits(1));paths={}
        for visible,arm in zip(('left','right'),('B','A') if swap else ('A','B')):
            src=Path(p[arm]);iterator=iter(frames(src));first=next(iterator,None);moving=False
            if first:
                import numpy as np
                moving=any(frame.shape==first[1].shape and np.mean(np.abs(frame.astype(float)-first[1].astype(float)))>.5 for _,frame in iterator)
            if not moving:raise ValueError('Spot-check requires genuinely moving clips: '+str(src))
            if src.suffix.lower() not in ('.mp4','.gif'):raise ValueError('Use MP4 or GIF')
            dest=out/(token+'-'+visible+src.suffix);shutil.copy2(src,dest);paths[visible]=dest.name
        public.append(dict(id=token,**paths));key.append(dict(id=token,topic=p['id'],left_arm='B' if swap else 'A',role=p.get('role','topic'),
                                                        technical=p.get('technical',{}),panel=p.get('panel'),source_hashes={a:hashlib.sha256(Path(p[a]).read_bytes()).hexdigest() for a in ('A','B')}))
    secrets.SystemRandom().shuffle(public)
    markup='<!doctype html><meta charset="utf-8"><title>Moving clip comparison</title><h1>'+QUESTION+'</h1>'
    markup+='<p>Watch both at original speed. Record left, right or tie for each ID.</p>'
    for p in public:
        markup+='<section><h2>'+p['id']+'</h2>'
        for side in ('left','right'):
            filename=html.escape(p[side]);markup+=f'<video controls loop playsinline width="320" src="{filename}"></video>' if filename.endswith('.mp4') else f'<img width="320" src="{filename}">'
        markup+='</section>'
    (out/'review.html').write_text(markup,encoding='utf-8')
    write_new(out/'private-key.json',dict(registration_sha256=sha(registration),registration_status=registration['status'],pairs=key));write_new(out/'pairs.json',public)
    return dict(status='awaiting user and independent technical panel',review=str(out/'review.html'),claim='未證明更好')


def wilson(wins,n):
    if n==0:return [0.,1.]
    z=1.95996398454;p=wins/n;center=(p+z*z/(2*n))/(1+z*z/n);margin=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return [center-margin,center+margin]


def score(key,votes):
    mapping={p['id']:p for p in key['pairs']}
    if len({v['id'] for v in votes})!=len(votes) or any(v['id'] not in mapping for v in votes):raise ValueError('Unknown/duplicate vote ID')
    wins=total=agreement=compared=0;controls={};technical=True
    for vote in votes:
        p=mapping[vote['id']];choice=vote['choice']
        if choice not in ('left','right','tie'):raise ValueError('Choose left, right or tie')
        arm='tie' if choice=='tie' else p['left_arm'] if choice=='left' else ('B' if p['left_arm']=='A' else 'A')
        if p['role']!='topic':controls[p['role']]=arm=='A' if p['role']=='positive_control' else arm=='tie';continue
        total+=1;wins+=arm=='A'
        tech=p.get('technical',{})
        technical &= tech.get('A_auto') is True and tech.get('B_auto') is True and tech.get('panel_no_regression') is True
        if p.get('panel') in ('A','B'):compared+=1;agreement+=arm==p['panel']
    complete=len(votes)==len(mapping);interval=wilson(wins,total)
    proven=key.get('registration_status')=='committed' and complete and all(controls.get(k) for k in ('positive_control','negative_control')) and technical and interval[0]>.5
    return dict(benchmark='director-brief-s135',status='complete' if complete else 'pending',technical_axis='pass' if technical and complete else 'pending_or_failed',
                user_preference_rate=wins/total if total else None,user_wilson95=interval,panel_user_agreement=agreement/compared if compared else None,
                agreement_wilson95=wilson(agreement,compared),controls=controls,claim='擴寫更好' if proven else '未證明更好')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['register','prepare','score']);p.add_argument('input');p.add_argument('--data');p.add_argument('--out',required=True);a=p.parse_args()
    try:
        data=json.loads(Path(a.input).read_text(encoding='utf-8'));other=json.loads(Path(a.data).read_text(encoding='utf-8')) if a.data else None
        if a.command=='register':result=register(data,a.out)
        elif a.command=='prepare':result=prepare(data,other,a.out)
        else:result=score(data,other);write_new(a.out,result)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,OSError,KeyError) as exc:print(json.dumps(dict(ok=False,error=dict(code='E_BENCH',location=a.input,message=str(exc),suggestion='Preserve registration; supply missing receipts or held-out topics'))));return 2


if __name__=='__main__':raise SystemExit(main())
