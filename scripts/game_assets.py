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
        sp=sub.add_parser('sprite-check');sp.add_argument('images',nargs='+',type=Path);sp.add_argument('--experimental',action='store_true');sp.add_argument('--json',action='store_true')
        sp.add_argument('--out',type=Path);sp.add_argument('--cleanup',action='store_true');sp.add_argument('--pixel',type=int);sp.add_argument('--palette',type=Path)
        sp.add_argument('--scale',type=int,default=1);sp.add_argument('--alpha-mode',choices=['straight','premultiplied'],default='straight');sp.add_argument('--particles',action='store_true')
        icons=sub.add_parser('iconset');options(icons);icons.add_argument('--items',required=True);icons.add_argument('--style-token',type=Path,required=True)
        icons.add_argument('--pixel',action='store_true');icons.add_argument('--fix',action='store_true');icons.set_defaults(round='spec-14',cap=40)
        tile=sub.add_parser('tile');ts=tile.add_subparsers(dest='action',required=True)
        tex=ts.add_parser('texture');options(tex);tex.set_defaults(size='256',round='spec-14',cap=40)
        tiles=ts.add_parser('tileset');options(tiles);tiles.add_argument('--grid',type=int,default=16);tiles.add_argument('--set',choices=['wang16','blob47','min13'],default='wang16')
        a=p.parse_args(argv)
        if not a.experimental:raise ImageError('E_EXPERIMENTAL','Game assets are experimental.',suggestion='Pass --experimental.')
        if a.command=='sprite-check':
            from game_sprite import sprite_check
            from image_common import read
            result=sprite_check(a.images,mode=a.alpha_mode,palette=read(a.palette) if a.palette else None,pixel=a.pixel,scale=a.scale,cleanup=a.cleanup,out=a.out,particles=a.particles)
            print(json.dumps(dict(ok=result['status']=='PASS',result=result)));return 0 if result['status']=='PASS' else 2
        if not a.out:raise ImageError('E_ARGUMENT','--out is required.')
        if a.loop and a.oneshot:raise ImageError('E_ARGUMENT','Choose --loop or --oneshot, not both.')
            result=vfx(a.out,a.kind,a.frames,int(a.size),a.loop,a.pixel,a.blend,a.color)
            print(json.dumps(dict(ok=result['qa']['status']=='PASS',result=result)));return 0 if result['qa']['status']=='PASS' else 2
        if a.command=='tile' and a.action=='tileset':
            from game_tiles import tileset
            result=tileset(a.out,a.grid,a.set)
            print(json.dumps(dict(ok=True,result=result)));return 0
        if a.command=='tile':a.size=f'{a.size}x{a.size}' if 'x' not in a.size else a.size
        adapter,req=adapter_request(a)
        if a.command=='character':
            from game_character import sheet
            result=sheet(adapter,req,a.out,a.image,a.pixel,a.negative,a.near_negative,a.asymmetric_feature,a.reference_licence)
        elif a.command=='iconset':
            from game_icons import iconset
            result=iconset(adapter,req,a.items.split(','),a.style_token,a.out,a.pixel,a.fix)
        elif a.command=='tile':
            from game_tiles import texture
            result=texture(adapter,req,a.out,int(a.size.split('x')[0]))
        else:
            from game_animation import animate
            rates={k:float(v) for k,v in (item.split('=') for item in a.fps)}
            result=animate(adapter,req,a.charsheet,a.out,a.states.split(','),a.pose_plan,rates)
        print(json.dumps(dict(ok=True,result=result),ensure_ascii=False));return 0
    except (ImageError,OSError,ValueError,KeyError,TypeError) as exc:
        error=exc.error if isinstance(exc,ImageError) else ImageError('E_GAME',str(exc)).error
        print(json.dumps(dict(ok=False,error=error),ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main(sys.argv[1:]))
