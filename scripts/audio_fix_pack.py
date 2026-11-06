"""Offline experimental S-15 repair pack from existing licensed downloads.

No MCP transport, credentials, generation or downloads. The partial five-cue
status is explicit; successful engine playback cannot certify S-178 completion.
"""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
import numpy as np
from audio_loop import decode,encode,export,check
from audio_loop_make import make_loop
from audio_variants import align_to_loop,switches
from audio_jingle import correct_key,cleanup,regeneration_request
from audio_measure import measure
from audio_grid import grid
from audio_provenance import artifact,audit
from audio_engine import verify_godot
from audio_demo import scene
from audio_beat_sync import schedule,export_clock
from image_common import read,write,digest,ImageError


def next_switch_time(after_ms,points_ms,cycle_ms):
    """Select a verified phase in a later cycle; wrap is not implicitly allowed."""
    if cycle_ms<=0 or not points_ms or any(not 0<=p<cycle_ms for p in points_ms):
        raise ValueError('Need declared switch phases inside the cycle')
    return min(p+max(0,math.ceil((after_ms-p)/cycle_ms))*cycle_ms for p in points_ms)


def build(original,sources,out,godot=None):
    original,sources,out=map(Path,(original,sources,out))
    if out.exists():raise ValueError('Use a new output directory; preserve previous evidence')
    old=read(original/'gen-manifest.json');out.mkdir(parents=True)
    bgm=out/'audio/bgm';sfx=out/'audio/sfx';project=out/'godot-project';evidence=out/'evidence'
    for p in (bgm,sfx,evidence):p.mkdir(parents=True)
    records=[];reports={};receipts={};pcm={}
    # Copy only the existing scene/sprite resources, excluding stale audio/QA/cache.
    def ignore(folder,names):
        return [n for n in names if n in ('.godot','.engine-state') or n.endswith(('.wav','.ogg','.loop.json','.wav.import','.ogg.import'))
                or n in ('audio-check.json','engine-check.json','runtime-events.json','beat-sync.json')]
    shutil.copytree(original/'godot-project',project,ignore=ignore)
    for name in ('explore','battle'):
        source=sources/(name+'-0.wav');sha=digest(source)
        receipt=next(r for r in old['suno']['artifacts'] if r['sha256']==sha and not r.get('operations'))
        receipts[name]=receipt;records.append(receipt)
        pcm[name]=decode(source)
        prior=original/'audio/bgm'/(name+'.wav')
        reports[name+'_before']=check(decode(prior),120,measured_bpm=measure(decode(prior))['bpm'])
    explore,explore_make=make_loop(pcm['explore'])
    initial_battle,battle_make=make_loop(pcm['battle'])
    battle,alignment=align_to_loop(explore,pcm['battle'])
    reports.update(explore_make=explore_make,battle_make=battle_make,alignment=alignment,
                   transitions_before=old.get('reports',{}).get('variants'),
                   initial_processed_transitions=switches(explore,initial_battle,120))
    processed={'explore':explore,'battle':battle}
    for name,y in processed.items():
        recipe=explore_make if name=='explore' else alignment
        source=evidence/(name+'.wav');encode(source,y)
        # Measure the processed cut too; preserve the older estimator's disagreement.
        output_grid=grid(decode(source));legacy=measure(decode(source))
        reports[name+'_output_measurements']=dict(spectral_flux=output_grid,legacy_rms_chroma=legacy)
        provenance=dict(receipts[name],measured_bpm=output_grid['bpm'])
        result=export(source,bgm,120,provenance=provenance)
        source.unlink()  # Only intermediate created in this new output directory.
        reports[name+'_after']=result
        for fmt in ('wav','ogg'):
            path=bgm/(name+'.'+fmt)
            records.append(artifact(path,provenance,dict(bpm=output_grid['bpm'],key=measure(y)['key'],meter='4/4',duration_ms=len(y)/48,
                        **result['formats'][fmt]['qa']['checks']['loudness']),
                        parents=[receipts[name]['sha256']],operations=[dict(operation='make aligned loop',**recipe['selected'])]))
    # Recheck actual decoded delivery formats, including crossfades and hard cuts.
    reports['transitions_after']={fmt:switches(decode(bgm/('explore.'+fmt)),decode(bgm/('battle.'+fmt)),120) for fmt in ('wav','ogg')}
    if any(r['status']!='PASS' for r in reports['transitions_after'].values()):
        raise ImageError('E_VARIANT_ENCODE','Decoded transitions failed',reports=reports['transitions_after'])
    cue_reports={};cue_audio={}
    for name,filename in [('level-up','level-up-0.wav'),('victory','victory-1.wav'),('confirm','confirm-0.wav')]:
        source=sources/filename;sha=digest(source);x=decode(source)
        receipt=next(r for r in old['suno']['artifacts'] if r['sha256']==sha and not r.get('operations'))
        records.append(receipt);y,r=correct_key(x)
        if y is None:
            # Retain the available cue for inspection/demo, clearly rejected for key compliance.
            y,post=cleanup(x);r['inspection_only']=True;r['cleanup']=post
            r['regeneration_request']=regeneration_request(name)
        cue_reports[name]=r;cue_audio[name]=y
        path=sfx/(name+'.wav');encode(path,y)
        records.append(artifact(path,receipt,dict(key=measure(y)['key'],duration_ms=len(y)/48,
                     **r['cleanup']['measured']),parents=[sha],operations=[dict(operation='local cue cleanup',pitch_semitones=r['pitch_semitones'],status=r['status'])]))
    for name in ('failure','pickup'):
        cue_reports[name]=dict(status='regenerate_needed',reason='Never delivered; no local audio exists',
                               measured_key=None,regeneration_request=regeneration_request(name))
    # Exactly three available cues, never an alleged complete five-cue sprite.
    parts=[];cursor=0;sprite={};cues={};parents=[]
    for name,y in cue_audio.items():
        sprite[name]=[cursor/48,len(y)/48];cues[name]=dict(start_ms=cursor/48,end_ms=(cursor+len(y))/48,status=cue_reports[name]['status'])
        parts.extend([y,np.zeros((24000,2))]);cursor+=len(y)+24000
        parents.append(digest(sfx/(name+'.wav')))
    sprite_path=sfx/'audio-sprite.wav';encode(sprite_path,np.concatenate(parts))
    receipt=next(r for r in records if r['sha256']==parents[0])
    records.append(artifact(sprite_path,receipt,{},parents=parents,operations=['assemble three available cues; two missing']))
    write(sfx/'audio-sprite.json',dict(status='INCOMPLETE',required_count=5,delivered_count=3,cues=cues,sprite=sprite))
    write(sfx/'cue-status.json',cue_reports);reports['cues']=cue_reports
    for p in bgm.iterdir():
        if p.suffix!='.md':shutil.copyfile(p,project/p.name)
    for p in sfx.glob('*.wav'):shutil.copyfile(p,project/p.name)
    analysis=dict(bpm=120,beats=[dict(time_s=i*.5,bar_position=i%4+1) for i in range(80)],
                  duration_s=40,source='local spectral-flux grid refined by measured variant onset correlation',
                  downbeat_source='local_estimate',independent_listening='pending')
    states={}
    for state in ('idle','attack'):
        anim=read(original/'retimed-sprite'/state/'anim.json')
        states[state]=schedule(anim,analysis,2)
    write(project/'beat-sync.json',dict(states=states,runtime_av_sync='untested'))
    switch_at_ms=next_switch_time(4000,alignment['switch_points_ms'],len(explore)/48)
    reports['switch_schedule']=dict(cycle_ms=len(explore)/48,verified_phases_ms=alignment['switch_points_ms'],
                                    scheduled_switch_ms=switch_at_ms,cycle_wrap_verified=False)
    write(evidence/'local-beat-map.json',analysis);export_clock(project/'audio_clock.gd');scene(project,switch_at_ms)
    reports['engine']=dict(engine_load='untested');reports['runtime']=dict(runtime_av_sync='untested')
    if godot:
        reports['engine']=verify_godot(project,godot)
        state=(project/'.engine-state').resolve()
        env=dict(os.environ,APPDATA=str(state),LOCALAPPDATA=str(state))
        result=subprocess.run([str(godot),'--headless','--path',str(project.resolve()),'--max-fps','120'],capture_output=True,text=True,env=env,timeout=50)
        log=result.stdout+result.stderr;(evidence/'godot-scene.log').write_text(log,encoding='utf-8')
        runtime=read(project/'runtime-events.json') if (project/'runtime-events.json').exists() else dict(runtime_av_sync='untested')
        audio_log=log.replace('ERROR: Failed to read the root certificate store.','')
        runtime.update(exit_code=result.returncode,audio_errors='ERROR' in audio_log or 'WARNING' in audio_log)
        reports['runtime']=runtime
        if result.returncode or runtime['audio_errors'] or runtime.get('runtime_av_sync')!='tested':
            write(evidence/'runtime-failure.json',runtime)
            raise ImageError('E_RUNTIME_SYNC','Real engine audio-clock validation failed',report=runtime)
    reports['preview']=dict(status='BLOCKED_LIVE',provider_encoding='1.0.0',
                            evidence=read(original/'evidence/preview-fetch-report.json'),
                            reason='Supplied artifacts do not contain stream payload or an identifiable standard container; HLS/AAC/Opus decoder verified separately')
    reports['controls']=read(original/'evidence/control-report.json')
    manifest=dict(status='EXPERIMENTAL_PARTIAL_REGENERATE_NEEDED',experimental=True,
                  credits_used_this_round=dict(song=0,download=0),suno=dict(artifacts=records),reports=reports,
                  unresolved=['Two undelivered cues','Victory and confirm exact-key mismatches','Live preview encoding unresolved','Independent listening and motif acceptance pending'])
    manifest['provenance_audit']=audit(out,manifest)
    if manifest['provenance_audit']['status']!='PASS':raise ImageError('E_PROVENANCE','Repair lineage incomplete',report=manifest['provenance_audit'])
    shutil.copyfile(original/'suno-ledger.json',out/'suno-ledger.json')
    write(out/'gen-manifest.json',manifest)
    write(evidence/'fix-report.json',reports)
    (out/'README.md').write_text(
        '# S-15 fix round — EXPERIMENTAL / partial\n\n'
        'Both processed BGM loops pass decoded WAV/OGG checks and declared bidirectional transitions. '
        f'Open godot-project/project.godot. The scene runs 30 seconds, switches at {switch_at_ms/1000:g} s (a verified phase), plays the inspection-only confirm at 10 s, '
        'and schedules two attacks on the locally estimated grid. Read evidence and cue-status.json before reuse.\n\n'
        'Five-cue status: level-up PASS; victory/confirm regenerate_needed (mode conflicts); failure/pickup regenerate_needed (never delivered). '
        'The sprite contains only the three existing cues. Exact unsubmitted sounds_create requests are in audio/sfx/cue-status.json. '
        'No new Suno calls or credits. Historical spending remains in the copied ledger.\n\n'
        'Live stream encoding 1.0.0 remains unidentified from supplied evidence; standard HLS MPEG-TS/fMP4 AAC and Opus have offline decoder tests. '
        'Independent listening, motif, and source motion acceptance remain pending; this pack does not pass complete S-178.\n\n'
        'Loop points: WAV RIFF smpl end is inclusive L-1; JSON/Godot end is exclusive L. OGG LOOPSTART=0, LOOPLENGTH=L. '
        'Godot import uses WAV loop mode 2 and OGG loop_offset=0. Unity/FMOD/Wwise remain untested. '
        'Windows certificate-store diagnostics are retained separately from audio/script/resource errors.\n',encoding='utf-8')
    (project/'README.md').write_text('Experimental S-15 repaired audio scene. See ../README.md and ../evidence/fix-report.json for this run. '
                                   'The confirm cue remains inspection-only because of its key mismatch.\n',encoding='utf-8')
    # Deterministic archive contents, no engine caches or user-machine state.
    files=sorted(p for p in out.rglob('*') if p.is_file() and not any(s in p.parts for s in ('.godot','.engine-state')))
    write(out/'file-list.json',[dict(file=p.relative_to(out).as_posix(),bytes=p.stat().st_size,sha256=digest(p)) for p in files])
    archive=out.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files+[out/'file-list.json']:
            info=zipfile.ZipInfo(p.relative_to(out).as_posix(),date_time=(2026,11,7,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,p.read_bytes())
    return dict(status=manifest['status'],archive=str(archive),reports=reports,provenance_audit=manifest['provenance_audit'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--original',type=Path,required=True)
    p.add_argument('--sources',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--godot',type=Path);p.add_argument('--experimental',action='store_true');a=p.parse_args(argv)
    try:
        if not a.experimental:raise ImageError('E_EXPERIMENTAL','Repair pack requires --experimental')
        r=build(a.original,a.sources,a.out,a.godot);print(json.dumps(dict(status=r['status'],archive=r['archive'],provenance_audit=r['provenance_audit'])));return 0
    except (ValueError,OSError,subprocess.SubprocessError) as e:
        print(json.dumps(dict(error=getattr(e,'error',dict(code='E_FIX_PACK',message=str(e))))));return 2


if __name__=='__main__':raise SystemExit(main())
