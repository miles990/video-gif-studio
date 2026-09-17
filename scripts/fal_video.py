#!/usr/bin/env python3
"""Submit once or resume a fal MiniMax H3 Max job. Standard library only."""
import argparse
import base64
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://queue.fal.run/"
MODEL = "minimax/h3-max/"
KEY_FILE = Path.home() / '.config/video-gif-studio/fal.key'


def key_present():
    return bool(os.environ.get('FAL_KEY', '').strip()) or KEY_FILE.is_file()


def read_key():
    key = os.environ.get('FAL_KEY', '').strip()
    if key:
        return key
    if KEY_FILE.is_file():
        if os.name == 'posix' and KEY_FILE.stat().st_mode & 0o077:
            raise FalError('Set permissions 600 on ~/.config/video-gif-studio/fal.key')
        return KEY_FILE.read_text().strip()
    return ''



class FalError(RuntimeError):
    pass


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2) + "\n")
    temp.replace(path)


def queue_url(url):
    p = urllib.parse.urlsplit(url)
    if (p.scheme != 'https' or p.netloc != 'queue.fal.run' or p.query
            or p.fragment or not p.path.startswith('/minimax/h3-max/requests/')):
        raise FalError('Unexpected queue URL; reconcile request in fal dashboard')
    return url


class Client:
    def __init__(self):
        self.key = read_key()
        if not self.key:
            raise FalError('FAL_KEY is missing. Set it locally; never paste credentials into chat.')

    def request(self, url, payload=None):
        req = urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode(),
            headers={'Authorization': 'Key ' + self.key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise FalError('fal HTTP ' + str(exc.code) + '; inspect dashboard, do not blindly resubmit') from None
        except Exception:
            raise FalError('fal transport/response failure; request outcome may be unresolved') from None

    def submit(self, endpoint, payload):
        return self.request(BASE + endpoint, payload)

    def poll(self, url):
        return self.request(queue_url(url))

    def download(self, url, target):
        p = urllib.parse.urlsplit(url)
        if p.scheme != 'https' or p.username or p.password:
            raise FalError('Invalid video delivery URL')
        temp = target.with_suffix('.part')
        try:
            # Never forward the API key to media storage.
            with urllib.request.urlopen(url, timeout=180) as source, temp.open('wb') as dest:
                shutil.copyfileobj(source, dest)
            if not temp.stat().st_size:
                raise FalError('Empty video download')
            temp.replace(target)
        except Exception:
            temp.unlink(missing_ok=True)
            raise FalError('Video download failed; resume the same job') from None


def duration_of(path):
    from media_runtime import locate
    binary = locate('ffprobe')
    if not binary:
        raise ValueError('ffprobe is required for video/audio references')
    try:
        result = subprocess.run([str(binary), '-v', 'error', '-show_entries', 'format=duration',
                                 '-of', 'json', str(path)], capture_output=True, check=True, timeout=30)
        seconds = float(json.loads(result.stdout)['format']['duration'])
    except Exception:
        raise ValueError('Unable to probe reference duration') from None
    if not 2 <= seconds <= 15:
        raise ValueError('Video/audio reference must be 2–15 seconds')
    return seconds


def asset(path, role, encoded):
    if not path.is_file():
        raise ValueError('Reference file missing: ' + str(path))
    mime = mimetypes.guess_type(path.name)[0]
    kind = 'image' if role in ('first', 'last', 'image') else role
    if not mime or not mime.startswith(kind + '/'):
        raise ValueError('Unsupported reference type: ' + str(path))
    record = {'role': role, 'name': path.name, 'sha256': sha(path), 'bytes': path.stat().st_size}
    if kind in ('video','audio'): record['duration'] = duration_of(path)
    uri = ('data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode()) if encoded else None
    return record, uri


def build(args, encoded=False):
    if not args.prompt or not args.prompt.is_file():
        raise ValueError('Supply --prompt pointing to a UTF-8 text file')
    prompt = args.prompt.read_text().strip()
    if not prompt:
        raise ValueError('Prompt must not be empty')
    refs = []
    if args.image: refs.append(('image_url', args.image, 'first'))
    if args.end_image: refs.append(('end_image_url', args.end_image, 'last'))
    for field, paths, role in [('reference_image_urls', args.reference_image, 'image'),
                              ('reference_video_urls', args.reference_video, 'video'),
                              ('reference_audio_urls', args.reference_audio, 'audio')]:
        refs.extend((field, p, role) for p in paths)
    multi = any(x[0].startswith('reference_') for x in refs)
    if multi and (args.image or args.end_image):
        raise ValueError('Reference mode cannot be combined with first/last frames in this adapter')
    if multi and len(refs) > 12:
        raise ValueError('At most 12 reference files in total')
    if (args.image or args.end_image) and args.aspect_ratio != 'adaptive':
        raise ValueError('First/last frame mode inherits the image canvas; omit --aspect-ratio')
    mode = 'reference-to-video' if multi else ('image-to-video' if refs else 'text-to-video')
    payload = dict(prompt=prompt, duration=args.duration, resolution=args.resolution,
                   prompt_expansion_mode=args.prompt_expansion, enable_safety_checker=True)
    if mode != 'image-to-video': payload['aspect_ratio'] = args.aspect_ratio
    if args.seed is not None: payload['seed'] = args.seed
    records = []
    for field, path, role in refs:
        record, uri = asset(path, role, encoded)
        records.append(record)
        if encoded:
            if field.startswith('reference_'): payload.setdefault(field, []).append(uri)
            else: payload[field] = uri
    for role in ('video','audio'):
        if sum(r.get('duration',0) for r in records if r['role']==role) > 15:
            raise ValueError('Combined reference duration exceeds 15 seconds for ' + role)
    return MODEL + mode, payload, records


def main(argv=None, client=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, type=Path)
    action = ap.add_mutually_exclusive_group(required=True)
    for name in ['submit', 'resume', 'dry-run']: action.add_argument('--' + name, action='store_true')
    ap.add_argument('--prompt', type=Path)
    ap.add_argument('--image', type=Path)
    ap.add_argument('--end-image', type=Path)
    for name in ['image', 'video', 'audio']:
        ap.add_argument('--reference-' + name, type=Path, action='append', default=[])
    ap.add_argument('--duration', type=int, choices=range(5, 16), default=5)
    ap.add_argument('--resolution', choices=['480P', '768P', '1080P'], default='768P')
    ap.add_argument('--aspect-ratio', choices=['adaptive','21:9','16:9','4:3','1:1','3:4','9:16'], default='adaptive')
    ap.add_argument('--prompt-expansion', choices=['balanced','quality'], default='balanced')
    ap.add_argument('--seed', type=int)
    args = ap.parse_args(argv)
    ledger = args.out / 'job.json'
    if args.dry_run:
        endpoint, payload, records = build(args)
        print(json.dumps(dict(endpoint=endpoint, settings=payload, inputs=records,
                              fal_key_present=key_present(), network_requests=0), indent=2))
        return
    if args.submit:
        if ledger.exists():
            raise FalError('Job ledger exists; resume or reconcile it before another attempt')
        endpoint, payload, records = build(args, encoded=True)
        client = client or Client()
        args.out.mkdir(parents=True, exist_ok=True)
        data = dict(provider='fal.ai', model=endpoint, status='submitting', inputs=records,
                    settings={k:v for k,v in payload.items() if not k.endswith('_url') and not k.endswith('_urls')},
                    adapter_sha256=sha(Path(__file__)))
        with ledger.open('x') as f: json.dump(data, f, indent=2)
        try:
            result = client.submit(endpoint, payload)
            job = result.get('request_id')
            if not isinstance(job, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', job):
                raise FalError('No valid request ID')
            # Persist the ID BEFORE validating URLs, even if the response schema changes.
            data.update(request_id=job, status='submitted')
            save(ledger, data)
            data['status_url'] = queue_url(result['status_url'])
            data['response_url'] = queue_url(result['response_url'])
        except Exception:
            data['status'] = 'submission-unresolved'
            save(ledger, data)
            raise FalError('Submission unresolved; reconcile recorded request/dashboard before retry') from None
        save(ledger, data)
    else:
        data = json.loads(ledger.read_text())
        if data['status'] == 'downloaded':
            target = args.out / 'source.mp4'
            if not target.is_file() or sha(target) != data['output_sha256']:
                raise FalError('Downloaded output missing or changed; do not regenerate automatically')
            print('Already downloaded and hash verified')
            return
        if data['status'] in ('failed', 'submission-unresolved'):
            raise FalError('Job needs dashboard reconciliation: ' + data['status'])
        client = client or Client()
        result = client.poll(data['status_url'])
        status = str(result.get('status', 'UNKNOWN')).upper()
        if status not in ('IN_QUEUE','IN_PROGRESS','COMPLETED','FAILED'):
            raise FalError('Unknown queue status; keep job and inspect dashboard')
        data['status'] = status.lower()
        save(ledger, data)
        if status == 'COMPLETED':
            result = client.poll(data['response_url'])
            url = (result.get('video') or {}).get('url')
            if not url: raise FalError('Completed response has no video; inspect existing job')
            client.download(url, args.out / 'source.mp4')
            # Retain useful provenance, never media URLs or response logs.
            data.update(status='downloaded', output_sha256=sha(args.out/'source.mp4'),
                        timings=result.get('timings'), seed=result.get('seed'), expanded_prompt_present=bool(result.get('expanded_prompt')))
            save(ledger, data)
    print(json.dumps({'status':data['status'], 'request_id':data.get('request_id')}))


if __name__ == '__main__':
    try:
        main()
    except FalError as exc:
        raise SystemExit(str(exc)) from None
    except (ValueError, OSError, KeyError):
        # Provider responses or exception text can contain signed URLs/credentials.
        raise SystemExit('Operation failed. Check local inputs, FAL_KEY and job.json; do not blindly resubmit.') from None
