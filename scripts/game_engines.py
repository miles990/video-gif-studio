"""Native engine atlas adapters. Load status changes only after actual runtimes run."""
from pathlib import Path
import json
import math
import re
import shutil
import tempfile
import uuid
import numpy as np
from PIL import Image
from image_common import ROOT,ImageError,digest,read,write

ENGINES={'godot4','unity','phaser-hash','phaser-array','pixi','aseprite'}


def validated_states(manifests):
    states=[];contract=None;names=set()
    for path in manifests:
        path=Path(path);m=read(path);name=m['state']
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',name) or name in names:raise ImageError('E_STATE','State names must be unique safe identifiers.')
        names.add(name);identity=(m['canvas'],m['pivot'],m['alpha_mode'],m.get('pixel_scale',1))
        if contract is not None and identity!=contract:raise ImageError('E_CONTRACT','All states must share canvas, pivot, alpha convention and pixel scale.')
        contract=identity
        if m['alpha_mode'] not in ('straight','premultiplied'):raise ImageError('E_ALPHA_MODE','Unknown alpha convention.')
        if not isinstance(m['loop'],bool) or not math.isfinite(m['fps']) or m['fps']<=0:raise ImageError('E_TIMING','State fps and loop are invalid.')
        if not m['frames']:raise ImageError('E_FRAMES','Empty animation state.')
        for i,r in enumerate(m['frames']):
            if not math.isfinite(r['duration_ms']) or r['duration_ms']<=0:raise ImageError('E_TIMING','Frame durations must be positive finite milliseconds.')
            file=path.parent/r['file']
            with Image.open(file) as im:
                if list(im.size)!=m['canvas']:raise ImageError('E_CANVAS','Frame differs from declared canvas.')
            r.update(source=str(file.resolve()),name=f'{name}/{i:05d}',local_index=i)
        for e in m.get('events',[]):
            if not isinstance(e['frame'],int) or not 0<=e['frame']<len(m['frames']):raise ImageError('E_EVENT','Event index out of range.')
            expected=sum(r['duration_ms'] for r in m['frames'][:e['frame']])
            if abs(e.get('time_ms',expected)-expected)>1:raise ImageError('E_EVENT','Event time does not match frame timeline.')
            e['time_ms']=expected
        states.append(m)
    if not states:raise ImageError('E_STATE','Supply at least one animation manifest.')
    return states


def extrude_pages(out,packed,amount):
    if amount<=0:return
    for page in packed['pages']:
        file=out/page['file'];im=Image.open(file).convert('RGBA');a=np.array(im)
        for f in packed['frames']:
            if f['page']!=page['file']:continue
            x,y,w,h=f['rect'];crop=a[y:y+h,x:x+w].copy();a[y-amount:y+h+amount,x-amount:x+w+amount]=np.pad(crop,((amount,amount),(amount,amount),(0,0)),mode='edge')
        Image.fromarray(a).save(file)


def state_sidecar(states,packed):
    result={};offset=0
    for m in states:
        count=len(m['frames']);frames=packed['frames'][offset:offset+count]
        result[m['state']]=dict(fps=m['fps'],loop=m['loop'],events=m.get('events',[]),pivot=m['pivot'],alpha_mode=m['alpha_mode'],pixel_scale=m.get('pixel_scale',1),
            canvas=m['canvas'],frames=[dict(name=r['name'],page=f['page'],rect=f['rect'],duration_ms=r['duration_ms']) for r,f in zip(m['frames'],frames)])
        offset+=count
    return result


def godot4(out,packed,states,sidecar):
    sections=[f'[gd_resource type="SpriteFrames" load_steps={len(packed["pages"])+len(packed["frames"])+1} format=3 uid="uid://s14{digest(out/packed["pages"][0]["file"])[:8]}"]']
    for i,page in enumerate(packed['pages']):sections.append(f'[ext_resource type="Texture2D" path="res://{page["file"]}" id="p{i}"]')
    pages={p['file']:i for i,p in enumerate(packed['pages'])}
    for i,f in enumerate(packed['frames']):
        sections.append(f'[sub_resource type="AtlasTexture" id="f{i}"]\natlas = ExtResource("p{pages[f["page"]]}")\nregion = Rect2({", ".join(map(str,f["rect"]))})')
    animations=[];offset=0
    for m in states:
        frames=[f'{{"duration": {r["duration_ms"]*m["fps"]/1000:.9f}, "texture": SubResource("f{offset+i}")}}' for i,r in enumerate(m['frames'])]
        animations.append('{"frames": ['+', '.join(frames)+f'], "loop": {str(m["loop"]).lower()}, "name": &"{m["state"]}", "speed": {m["fps"]}'+'}')
        offset+=len(m['frames'])
    sections.append('[resource]\nanimations = [\n'+',\n'.join(animations)+'\n]')
    (out/'character.tres').write_text('\n\n'.join(sections)+'\n',encoding='utf-8')
    write(out/'character.events.json',dict(states=sidecar,engine_load='untested'))
    (out/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Original Character Sprite Demo"\nrun/main_scene="res://demo.tscn"\n[display]\nwindow/size/viewport_width=640\nwindow/size/viewport_height=360\n[rendering]\nrenderer/rendering_method="gl_compatibility"\ntextures/canvas_textures/default_texture_filter=0\n',encoding='utf-8')
    (out/'demo.tscn').write_text('[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="res://demo.gd" id="1"]\n[node name="CharacterDemo" type="Node2D"]\nscript = ExtResource("1")\n',encoding='utf-8')
    (out/'demo.gd').write_text('''extends Node2D
var sprite: AnimatedSprite2D
var states: Dictionary
var names: Array
var current: int = 0
var hit_flash: ColorRect
func _ready():
    states = JSON.parse_string(FileAccess.get_file_as_string("res://character.events.json"))["states"]
    names = states.keys()
    sprite = AnimatedSprite2D.new()
    sprite.sprite_frames = load("res://character.tres")
    sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    sprite.position = Vector2(320, 240)
    sprite.scale = Vector2(3, 3)
    sprite.centered = false
    sprite.offset = -Vector2(states[names[0]]["pivot"][0], states[names[0]]["pivot"][1])
    add_child(sprite)
    hit_flash = ColorRect.new()
    hit_flash.position = Vector2(120, 120)
    hit_flash.size = Vector2(12, 40)
    hit_flash.color = Color.CYAN
    hit_flash.visible = false
    add_child(hit_flash)
    sprite.frame_changed.connect(_event)
    sprite.animation_looped.connect(_next)
    sprite.animation_finished.connect(_next)
    sprite.play(names[0])
func _event():
    hit_flash.visible = false
    for event in states[str(sprite.animation)]["events"]:
        if event["frame"] == sprite.frame:
            hit_flash.visible = true
func _next():
    current = (current + 1) % names.size()
    sprite.play(names[current])
''',encoding='utf-8')
    (out/'check_frames.gd').write_text('''extends SceneTree
var ticks: int = 0
func _initialize():
    call_deferred("verify")
func verify():
    var frames = load("res://character.tres") as SpriteFrames
    assert(frames != null)
    var states = JSON.parse_string(FileAccess.get_file_as_string("res://character.events.json"))["states"]
    var sprite = AnimatedSprite2D.new()
    root.add_child(sprite)
    sprite.sprite_frames = frames
    for state in states:
        var expected = states[state]
        assert(frames.has_animation(state))
        assert(frames.get_frame_count(state) == expected["frames"].size())
        assert(abs(frames.get_animation_speed(state) - expected["fps"]) < 0.001)
        assert(frames.get_animation_loop(state) == expected["loop"])
        for i in range(frames.get_frame_count(state)):
            var tex = frames.get_frame_texture(state, i) as AtlasTexture
            var rect = expected["frames"][i]["rect"]
            assert(tex.region == Rect2(rect[0], rect[1], rect[2], rect[3]))
            var ms = frames.get_frame_duration(state, i) / frames.get_animation_speed(state) * 1000
            assert(abs(ms - expected["frames"][i]["duration_ms"]) <= 1)
        sprite.play(state)
        var seen = {}
        var elapsed: float = 0
        var duration: float = 0
        for f in expected["frames"]: duration += f["duration_ms"] / 1000.0
        while elapsed < duration + 0.08:
            seen[sprite.frame] = true
            await process_frame
            elapsed += 1.0 / 120.0
        assert(seen.size() == expected["frames"].size())
    print("S14_GODOT_PASS ", Engine.get_version_info()["string"])
    quit(0)
''',encoding='utf-8')


def unity(out,packed,states,sidecar,pixel):
    rows=[r for m in states for r in m['frames']];pivot=states[0]['pivot'];w,h=states[0]['canvas']
    for page in packed['pages']:
        selected=[(i,f) for i,f in enumerate(packed['frames']) if f['page']==page['file']]
        guid=uuid.uuid5(uuid.NAMESPACE_URL,page['file']+digest(out/page['file'])).hex
        text=['fileFormatVersion: 2',f'guid: {guid}','TextureImporter:','  internalIDToNameTable:']
        for i,f in selected:text.extend(['  - first:',f'      213: {21300000+i*2}','    second: '+json.dumps(rows[i]['name'])])
        text.extend(['  serializedVersion: 12','  mipmaps:','    enableMipMap: 0','  textureSettings:',f'    filterMode: {0 if pixel else 1}','    aniso: 1','    mipBias: 0','    wrapU: 1','    wrapV: 1','    wrapW: 1','  textureCompression: 0','  spriteMode: 2','  spritePixelsToUnits: 64','  alphaSource: 1',f'  alphaIsTransparency: {1 if states[0]["alpha_mode"]=="straight" else 0}','  textureType: 8','  spriteSheet:','    serializedVersion: 2','    sprites:'])
        for i,f in selected:
            x,y,fw,fh=f['rect']
            text.extend(['    - serializedVersion: 2','      name: '+json.dumps(rows[i]['name']),'      rect:','        serializedVersion: 2',f'        x: {x}',f'        y: {page["size"][1]-y-fh}',f'        width: {fw}',f'        height: {fh}','      alignment: 9',f'      pivot: {{x: {pivot[0]/w}, y: {1-pivot[1]/h}}}','      border: {x: 0, y: 0, z: 0, w: 0}',f'      internalID: {21300000+i*2}',f'      spriteID: {uuid.uuid5(uuid.NAMESPACE_URL,guid+rows[i]["name"]).hex}'])
        text.append('    nameFileIdTable:')
        for i,f in selected:text.append('      '+json.dumps(rows[i]['name'])+f': {21300000+i*2}')
        (out/(page['file']+'.meta')).write_text('\n'.join(text)+'\n',encoding='utf-8')
    write(out/'unity.animations.json',dict(states=sidecar,engine_load='untested',format_validation='YAML and crop roundtrip; Unity unavailable'))


def texturepacker(out,packed,states,sidecar,engine):
    names=[r['name'] for m in states for r in m['frames']];w,h=states[0]['canvas'];pivot=states[0]['pivot'];files=[]
    for page_index,page in enumerate(packed['pages']):
        records={}
        for i,f in enumerate(packed['frames']):
            if f['page']!=page['file']:continue
            x,y,fw,fh=f['rect'];records[names[i]]=dict(frame=dict(x=x,y=y,w=fw,h=fh),rotated=False,trimmed=False,spriteSourceSize=dict(x=0,y=0,w=w,h=h),sourceSize=dict(w=w,h=h),pivot=dict(x=pivot[0]/w,y=pivot[1]/h),duration=f['duration_ms'])
        filename=f'{engine}-{page_index:03d}.json';files.append(filename)
        meta=dict(app='vgs game assets',version='1',image=page['file'],format='RGBA8888',size=dict(w=page['size'][0],h=page['size'][1]),scale='1',premultipliedAlpha=states[0]['alpha_mode']=='premultiplied',related_multi_packs=[f'{engine}-{j:03d}.json' for j in range(len(packed['pages'])) if j!=page_index])
        result=dict(frames=[dict(filename=k,**v) for k,v in records.items()] if engine=='phaser-array' else records,meta=meta)
        if engine=='pixi':result['animations']={m['state']:[r['name'] for r in m['frames'] if r['name'] in records] for m in states}
        write(out/filename,result)
    write(out/(engine+'.animations.json'),dict(states=sidecar,engine_load='untested',pages=files))
    if engine.startswith('phaser'):
        anims=[]
        for name,m in sidecar.items():
            base=min(f['duration_ms'] for f in m['frames'])
            anims.append(dict(key=name,frameRate=1000/base,repeat=-1 if m['loop'] else 0,
                frames=[dict(key='atlas-'+str(next(i for i,p in enumerate(packed['pages']) if p['file']==f['page'])),frame=f['name'],duration=f['duration_ms']-base) for f in m['frames']],
                events=m['events'],pivot=m['pivot'],alpha_mode=m['alpha_mode'],pixel_scale=m['pixel_scale']))
        write(out/'anims.json',dict(anims=anims,globalTimeScale=1))
    return files


def aseprite(out,packed,states,sidecar):
    names=[r['name'] for m in states for r in m['frames']];w,h=states[0]['canvas'];pivot=states[0]['pivot']
    # Each page is an independently valid Aseprite JSON with page-local frame tags.
    for page_index,page in enumerate(packed['pages']):
        records={};tags=[];local=0
        for m in states:
            start=local
            for i,f in enumerate(packed['frames']):
                if f['page']!=page['file'] or not names[i].startswith(m['state']+'/'):continue
                x,y,fw,fh=f['rect'];records[names[i]]=dict(frame=dict(x=x,y=y,w=fw,h=fh),rotated=False,trimmed=False,spriteSourceSize=dict(x=0,y=0,w=w,h=h),sourceSize=dict(w=w,h=h),duration=f['duration_ms']);local+=1
            if local>start:tags.append(dict(name=m['state'],**{'from':start,'to':local-1},direction='forward',data=json.dumps(dict(loop=m['loop'],events=m.get('events',[])))))
        meta=dict(app='vgs',version='1',image=page['file'],format='RGBA8888',size=dict(w=page['size'][0],h=page['size'][1]),scale='1',frameTags=tags,
            slices=[dict(name='pivot',color='#00000000',keys=[dict(frame=0,bounds=dict(x=0,y=0,w=w,h=h),pivot=dict(x=pivot[0],y=pivot[1]))])])
        write(out/f'aseprite-{page_index:03d}.json',dict(frames=records,meta=meta))
    write(out/'aseprite.animations.json',dict(states=sidecar,engine_load='untested'))


def export_engines(manifests,out,engines=('godot4','phaser-hash'),max_size=2048,padding=2,extrude=1,pixel=False):
    from sprite_export import export
    if set(engines)-ENGINES:raise ImageError('E_ENGINE','Unknown engine: '+','.join(set(engines)-ENGINES))
    if padding<2 or extrude<0 or extrude>padding:raise ImageError('E_PADDING','Padding >=2 and 0<=extrude<=padding are required.')
    states=validated_states(manifests);out=Path(out);scratch=ROOT/'.scratch';scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch,prefix='game-pack-') as temp:
        temp=Path(temp);(temp/'frames').mkdir();rows=[r for m in states for r in m['frames']]
        for i,r in enumerate(rows):shutil.copyfile(r['source'],temp/'frames'/f'{i:05d}.png')
        write(temp/'timing.json',dict(durations_ms=[r['duration_ms'] for r in rows]))
        packed=export(temp/'frames',temp/'timing.json',out,max_size,padding,pivot=states[0]['pivot'])
    extrude_pages(out,packed,extrude);sidecar=state_sidecar(states,packed)
    for i,f in enumerate(packed['frames']):
        x,y,w,h=f['rect']
        with Image.open(out/f['page']) as page,Image.open(rows[i]['source']) as frame:
            if page.crop((x,y,x+w,y+h)).tobytes()!=frame.convert('RGBA').tobytes():raise ImageError('E_CROP','Engine atlas differs from source RGBA.')
    packed.update(states=sidecar,alpha=states[0]['alpha_mode'],alpha_mode=states[0]['alpha_mode'],extrusion=extrude,engines={e:dict(engine_load='untested') for e in engines})
    if 'godot4' in engines:godot4(out,packed,states,sidecar)
    if 'unity' in engines:unity(out,packed,states,sidecar,pixel)
    for e in ('phaser-hash','phaser-array','pixi'):
        if e in engines:texturepacker(out,packed,states,sidecar,e)
    if 'aseprite' in engines:aseprite(out,packed,states,sidecar)
    write(out/'sprites.json',packed)
    (out/'README.md').write_text('''# Original character engine assets

All crop rectangles preserve source RGBA exactly, including transparent RGB.
All states use one canvas and top-left pixel pivot. Durations are milliseconds.
`sprites.json` and each engine sidecar retain fps, loop, events, pivot,
alpha_mode and pixel_scale. Root travel remains in the frames unless explicitly
declared separately in the source animation manifest.

Godot 4: open project.godot. character.tres is SpriteFrames format=3;
character.events.json supplies frame events (SpriteFrames has no event track).
The scene uses nearest filtering and cycles states. check_frames.gd asserts
frame regions, timing, fps, loop and observes each frame in AnimatedSprite2D.
Import with `godot --headless --editor --path DIR --quit`, then run
`godot --headless --path DIR --fixed-fps 120 --script check_frames.gd`.
Straight PNGs use the engine default process/premult_alpha=false. For explicit
premultiplied source art use a matching material and avoid double premultiplying.

Unity: .png.meta rectangles use bottom-left coordinates and normalized pivots.
The YAML and decoded crops are checked; Unity engine loading is untested.
Timing/events live in unity.animations.json; no fabricated .anim resources.

Phaser: load each phaser-hash-NNN.json under atlas-N, then anims.fromJSON with
anims.json. Frame `duration` is extra time beyond the state's base frame period.
Use pixelArt:true. On animationupdate, match zero-based frame indexes against
events in phaser-hash.animations.json and emit the event name.
PixiJS: load pixi-NNN.json; assemble cross-page animations using the sidecar.
Use TextureStyle.defaultOptions.scaleMode='nearest' and AnimatedSprite timed
textures. alpha mode is recorded in meta.premultipliedAlpha.
Aseprite: per-page JSON has nonoverlapping page-local frameTags, pixel pivots
in meta.slices, loop/events in tag data and the complete state sidecar.

All engine_load values begin as untested. Only a real engine check may promote
one to tested:<version>; format/schema parsing alone cannot do so.
''',encoding='utf-8')
    return packed
