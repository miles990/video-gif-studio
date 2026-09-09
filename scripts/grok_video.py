#!/usr/bin/env python3
"""Grok I2V via an existing official OAuth adapter. No embedded credentials."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--adapter', type=Path, required=True, help='Existing motiongen.py from MV Studio')
    ap.add_argument('--image', type=Path)
    ap.add_argument('--prompt', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--model', default='grok-imagine-video-1.5')
    ap.add_argument('--duration', type=int, default=10)
    ap.add_argument('--resolution', choices=['480p','720p','1080p'], default='720p')
    ap.add_argument('--submit', action='store_true', help='Submit one already-authorized generation')
    ap.add_argument('--resume', action='store_true', help='Poll existing job once; never resubmit')
    args = ap.parse_args()
    if args.submit == args.resume:
        ap.error('Choose exactly one: --submit or --resume')
    if not args.adapter.is_file():
        ap.error('Adapter missing; locate a supported provider or explain the blocker')
    sys.path.insert(0, str(args.adapter.resolve().parent))
    spec = importlib.util.spec_from_file_location('video_gif_grok_adapter', args.adapter)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    required = ['_fresh_oauth_session','_request','_data_uri','API']
    if not all(hasattr(module, name) for name in required):
        ap.error('Adapter contract changed; inspect it before submitting')
    args.out.mkdir(parents=True, exist_ok=True)
    ledger = args.out/'job.json'
    if args.submit:
        if ledger.exists():
            ap.error('Job ledger exists; resume it or use a new attempt directory')
        if not args.image or not args.prompt or not 1 <= args.duration <= 30:
            ap.error('Supply image, prompt and a valid requested duration; check live model limits')
        prompt = args.prompt.read_text()
        data = {'status':'submitting', 'model':args.model,'duration':args.duration,
                'resolution':args.resolution,'prompt':prompt,
                'input_sha256':hashlib.sha256(args.image.read_bytes()).hexdigest(),
                'adapter_sha256':hashlib.sha256(args.adapter.read_bytes()).hexdigest()}
        session = module._fresh_oauth_session()
        ledger.write_text(json.dumps(data,indent=2)+'\n')
        try:
            result = module._request(module.API+'/videos/generations', session['token'], 'POST',
                {'model':args.model,'prompt':prompt,'image':{'url':module._data_uri(args.image)},
                 'duration':args.duration,'resolution':args.resolution})
            job = result.get('request_id') or result.get('id')
            if not job:
                raise RuntimeError('Submission response lacks job ID; do not auto-resubmit')
            data.update(status='submitted',request_id=job)
        except Exception as exc:
            data.update(status='submission-unresolved',error=str(exc)[:600])
            ledger.write_text(json.dumps(data,indent=2)+'\n')
            raise SystemExit('Submission unresolved; inspect job.json; no automatic retry') from None
        ledger.write_text(json.dumps(data,indent=2)+'\n')
        print(json.dumps({'status':data['status'],'request_id':job}))
    else:
        data = json.loads(ledger.read_text())
        if not data.get('request_id'):
            ap.error('Missing request ID: reconcile ambiguous submission before retry')
        if data.get('status') == 'downloaded':
            target = args.out/'source.mp4'
            if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != data['output_sha256']:
                ap.error('Downloaded file missing or changed; investigate before regenerating')
            print('Already downloaded and verified')
            return
        session = module._fresh_oauth_session()
        result = module._request(module.API+'/videos/'+data['request_id'],session['token'])
        video = result.get('video') or {}
        url = video.get('url') or result.get('video_url')
        data.update(status=result.get('status','pending'),usage=result.get('usage'),progress=result.get('progress'))
        if url:
            import urllib.request
            temporary = args.out/'source.part'
            with urllib.request.urlopen(url, timeout=60) as response, open(temporary,'wb') as out:
                import shutil
                shutil.copyfileobj(response,out)
            temporary.replace(args.out/'source.mp4')
            data.update(status='downloaded',output_sha256=hashlib.sha256((args.out/'source.mp4').read_bytes()).hexdigest())
        ledger.write_text(json.dumps(data,indent=2)+'\n')
        print(json.dumps({'status':data['status'],'progress':data.get('progress')}))


if __name__ == '__main__':
    main()
