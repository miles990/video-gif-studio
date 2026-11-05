"""Constraint-based deterministic FX selection, with numeric reasons."""
import argparse
import json
from pathlib import Path
import sys
from fx_director import query
from fx.core import load_directory


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--intent',required=True);ap.add_argument('--needs',nargs='*',default=[])
    ap.add_argument('--max-cost',type=float,default=float('inf'));ap.add_argument('--section',default='')
    ap.add_argument('--history',type=Path);ap.add_argument('--json',action='store_true');ap.add_argument('--experimental',action='store_true')
    ap.add_argument('--fx-dir',action='append',default=[])
    a=ap.parse_args(argv)
    try:
        for directory in a.fx_dir:load_directory(directory)
        history=json.loads(a.history.read_text(encoding='utf-8')) if a.history else []
        diagnostics={}
        results=query(a.intent,a.needs,a.max_cost,a.section,history,a.experimental,diagnostics)
        print(json.dumps(results if results else dict(results=[],explanation=diagnostics),sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('fx_query: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
