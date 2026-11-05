"""Serial render evidence for every recipe; never assigns an independent verdict."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import cv2
from fx_previews import render_preview
from fx_recipes import load_recipes
from fx_director import recipe_cards
from fx_catalog import output_root,write_html
from fx_calibrate import revision


def main():
    cv2.setNumThreads(1)
    folder=output_root()/'recipes';records=[];cards=[]
    meta={c['name']:c for c in recipe_cards(True)}
    for name,r in load_recipes(experimental=True).items():
        report=render_preview(name,'recipe',folder,recipe=r,seconds=3,at_ms=500)
        records.append(dict(name=name,status='pending-review',axis='technical',date='2026-11-05',commit=revision(),
            source_path='recipes/'+name+'.json',preview=report['preview'],measurements=report['events'],wcag=report['wcag'],
            render_seconds=report['render_seconds'],sfx=report['sfx'],
            independent_panel='not run; independent technical panel evidence is not present',appeal='user taste; not scored'))
        cards.append(dict(meta[name],preview=report['preview'],snippet={'recipe':name,'at_beat':4,'perceived':r['perceived_target']}))
        print(name+': '+report['wcag']['status'],flush=True)
    write_html(cards,folder/'index.html','Intent recipes / technical review')
    # A preview refresh must not erase the separately prepared technical triplets.
    (ROOT/'wow/fx/gate/s6-recipe-previews.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'recipes':len(records),'wcag_violations':sum(r['wcag']['status']=='harsh' for r in records),
                      'out':str(folder),'seconds':sum(r['render_seconds'] for r in records)}))


if __name__=='__main__':main()
