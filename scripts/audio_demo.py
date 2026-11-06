"""Original Rime snow-mountain pack. Offline rehearsal is never Suno delivery."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import numpy as np
from PIL import Image
from audio_loop import encode,normalise,export,decode,check
from audio_engine import verify_godot
from audio_jingle import split_sheet
from audio_beat_sync import schedule,retime_manifest,verify_motion,export_clock
from audio_provenance import artifact,audit
from image_common import write,read,digest,ImageError


def rehearsal_loop(battle=False):
    """Original deterministic calibration music, explicitly synthetic_test."""
    t=np.arange(384000)/48000
    notes=(110,220,261.5,329.5);phases=(.8,2.1,3.8,5.2)
    x=sum(.1*np.sin(2*np.pi*f*t+p) for f,p in zip(notes,phases))
    pulse=t%.5;x+=.12*np.sin(2*np.pi*80*pulse)*np.exp(-20*pulse)*np.minimum(pulse/.004,1)
    x+=.015*np.sin(2*np.pi*6000*t)*(.65+.35*np.cos(2*np.pi*t*4))
    if battle:x+=.018*np.sin(2*np.pi*440*t+1.7)*np.sin(np.pi*t/2)**2
    return normalise(np.repeat(x[:,None],2,axis=1),-16)[0]


def rehearsal_sheet():
    pieces=[]
    for index in range(5):
        t=np.arange(48000)/48000;f=(440,523.25,329.63,659.25,880)[index]
        x=.4*np.sin(2*np.pi*f*t)*np.minimum(t/.003,1)*np.exp(-7*t)
        pieces.extend([x,np.zeros(24000)])
    return np.repeat(np.concatenate(pieces)[:,None],2,axis=1)


def prepare_sprite(sprite_pack,project,analysis):
    from game_engines import export_engines
    stage=project.parent/'retimed-sprite';stage.mkdir(exist_ok=True);manifests=[];syncs={};qa={}
    for state in ('idle','attack'):
        source=Path(sprite_pack)/'anim'/state/'anim.json';anim=read(source)
        sync=schedule(anim,analysis,2);adjusted=retime_manifest(anim,sync)
        frames=[Image.open(source.parent/f['file']).convert('RGBA') for f in anim['frames']]
        result=verify_motion(adjusted,frames);qa[state]=result;sync['motion_qa']=result
        adjusted['qa']=result;dest=stage/state
        shutil.copytree(source.parent,dest,dirs_exist_ok=True);write(dest/'anim.json',adjusted);manifests.append(dest/'anim.json');syncs[state]=sync
    # Rehearsal explicitly records any failed/unassessed source motion.
    export_engines(manifests,project,['godot4'],allow_qa_fail=True)
    write(project/'beat-sync.json',dict(states=syncs,runtime_av_sync='untested'));export_clock(project/'audio_clock.gd')
    return qa


def scene(project):
    (project/'demo.gd').write_text('''extends Node2D
var explore: AudioStreamPlayer
var battle: AudioStreamPlayer
var cue: AudioStreamPlayer
var sprite: AnimatedSprite2D
var clock_driver: Node
var schedules: Dictionary
var switched: bool = false
var signaled: bool = false
var attacks: int = 0
var hits: Array = []
var elapsed: float = 0
func _ready():
    schedules = JSON.parse_string(FileAccess.get_file_as_string("res://beat-sync.json"))["states"]
    sprite = AnimatedSprite2D.new()
    sprite.sprite_frames = load("res://character.tres")
    assert(sprite.sprite_frames.has_animation("idle"))
    assert(sprite.sprite_frames.has_animation("attack"))
    sprite.position = Vector2(320, 240)
    sprite.scale = Vector2(3, 3)
    sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    sprite.animation = "idle"
    add_child(sprite)
    explore = AudioStreamPlayer.new()
    battle = AudioStreamPlayer.new()
    cue = AudioStreamPlayer.new()
    for p in [explore, battle, cue]: add_child(p)
    explore.stream = load("res://explore.ogg")
    battle.stream = load("res://battle.ogg")
    cue.stream = load("res://confirm.wav")
    battle.volume_db = -80
    explore.play()
    battle.play()
    clock_driver = load("res://audio_clock.gd").new()
    clock_driver.player = explore
    clock_driver.sprite = sprite
    clock_driver.loop_duration = explore.stream.get_length()
    clock_driver.timeline = schedules.idle
    clock_driver.process_priority = -100
    add_child(clock_driver)
    clock_driver.beat_event.connect(_hit)
    queue_redraw()
func _draw():
    draw_rect(Rect2(0,0,640,360),Color("142838"))
    draw_colored_polygon(PackedVector2Array([Vector2(0,260),Vector2(150,50),Vector2(260,210),Vector2(410,30),Vector2(640,260)]),Color("bedee0"))
    draw_rect(Rect2(0,270,640,90),Color("e6f2eb"))
func _hit(_name: String, audio_ms: float, target_ms: float):
    hits.append({"audio_ms":audio_ms,"target_ms":target_ms,"offset_ms":audio_ms-target_ms})
    print("S15_HIT ", JSON.stringify(hits[-1]))
func _process(delta: float):
    elapsed += delta
    if clock_driver == null: return
    var audio_ms: float = clock_driver.current_audio_ms
    if not switched and audio_ms >= 8000:
        explore.volume_db = -80
        battle.volume_db = 0
        switched = true
        print("S15_SWITCH ", audio_ms)
    if not signaled and audio_ms >= 10000:
        cue.play()
        signaled = true
        print("S15_JINGLE ", audio_ms)
    var attack_active: bool = (audio_ms >= 3600 and audio_ms < 4600) or (audio_ms >= 15600 and audio_ms < 16600)
    sprite.animation = "attack" if attack_active else "idle"
    clock_driver.timeline = schedules.attack if attack_active else schedules.idle
    if elapsed >= 30:
        var status: String = clock_driver.runtime_status()
        var sync_pass: bool = hits.size() >= 2
        for h in hits: sync_pass = sync_pass and abs(h.offset_ms) <= 1000.0/60.0
        if status == "measured": status = "tested" if sync_pass else "failed"
        var report = {"runtime_av_sync":status,"sync_pass":sync_pass,"events":hits,"switched":switched,"jingle":signaled,"seconds":elapsed}
        var file = FileAccess.open("res://runtime-events.json",FileAccess.WRITE)
        file.store_string(JSON.stringify(report,"  "))
        file.close()
        print("S15_SCENE_DONE ",JSON.stringify(report))
        set_process(false)
        clock_driver.set_process(false)
        clock_driver.player = null
        clock_driver.sprite = null
        clock_driver.timeline = {}
        clock_driver.queue_free()
        for p in [explore,battle,cue]:
            p.stop()
        # Allow the real audio mixing thread to retire Vorbis playbacks before
        # clearing the resources; a render frame alone can precede the next mix.
        await get_tree().create_timer(0.25).timeout
        for p in [explore,battle,cue]:
            p.stream = null
            p.queue_free()
        sprite.sprite_frames = null
        sprite.queue_free()
        explore = null
        battle = null
        cue = null
        sprite = null
        clock_driver = null
        await get_tree().process_frame
        get_tree().call_deferred("quit",0)
''',encoding='utf-8')


def build(out,sprite_pack,inputs=None,rehearsal=False,godot=None):
    out=Path(out)
    if out.exists():
        if not (out/'gen-manifest.json').exists():raise ImageError('E_CACHE','Previous attempt incomplete; use a fresh output directory')
        manifest=read(out/'gen-manifest.json')
        if all((out/p).is_file() and digest(out/p)==sha for p,sha in manifest['output_hashes'].items()):return dict(manifest,cache='hit')
        raise ImageError('E_CACHE','Existing demo is incomplete/modified; use another output directory')
    if not rehearsal and inputs is None:raise ImageError('E_LIVE_INPUT','Need selected downloaded loop files and a five-cue sheet; streams cannot be delivered')
    out.mkdir(parents=True);audio=out/'audio';bgm=audio/'bgm';sfx=audio/'sfx';theme=audio/'theme'
    for folder in (bgm,sfx,theme):folder.mkdir(parents=True)
    analysis=dict(beats=[dict(time_s=i*.5,bar_position=i%4+1) for i in range(260)],bpm=120,duration_s=130)
    records=[];reports={}
    for name in ('explore','battle'):
        if rehearsal:
            source=out/(name+'-test-source.wav');encode(source,rehearsal_loop(name=='battle'))
            provenance=dict(source='synthetic_test',measured_bpm=120)
        else:
            entry=inputs[name];source=Path(entry['file']);provenance=entry['provenance'];analysis=inputs['analysis']
        # Stable output names, while raw selected source lineage remains recorded.
        temp=out/(name+'.wav');shutil.copyfile(source,temp)
        reports[name]=export(temp,bgm,analysis['bpm'],provenance=provenance)
        temp.unlink()
        if not rehearsal:
            for fmt in ('wav','ogg'):
                records.append(artifact(bgm/(name+'.'+fmt),provenance,dict(bpm=analysis['bpm']),operations=['loop export']))
    sheet=out/'jingle-sheet.wav'
    if rehearsal:encode(sheet,rehearsal_sheet())
    else:shutil.copyfile(inputs['sheet']['file'],sheet)
    reports['sfx']=split_sheet(sheet,['level-up','victory','failure','pickup','confirm'],sfx)
    if not rehearsal:
        source_info=inputs['sheet']['provenance']
        records.append(artifact(sheet,source_info,{},operations=['downloaded combined sprite']))
        for name,cue in reports['sfx']['cues'].items():
            records.append(artifact(sfx/(name+'.wav'),source_info,dict(duration_ms=cue['end_ms']-cue['start_ms'],**{k:cue['post']['measured'].get(k) for k in ('lufs','true_peak')}),
                parents=[digest(sheet)],operations=[dict(operation='silence split and cleanup',start_ms=cue['start_ms'],end_ms=cue['end_ms'])]))
    write(theme/'preview.json',dict(status='synthetic_rehearsal' if rehearsal else 'stream_preview_only',clip_id=None if rehearsal else inputs.get('theme_clip_id')))
    project=out/'godot-project'
    reports['motion']=prepare_sprite(sprite_pack,project,analysis)
    for p in bgm.iterdir():
        if p.is_file():shutil.copyfile(p,project/p.name)
    for p in sfx.glob('*.wav'):shutil.copyfile(p,project/p.name)
    scene(project)
    if godot:
        reports['engine']=verify_godot(project,godot)
        env=dict(os.environ,APPDATA=str((project/'.engine-state').resolve()),LOCALAPPDATA=str((project/'.engine-state').resolve()))
        result=subprocess.run([str(godot),'--headless','--path',str(project.resolve()),'--max-fps','120'],capture_output=True,text=True,env=env,timeout=50)
        logs=result.stdout+result.stderr;(out/'godot-scene.log').write_text(logs,encoding='utf-8')
        reports['runtime']=read(project/'runtime-events.json') if (project/'runtime-events.json').exists() else dict(runtime_av_sync='untested',reason='Scene produced no timing log')
        reports['runtime']['exit_code']=result.returncode
        audio_log=logs.replace('ERROR: Failed to read the root certificate store.','')
        reports['runtime']['audio_errors']=bool('ERROR' in audio_log or 'WARNING' in audio_log)
    manifest=dict(status='REHEARSAL_NOT_LIVE' if rehearsal else 'experimental_pending_review',scene='snow-mountain',character='Rime, the original amber courier',
        suno=dict(artifacts=records),reports=reports,credits_used=dict(song=0,download=0),cache='miss')
    if not rehearsal:
        # Fail closed until every duplicated/exported/cut file has full lineage.
        report=audit(out,manifest);manifest['provenance_audit']=report
        if report['status']!='PASS':manifest['status']='FAIL_PROVENANCE'
    (out/'README.md').write_text('Rime — Glass Ridge\n\n'+('OFFLINE REHEARSAL ONLY. Audio is deterministic synthetic test material, not Suno output.\n' if rehearsal else 'Experimental live candidate; check all reports before use.\n')+
        'Open godot-project/project.godot in Godot 4.7.2. Idle follows the audio clock, two attack windows target downbeats, exploration changes to battle at 8s, confirm at 10s. Scene exits after 30s.\n'+
        'JSON/Godot loop ends are exclusive; RIFF smpl end is inclusive. Unity/FMOD/Wwise engine loading untested. Runtime audio sync is untested when the dummy playback clock does not advance.\n'+
        'This rehearsal has zero Suno credits; live generation accounting is in the separate live manifest.\n',encoding='utf-8')
    manifest['output_hashes']={str(p.relative_to(out)).replace('\\','/'):digest(p) for p in sorted(out.rglob('*')) if p.is_file() and '.godot' not in p.parts and '.engine-state' not in p.parts and p.name!='gen-manifest.json'}
    write(out/'gen-manifest.json',manifest);return manifest


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('kind',choices=['game']);p.add_argument('--scene',choices=['snow-mountain'],default='snow-mountain')
    p.add_argument('--out',type=Path,required=True);p.add_argument('--sprite-pack',type=Path,required=True);p.add_argument('--inputs',type=Path)
    p.add_argument('--offline-rehearsal',action='store_true');p.add_argument('--experimental',action='store_true');p.add_argument('--godot',type=Path);a=p.parse_args(argv)
    try:
        if not a.experimental:raise ImageError('E_EXPERIMENTAL','Demo requires --experimental')
        r=build(a.out,a.sprite_pack,read(a.inputs) if a.inputs else None,a.offline_rehearsal,a.godot)
        print(json.dumps(dict(status=r['status'],cache=r['cache'],reports=r['reports'])));return 0
    except (ValueError,OSError,subprocess.SubprocessError) as e:
        print(json.dumps(dict(error=getattr(e,'error',dict(code='E_DEMO',message=str(e))))));return 2


if __name__=='__main__':raise SystemExit(main())
