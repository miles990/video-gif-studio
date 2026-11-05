"""Preserve initial demonstration evidence and rerender unsafe catalog plates."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import cv2
from fx.core import catalog
from fx_catalog import output_root,write_html
from fx_previews import render_preview


def main():
    cv2.setNumThreads(1)
    root=output_root().resolve();archive=root/'initial-evidence';archive.mkdir(exist_ok=True)
    repaired=[]
    for path in sorted(root.glob('transition-*.json')):
        if path.name.endswith('.mp4.json'):continue
        report=json.loads(path.read_text())
        if report.get('wcag',{}).get('status')!='harsh':continue
        stem=path.stem;name=report['name']
        # Only known, generated files immediately inside this preview root move.
        for file in root.glob(stem+'.*'):
            if file.is_file() and file.resolve().parent==root:
                file.rename(archive/file.name)
        for file in root.glob(stem+'-reference.*'):
            if file.is_file() and file.resolve().parent==root:
                file.rename(archive/file.name)
        result=render_preview(name,'transition',root)
        repaired.append(dict(name=name,wcag=result['wcag'],source=result['source']))
        print(name+': '+result['wcag']['status'],flush=True)
    cards=[dict(c,name=n,kind=k[:-1]) for k,entries in catalog().items() for n,c in entries.items()]
    write_html(cards,root/'catalog.html')
    (ROOT/'wow/fx/s6-preview-repairs.json').write_text(json.dumps(repaired,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
