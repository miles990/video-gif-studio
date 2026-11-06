"""Offline storyboard preflight, predicted plot, shot table and generation prompts."""
import argparse
from pathlib import Path
import sys
from taste_common import read, write, plot_curve
from storyboard import lint, normalize, shot_table, prompts


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('storyboard',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--design',type=Path);p.add_argument('--tokens',type=Path);p.add_argument('--prompts',action='store_true');p.add_argument('--animatic-receipt',type=Path)
    a=p.parse_args(argv)
    try:
        b=read(a.storyboard)
        if a.design:b['design_curve']=read(a.design)
        report=lint(b,read(a.tokens) if a.tokens else None)
        if a.prompts:report['generation']=prompts(b,read(a.animatic_receipt) if a.animatic_receipt else None)
        write(a.out.with_suffix('.json'),report);pred=report['predicted']
        plot_curve(a.out.with_suffix('.png'),pred['times'],pred['values'],report['comparison']['design'])
        a.out.with_suffix('.md').write_text(shot_table(b),encoding='utf-8')
        return int(report['errors']>0)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError) as exc:
        print('storyboard_lint: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
