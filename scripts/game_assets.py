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
        s.add_argument('--views',default='front,side,back,three_quarter');s.add_argument('--expressions',type=int,default=6)
        s.set_defaults(round='spec-14',cap=40)
        an=sub.add_parser('animate');options(an);an.add_argument('--charsheet',required=True,type=Path)
        an.add_argument('--states',default='idle,run,attack,hurt');an.add_argument('--pose-plan',type=Path);an.add_argument('--fps',nargs='*',default=[])
        an.set_defaults(round='spec-14',cap=40)
        next(action for action in an._actions if action.dest=='route').choices=['codex','auto','api','video']
        sp=sub.add_parser('sprite-check');sp.add_argument('images',nargs='+',type=Path);sp.add_argument('--experimental',action='store_true');sp.add_argument('--json',action='store_true')
        sp.add_argument('--out',type=Path);sp.add_argument('--cleanup',action='store_true');sp.add_argument('--pixel',type=int);sp.add_argument('--palette',type=Path)
        sp.add_argument('--scale',type=int,default=1);sp.add_argument('--alpha-mode',choices=['straight','premultiplied'],default='straight');sp.add_argument('--particles',action='store_true')
        icons=sub.add_parser('iconset');options(icons);icons.add_argument('--items',required=True);icons.add_argument('--style-token',type=Path,required=True)
        icons.add_argument('--pixel',action='store_true');icons.add_argument('--fix',action='store_true');icons.set_defaults(round='spec-14',cap=40)
        tile=sub.add_parser('tile');ts=tile.add_subparsers(dest='action',required=True)
        tex=ts.add_parser('texture');options(tex);tex.set_defaults(size='256',round='spec-14',cap=40)
        tiles=ts.add_parser('tileset');options(tiles);tiles.add_argument('--grid',type=int,default=16);tiles.add_argument('--set',choices=['wang16','blob47','min13'],default='wang16')
        vf=sub.add_parser('vfx');options(vf);vf.add_argument('--kind',choices=['explosion','magic','hit','pickup'],default='explosion')
        vf.add_argument('--loop',action='store_true');vf.add_argument('--oneshot',action='store_true');vf.add_argument('--pixel',action='store_true');vf.add_argument('--blend',choices=['add','alpha'],default='add');vf.add_argument('--color',default='#80DAFF');vf.set_defaults(size='96',frames=12)
        kv=sub.add_parser('kf-video');options(kv);kv.add_argument('--first',type=Path,required=True);kv.add_argument('--last',type=Path,required=True)
        kv.add_argument('--approve-video');kv.add_argument('--video-driver',type=Path);kv.add_argument('--duration',type=float,default=5)
        # Override the generic image route choices; video never shares API authority.
        next(a for a in kv._actions if a.dest=='route').choices=['grok','fal','local'];kv.set_defaults(route='local')
        dm=sub.add_parser('demo');ds=dm.add_subparsers(dest='action',required=True);game=ds.add_parser('game');options(game)
        game.add_argument('--source-pack',required=True,type=Path);game.add_argument('--vendor',type=Path);game.add_argument('--godot',type=Path)
        a=p.parse_args(argv)
        if not a.experimental:raise ImageError('E_EXPERIMENTAL','Game assets are experimental.',suggestion='Pass --experimental.')
        if a.command=='sprite-check':
            from game_sprite import sprite_check
            from image_common import read
            result=sprite_check(a.images,mode=a.alpha_mode,palette=read(a.palette) if a.palette else None,pixel=a.pixel,scale=a.scale,cleanup=a.cleanup,out=a.out,particles=a.particles)
            print(json.dumps(dict(ok=result['status']=='PASS',result=result)));return 0 if result['status']=='PASS' else 2
        if not a.out:raise ImageError('E_ARGUMENT','--out is required.')
        if a.command=='animate' and a.route=='video':
            raise ImageError('E_APPROVAL_REQUIRED','Continuous model-video animation requires explicit consent after its input-bound estimate.',network_requests=0,
                             estimate=dict(duration_seconds=5,cost_estimate_usd=None),suggestion='Prepare first/last key poses and use kf-video to obtain an estimate; local pose interpolation is available without approval.')
        if a.command=='demo':
            from game_demo import demo
            result=demo(a.source_pack,a.out,a.vendor,a.godot)
            print(json.dumps(dict(ok=True,result=result)));return 0
        if a.command=='kf-video':
            from game_video import keyframes_video
            from image_identity import load
            refs=[r['path'] for r in load(a.refs)['images']] if a.refs else []
            result=keyframes_video(a.first,a.last,refs,a.route,a.out,a.approve_video,a.duration,a.prices,a.video_driver,a.prompt or 'Original character motion')
            print(json.dumps(dict(ok=True,result=result)));return 0
        if a.command=='vfx':
            from game_vfx import vfx
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
            if a.views.split(',')!=['front','side','back','three_quarter'] or a.expressions!=6:raise ImageError('E_CHARACTER_LAYOUT','This version delivers four canonical views and six expressions.')
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
        failed=result.get('qa',{}).get('status')=='FAIL' or any(r.get('qa',{}).get('status')=='FAIL' for r in result.get('states',{}).values())
        envelope=dict(ok=not failed,result=result)
        if failed:envelope['error']=ImageError('E_GAME_QA','Generated preview failed measured QA; inspect the retained report before delivery.').error
        print(json.dumps(envelope,ensure_ascii=False));return 2 if failed else 0
    except (ImageError,OSError,ValueError,KeyError,TypeError) as exc:
        error=exc.error if isinstance(exc,ImageError) else ImageError('E_GAME',str(exc)).error
        print(json.dumps(dict(ok=False,error=error),ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main(sys.argv[1:]))
