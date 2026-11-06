"""Offline one-shot cleanup, five-cue sprite splitting and VFX event alignment."""
import argparse
from pathlib import Path
import json
import numpy as np
from audio_loop import RATE,decode,encode,normalise,loudness
from image_common import write,read,ImageError


def regeneration_request(name,theme_key='Am',bpm=120):
    """An exact unsubmitted request; caller still needs spending authorization."""
    from audio_measure import key_name
    descriptions={
        'level-up':'One isolated 2-second level-up jingle: ascending A C E A bell motif',
        'victory':'One isolated 3-second victory jingle: triumphant A C E A motif resolving to a minor triad',
        'failure':'One isolated 2-second failure jingle: descending E D C A bell motif, soft low strings',
        'pickup':'One isolated 0.5-second item pickup UI sound: two sparkling plucked notes E A, crisp instant onset',
        'confirm':'One isolated 0.4-second confirmation UI sound: soft plucked A C E minor chord, crisp instant onset',
    }
    if name not in descriptions:raise ValueError('Unknown cue')
    key=key_name(theme_key)
    return dict(tool='sounds_create',params=dict(
        description=f'{descriptions[name]}. In {key} at {bpm} BPM. Preserve a natural reverb decay, then silence. No repeats, no background music, no voice.',
        key=key,tempo=bpm,loop=False,title=f'Rime Glass Ridge {name} fix',
        idempotency_key=f's15-fix-{name}-{key}-{bpm}-v1'),submitted=False)


def correct_key(x,theme_key='Am',target=-12):
    """Conservative chroma-based correction, <=2 semitones, no paid fallback.

    Transposition preserves mode. A parallel major cannot be turned into minor
    by shifting its root; compatible relationships still retain spec_mismatch.
    """
    from audio_measure import measure,key_name,relation,NAMES
    from audio_loop import ffmpeg_pcm
    theme=key_name(theme_key);before=measure(x);key=before['key']
    report=dict(theme_key=theme,before=before,theme_relation=relation(theme,key),
                key_source='local_estimate',listening_review='pending',pitch_semitones=0)
    if key is None or key.endswith('m')!=theme.endswith('m'):
        return None,dict(report,status='regenerate_needed',reason='Unknown key or mode mismatch; transposition cannot change mode')
    shift=(NAMES.index(theme.rstrip('m'))-NAMES.index(key.rstrip('m'))+6)%12-6
    if abs(shift)>2:
        return None,dict(report,status='regenerate_needed',reason='Required transposition exceeds two semitones',required_semitones=shift)
    y=x
    if shift:
        ratio=2**(shift/12)
        # Rubberband preserves tempo. Missing filter is a local failure, never a paid retry.
        y=ffmpeg_pcm(x,f'rubberband=tempo=1:pitch={ratio:.12f}')
    duration_error=abs(len(y)-len(x))/48
    y,post=cleanup(y,target)
    after=measure(y)
    levels=post['measured']
    quality=dict(duration_error_ms=duration_error,key_match=after['key']==theme,
                 true_peak=levels['true_peak'],lufs=levels['lufs'],dc=post['dc'],
                 release_peak=float(np.max(abs(y[-480:]))))
    passed=(duration_error<=10 and quality['key_match'] and levels['true_peak'] is not None
            and levels['true_peak']<=-1 and levels['lufs'] is not None
            and abs(levels['lufs']-target)<=1 and post['dc']<=.001 and quality['release_peak']<=.001)
    report.update(status='PASS' if passed else 'regenerate_needed',after=after,quality=quality,
                  cleanup=post,pitch_semitones=shift,method='ffmpeg rubberband' if shift else 'cleanup only')
    return (y if passed else None),report


def regions(x,threshold_db=-50,gap_ms=400):
    signal=x-np.median(x,axis=0)
    active=np.flatnonzero(np.max(np.abs(signal),axis=1)>10**(threshold_db/20))
    if not len(active):return []
    groups=np.split(active,np.where(np.diff(active)>round(gap_ms*RATE/1000))[0]+1)
    return [(max(0,int(g[0])-240),min(len(x),int(g[-1])+241)) for g in groups]


def cleanup(x,target=-12,fade_ms=20):
    if not 5<=fade_ms<=30:raise ValueError('Fade must be 5..30ms')
    x=np.asarray(x,dtype=float);x=x-np.median(x,axis=0)
    spans=regions(x,gap_ms=1e9)
    if not spans:raise ValueError('No audible one-shot')
    start,end=spans[0];y=x[start:end].copy();y-=np.mean(y,axis=0)
    # Preserve decay through -50 dBFS, then add a quiet 10ms release guard.
    y=np.pad(y,((0,480),(0,0)));fade=min(len(y),round(fade_ms*48))
    y[-fade:]*=np.linspace(1,0,fade)[:,None]**2
    measured=np.pad(y,((0,max(0,144000-len(y))),(0,0)))
    normalized,report=normalise(measured,target)
    y=normalized[:len(y)];y[-480:]=0
    active=np.flatnonzero(np.max(np.abs(y),axis=1)>10**(-50/20))
    return y,dict(trim_start_samples=start,trim_end_samples=end,fade_ms=fade_ms,
        onset_ms=float(active[0]/48) if len(active) else None,dc=float(np.max(np.abs(y.mean(axis=0)))),
        measured=loudness(np.pad(y,((0,max(0,144000-len(y))),(0,0)))),normalization=report)


def split_sheet(source,names,out,target=-12,requested_key=None,theme_key=None,bgm_lufs=None):
    from audio_measure import measure,relation,key_name
    if len(names)!=len(set(names)) or any(not n.replace('-','').replace('_','').isalnum() for n in names):raise ValueError('Unique safe cue names required')
    x=decode(source);spans=regions(x)
    if len(spans)!=len(names):raise ImageError('E_SPRITE_COUNT',f'Expected {len(names)} isolated sounds, found {len(spans)}',regions_samples=spans)
    out=Path(out);out.mkdir(parents=True,exist_ok=True);records={};howler={}
    for name,(start,end) in zip(names,spans):
        y,report=cleanup(x[start:end],target);encode(out/(name+'.wav'),y)
        report['musical']=measure(y)
        report['measured_key']=report['musical']['key'];report['key_source']='local_estimate'
        report['spec_mismatch']=requested_key is not None and key_name(requested_key)!=report['measured_key']
        report['theme_key_relation']=relation(theme_key,report['measured_key']) if theme_key else None
        records[name]=dict(start_ms=start/48,end_ms=end/48,post=report,file=name+'.wav')
        howler[name]=[start/48,(end-start)/48]
    levels=[r['post']['measured']['lufs'] for r in records.values()]
    spread=max(levels)-min(levels)
    compatible=all(not r['post']['spec_mismatch'] and r['post']['theme_key_relation'] not in ('unknown','conflict') for r in records.values())
    relative=all(2<=v-bgm_lufs<=6 for v in levels) if bgm_lufs is not None else None
    result=dict(cues=records,sprite=howler,source_file=str(Path(source).name),sample_rate=RATE,
                group_lufs_spread=spread,bgm_relative_pass=relative,key_compatible=compatible,
                status='PASS' if spread<=2 and compatible and relative is not False else 'FAIL')
    write(out/'audio-sprite.json',result);return result


def align_event(animation,event_name,onset_ms,sync_point_ms=None):
    events=[e for e in animation.get('events',[]) if e.get('name')==event_name]
    if len(events)!=1:raise ValueError('Exactly one matching sprite event required')
    frame=events[0]['frame'];at=sum(f['duration_ms'] for f in animation['frames'][:frame])
    anchor=onset_ms if sync_point_ms is None else sync_point_ms
    start=at-anchor
    if start<0:raise ImageError('E_PREROLL','Audio sync point needs preroll before animation')
    return dict(event=event_name,event_frame=frame,event_ms=at,audio_start_ms=start,
                sync_point_ms=anchor,onset_ms=onset_ms,offset_ms=start+anchor-at)


def godot_event_library(out,cue,alignment):
    # Consumer node supplies play_cue(name); this is a real Animation method track.
    text='''[gd_resource type="AnimationLibrary" load_steps=2 format=3]
[sub_resource type="Animation" id="cue"]
resource_name = "cue"
length = LENGTH
tracks/0/type = "method"
tracks/0/path = NodePath(".")
tracks/0/keys = {"times": PackedFloat32Array(TIME), "transitions": PackedFloat32Array(1), "values": [{"method": &"play_cue", "args": [CUE]}]}
[resource]
_data = {&"cue": SubResource("cue")}
'''.replace('LENGTH',str(max(.1,(alignment['event_ms']+100)/1000))).replace('TIME',str(alignment['audio_start_ms']/1000)).replace('CUE',json.dumps(cue))
    Path(out).write_text(text,encoding='utf-8')


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--names',default='level-up,victory,failure,pickup,confirm');p.add_argument('--experimental',action='store_true');a=p.parse_args(argv)
    try:
        if not a.experimental:raise ImageError('E_EXPERIMENTAL','Jingle post requires --experimental')
        print(json.dumps(split_sheet(a.source,a.names.split(','),a.out)));return 0
    except (ValueError,OSError) as e:print(json.dumps(dict(error=getattr(e,'error',dict(code='E_AUDIO',message=str(e))))));return 2


if __name__=='__main__':raise SystemExit(main())
