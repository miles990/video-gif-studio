"""Serially recheck existing decoded evidence after the flash-window repair."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import cv2
from fx_check import check_video
from fx_catalog import output_root
from fix_s6_evidence import summarize_legacy,summarize_recipes


def write(path,data):
    Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def run(legacy,recipes):
    cv2.setNumThreads(1);root=output_root();checks=[]
    cards=json.loads((root/'catalog.json').read_text(encoding='utf-8'))
    for card in cards:
        stem=card['kind']+'-'+card['name'];path=root/(stem+'.json')
        report=json.loads(path.read_text(encoding='utf-8'));before=report['wcag']['max_flashes_per_s']
        wcag=check_video(root/card['preview']['video'],fps=30)['wcag'];report['wcag']=wcag
        for event in report['events']:
            v=event['visibility'];v['wcag_flashes_max_per_s']=wcag['max_flashes_per_s']
            if v['status']=='harsh' and wcag['status']=='ok':
                v['status']='unknown';v['advice']='Visibility unknown: independent family anchors and 2AFC calibration pending.'
        write(path,report)
        checks.append(dict(item=stem,before=before,after=wcag['max_flashes_per_s'],scope='catalog'))
    preview_record=json.loads((ROOT/'wow/fx/s6-fix-previews.json').read_text(encoding='utf-8'))
    preview_record['reports']=[json.loads((root/(r['kind']+'-'+r['name']+'.json')).read_text(encoding='utf-8')) for r in preview_record['reports']]
    write(ROOT/'wow/fx/s6-fix-previews.json',preview_record)
    summary=json.loads((ROOT/'wow/fx/s6-fix-catalog.json').read_text(encoding='utf-8'))
    for item in summary['checks']:
        item['flashes']=next(c['after'] for c in checks if c['item']==item['kind']+'-'+item['name'])
    summary['wcag_violations']=sum(c['flashes']>3 for c in summary['checks'])
    write(ROOT/'wow/fx/s6-fix-catalog.json',summary)
    for folder in (legacy,recipes):
        path=folder/'gate-auto.json';report=json.loads(path.read_text(encoding='utf-8'))
        for item in report['items']:
            for case in item['cases']:
                movie=folder/item['id'].replace(':','-')/case['clip']
                before=case['wcag']['measurement']['max_flashes_per_s'];wcag=check_video(movie,fps=24)['wcag']
                case['wcag']=dict(level='FAIL' if wcag['status']=='harsh' else 'PASS',measurement=wcag)
                checks.append(dict(item=item['id']+'/'+case['clip'],before=before,after=wcag['max_flashes_per_s'],scope=folder.name))
            print('rechecked '+item['id'],flush=True)
        report['wcag_recheck']=dict(date='2026-11-05',instrument='per-pixel repetitions v2',window='[t,t+1 s)',media_unchanged=True)
        write(path,report)
    summarize_legacy(legacy);summarize_recipes(recipes)
    result=dict(checks=checks,clips=len(checks),violations=sum(c['after']>3 for c in checks),
                note='Spatially staggered completion of one flash is counted once per pixel, then the fixed area threshold is applied. No flash thresholds changed.')
    write(ROOT/'wow/fx/s6-fix-flash-recheck.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='checks'}),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--legacy',type=Path,required=True);ap.add_argument('--recipes',type=Path,required=True)
    args=ap.parse_args();run(args.legacy,args.recipes)
