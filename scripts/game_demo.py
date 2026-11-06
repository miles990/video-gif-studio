"""Deterministic assembly of reviewed original source packs; no implicit network.

Source pack JSON records live tool provenance and explicit per-strip camera
transforms. An animation strip gets ONE scale/ground transform for all keys.
Never fit each animation key's bbox or silently advertise pending QA as accepted.
"""
from pathlib import Path
import json
import math
import os
import shutil
import subprocess
import sys
from copy import deepcopy
import numpy as np
import cv2
from PIL import Image,ImageDraw
from image_common import ImageError,digest,key,read,write
from game_character import rgba,quantize,palette_image,identity_report,expressions_qa,asymmetry_qa,originality
from game_animation import animate,previews
from game_engines import export_engines

PALETTE=['#281B20','#573021','#81462E','#B0734C','#DC761E','#F5A32D','#FFE0B1','#A12268','#E2B75B','#142D38','#1B5964','#2B8990','#292E46','#484865','#8FC1D7','#D0EFFF']


def isolate_single_subject(im):
    """Reviewed single-subject source cells: exclude neighbors and exterior specks.

    A two-source-pixel alpha support band retains fractional contour coverage;
    it never fills interior gaps. This is not suitable for detached VFX layers.
    """
    a=np.array(im);mask=(a[...,3]>127).astype(np.uint8)
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
    if n<2:raise ImageError('E_SUBJECT','Source cell contains no opaque subject.')
    main=labels==(1+int(np.argmax(stats[1:,cv2.CC_STAT_AREA])))
    support=cv2.dilate(main.astype(np.uint8),np.ones((5,5),np.uint8))>0
    a[~support]=0
    return Image.fromarray(a)


def camera(im,scale,offset,canvas=(64,64)):
    """Inverse affine, integer nearest sampling, fixed across the entire strip."""
    x,y=offset
    return im.transform(canvas,Image.Transform.AFFINE,(1/scale,0,-x/scale,0,1/scale,-y/scale),resample=Image.Resampling.NEAREST)


def strip_keys(path,cols,rows,scale,offset,canvas=(64,64),gutter=0):
    im=rgba(path);w=im.width/cols;h=im.height/rows;result=[]
    for i in range(cols*rows):
        box=(round((i%cols)*w)-gutter,round((i//cols)*h),round((i%cols+1)*w)+gutter,round((i//cols+1)*h))
        result.append(camera(isolate_single_subject(im.crop(box)),scale,[offset[0]-gutter*scale,offset[1]],canvas))
    return result


def browser_demo(out,packed,vendor=None):
    """Portable Phaser runtime page; libraries must be supplied, never CDN-fetched."""
    folder=Path(out);folder.mkdir(parents=True,exist_ok=True)
    if vendor:
        vendor=Path(vendor);(folder/'vendor').mkdir(exist_ok=True)
        for name in ('phaser-3.90.0.min.js','pixi-8.6.6.min.js'):
            if (vendor/name).exists():shutil.copyfile(vendor/name,folder/'vendor'/name)
        for licence in vendor.glob('*LICENSE*'):shutil.copyfile(licence,folder/'vendor'/licence.name)
    pages=packed['pages'];states=packed['states'];write(folder/'states.json',states)
    for page in pages:shutil.copyfile(folder.parent/'export'/page['file'],folder/page['file'])
    for i in range(len(pages)):
        for kind in ('phaser-hash','phaser-array','pixi'):
            shutil.copyfile(folder.parent/'export'/f'{kind}-{i:03d}.json',folder/f'{kind}-{i:03d}.json')
    shutil.copyfile(folder.parent/'export/anims.json',folder/'anims.json')
    (folder/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>Rimewick • Original Sprite Demo</title>
<style>body{margin:0;background:#101c28;color:#e6edf4;font:16px system-ui;padding:24px}canvas{image-rendering:pixelated}a{color:#8ddbed}</style>
<h1>Rimewick / original wayfinder</h1><p>Idle · Run · Attack · Hurt | nearest pixels | shared ground pivot</p>
<p id="status">Loading local Phaser 3.90.0…</p><div id="game"></div>
<script src="vendor/phaser-3.90.0.min.js"></script><script src="runtime.js"></script>
''',encoding='utf-8')
    (folder/'runtime.js').write_text('''"use strict";
window.S14={done:false,frames:{},events:[],errors:[]};
window.addEventListener('error',e=>window.S14.errors.push(e.message));
(async()=>{
 const states=await (await fetch('states.json')).json();
 const anims=await (await fetch('anims.json')).json();
 const pages=[...new Set(Object.values(states).flatMap(s=>s.frames.map(f=>f.page)))];
 const names=Object.keys(states);
 const format=new URLSearchParams(location.search).get('format')||'phaser-hash';
 new Phaser.Game({type:Phaser.CANVAS,width:640,height:360,parent:'game',pixelArt:true,backgroundColor:'#223341',audio:{noAudio:true},
 scene:{preload(){pages.forEach((p,i)=>this.load.atlas('atlas-'+i,p,format+'-'+String(i).padStart(3,'0')+'.json'));},
 create(){
  this.anims.fromJSON(anims); let current=0;
  const sprite=this.add.sprite(320,290,'atlas-0',states[names[0]].frames[0].name).setScale(3);
  sprite.setOrigin(states[names[0]].pivot[0]/states[names[0]].canvas[0],states[names[0]].pivot[1]/states[names[0]].canvas[1]);
  const flash=this.add.rectangle(140,160,16,36,0x8fdfff).setVisible(false);
  const observe=(animation,frame)=>{
   const name=animation.key, i=frame.index-1; (window.S14.frames[name]??=[]).push(i);flash.setVisible(false);
   const expected=states[name].frames[i]; const tex=this.textures.get(frame.textureKey).get(frame.textureFrame);
   if(tex.width!==states[name].canvas[0]||tex.height!==states[name].canvas[1])throw Error('Texture dimensions');
   if(frame.duration!==expected.duration_ms)throw Error('Frame timing');
   const box=states[name].target_box;if(box){flash.setPosition(sprite.x+(box[0]+box[2]/2-states[name].pivot[0])*3,sprite.y+(box[1]+box[3]/2-states[name].pivot[1])*3).setSize(box[2]*3,box[3]*3);}
   for(const event of states[name].events)if(event.frame===i){flash.setVisible(true);window.S14.events.push({state:name,name:event.name,frame:i});sprite.emit(event.name,event);}
  };
  sprite.on('animationstart',observe);sprite.on('animationupdate',observe);
  const next=()=>{if(++current>=names.length){window.S14.done=true;document.getElementById('status').textContent='All four states played • frame events checked';current=0;}sprite.play(names[current]);};
  sprite.on('animationrepeat',next);sprite.on('animationcomplete',next);sprite.play(names[0]);
 }}});
})().catch(e=>{window.S14.errors.push(String(e));document.getElementById('status').textContent=String(e);});
''',encoding='utf-8')
    (folder/'pixi.html').write_text('''<!doctype html><meta charset="utf-8"><title>PixiJS 8 atlas check</title>
<script src="vendor/pixi-8.6.6.min.js"></script><script src="pixi-runtime.js"></script>''',encoding='utf-8')
    (folder/'pixi-runtime.js').write_text('''window.S14={done:false,frames:{},events:[],errors:[]};
(async()=>{
 const states=await(await fetch('states.json')).json();
 PIXI.TextureStyle.defaultOptions.scaleMode='nearest';
 const app=new PIXI.Application();await app.init({width:640,height:360,preference:'webgl',background:0x223341});document.body.appendChild(app.canvas);
 const pages=[...new Set(Object.values(states).flatMap(s=>s.frames.map(f=>f.page)))];let textures={};
 for(let i=0;i<pages.length;i++){const sheet=await PIXI.Assets.load('pixi-'+String(i).padStart(3,'0')+'.json');Object.assign(textures,sheet.textures);}
 for(const [name,state] of Object.entries(states)){
  const timed=state.frames.map(f=>({texture:textures[f.name],time:f.duration_ms}));
  if(timed.some(f=>f.texture.width!==state.canvas[0]||f.texture.height!==state.canvas[1]))throw Error('Texture size');
  const sprite=new PIXI.AnimatedSprite(timed);sprite.loop=false;sprite.position.set(320,280);sprite.scale.set(3);sprite.anchor.set(state.pivot[0]/state.canvas[0],state.pivot[1]/state.canvas[1]);app.stage.addChild(sprite);
  const observe=i=>{(window.S14.frames[name]??=[]).push(i);for(const e of state.events)if(e.frame===i)window.S14.events.push({state:name,name:e.name,frame:i});};
  sprite.onFrameChange=observe;observe(0);await new Promise(resolve=>{sprite.onComplete=resolve;sprite.play();});app.stage.removeChild(sprite);sprite.destroy();
 }
 window.S14.done=true;
})().catch(e=>window.S14.errors.push(String(e)));
''',encoding='utf-8')


def demo(source_pack,out,vendor=None,godot=None):
    source_pack=Path(source_pack);pack=read(source_pack);out=Path(out)
    if out.exists():raise ImageError('E_OUTPUT','Use a new demo directory; source-pack replay is deterministic.')
    if pack.get('originality',{}).get('action')!='proceed':raise ImageError('E_ORIGINAL_REQUIRED','Demo source pack must declare original artwork.')
    originality(pack['name']);out.mkdir(parents=True);(out/'sources').mkdir();sources={}
    for name,r in pack['sources'].items():
        source=(source_pack.parent/r['file']).resolve()
        if r.get('sha256') and digest(source)!=r['sha256']:raise ImageError('E_SOURCE_CHANGED','Source pack input hash changed: '+name)
        target=out/'sources'/f'{name}.png';shutil.copyfile(source,target);sources[name]=target
    portable_pack=deepcopy(pack)
    for name in portable_pack['sources']:portable_pack['sources'][name]['file']=name+'.png'
    write(out/'sources/source-pack.json',portable_pack)
    palette=[dict(name=f'color-{i+1}',hex=c,role='face' if i==7 else 'shade' if i in (1,3,9,10,13) else 'main',area_pct=0) for i,c in enumerate(pack.get('palette',PALETTE))]
    char=out/'charsheet';(char/'views').mkdir(parents=True);(char/'expressions').mkdir();views={};view_records=[]
    for name,facing in [('front','front'),('side','left'),('back','back'),('three_quarter','three_quarter_left')]:
        im=isolate_single_subject(rgba(sources[name]));transform=pack['views'][name];fixed=quantize(camera(im,transform['scale'],transform['offset']),palette);fixed.save(char/'views'/f'{name}.png');views[name]=fixed
        view_records.append(dict(name=name,facing=facing,file=f'views/{name}.png',refs_sent=pack['sources'][name].get('refs_sent',[]),source_sha=digest(sources[name]),camera=transform,size_actual=list(im.size),size_delivered=[64,64]))
    # Real palette areas are computed from delivered views, including small accents.
    arrays=[np.array(im) for im in views.values()];total=sum(np.count_nonzero(a[...,3]) for a in arrays)
    for p in palette:
        c=np.array(tuple(bytes.fromhex(p['hex'][1:])));p['area_pct']=100*sum(np.count_nonzero(np.all(a[...,:3]==c,axis=-1)&(a[...,3]>0)) for a in arrays)/max(1,total)
    write(char/'palette.json',palette);palette_image(palette).save(char/'palette.png')
    exp=pack['expressions'];raw=rgba(sources['expressions']);expressions={};exp_records=[];face=exp['target_box'];x,y,w,h=face
    for i,name in enumerate(('neutral','joy','anger','sadness','surprise','pain')):
        box=exp['source_boxes'][i];crop=quantize(raw.crop(box).resize((w,h),Image.Resampling.NEAREST),palette)
        im=views['front'].copy();im.paste(crop,(x,y));im.save(char/'expressions'/f'{name}.png');expressions[name]=im
        exp_records.append(dict(name=name,file=f'expressions/{name}.png',refs_sent=pack['sources']['expressions'].get('refs_sent',[]),fallback='local_face_composite',source_box=box,face_box=face))
    negatives=[];near=None
    if 'negative' in sources:
        (char/'controls').mkdir();negative=char/'controls/negative.png';rgba(sources['negative']).save(negative);negatives=[negative]
        near=char/'controls/near-negative.png';a=np.array(views['front']);base=a.copy()
        for before,after in [('#2B8990','#2B6BB5'),('#1B5964','#234D8A'),('#142D38','#182D59'),('#A12268','#DC761E')]:
            mask=np.all(base[...,:3]==tuple(bytes.fromhex(before[1:])),axis=-1);a[...,:3][mask]=tuple(bytes.fromhex(after[1:]))
        Image.fromarray(a).save(near)
    identity=identity_report({n:char/'views'/f'{n}.png' for n in views},negatives,near,palette)
    asym=[dict(feature='magenta stitch above character-left eye',color='#A12268',side='character_left',regions=pack.get('asymmetric_regions',{}))]
    contract=dict(version=1,name=pack['name'],canvas=[64,64],pivot=[32,60],ground_line=60,pixel=True,pixel_scale=1,alpha_mode='straight',palette='palette.json',views=view_records,expressions=exp_records,
        asymmetric_features=asym,asymmetry_qa=asymmetry_qa(views,asym),mirror_ok=False,originality=pack['originality'],identity=identity,
        expressions_qa=expressions_qa(views['front'],expressions,face),size_requested='64x64 (prompt only)',size_actual={v['name']:v['size_actual'] for v in view_records},fallback='pixel_quantize',review='pending',status='experimental')
    write(char/'charsheet.json',contract);write(char/'refset.json',dict(version=1,name=pack['name'],images=[dict(path=v['file'],sha256=digest(char/v['file']),role='identity',source='generated',licence='original generated artwork') for v in view_records],negative_images=[dict(path='controls/negative.png',sha256=digest(p)) for p in negatives],controls=dict(valid=identity['controls_valid']),visual_review=dict(status='pending')))
    sheet=Image.new('RGBA',(512,440),(21,30,43,255));d=ImageDraw.Draw(sheet);d.text((12,8),pack['name']+' / ORIGINAL WAYFINDER / 64 px',fill='#D0EFFF')
    for i,im in enumerate([*views.values(),*expressions.values()]):sheet.alpha_composite(im.resize((128,128),Image.Resampling.NEAREST),((i%4)*128,28+(i//4)*132))
    sheet.save(char/'sheet.png');write(char/'gen-manifest.json',dict(route='builtin-subscription-imagegen import',source_refs=view_records,expressions=exp_records,model_reported=None,fallback='pixel_quantize'))
    plan={};keys_dir=out/'pose-keys';keys_dir.mkdir()
    for state,config in pack['animations'].items():
        images=strip_keys(sources[state],4,1,config['scale'],config['offset'],gutter=config.get('gutter',0));folder=keys_dir/state;folder.mkdir();keys=[]
        for i,im in enumerate(images):
            im=quantize(im,palette);path=folder/f'{i:02d}.png';im.save(path)
            keys.append(dict(image=str(path.resolve()),refs_sent=pack['sources'][state].get('refs_sent',[]),points=config.get('points',[None]*4)[i]))
        plan[state]={**config,'keys':keys}
    from image_route import Request
    result=animate(None,Request('Rimewick original amber fox wayfinder',experimental=True),char/'charsheet.json',out/'anim',list(plan),plan)
    # Make source references portable after assembly; they are provenance, not a
    # trigger to regenerate. Frame assets remain local relative paths.
    for state in plan:
        file=out/'anim'/state/'anim.json';m=read(file)
        for i,r in enumerate(m.get('keys',[])):r['image']=f'../../pose-keys/{state}/{i:02d}.png'
        write(file,m)
    packed=export_engines(sorted((out/'anim').glob('*/anim.json')),out/'export',['godot4','unity','phaser-hash','phaser-array','pixi','aseprite'],pixel=True)
    shutil.copytree(out/'export',out/'godot-project',ignore=shutil.ignore_patterns('frames','*.meta','*phaser*','*pixi*','*aseprite*','unity*'))
    browser_demo(out/'phaser-demo',packed,vendor)
    icons=out/'icons';icons.mkdir();raw=rgba(sources['icons']);icon_images=[];icon_records=[]
    from game_icons import style_qa
    for i,box in enumerate(pack['icons']['source_boxes']):
        im=raw.crop(box);scale=52/max(im.size);im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.NEAREST)
        canvas=Image.new('RGBA',(64,64));canvas.paste(im,((64-im.width)//2,(64-im.height)//2));canvas=quantize(canvas,palette);canvas.save(icons/f'{i:02d}.png');icon_images.append(canvas)
        icon_records.append(dict(index=i,file=f'{i:02d}.png',item=pack['icons']['items'][i],refs_sent=pack['sources']['icons'].get('refs_sent',[])))
    token=dict(grid=64,light_deg=135,outline_px=2,outline_hex=palette[0]['hex'],palette=palette,safe_margin=4,shading='cel');write(icons/'style.json',token)
    for r in icon_records:r['style_token_sha']=key(token)
    write(icons/'iconset.json',dict(items=pack['icons']['items'],records=icon_records,style_token_sha=key(token),qa=style_qa(icon_images,token,True),status='experimental'))
    overview=Image.new('RGBA',(256,128));
    for i,im in enumerate(icon_images):overview.paste(im,((i%4)*64,(i//4)*64))
    overview.resize((768,384),Image.Resampling.NEAREST).save(icons/'sheet.png')
    tex=out/'tex';tex.mkdir();from game_tiles import repair_periodic,preview,tile_qa
    source=rgba(sources['texture']).convert('RGB').resize((256,256),Image.Resampling.NEAREST);fixed,repair=repair_periodic(source);fixed.save(tex/'texture.png');preview(fixed,tex/'preview-3x3.png');write(tex/'qa.json',repair)
    from game_sprite import sprite_check
    quality=dict(character=identity,asymmetry=contract['asymmetry_qa'],expressions=contract['expressions_qa'],animation={name:read(out/'anim'/name/'anim.json')['qa'] for name in plan},
        sprites=sprite_check(sorted((out/'anim').glob('*/frames/*.png')),pivot=[32,60],palette=palette,pixel=64),icons=read(icons/'iconset.json')['qa'],texture=repair['after'],technical_panel='pending',user_taste_axis='pending; eight moving pairs with Wilson interval required')
    write(out/'qa-summary.json',quality)
    engine_load=dict(godot4='untested',phaser='untested',pixi='untested',unity='untested')
    if godot:
        engine=Path(godot);logs=[]
        userdata=(out/'godot-userdata').resolve();userdata.mkdir()
        engine_env=dict(os.environ,APPDATA=str(userdata),LOCALAPPDATA=str(userdata))
        for args in [['--editor','--quit'],['--fixed-fps','120','--script','check_frames.gd']]:
            response=subprocess.run([str(engine),'--headless','--path',str((out/'godot-project').resolve()),*args],capture_output=True,text=True,timeout=90,env=engine_env);logs.append(response.stdout+response.stderr)
            if response.returncode or 'SCRIPT ERROR' in response.stderr:raise ImageError('E_GODOT','Godot load/playback failed.',log=logs[-1])
        (out/'godot-load.log').write_text('\n'.join(logs),encoding='utf-8')
        if 'S14_GODOT_PASS' not in logs[-1]:raise ImageError('E_GODOT','Godot did not complete every state.')
        version=logs[-1].split('S14_GODOT_PASS ',1)[1].splitlines()[0].strip();engine_load['godot4']='tested:'+version
        write(out/'godot-evidence.json',dict(version=version,engine_sha256=digest(engine),log='godot-load.log'))
        for folder in (out/'export',out/'godot-project'):
            data=read(folder/'sprites.json');data['engines']['godot4']['engine_load']=engine_load['godot4'];write(folder/'sprites.json',data)
            events=read(folder/'character.events.json');events['engine_load']=engine_load['godot4'];write(folder/'character.events.json',events)
    manifest=dict(name=pack['name'],status='experimental_preview',originality=pack['originality'],route='builtin-subscription-imagegen imported source pack',model_reported=None,
        subscription_images=pack['subscription_images'],generation_ledger=pack.get('generation_ledger',[]),generated_this_run=0,cache_replay=True,source_pack_sha=key(portable_pack),sources={n:{**pack['sources'][n],'sha256':digest(p),'file':'sources/'+p.name} for n,p in sources.items()},
        engine_load=engine_load,fallback=['pixel_quantize','nearest_pose_mesh_inbetweens','local_face_composite','periodic_texture_repair'],technical_review='pending',taste_review='pending')
    write(out/'gen-manifest.json',manifest)
    (out/'README.md').write_text(f'''# {pack['name']} — original character demo

Experimental preview, not a ship-approved character library. Read qa-summary.json
for measured failures and unassessed identity. This package does not claim the
spec-14 acceptance gates passed. No video model or paid image API was called.

* charsheet: 4 views, 6 face-composited expressions, shared 16-color palette,
  sheet, identity refset and reports. Hidden views are original inferred designs.
* anim: idle/run/attack/hurt RGBA masters, four reference keys per state,
  nearest mesh inbetweens, GIF/APNG/contact previews, timings and events.
* export: exact RGBA atlases; native Godot 4, Unity metadata, Phaser hash/array,
  Pixi and Aseprite JSON. Sidecars retain variable timing and events.
* godot-project: open project.godot, or run check_frames.gd headlessly.
* phaser-demo: serve this folder over localhost, then open index.html or
  pixi.html. Local pinned libraries belong in vendor/. No CDN requests occur.
* icons: eight original inventory icons and measured style-token QA.
* tex: periodic repaired texture and 3x3 inspection preview.
* sources: original subscription-generated source images and source-pack data.

Generated images: {pack['subscription_images']} of the authorized 40; this replay
uses zero new images. Pixel style was quantized locally and is not claimed to
be hand-authored native pixel art. All motion canvases/pivots are fixed. Each
source pose strip has one recorded scale/ground transform, never per-frame bbox
recentering. Sprite GIF is binary-alpha; APNG/PNG retain RGBA.

Engine load evidence: {json.dumps(engine_load)}. Unity is format-level only.
Human taste/playback and independent technical-panel review remain pending.
Rebuild to a fresh directory with imagegen.py demo game --source-pack PATH
--out DIR --experimental. Identical source-pack inputs yield identical assets.
''',encoding='utf-8')
    return manifest
