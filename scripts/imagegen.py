#!/usr/bin/env python3
"""Experimental vgs image command mapping (this checkout has no unified vgs CLI)."""
import argparse
import json
from pathlib import Path
import sys
from image_common import DEFAULT_STATE, ImageError, read, write
from image_route import Adapter, Request


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ImageError('E_ARGUMENT',message,location='arguments',suggestion='See imagegen.py --help.')


def options(p):
    p.add_argument('--prompt',default='')
    p.add_argument('--refs',type=Path)
    p.add_argument('--identity-override',choices=['same','different'],help='Human identity decision, recorded in the manifest.')
    p.add_argument('--size',default='1024x1024')
    p.add_argument('--aspect')
    p.add_argument('--quality',choices=['draft','final'],default='draft')
    p.add_argument('--n',type=int,default=1)
    p.add_argument('--route',choices=['codex','auto','api'],default='codex')
    p.add_argument('--transparent',action='store_true')
    p.add_argument('--format',choices=['png','gif','svg'],default='png')
    p.add_argument('--model');p.add_argument('--seed',type=int)
    p.add_argument('--experimental',action='store_true')
    p.add_argument('--approve-spend');p.add_argument('--max-usd',type=float,default=0)
    p.add_argument('--prices',type=Path);p.add_argument('--api-base')
    p.add_argument('--price-table-trusted',action='store_true',help='Explicitly trust a custom price table; recorded with its SHA256.')
    p.add_argument('--state',type=Path,default=DEFAULT_STATE)
    p.add_argument('--codex',help='Executable or Python fake-Codex script')
    p.add_argument('--timeout',type=float,default=300)
    p.add_argument('--round',default='spec-13');p.add_argument('--cap',type=int,default=60);p.add_argument('--run-id')
    p.add_argument('--no-cache',action='store_true');p.add_argument('--out',type=Path)
    p.add_argument('--since')
    p.add_argument('--frames',type=int,default=48);p.add_argument('--frame-ms',type=int,default=40)
    p.add_argument('--start-image',type=Path)
    p.add_argument('--json',action='store_true')


def adapter_request(a):
    refs=[];refset_sha=None
    if a.refs:
        from image_identity import load
        data=load(a.refs)
        refs=[r['path'] for r in data['images']]
        from image_common import digest
        refset_sha=digest(a.refs)
    cmd=[sys.executable,a.codex] if a.codex and a.codex.endswith('.py') else a.codex
    adapter=Adapter(state=a.state,codex=cmd,timeout=a.timeout,round_id=a.round,cap=a.cap,run_id=a.run_id,api_base=a.api_base,prices=a.prices,price_table_trusted=a.price_table_trusted)
    req=Request(prompt=a.prompt,refs=refs,refset_sha=refset_sha,refset_path=str(a.refs) if a.refs else None,size=a.size,aspect=a.aspect,quality=a.quality,n=a.n,
                route=a.route,transparent=a.transparent,format=a.format,model=a.model,seed=a.seed,experimental=a.experimental,identity_override=a.identity_override)
    return adapter,req


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    from game_assets import COMMANDS
    if args and args[0] in COMMANDS:
        from game_assets import main as game_main
        return game_main(args)
    try:
        p=Parser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
        for name in ('generate','estimate','probe','usage'):options(sub.add_parser(name))
        motion=sub.add_parser('motion');motion.add_argument('--keyframes',nargs='+',required=True,type=Path);motion.add_argument('--out',required=True,type=Path)
        motion.add_argument('--frames',type=int,default=48);motion.add_argument('--frame-ms',type=int,default=40);motion.add_argument('--size');motion.add_argument('--json',action='store_true')
        ing=sub.add_parser('ingest');ing.add_argument('gif',type=Path);ing.add_argument('--out',required=True,type=Path);ing.add_argument('--json',action='store_true')
        alpha=sub.add_parser('alpha');alpha.add_argument('image',type=Path);alpha.add_argument('--out',type=Path);alpha.add_argument('--cleanup',action='store_true');alpha.add_argument('--json',action='store_true')
        alpha.add_argument('--codex');alpha.add_argument('--timeout',type=float,default=120)
        alpha.add_argument('--prompt',default='',help='Character/asset description for contextual hole review')
        e=sub.add_parser('edit');options(e);e.add_argument('--image',type=Path,required=True);e.add_argument('--instruction',required=True)
        e.add_argument('--region');e.add_argument('--markup',type=Path);e.add_argument('--feather',type=int,default=8)
        d=sub.add_parser('delta');options(d);d.add_argument('storyboard',type=Path);d.add_argument('--draft',required=True);d.add_argument('--markup',type=Path);d.add_argument('--feedback',type=Path)
        v=sub.add_parser('vectorize');v.add_argument('image',type=Path);v.add_argument('--out',type=Path,required=True);v.add_argument('--colors',type=int,default=6);v.add_argument('--json',action='store_true')
        ss=sub.add_parser('svg-safe');ss.add_argument('svg',type=Path);ss.add_argument('--out',type=Path);ss.add_argument('--json',action='store_true')
        sr=sub.add_parser('svg-render');sr.add_argument('svg',type=Path);sr.add_argument('--out',type=Path,required=True);sr.add_argument('--sizes',default='512,2048,4096');sr.add_argument('--json',action='store_true')
        vs=sub.add_parser('variants');options(vs);vs.add_argument('--shot',default='1');vs.add_argument('--storyboard',type=Path)
        vp=sub.add_parser('variants-page');vp.add_argument('directory',type=Path);vp.add_argument('--out',type=Path);vp.add_argument('--json',action='store_true')
        pk=sub.add_parser('pick');pk.add_argument('directory',type=Path);pk.add_argument('--choose');pk.add_argument('--record',type=Path);pk.add_argument('--board',type=Path);pk.add_argument('--out-board',type=Path);pk.add_argument('--json',action='store_true')
        k=sub.add_parser('keyframes');options(k);k.add_argument('storyboard',type=Path);k.add_argument('--shots',nargs='+')
        r=sub.add_parser('refset');rs=r.add_subparsers(dest='ref_command',required=True)
        rb=rs.add_parser('build');rb.add_argument('--name',required=True);rb.add_argument('--images',nargs='+',type=Path,required=True)
        rb.add_argument('--out',type=Path,required=True);rb.add_argument('--role',default='identity');rb.add_argument('--source',default='user');rb.add_argument('--licence')
        rb.add_argument('--negative',nargs='+',type=Path);rb.add_argument('--json',action='store_true')
        rb.add_argument('--identity-override',choices=['same','different'])
        rc=rs.add_parser('check');rc.add_argument('--refs',type=Path,required=True);rc.add_argument('--image',type=Path,required=True);rc.add_argument('--json',action='store_true')
        rc.add_argument('--identity-override',choices=['same','different'])
        rr=rs.add_parser('review');rr.add_argument('--refs',type=Path,required=True);rr.add_argument('--same',choices=['yes','no'],required=True);rr.add_argument('--comment',default='');rr.add_argument('--json',action='store_true')
        a=p.parse_args(argv)
        if a.command in ('variants-page','pick'):
            from image_variants import page,pick
            result=page(a.directory,a.out) if a.command=='variants-page' else pick(a.directory,a.choose,a.record,a.board,a.out_board)
            print(json.dumps(dict(ok=True,result=result)));return 0
        if a.command in ('vectorize','svg-safe','svg-render'):
            from image_vector import trace,safe_svg,rasterize
            if a.command=='vectorize':result=trace(a.image,a.out,a.colors)
            elif a.command=='svg-safe':
                _,result=safe_svg(a.svg)
                if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(a.svg.read_bytes())
            else:
                a.out.mkdir(parents=True,exist_ok=True);files=[]
                for size in map(int,a.sizes.split(',')):
                    file=a.out/f'{size}.png';rasterize(a.svg,size).save(file);files.append(str(file))
                result=dict(renderer='local polygon renderer v1 (Pillow/OpenCV, 2x antialias)',files=files)
            print(json.dumps(dict(ok=True,result=result)));return 0
        if a.command=='alpha':
            from PIL import Image
            from image_alpha import alpha_qa,cleanup
            from image_hole_judge import SubscriptionHoleJudge
            folder=(a.out.parent if a.out else Path('.scratch/alpha-reviews')).resolve()
            folder.mkdir(parents=True,exist_ok=True)
            cmd=[sys.executable,a.codex] if a.codex and a.codex.endswith('.py') else a.codex
            judge=SubscriptionHoleJudge(Adapter(folder/'judge-state',codex=cmd,timeout=a.timeout))
            overlay_path=folder/(a.image.stem+'.holes.png')
            with Image.open(a.image) as im:
                if a.cleanup:
                    if not a.out:raise ImageError('E_ARGUMENT','Cleanup requires --out PNG.')
                    cleaned,result=cleanup(im,judge=judge,overlay_path=overlay_path,description=a.prompt);a.out.parent.mkdir(parents=True,exist_ok=True);cleaned.save(a.out)
                else:result=alpha_qa(im,judge=judge,overlay_path=overlay_path,description=a.prompt)
            status=result.get('after',result)['status']
            print(json.dumps(dict(ok=status=='PASS',result=result)));return 0 if status=='PASS' else 3 if status=='needs_review' else 2
        if a.command in ('motion','ingest'):
            from image_motion import loop_keyframes,ingest_gif
            if a.command=='motion':result=loop_keyframes(a.keyframes,a.out,a.frames,a.frame_ms,tuple(map(int,a.size.split('x'))) if a.size else None)
            else:result=ingest_gif(a.gif,a.out)
            print(json.dumps(dict(ok=True,result=result),ensure_ascii=False));return 0
        if a.command=='refset':
            from image_identity import build,check,review
            if a.ref_command=='build':result=build(a.name,a.images,a.out,a.role,a.source,a.licence,a.negative,a.identity_override)
            elif a.ref_command=='check':result=check(a.image,a.refs,a.identity_override)
            else:result=review(a.refs,a.same=='yes',a.comment)
            print(json.dumps(dict(ok=True,result=result),ensure_ascii=False));return 0
        adapter,req=adapter_request(a)
        if a.command=='variants':
            if not a.out:raise ImageError('E_ARGUMENT','--out is required.')
            from image_variants import variants
            result=variants(adapter,req,a.out,a.shot,read(a.storyboard) if a.storyboard else None,approval=a.approve_spend,max_usd=a.max_usd)
        elif a.command in ('edit','delta'):
            if not a.out:raise ImageError('E_ARGUMENT','--out is required.')
            from image_edit import edit,apply_delta
            if a.command=='edit':result=edit(adapter,req,a.image,a.out,a.instruction,a.region,a.markup,a.feather,a.approve_spend,a.max_usd)
            else:result=apply_delta(read(a.storyboard),a.draft,adapter,req,a.out,a.markup,a.approve_spend,a.max_usd,a.feedback)
        elif a.command=='keyframes':
            if not a.out:raise ImageError('E_ARGUMENT','--out is required.')
            from image_keyframes import keyframes
            result=keyframes(read(a.storyboard),adapter,a.out,req,a.shots,a.approve_spend,a.max_usd)
            failed=[s['id'] for s in result['shots'] if s.get('keyframe_failure')]
            if failed:
                kept=[s['id'] for s in result['shots'] if s.get('keyframe')]
                message='Some keyframes failed; successful shots are retained.' if kept else 'All requested keyframes failed; no successful keyframes are available.'
                error=ImageError('E_KEYFRAME_PARTIAL',message,location=str(a.out/'storyboard.json'),failed_shots=failed,kept_shots=kept).error
                print(json.dumps(dict(ok=False,error=error,result=result),ensure_ascii=False));return 2
        elif a.command=='estimate':result=adapter.estimate(req)
        elif a.command=='generate':
            if not a.out:raise ImageError('E_ARGUMENT','--out is required.')
            if a.format in ('gif','svg'):
                from dataclasses import replace
                raster=replace(req,format='png');raster.normalized()
                if a.format=='gif':
                    from image_motion import validate_motion,loop_keyframes
                    size=tuple(map(int,a.size.split('x')));validate_motion(size,a.frames,a.frame_ms)
                source=a.start_image
                if source is None:
                    generation=adapter.generate(raster,a.out/'source',a.approve_spend,a.max_usd,a.no_cache)
                    source=Path(generation['assets'][0]['path'])
                else:generation=None
                if a.format=='gif':result=loop_keyframes([source],a.out/'motion',a.frames,a.frame_ms,size)
                else:
                    from image_vector import trace
                    result=trace(source,a.out/'asset.svg')
                result['generation']=generation;write(a.out/'gen-manifest.json',result)
            elif a.transparent:
                from image_alpha import transparent_asset
                result=transparent_asset(adapter,req,a.out,a.approve_spend,a.max_usd,a.no_cache)
            else:result=adapter.generate(req,a.out,a.approve_spend,a.max_usd,a.no_cache)
        elif a.command=='probe':
            # Recorded probes are read-only evidence, not an implicit generation.
            result=read(Path(__file__).resolve().parents[1]/'references/image-capabilities.json')
            if a.out:write(a.out/'capabilities.json',result)
        else:
            from image_usage import summarize
            result=summarize(adapter.records(),a.since,a.round,a.run_id)
        if result.get('status')=='needs_review':
            print(json.dumps(dict(ok=False,status='needs_review',result=result),ensure_ascii=False));return 3
        print(json.dumps(dict(ok=True,result=result),ensure_ascii=False));return 0
    except (ImageError,OSError,ValueError,KeyError,TypeError) as exc:
        error=exc.error if isinstance(exc,ImageError) else ImageError('E_IMAGE',str(exc)).error
        print(json.dumps(dict(ok=False,error=error),ensure_ascii=False));return 2


if __name__=='__main__':raise SystemExit(main())
