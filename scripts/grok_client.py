"""Internal xAI video transport using the official Grok CLI's OAuth session."""
import base64
from datetime import datetime, timedelta, timezone
import json
import mimetypes
from pathlib import Path
import re
import shutil
import subprocess
import urllib.error
import urllib.request

API = 'https://api.x.ai/v1'


class ProviderError(RuntimeError):
    def __init__(self, status, code):
        self.status = status
        self.code = re.sub(r'[^a-zA-Z0-9_:.-]', '-', str(code))[:100]
        super().__init__(f'xAI HTTP {status}: {self.code}')


class GrokClient:
    def __init__(self, auth_path=None):
        self.auth_path = Path(auth_path) if auth_path else Path.home()/'.grok/auth.json'

    def session(self):
        try:
            data = json.loads(self.auth_path.read_text())
        except (OSError, ValueError):
            data = {}
        records = [r for r in data.values() if isinstance(r, dict)] if isinstance(data, dict) else []
        records = [r for r in records if str(r.get('auth_mode','')).lower() in ('oauth','oidc')
                   and isinstance(r.get('key'),str) and r['key'].strip()]
        if not records:
            return {'token':'', 'expired':True, 'has_refresh':False, 'expiry_known':False}
        r = max(records, key=lambda x:str(x.get('create_time','')))
        expiry = None
        try:
            expiry = datetime.fromisoformat(str(r.get('expires_at','')).replace('Z','+00:00'))
            if expiry.tzinfo is None:
                expiry = None
        except ValueError:
            pass
        return {'token':r['key'].strip(),'has_refresh':bool(r.get('refresh_token')),
                'expired':bool(expiry and expiry <= datetime.now(timezone.utc)+timedelta(seconds=60)),
                'expiry_known':expiry is not None}

    def inspect(self):
        s = self.session()
        return {'oauth_session_present':bool(s['token']), 'expired':s['expired'],
                'expiry_known':s['expiry_known'], 'refresh_available':s['has_refresh'],
                'generation_entitlement':'not checked'}

    def token(self):
        s = self.session()
        if s['token'] and not s['expired']:
            return s['token']
        if s['has_refresh']:
            cli = shutil.which('grok') or str(Path.home()/'.grok/bin/grok')
            try:
                r = subprocess.run([cli,'models'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,timeout=30)
                if r.returncode == 0:
                    s = self.session()
            except (OSError, subprocess.SubprocessError):
                pass
        if not s['token'] or s['expired']:
            raise RuntimeError('Grok OAuth unavailable or expired; run grok login and retry')
        return s['token']

    def request(self, route, body=None):
        token = self.token()
        request = urllib.request.Request(API+route,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=60) as response:
                result = json.loads(response.read())
                if not isinstance(result,dict):
                    raise RuntimeError('Invalid provider response')
                return result
        except urllib.error.HTTPError as exc:
            try:
                payload = json.loads(exc.read())
            except (ValueError,OSError):
                payload = {}
            code = payload.get('code',f'http-{exc.code}') if isinstance(payload,dict) else f'http-{exc.code}'
            # Do not persist provider message, URL, bearer or echoed request.
            code = str(code).replace(token,'REDACTED')
            raise ProviderError(exc.code, code) from None
        except (urllib.error.URLError,TimeoutError,OSError,ValueError):
            raise RuntimeError('Provider transport failed; preserve the job and do not blindly resubmit') from None

    def submit(self,image,prompt,model,duration,resolution):
        mime = mimetypes.guess_type(image.name)[0] or 'image/png'
        uri = 'data:'+mime+';base64,'+base64.b64encode(image.read_bytes()).decode()
        return self.request('/videos/generations',{'model':model,'prompt':prompt,
            'image':{'url':uri},'duration':duration,'resolution':resolution})

    def poll(self,job):
        if not re.fullmatch(r'[a-zA-Z0-9_-]+',job):
            raise ValueError('Invalid provider job ID')
        return self.request('/videos/'+job)

    def download(self,url,target):
        if not url.startswith('https://'):
            raise ValueError('Provider delivery must use HTTPS')
        temporary = target.with_suffix('.part')
        try:
            # Never forward the API bearer to a delivery URL.
            with urllib.request.urlopen(url,timeout=60) as response, open(temporary,'wb') as out:
                shutil.copyfileobj(response,out)
            if temporary.stat().st_size == 0:
                raise ValueError('Empty provider video')
            temporary.replace(target)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise RuntimeError('Video download failed; resume the existing job') from None
