"""Render 2–3 recipe proxies at a key moment on the supplied timeline."""
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image
from fx_render import validate_plan
from fx_recipes import load_recipes
from fx_director import query,recipe_cards
from fx_previews import render_preview
from fx_catalog import output_root,write_html


def build(plan_path,moment='drop',out=None,needs=(),experimental=False,choose=None,reason=None):
    if choose is not None and (type(choose) is not int or not 1<=choose<=3 or not reason or not reason.strip()):
        raise ValueError('--choose needs an index from 1 to 3 and --reason')
    path=Path(plan_path).resolve();original=json.loads(path.read_text(encoding='utf-8-sig'))
    plan,items,segments,ctx,_,_=validate_plan(path,('mp4',),experimental,proxy=True)
    sections=plan.get('sections',[])
    if not sections and plan.get('beatmap'):
        sections=json.loads((path.parent/plan['beatmap']).read_text(encoding='utf-8')).get('sections',[])
    at=0 if moment=='hook' else next((s['start_ms'] for s in sections if s.get('name',s.get('label'))==moment),None)
    if at is None:raise ValueError('Unknown key moment '+moment)
    candidates=[c for c in query('hit' if moment=='hook' else 'drop',needs,section=moment,experimental=experimental) if c['kind']=='recipe']
    if len(candidates)<2:
        candidates=[c for c in query('hit',needs,section=moment,experimental=experimental) if c['kind']=='recipe']
    candidates=candidates[:3]
    if len(candidates)<2:raise ValueError('Fewer than two eligible recipes; pending recipes require --experimental')
    ident=hashlib.sha256(path.read_bytes()+moment.encode()).hexdigest()[:16]
    out=Path(out or output_root()/('candidates-'+ident));out.mkdir(parents=True,exist_ok=True)
    start=max(0,at-1000);duration=min(4000,sum(d for _,d in items)-start)
    if duration<=0:raise ValueError('Moment outside timeline')
    scale=min(1,540/min(ctx.width,ctx.height));w=max(2,round(ctx.width*scale/2)*2);h=max(2,round(ctx.height*scale/2)*2)
    edges=np.cumsum([0]+[d for _,d in items]).tolist();cache={}
    def source(i):
        t=min(start+i*1000/30,edges[-1]-1)
        index=max(0,bisect.bisect_right(edges,t)-1);file=items[index][0]
        if str(file) not in cache:
            cache.clear()
            with Image.open(file) as im:cache[str(file)]=np.asarray(im.convert('RGBA').resize((w,h)))
        return cache[str(file)].copy()
    recipes=load_recipes(experimental=experimental);results=[]
    for c in candidates:
        report=render_preview(c['name'],'recipe',out,w,h,recipes[c['name']],source,duration/1000,at-start)
        report['cost_ms_per_frame@720p']=c['cost_ms_per_frame@720p'];results.append(report)
    cards=[dict(c,preview=r['preview']) for c,r in zip(candidates,results)]
    write_html(cards,out/'index.html','Choose the key moment')
    record=dict(id=ident,moment=moment,at_ms=at,window_ms=[start,start+duration],candidates=results,
                limitations='Proxy samples the resolved source timeline; existing effects/transitions are not baked into alternatives.')
    if choose is not None:
        if not reason or not reason.strip() or not 1<=choose<=len(results):raise ValueError('--choose needs a valid 1-based index and --reason')
        selected=results[choose-1]['name'];record['selection']={'recipe':selected,'reason':reason}
        original.setdefault('director_choices',[]).append(dict(candidate_set=ident,moment=moment,recipe=selected,reason=reason))
        original.setdefault('effects',[]).append(dict(recipe=selected,at_ms=at))
        if recipes[selected]['status']=='experimental':original['experimental']=True
        # Write a reviewable derivative; never overwrite the user's source plan.
        for segment in original['segments']:
            for key in ('image','manifest'):
                if key in segment:segment[key]=str((path.parent/segment[key]).resolve())
        if 'beatmap' in original:original['beatmap']=str((path.parent/original['beatmap']).resolve())
        for key in ('music','source_audio'):
            if isinstance(original.get(key),dict) and 'file' in original[key]:original[key]['file']=str((path.parent/original[key]['file']).resolve())
        (out/'selected-plan.json').write_text(json.dumps(original,indent=2)+'\n',encoding='utf-8')
    (out/'candidates.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return record


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan',type=Path);ap.add_argument('--moment',default='drop')
    ap.add_argument('--out',type=Path);ap.add_argument('--needs',nargs='*',default=[]);ap.add_argument('--experimental',action='store_true')
    ap.add_argument('--choose',type=int);ap.add_argument('--reason')
    a=ap.parse_args(argv)
    try:
        report=build(a.plan,a.moment,a.out,a.needs,a.experimental,a.choose,a.reason)
        print(json.dumps({'id':report['id'],'candidates':len(report['candidates'])}));return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
        print('fx_candidates: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
