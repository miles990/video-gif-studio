"""Run real Godot import and AudioStream assertions; never infer tested status."""
from pathlib import Path
import os
import subprocess
from image_common import read,write,ImageError


def verify_godot(project,executable,play_cycles=2):
    project=Path(project).resolve();metas=sorted(project.glob('*.loop.json'))
    if not metas:raise ValueError('No loop sidecars in project root')
    expected={p.stem.removesuffix('.loop'):read(p) for p in metas}
    write(project/'audio-check.json',expected)
    if not (project/'project.godot').exists():
        (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Audio Pack"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    script='''extends SceneTree
func _initialize():
    call_deferred("verify")
func verify():
    var records = JSON.parse_string(FileAccess.get_file_as_string("res://audio-check.json"))
    var longest: float = 0
    var players: Array = []
    for name in records:
        var record = records[name]
        var duration: float = record.loop_end_samples / float(record.sample_rate)
        longest = max(longest, duration)
        for ext in ["wav", "ogg"]:
            var stream = load("res://" + name + "." + ext)
            assert(stream != null)
            assert(abs(stream.get_length() - duration) <= 0.001)
            if ext == "ogg":
                assert(stream is AudioStreamOggVorbis)
                assert(stream.loop)
                assert(abs(stream.loop_offset) <= 0.00001)
                assert(abs(stream.bpm - record.bpm) <= 0.001)
                assert(stream.bar_beats == record.beats_per_bar)
                assert(stream.beat_count == round(duration * record.bpm / 60.0))
            else:
                assert(stream is AudioStreamWAV)
                assert(stream.loop_mode == AudioStreamWAV.LOOP_FORWARD)
                assert(stream.loop_begin == 0)
                assert(stream.loop_end == record.loop_end_samples)
            var player = AudioStreamPlayer.new()
            root.add_child(player)
            player.stream = stream
            player.volume_db = -60
            player.play()
            players.append(player)
    await create_timer(longest * CYCLES + 0.05).timeout
    for player in players:
        assert(player.playing)
        player.stop()
    await create_timer(0.25).timeout
    for player in players:
        player.stream = null
        player.queue_free()
    players.clear()
    await process_frame
    print("S15_AUDIO_PASS ", Engine.get_version_info()["string"])
    call_deferred("quit", 0)
'''.replace('CYCLES',str(int(play_cycles)))
    (project/'check_audio.gd').write_text(script,encoding='utf-8')
    commands=[[str(executable),'--headless','--path',str(project),'--import'],
              [str(executable),'--headless','--path',str(project),'--script','check_audio.gd','--quit-after','10000']]
    logs=[]
    env=dict(os.environ)
    state=project/'.engine-state';state.mkdir(exist_ok=True)
    env.update(APPDATA=str(state),LOCALAPPDATA=str(state))
    timeout=max(v['loop_end_samples']/v['sample_rate'] for v in expected.values())*play_cycles+60
    for cmd in commands:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,env=env)
        logs.append(r.stdout+r.stderr)
        audio_log=logs[-1].replace('ERROR: Failed to read the root certificate store.','')
        if r.returncode or 'ERROR' in audio_log or 'WARNING' in audio_log:
            write(project/'engine-check.json',dict(engine_load='failed',logs=logs))
            raise ImageError('E_ENGINE_LOAD','Godot reported errors/warnings',logs=logs)
    if 'S15_AUDIO_PASS 4.7.2' not in logs[-1]:raise ImageError('E_ENGINE_VERSION','Expected actual Godot 4.7.2 successful assertion run')
    result=dict(engine_load='tested:4.7.2',play_cycles=play_cycles,logs=logs,
                environment_diagnostics=['Windows root certificate store unavailable'] if any('root certificate' in s for s in logs) else [])
    write(project/'engine-check.json',result)
    for p in metas:
        m=read(p);m['engine_load']['godot4']='tested:4.7.2';write(p,m)
    return result
