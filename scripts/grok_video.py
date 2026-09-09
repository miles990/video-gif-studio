#!/usr/bin/env python3
"""Generate/resume Grok video through the bundled OAuth client."""
import argparse
import hashlib
import json
from pathlib import Path
from grok_client import GrokClient, ProviderError

TERMINAL = {'failed','error','cancelled','expired','moderated','rejected'}


def save(path,data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data,indent=2)+'\n')
    temporary.replace(path)


def main(argv=None,client=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--image',type=Path)
    ap.add_argument('--prompt',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--model',default='grok-imagine-video-1.5')
    ap.add_argument('--duration',type=int,default=10)
    ap.add_argument('--resolution',choices=['480p','720p','1080p'],default='720p')
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--submit',action='store_true')
    mode.add_argument('--resume',action='store_true')
    args=ap.parse_args(argv)
    client = client or GrokClient()
    args.out.mkdir(parents=True,exist_ok=True)
    ledger=args.out/'job.json'
    if args.submit:
        if ledger.exists():
            ap.error('Job ledger exists: resume it; use a new attempt only after resolving this job')
        if not args.image or not args.prompt or not 1<=args.duration<=30:
            ap.error('Supply image, prompt and valid duration; verify current model limits')
        prompt=args.prompt.read_text()
        data={'status':'submitting','model':args.model,'duration':args.duration,
              'resolution':args.resolution,'prompt':prompt,'transport':'bundled-oauth-rest',
              'input_sha256':hashlib.sha256(args.image.read_bytes()).hexdigest(),
              'client_sha256':hashlib.sha256(Path(__file__).with_name('grok_client.py').read_bytes()).hexdigest()}
        client.token()  # Resolve login before recording any potentially submitted request.
        with ledger.open('x') as out:
            json.dump(data,out,indent=2)
        try:
            result=client.submit(args.image,prompt,args.model,args.duration,args.resolution)
            job=result.get('request_id') or result.get('id')
            if not isinstance(job,str) or not job:
                raise ValueError('Missing job ID')
            data.update(status='submitted',request_id=job)
        except ProviderError as exc:
            data.update(status='rejected' if 400<=exc.status<500 else 'submission-unresolved',
                        error={'http_status':exc.status,'code':exc.code})
            save(ledger,data)
            raise SystemExit(str(exc)) from None
        except Exception:
            data.update(status='submission-unresolved',error='No confirmed job ID; reconcile provider state before retry')
            save(ledger,data)
            raise SystemExit(data['error']) from None
        save(ledger,data)
    else:
        data=json.loads(ledger.read_text())
        if data.get('status') in TERMINAL:
            raise SystemExit('Existing job is terminal: '+data['status'])
        if not data.get('request_id'):
            ap.error('Missing job ID; reconcile unresolved submission first')
        if data.get('status')=='downloaded':
            target=args.out/'source.mp4'
            if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=data['output_sha256']:
                ap.error('Downloaded file changed or missing; investigate before regeneration')
            print('Already downloaded and verified')
            return
        result=client.poll(data['request_id'])
        video=result.get('video') or {}
        url=video.get('url') if isinstance(video,dict) else None
        url=url or result.get('video_url')
        data.update(status=str(result.get('status','pending')).lower(),usage=result.get('usage'),progress=result.get('progress'))
        save(ledger,data)  # Preserve progress even if download fails; never persist the delivery URL.
        if data['status'] in TERMINAL:
            raise SystemExit('Provider job is terminal: '+data['status'])
        if url:
            client.download(url,args.out/'source.mp4')
            data.update(status='downloaded',output_sha256=hashlib.sha256((args.out/'source.mp4').read_bytes()).hexdigest())
            save(ledger,data)
    print(json.dumps({'status':data['status'],'request_id':data.get('request_id'),'progress':data.get('progress')}))


if __name__=='__main__':
    try:
        main()
    except (RuntimeError,OSError,ValueError) as exc:
        # Avoid raw transport tracebacks (which can include signed URLs).
        raise SystemExit(str(exc) if isinstance(exc,RuntimeError) else 'Operation failed; check input files and existing job ledger') from None
