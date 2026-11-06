"""Run saved exact two-pass judge inputs on a working subscription CLI.

python tests/s13_r4_judge_replay.py --inputs .scratch/judge-inputs --state .scratch/r4-live-state
Use --case spHipsClean-designed for one case. No generation or paid fallback.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from image_hole_judge import SubscriptionHoleJudge,validate
from image_route import Adapter
from image_common import read,write


def replay(case,judge):
 observations=[];errors=[]
 for path in case['inputs']:
  manifest=read(path);regions=manifest['regions']
  try:
   answer=validate(judge(manifest['full_view'],regions),regions)
   observations.append({r['label']:answer[r['id']]['classification'] for r in regions})
  except Exception as exc:
   errors.append(str(exc));observations.append({})
 labels=range(1,case['regions']+1);merged={}
 for label in labels:
  values=[r.get(label,'uncertain') for r in observations]
  merged[label]=values[0] if len(values)==2 and values[0]==values[1] else 'uncertain'
 status='needs_review' if errors or 'uncertain' in merged.values() else 'FAIL' if case['other_issues'] or 'body_hole' in merged.values() else 'PASS'
 injected=set(case['injected_region_ids'])
 return dict(name=case['name'],status=status,errors=errors,merged=merged,
  injected=bool(injected),detected=any(merged[i]=='body_hole' for i in injected),
  designed_regions=len(merged)-len(injected),
  designed_false_alarm=sum(v=='body_hole' and i not in injected for i,v in merged.items()))


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--state',type=Path,required=True);parser.add_argument('--codex');parser.add_argument('--case');parser.add_argument('--timeout',type=float,default=300)
 args=parser.parse_args();index=read(args.inputs/'alpha.json');rows=[]
 judge=SubscriptionHoleJudge(Adapter(args.state,codex=args.codex,timeout=args.timeout,round_id='s13-r4-replay'))
 for case in index['injections']+index['designed_controls']:
  if args.case and case['name']!=args.case:continue
  rows.append(replay(case,judge));write(args.inputs/'live-results.partial.json',rows);print(rows[-1]['name'],rows[-1]['status'],flush=True)
 injected=[r for r in rows if r['injected']];controls=[r for r in rows if not r['injected']]
 result=dict(rows=rows,completed_cases=len(rows),recall=sum(r['detected'] for r in injected)/len(injected) if injected else None,
  false_pass=sum(r['status']=='PASS' for r in injected),unassessed=sum(r['status']=='needs_review' for r in rows),
  designed_gap_false_alarm=sum(r['designed_false_alarm'] for r in controls),designed_gap_denominator=sum(r['designed_regions'] for r in controls))
 write(args.inputs/'live-results.json',result)
