"""Audio-clock driven SpriteFrames schedules, with integer exposure allocation."""
import copy
import bisect
from pathlib import Path
import numpy as np
from audio_score import beat_map
from image_common import ImageError,write


def allocate(weights,duration_ms):
    if not weights or min(weights)<=0 or duration_ms<=0:raise ValueError('Positive frame weights and cycle duration required')
    edges=np.rint(np.r_[0,np.cumsum(weights)/sum(weights)*duration_ms]).astype(int)
    durations=np.diff(edges).tolist()
    if min(durations)<=0:raise ImageError('E_TIMING','Beat interval would erase a frame; use more beats')
    return durations


def schedule(animation,analysis,beats_per_cycle=2):
    if not isinstance(beats_per_cycle,int) or beats_per_cycle<1:raise ValueError('Integer beats per cycle required')
    m=beat_map(analysis) if 'beats' in analysis else analysis
    beats=m['beats_ms'];down=m['downbeats_ms'];weights=[f['duration_ms'] for f in animation['frames']]
    if len(beats)<beats_per_cycle+1 or any(b<=a for a,b in zip(beats,beats[1:])):raise ValueError('Strictly increasing measured beat times required')
    cycles=[];hits=[e for e in animation.get('events',[]) if e['name']=='hit']
    if hits:
        hit=hits[0]['frame']
        if not 0<hit<len(weights):raise ValueError('Hit requires anticipation frames')
        pre=sum(weights[:hit]);post=sum(weights[hit:]);adjusted=list(weights);expanded=False
        if pre<.4*post:
            factor=.4*post/pre;adjusted[:hit]=[w*factor for w in adjusted[:hit]];expanded=True
            beats_per_cycle=max(beats_per_cycle,2)
        for target in down:
            i=bisect.bisect_left(beats,target)
            if i+beats_per_cycle>=len(beats):continue
            duration=beats[i+beats_per_cycle]-beats[i];durations=allocate(adjusted,duration)
            # Exact target anchor, independent of every previous animation cycle.
            start=round(target)-sum(durations[:hit])
            if start<0:continue
            cycles.append(dict(start_ms=start,end_ms=start+sum(durations),duration_ms=durations,
                event=dict(name='hit',frame=hit,target_ms=target,actual_ms=start+sum(durations[:hit]),
                           offset_ms=start+sum(durations[:hit])-target)))
    else:
        expanded=False
        for i in range(0,len(beats)-beats_per_cycle,beats_per_cycle):
            start=round(beats[i]);end=round(beats[i+beats_per_cycle]);durations=allocate(weights,end-start)
            cycles.append(dict(start_ms=start,end_ms=end,duration_ms=durations))
    return dict(status='experimental',state=animation['state'],clock='audio_playback',beats_per_cycle=beats_per_cycle,
        cycles=cycles,anticipation_expanded=expanded,runtime_av_sync='untested',motion_qa='required after retiming',
        downbeats_ms=down,source_bpm=m.get('bpm'),uses_bar_position=True)


def frame_at(schedule,audio_ms):
    cycles=schedule['cycles'];starts=[c['start_ms'] for c in cycles];i=bisect.bisect_right(starts,audio_ms)-1
    if i<0:return None
    cycle=cycles[i]
    if audio_ms>=cycle['end_ms']:return None
    edges=np.cumsum(cycle['duration_ms']);frame=bisect.bisect_right(edges,audio_ms-cycle['start_ms'])
    return dict(cycle=i,frame=frame)


def retime_manifest(animation,sync):
    if not sync['cycles']:raise ValueError('No complete beat cycle')
    result=copy.deepcopy(animation);durations=sync['cycles'][0]['duration_ms']
    for f,ms in zip(result['frames'],durations):f['duration_ms']=ms
    for e in result.get('events',[]):e['time_ms']=sum(durations[:e['frame']])
    result['beat_sync']=dict(beats_per_cycle=sync['beats_per_cycle'],clock='audio_playback',motion_qa='pending')
    return result


def verify_motion(animation,frames):
    from game_animation import motion_qa
    return motion_qa(frames,animation)


def drift_report(actual,target,tolerance_ms=5):
    if len(actual)!=len(target):raise ValueError('Events and downbeats must pair one-to-one')
    errors=[abs(a-b) for a,b in zip(actual,target)]
    return dict(status='PASS' if errors and max(errors)<=tolerance_ms else 'FAIL',max_error_ms=max(errors,default=None),errors_ms=errors)


def export_clock(path):
    Path(path).write_text('''extends Node
# Drive frames from audio position. Never advance animation using delta/fps.
var player: AudioStreamPlayer
var sprite: AnimatedSprite2D
var timeline: Dictionary
var loop_duration: float = 0.0
var previous_position: float = 0.0
var loop_count: int = 0
var clock_advanced: bool = false
var current_audio_ms: float = 0.0
var last_event: String = ""
signal beat_event(name: String, audio_ms: float, target_ms: float)
func audio_time_ms() -> float:
    var pos: float = player.get_playback_position()
    if pos > previous_position + 0.0001:
        clock_advanced = true
    if loop_duration > 0 and pos + loop_duration * 0.5 < previous_position:
        loop_count += 1
    previous_position = pos
    return (pos + loop_count * loop_duration + AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()) * 1000.0
func _process(_delta: float):
    if player == null or sprite == null or timeline.is_empty():
        return
    var audio_ms: float = audio_time_ms()
    current_audio_ms = audio_ms
    for cycle in timeline.cycles:
        if audio_ms < cycle.start_ms or audio_ms >= cycle.end_ms:
            continue
        var elapsed: float = audio_ms - cycle.start_ms
        var edge: float = 0
        for i in range(cycle.duration_ms.size()):
            edge += cycle.duration_ms[i]
            if elapsed < edge:
                sprite.set_frame_and_progress(i, 0)
                if cycle.has("event") and i == int(cycle.event.frame):
                    var token: String = str(cycle.start_ms)
                    if token != last_event:
                        last_event = token
                        beat_event.emit(cycle.event.name, audio_ms, cycle.event.target_ms)
                return
func runtime_status() -> String:
    return "measured" if clock_advanced else "untested"
''',encoding='utf-8')
