"""Pairwise evidence: 2 s detail, 10 s edit context, twelve stills and 1:1 crops.

No judge is invoked here. Answers/control labels are kept out of blind context.
"""
from collections import deque
import json
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from fx import Context, EFFECTS, TRANSITIONS
from media_runtime import executable


def family(kind,name):
    if kind=='recipe':
        from fx_recipes import load_recipes
        recipe=load_recipes(experimental=True)[name]
        layer=recipe['layers'][0]
        return family(layer['kind'],layer['ref'])
    if kind=='transition':
        # "grayscale" contains "scale" but is a color blend, not geometry.
        if name=='gl_fade_grayscale': return 'transition-blend'
        if name=='gl_bow_tie_horizontal': return 'transition-reveal'
        if any(word in name for word in ('warp','dreamy','swirl','rotate','scale','bounce','spin','push','slide','zoom','whip','water','glitch','pixel','hexagonal')):
            return 'transition-motion'
        if any(word in name for word in ('wipe','shutter','curtain','squares','slices','wind','pinwheel','hatch','dither')): return 'transition-reveal'
        if name in ('flash_cut','gl_overexposure'): return 'transition-light'
        return 'transition-blend'
    if name in ('grade','film_grain','vignette','dust_scratches','posterize','halftone','kaleidoscope'):return 'effect-style'
    if name in ('halation','light_leak','flash_white','invert_flash','black_flash','rgb_split'):return 'effect-light'
    if name in ('cutout_card','multi_cutout','text'):return 'effect-layout'
    return 'effect-motion'


DEFAULT_REFERENCES={'transition-motion':'transition:whip_pan','transition-reveal':'transition:hex_shutter',
    'transition-light':'transition:flash_cut','transition-blend':'transition:crossfade',
    'effect-style':'effect:grade','effect-light':'effect:halation','effect-layout':'effect:cutout_card',
    'effect-motion':'effect:zoom_punch'}


def resolve_reference(kind,name,mapping):
    if not isinstance(mapping,dict): raise ValueError('Reference mapping must be a JSON object')
    ident=f'{kind}:{name}';ref=mapping.get(ident,mapping.get(name,DEFAULT_REFERENCES[family(kind,name)]))
    if not isinstance(ref,str) or ':' not in ref: raise ValueError('Reference must be kind:name for '+ident)
    rk,rn=ref.split(':',1);registry={'effect':EFFECTS,'transition':TRANSITIONS}.get(rk,{})
    if rn not in registry or registry[rn]['status']!='stable': raise ValueError('Reference must be known-good stable: '+ref)
    if family(rk,rn)!=family(kind,name): raise ValueError('Reference must have the same category/family: '+ident+' / '+ref)
    # A stable default is itself a registered anchor, not an experimental self-reference.
    if ref==ident and registry[rn]['status']!='stable': raise ValueError('Candidate cannot be its own reference')
    return ref


def restyle(frame):
    result=frame.copy()
    # Restrained global hue change, same geometry, alpha, timing and endpoints.
    result[...,:3]=.9*frame[...,:3]+.1*frame[...,[1,2,0]]
    return result


def break_frame(frame,index,flash_index):
    result=frame.copy()
    if index==flash_index:
        result[...,:3]=0 if float((frame[...,:3]*frame[...,3:4]).mean())>.5 else 1
        result[...,3]=1
    # A replicated four-pixel border is visible in the full-resolution crop.
    if 0<index<flash_index*2 and result.shape[1]>8: result[:,:3]=result[:,3:4]
    return result


def write_pair_files(out,pairs,controls):
    criteria=dict(intro='Compare two defaults for the same short-form editing brief. Inspect timing, subject edges, seams and endpoints. Ignore benign color/style differences.',
        criteria=[dict(name='professional_default',text='Would a professional editor use this default as-is in a short-form edit? Prefer legible subjects, coherent motion, clean alpha, correct endpoints and intentional rhythm. Use tie for equally usable defaults.')],
        overall='Choose the more usable default; style preference alone is a tie.',tieOverall=True,describeFiles=False)
    (out/'pairs.json').write_text(json.dumps(pairs,indent=2),encoding='utf-8')
    (out/'criteria.json').write_text(json.dumps(criteria,indent=2),encoding='utf-8')
    (out/'controls.json').write_text(json.dumps(controls,indent=2),encoding='utf-8')
    (out/'README.txt').write_text(
        'Pairwise gate kit; builder family codex. No quality promotions are made by this generator.\n'
        'Each item: 12 cells (2 materials x 2 aspects x 3 edit positions); REF/BAD/STYLE triplet per cell.\n'
        'Each variant: 10-second context MP4, 12 chronological stills, 3 native-resolution crop tiles, JPEG contact sheet at quality 90.\n'
        '2-second detail clips and automatic measurements are in the parent item folder.\n'
        'Styles are global restrained hue changes; geometry/alpha/timing are identical. BAD adds a 4-px stretch and a single-frame white/black exposure/alpha flash included in the stills.\n'
        'Pre-registration: BAD must lose and STYLE tie. Failed controls invalidate judging. REF win/tie >=2/3 and no significant loss -> eligible for stable; significant loss -> delete; otherwise experimental.\n'
        'Use sonnet,opus,codex in both orders; inconsistent order votes are ties; report without builder family separately.\n'
        'The controls.json answer key is NOT judge context. Do not reroll this version.\n'
        'The installed quick judge currently recompresses --sheet at q80, below the q85 protocol floor; preserve/raise its sheet quality before formal review. This generator does not edit installed tools.\n'
        'Compatible optional review command (not executed by the generator; add --dry-run to validate without model calls):\n'
        f'node C:\\Users\\User\\.claude\\skills\\wow\\tools\\wow-judge.mjs --pairs "{out / "pairs.json"}" --criteria "{out / "criteria.json"}" --sheet --thumb 200 --cols 6 --cite "[AB]#\\d+" --par 1 --cache "{out / "judge-cache"}" --out "{out / "judgments.json"}"\n',encoding='utf-8')


def build_item_pairs(kind,name,spec,reference,materials,folder,audio,resources=None):
    # Import lazily to avoid the gate entry point / helper dependency cycle.
    from fx_gate_kit import FPS, COUNT, checker, distinct_shot, edge_streaks, single_frame_flashes
    rk,rn=reference.split(':',1);refspec=(EFFECTS if rk=='effect' else TRANSITIONS)[rn]
    pairs=[];controls=[]
    for (material,size),frames in materials.items():
        w,h=size;slug=f'{material}-{w}x{h}';case=folder/('pairs-'+slug);case.mkdir()
        variants=('candidate','reference','broken','style')
        dirs={v:case/v for v in variants}
        for d in dirs.values():d.mkdir()
        # Middle 2 s applies the candidate; actual cuts bracket it at 3 s and 7 s.
        # A and B are distinct source content. The effect clock is local to the window.
        total=FPS*10;start=FPS*4;flash=start+COUNT//2
        keyframes=[0,3*FPS-1,3*FPS,start,start+1,start+COUNT//4,flash-1,flash,flash+1,start+COUNT-1,7*FPS, total-1]
        captures={v:[] for v in variants};checks=dict(streak_frames=[],flash_frame=flash,flash_detected=False)
        # Render one variant at a time: at most one encoder/heavy process.
        for variant in variants:
            levels=[]
            current=refspec if variant=='reference' else spec
            current_kind=rk if variant=='reference' else kind
            ctx=Context(w,h,fps=FPS,beats_ms=list(range(0,10000,500)),seed=19)
            history=deque(maxlen=current['history']);times=deque(maxlen=current['history'])
            target=case/(variant+'.mp4')
            command=[executable('ffmpeg'),'-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}',
                '-r',str(FPS),'-i','-','-stream_loop','-1','-i',str(audio),'-c:v','libx264','-threads','1','-preset','veryfast',
                '-crf','22','-pix_fmt','yuv420p','-c:a','aac','-b:a','48k','-t','10','-movflags','+faststart',str(target)]
            with subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE) as encoder:
                try:
                    for i in range(total):
                        a=frames[i%COUNT].astype(np.float32)/255;b=distinct_shot(size,i,material)
                        local=i-start
                        if 0<=local<COUNT:
                            ctx.t_ms=local*1000/FPS;ctx.history=tuple(reversed(history));ctx.history_times_ms=tuple(reversed(times))
                            output=current['function'](a,b,local/(COUNT-1),ctx) if current_kind=='transition' else current['function'](a,ctx.t_ms,ctx,**({} if variant=='reference' else resources or {}))
                            history.append(a);times.append(ctx.t_ms)
                        else:
                            output=a if i<start else b if current_kind=='transition' else a
                            if i<3*FPS or i>=7*FPS:output=distinct_shot(size,i,'opaque')
                        if variant=='style':output=restyle(output)
                        if variant=='broken':
                            output=break_frame(output,i,flash)
                            if start<=i<start+COUNT and edge_streaks(output):checks['streak_frames'].append(i)
                            levels.append(float((output[...,:3]*output[...,3:4]).mean()))
                        rgb=checker(np.rint(np.clip(output,0,1)*255).astype(np.uint8))
                        encoder.stdin.write(rgb.tobytes())
                        if i in keyframes:
                            image=Image.fromarray(rgb);index=keyframes.index(i)
                            image.save(dirs[variant]/f'{index+1:02d}.png');captures[variant].append(image)
                    encoder.stdin.close();error=encoder.stderr.read();code=encoder.wait()
                    if code:raise ValueError('Pair encode: '+error.decode(errors='replace'))
                except BaseException:
                    encoder.kill();encoder.wait();raise
            # Preserve native pixels for edge, central subject, and lower/title region.
            for j,(x,y) in enumerate(((0,h//4),(w//3,h//3),(w//3,h*2//3))):
                image=captures[variant][7]
                image.crop((x,y,min(w,x+160),min(h,y+120))).save(dirs[variant]/f'{13+j:02d}.png')
            sheet=Image.new('RGB',(1200,3*180),'#18202b');draw=ImageDraw.Draw(sheet)
            for j,path in enumerate(sorted(dirs[variant].glob('*.png'))):
                with Image.open(path) as im:
                    im=ImageOps.contain(im,(196,150));sheet.paste(im,((j%6)*200,(j//6)*180+20))
                draw.text(((j%6)*200+4,(j//6)*180+3),str(j+1),fill='white')
            sheet.save(case/(variant+'-contact.jpg'),quality=90)
            if variant=='broken':
                checks['flash_frames']=single_frame_flashes(levels)
                checks['flash_detected']=flash in checks['flash_frames']
        if not checks['flash_detected']:raise ValueError('Broken control injection is not detectable')
        # Three temporal cells keep stills/crops at native scale; parent context
        # folders retain the complete 10 s evidence for every variant.
        for phase,indices in (('entry',[2,3,4]),('middle',[5,6,7,8]),('exit',[8,9,10])):
            phase_dirs={}
            for v in variants:
                d=case/(v+'-'+phase);d.mkdir();phase_dirs[v]=d
                for j,idx in enumerate(indices):
                    # Full-size PNGs are directly consumable by wow-judge --sheet.
                    captures[v][idx].save(d/f'{j+1:02d}.png')
                # Every cell includes the flash and edge crop so gold is observable.
                captures[v][7].save(d/'05.png')
                for j in range(3):
                    (d/f'{6+j:02d}.png').write_bytes((dirs[v]/f'{13+j:02d}.png').read_bytes())
            for label,other,expected in (('benchmark','reference',None),('broken','broken','a'),('style','style','tie')):
                ident=f'{kind}:{name}/{slug}/{phase}/{label}'
                pairs.append(dict(id=ident,a=str(phase_dirs['candidate'].resolve()),b=str(phase_dirs[other].resolve()),
                    context=f'Same {material} short-form edit; {phase} of a 2-second treatment in a 10-second sequence. First tiles are chronological; final tiles are native-pixel details. Compare default usability, allow style ties.'))
                controls.append(dict(id=ident,item=f'{kind}:{name}',cell=f'{slug}/{phase}',role=label,expected=expected,
                    reference=reference,auto=checks if label=='broken' else None))
    return pairs,controls
