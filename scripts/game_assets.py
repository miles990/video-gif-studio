"""Experimental game-asset command surface; emits the shared image ERR envelope."""
from pathlib import Path
import argparse
import json
import sys
from image_common import ImageError

COMMANDS={'character','animate','sprite-check','iconset','tile','vfx','kf-video','demo'}


def main(argv):
    from imagegen import Parser,options,adapter_request
    try:
        p=Parser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
        c=sub.add_parser('character');cs=c.add_subparsers(dest='action',required=True);s=cs.add_parser('sheet');options(s)
        s.add_argument('--image',type=Path);s.add_argument('--pixel',type=int);s.add_argument('--negative',nargs='*',type=Path,default=[])
        s.add_argument('--near-negative',type=Path);s.add_argument('--asymmetric-feature',action='append',default=[])
        s.add_argument('--reference-licence',choices=['original','owned','licensed'],default='original')
        s.set_defaults(round='spec-14',cap=40)
        an=sub.add_parser('animate');options(an);an.add_argument('--charsheet',required=True,type=Path)
        an.add_argument('--states',default='idle,run,attack,hurt');an.add_argument('--pose-plan',type=Path);an.add_argument('--fps',nargs='*',default=[])
        an.set_defaults(round='spec-14',cap=40)
        a=p.parse_args(argv)
        if not a.experimental:raise ImageError('E_EXPERIMENTAL','Game assets are experimental.',suggestion='Pass --experimental.')
        if not a.out:raise ImageError('E_ARGUMENT','--out is required.')
        adapter,req=adapter_request(a)
        if a.command=='character':
            from game_character import sheet
            result=sheet(adapter,req,a.out,a.image,a.pixel,a.negative,a.near_negative,a.asymmetric_feature,a.reference_licence)
        else:
            from game_animation import animate
            rates={k:float(v) for k,v in (item.split('=') for item in a.fps)}
            result=animate(adapter,req,a.charsheet,a.out,a.states.split(','),a.pose_plan,rates)
        print(json.dumps(dict(ok=True,result=result),ensure_ascii=False));return 0
    except (ImageError,OSError,ValueError,KeyError,TypeError) as exc:
        error=exc.error if isinstance(exc,ImageError) else ImageError('E_GAME',str(exc)).error
        print(json.dumps(dict(ok=False,error=error),ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main(sys.argv[1:]))
