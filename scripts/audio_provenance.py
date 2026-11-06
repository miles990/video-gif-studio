"""Closed audio lineage, public/private manifest separation and credit summaries."""
from pathlib import Path
import hashlib
from image_common import read,write,digest,ImageError

LICENSE='user_account_generated (Suno Premier)'


def artifact(path,source,measured,parents=(),operations=()):
    path=Path(path)
    if source.get('preview_only') or any(p in ('suno-preview','analysis') for p in path.parts):
        raise ImageError('E_PREVIEW_ONLY','Stream previews cannot become delivered artifacts')
    if source.get('private'):raise ImageError('E_PRIVATE','Private library lineage belongs only in private-manifest.json')
    if source.get('source') not in ('download','upload'):raise ImageError('E_PROVENANCE','Delivery needs a download or user upload')
    if source['source']=='download':
        required=('clip_id','tool','params_requested','idempotency_key','download','source_sha256')
        if any(k not in source for k in required):raise ImageError('E_PROVENANCE','Incomplete download receipt')
        if not source['download'].get('url_sha256'):raise ImageError('E_PROVENANCE','Download URL response receipt is missing')
    record=dict(source,file=path.name,sha256=digest(path),measured={k:measured.get(k) for k in ('bpm','key','meter','duration_ms','lufs','true_peak')},
        parents=list(parents),operations=list(operations),license=LICENSE if source['source']=='download' else source.get('license','user-supplied; verify rights'))
    # Never invent model identity; absent provider model stays absent.
    return record


def audit(folder,manifest):
    folder=Path(folder);records=manifest.get('suno',{}).get('artifacts',[]);byhash={r['sha256']:r for r in records}
    issues=[];files=sorted(p for p in folder.rglob('*') if p.suffix.lower() in ('.wav','.ogg','.mp3','.flac'))
    for path in files:
        sha=digest(path);record=byhash.get(sha)
        if not record:issues.append(dict(file=str(path.relative_to(folder)),reason='missing provenance'));continue
        if record.get('preview_only') or record.get('source') not in ('download','upload'):issues.append(dict(file=record['file'],reason='invalid source'))
        if record.get('source')=='download' and not record.get('download',{}).get('url_sha256'):issues.append(dict(file=record['file'],reason='missing download receipt'))
        for parent in record.get('parents',[]):
            if parent not in byhash and parent!=record.get('source_sha256'):issues.append(dict(file=record['file'],reason='unresolved parent hash'))
    return dict(status='PASS' if files and not issues else 'FAIL',audio_files=len(files),covered=len(files)-len({r['file'] for r in issues}),issues=issues)


def account_summary(calls):
    """Provider debits can settle after create returns; snapshots are authoritative.

    Do not sum overlapping per-call deltas. Preserve each observation separately.
    """
    snapshots=[r['usage'] for r in calls if r.get('usage')]
    first=snapshots[0] if snapshots else {};last=snapshots[-1] if snapshots else {}
    creates=[r for r in calls if r.get('tool') in ('sounds_create','audio_create','audio_covers_create','audio_mashups_create','audio_extensions_create','speech_create')]
    return dict(create_calls=len(creates),song_credits=first.get('credits_remaining',0)-last.get('credits_remaining',0),
        download_credits=first.get('download_credits_remaining',0)-last.get('download_credits_remaining',0),
        remaining_download_credits=last.get('download_credits_remaining'),
        accounting='first/last account snapshots; delayed settlements are not attributed to an unrelated call')
