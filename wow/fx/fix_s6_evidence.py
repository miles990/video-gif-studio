"""Reproduce fix-round previews/labels and summarize existing technical auto checks.

Media stays under VIDEO_GIF_FX_PREVIEWS (persistent user catalog by default).
Only small JSON records and recipe labels are written to this worktree.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import cv2
from fx_catalog import output_root,coverage
from fx.core import catalog


def summarize_legacy(folder):
    from fx_gate_kit import sha
    from fx_calibrate import revision
    source_revision=revision()
    report=json.loads((folder/'gate-auto.json').read_text(encoding='utf-8'));items={}
    for item in report['items']:
        failed=[];warnings=[]
        if item.get('error'):failed.append(item['error'])
        if len(item['cases'])!=4:failed.append('Incomplete two-material/two-aspect matrix')
        for c in item['cases']:
            for key in ('alpha','edges','black','flicker','determinism','endpoints','wcag'):
                if c.get(key,{}).get('level')=='FAIL':failed.append(f'{c["material"]}/{c["size"]}/{key}')
                if c.get(key,{}).get('level')=='WARN':warnings.append(f'{c["material"]}/{c["size"]}/{key}')
        items[item['id']]=dict(status='needs-review' if failed else 'stable',auto_checks='FAIL' if failed else 'PASS',
            record_commit='uncommitted fix-round record',source_revision=source_revision,
            independent_review='pending',failures=failed,advisories=warnings,
            evidence_path='wow/fx/gate/s6-legacy-auto-details.json',media_root=str(folder),
            basis='Inherited status retained only if all mandatory auto checks pass; border WARN is advisory, not a pass/fail check. Independent technical review pending.')
    target=ROOT/'wow/fx/gate'
    (target/'s6-legacy-auto-details.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (target/'s6-legacy-auto.json').write_text(json.dumps(dict(axis='technical',date='2026-11-05',generator='fx_gate_kit --auto-only',
        auto_sha256=sha(folder/'gate-auto.json'),items=items),indent=2)+'\n',encoding='utf-8')


def previews():
    from fx_previews import render_preview
    from fx_recipes import load_recipes
    cv2.setNumThreads(1);root=output_root();root.mkdir(parents=True,exist_ok=True)
    reports=[]
    for name,r in load_recipes(experimental=True).items():
        if name in ('breathe','outro_settle','freeze_card'):
            r['intent']='texture'
            if 'Texture exemption:' not in r['notes']:
                r['notes']+=' Texture exemption: intentionally subtle sustained treatment; no hit/reveal visibility claim. Independent technical review remains required.'
        report=render_preview(name,'recipe',root,recipe=r,seconds=3,at_ms=500)
        measured=report['events'][0]['visibility']['perceived_measured']
        r['perceived_target']=measured;r['peak_ms']=report['events'][0]['peak_ms']-500
        r['gate'].update(measurement=dict(perceived=measured,source='STD-MOV; STD-A for alpha recipes',
                         resolution=[480,270],fps=30,duration_ms=3000,at_ms=500,decoded=True,report='recipe-'+name+'.json'),
                         basis='Measured default label; experimental combination pending independent technical triplets. No appeal score.')
        (ROOT/'recipes'/f'{name}.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
        reports.append(report);print('measured',name,measured,flush=True)
    glitch=render_preview('gl_glitch_memories','transition',root)
    reports.append(glitch)
    if glitch['wcag']['max_flashes_per_s']>3:raise ValueError('Glitch preview exceeds WCAG flash limit')
    (ROOT/'wow/fx/s6-fix-previews.json').write_text(json.dumps(dict(catalog_root=str(root),reports=reports),indent=2)+'\n',encoding='utf-8')
    (ROOT/'wow/fx/s6-fix-coverage.json').write_text(json.dumps(coverage(catalog(True)),indent=2)+'\n',encoding='utf-8')


def summarize_recipes(folder):
    """Link complete triplets, without modifying recipe inputs after rendering."""
    from fx_gate_kit import sha
    report=json.loads((folder/'gate-auto.json').read_text(encoding='utf-8'))
    controls=json.loads((folder/'controls.json').read_text(encoding='utf-8'))
    previews=json.loads((ROOT/'wow/fx/s6-fix-previews.json').read_text(encoding='utf-8'))
    measured={r['name']:r for r in previews['reports'] if r['kind']=='recipe'}
    records=[]
    for item in report['items']:
        name=item['id'].split(':',1)[1];r=measured[name]
        gold=[c for c in controls if c['item']==item['id'] and c['role']=='broken']
        ready=len(item['cases'])==4 and item.get('pairs')==36 and len(gold)==12 and all(c['auto']['flash_detected'] for c in gold) and not item.get('error')
        records.append(dict(name=name,status='pending-review',axis='technical',date='2026-11-05',source_path=item['source'],
                            source_sha256=item['source_sha256'],preview=r['preview'],measurements=r['events'],wcag=r['wcag'],
                            gate_ready=dict(ready=ready,axis='technical',pairs=item.get('pairs',0),controls_detectable=bool(gold) and all(c['auto']['flash_detected'] for c in gold),
                                            root=str(folder),index='index.html',pairs_path='pairs.json',controls_path='controls.json',criteria_path='criteria.json',
                                            auto_sha256=sha(folder/'gate-auto.json'),reference=item.get('reference'),independent_review='pending'),
                            auto_failures=[dict(material=c['material'],size=c['size'],check=k) for c in item['cases'] for k in ('alpha','black','flicker','determinism','wcag') if c.get(k,{}).get('level')=='FAIL']))
        if not ready:raise ValueError('Incomplete technical triplets: '+item['id'])
    (ROOT/'wow/fx/gate/s6-recipes.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    (ROOT/'wow/fx/gate/s6-recipe-auto-details.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


def complete_catalog():
    from fx_previews import render_preview,preview_override
    from fx_recipes import load_recipes
    from fx_director import recipe_cards
    from fx_catalog import write_html
    from fx_check import check_video
    from fx_measure import visibility_family
    cv2.setNumThreads(1);root=output_root()
    cards=[]
    # Complete an interrupted fix-round bundle without overwriting media.
    # Every reused movie is decoded again against its retained reference.
    for kind,entries in catalog().items():
        for name,card in entries.items():
            if card.get('card') in ('missing','incomplete'):continue
            stem=kind[:-1]+'-'+name;path=root/(stem+'.json')
            if path.is_file():
                report=json.loads(path.read_text(encoding='utf-8'))
                expected=preview_override(name)
                if report['default_override']!=expected:raise ValueError('Preview parameters changed; use a fresh catalog root: '+name)
                events=[dict(name=name,start_ms=0,end_ms=2000,intent='texture' if name=='grade' else 'hit',kind=kind[:-1])]
                report.update(check_video(root/(stem+'.mp4'),root/(stem+'-reference.mp4'),events,30))
                path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            else:report=render_preview(name,kind[:-1],root)
            cards.append(dict(card,name=name,kind=kind[:-1],preview=dict(card['preview'],**report['preview'])))
            print('verified preview '+name,flush=True)
    meta={c['name']:c for c in recipe_cards(True)};reports=[]
    for name,r in load_recipes(experimental=True).items():
        stem='recipe-'+name;path=root/(stem+'.json')
        previous=json.loads(path.read_text(encoding='utf-8'))
        events=[dict(name=name,start_ms=500,end_ms=3000,intent=r['intent'],kind='recipe',family=visibility_family(r['layers'][0]['ref']))]
        previous.update(check_video(root/(stem+'.mp4'),root/(stem+'-reference.mp4'),events,30))
        if abs(previous['events'][0]['visibility']['perceived_measured']-r['perceived_target'])>1e-6:
            raise ValueError('Recipe default measurement drift: '+name)
        path.write_text(json.dumps(previous,indent=2)+'\n',encoding='utf-8');reports.append(previous)
        cards.append(dict(meta[name],preview=previous['preview'],snippet={'recipe':name,'at_ms':500,'perceived':r['perceived_target']}))
    reports.append(json.loads((root/'transition-gl_glitch_memories.json').read_text(encoding='utf-8')))
    write_html(cards,root/'catalog.html')
    (root/'catalog.json').write_text(json.dumps(cards,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (root/'coverage.json').write_text(json.dumps(coverage(catalog()),indent=2)+'\n',encoding='utf-8')
    (ROOT/'wow/fx/s6-fix-previews.json').write_text(json.dumps(dict(catalog_root=str(root),reports=reports),indent=2)+'\n',encoding='utf-8')
    checks=[]
    for c in cards:
        r=json.loads((root/(c['kind']+'-'+c['name']+'.json')).read_text(encoding='utf-8'))
        for key in ('video','thumbnail'):
            if Path(c['preview'][key]).is_absolute() or not (root/c['preview'][key]).is_file():raise ValueError('Nonportable/missing preview '+c['name'])
        checks.append(dict(name=c['name'],kind=c['kind'],flashes=r['wcag']['max_flashes_per_s']))
    summary=dict(root=str(root),cards=len(cards),checks=checks,wcag_violations=sum(c['flashes']>3 for c in checks),
                 total_bytes=sum(p.stat().st_size for p in root.iterdir() if p.is_file()),coverage=coverage(catalog()))
    (ROOT/'wow/fx/s6-fix-catalog.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='checks'}),flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--legacy',type=Path);ap.add_argument('--previews',action='store_true');ap.add_argument('--recipe-gates',type=Path);ap.add_argument('--catalog',action='store_true')
    a=ap.parse_args()
    if a.legacy:summarize_legacy(a.legacy)
    if a.previews:previews()
    if a.catalog:complete_catalog()
    if a.recipe_gates:summarize_recipes(a.recipe_gates)


if __name__=='__main__':main()
