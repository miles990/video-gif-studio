"""Subscription-first PNG adapter with explicit paid authority and atomic cache."""
import base64
from copy import deepcopy
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from PIL import Image
from image_common import DEFAULT_STATE, ImageError, c2pa, canonical, digest, key, locked, read, utc, write


@dataclass
class Request:
    prompt: str
    route: str = 'codex'
    refs: list = field(default_factory=list)
    size: str = '1024x1024'
    aspect: str | None = None
    quality: str = 'draft'
    n: int = 1
    transparent: bool = False
    format: str = 'png'
    model: str | None = None
    seed: int | None = None
    markup_sha: str | None = None
    refset_sha: str | None = None
    refset_path: str | None = None
    experimental: bool = False

    def normalized(self):
        if not self.experimental:
            raise ImageError('E_EXPERIMENTAL', 'Image generation is experimental.', suggestion='Pass --experimental or experimental: true.')
        if self.route not in ('codex', 'api', 'auto'):
            raise ImageError('E_ROUTE', 'Supported routes: codex, auto (subscription only), api.')
        if not isinstance(self.n, int) or not 1 <= self.n <= 8:
            raise ImageError('E_COUNT', 'Image count must be between 1 and 8.')
        if len(self.refs) > 16:
            raise ImageError('E_REFSET_LIMIT', 'At most 16 references may be sent.')
        if not re.fullmatch(r'[1-9]\d{1,4}x[1-9]\d{1,4}', self.size):
            raise ImageError('E_SIZE', 'Use WIDTHxHEIGHT in pixels.')
        w, h = map(int, self.size.split('x'))
        if max(w, h) > 8192:
            raise ImageError('E_SIZE', 'Maximum local canvas dimension is 8192.')
        if self.aspect:
            try:
                a, b = map(float, self.aspect.split(':'))
                if not math.isfinite(a+b) or min(a,b) <= 0:raise ValueError()
            except ValueError:
                raise ImageError('E_ASPECT', 'Use a positive ratio such as 9:16.') from None
        if self.quality not in ('draft', 'final') or self.format != 'png':
            raise ImageError('E_CAPABILITY', 'The route adapter accepts draft/final PNG; use the documented local GIF/SVG fallbacks.')
        if self.route != 'api' and self.model:
            raise ImageError('E_CAPABILITY', 'The subscription tool cannot select or report its image model.')
        prompt = ' '.join(unicodedata.normalize('NFC', self.prompt).split())
        if not prompt:
            raise ImageError('E_PROMPT', 'A nonempty prompt is required.')
        refs = []
        for p in self.refs:
            path = Path(p).resolve()
            with Image.open(path) as im:im.verify()
            refs.append(dict(path=str(path), sha256=digest(path)))
        return dict(route='codex' if self.route == 'auto' else self.route, model=self.model,
                    prompt=prompt, size=self.size, aspect=self.aspect, quality=self.quality,
                    n=self.n, transparent=self.transparent, format=self.format, seed=self.seed,
                    refs=refs, markup_sha=self.markup_sha, refset_sha=self.refset_sha)


def request_key(data):
    data = deepcopy(data)
    data['refs'] = [r['sha256'] for r in data['refs']]
    return key(data)


def child_env():
    # Also strip the exec-specific API key and provider overrides: never inherit billing.
    return {k:v for k,v in os.environ.items() if not k.upper().startswith(('OPENAI_', 'CODEX_API_KEY'))}


class Adapter:
    def __init__(self, state=DEFAULT_STATE, codex=None, timeout=300, round_id='spec-13', cap=60,
                 run_id=None, api_base=None, prices=None):
        self.state = Path(state).resolve()
        self.codex = codex or [shutil.which('codex.exe') or shutil.which('codex') or 'codex']
        if isinstance(self.codex, (str, Path)):self.codex = [str(self.codex)]
        self.timeout = timeout
        if not 1 <= cap <= 60:raise ImageError('E_CAP', 'Round cap must be 1..60; larger rounds need a separate authorization policy.')
        self.cap, self.round_id = cap, round_id
        self.run_id = run_id or uuid.uuid4().hex
        self.api_base = (api_base or os.environ.get('OPENAI_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')
        self.prices = read(prices) if isinstance(prices, (str, Path)) else prices

    def records(self):
        path = self.state/'ledger.jsonl'
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []

    def event(self, record):
        record = dict(record, timestamp=utc(), run_id=self.run_id, round_id=self.round_id)
        with locked(self.state/'ledger.lock'):
            with (self.state/'ledger.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(canonical(record)+'\n'); stream.flush(); os.fsync(stream.fileno())
        return record

    def reserve(self, n):
        # Reserve BEFORE dispatch. Failed/ambiguous calls remain charged to the cap.
        with locked(self.state/'ledger.lock'):
            used = sum(r.get('reserved_images', 0) for r in self.records() if r['round_id'] == self.round_id)
            if used+n > self.cap:
                raise ImageError('E_CAP', f'Round would exceed its {self.cap}-image cap.', used=used, requested=n)
            record = dict(event='reservation', reserved_images=n, timestamp=utc(), run_id=self.run_id, round_id=self.round_id)
            with (self.state/'ledger.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(canonical(record)+'\n'); stream.flush(); os.fsync(stream.fileno())

    def estimate(self, req):
        data = req.normalized()
        if data['route'] != 'api':
            return dict(route='codex', images=data['n'], cost_estimate_usd=0, subscription_images=data['n'], model='unreported')
        if not self.prices:
            raise ImageError('E_PRICE_REQUIRED', 'A dated, reviewed price table is required; no prices are guessed.', suggestion='Supply --prices with version, date, and rows of model/quality/size/unit_usd.')
        model = data['model'] or ('gpt-image-2.6-flare' if data['quality']=='draft' else 'gpt-image-2.6-sunburst')
        quality = 'low' if data['quality']=='draft' else 'high'
        rows = [r for r in self.prices['rows'] if (r['model'],r['quality'],r['size'])==(model,quality,data['size'])]
        if len(rows)!=1:raise ImageError('E_PRICE_REQUIRED', 'No unique reviewed price for this model/quality/size.')
        unit = float(rows[0]['unit_usd'])
        if not math.isfinite(unit) or unit < 0:raise ImageError('E_PRICE_REQUIRED', 'Price must be finite and nonnegative.')
        result = dict(route='api', model=model, quality=quality, size=data['size'], n=data['n'], unit_usd=unit,
                      cost_estimate_usd=round(unit*data['n'], 8), price_version=self.prices['version'], price_date=self.prices['date'],
                      request_sha=request_key(data), endpoint=self.api_base)
        result['estimate_id'] = key(result)
        return result

    def approve(self, req, approval, max_usd):
        estimate = self.estimate(req)
        if not approval:
            raise ImageError('E_APPROVAL_REQUIRED', 'Paid route requires approval for this exact estimate.',
                             suggestion='After explicit user consent, pass --approve-spend ESTIMATE_ID and --max-usd AMOUNT.', estimate=estimate)
        if approval != estimate['estimate_id']:
            raise ImageError('E_APPROVAL_MISMATCH', 'Approval does not match the current request, price, and endpoint.', estimate=estimate)
        if not math.isfinite(max_usd) or max_usd < estimate['cost_estimate_usd']:
            raise ImageError('E_BUDGET', 'Estimate exceeds --max-usd (default 0).', estimate=estimate)
        return estimate

    def command(self, args, env, prompt=None):
        try:
            return subprocess.run([*self.codex, *args], input=prompt, capture_output=True, text=True,
                                  encoding='utf-8', errors='replace', timeout=self.timeout, env=env,
                                  cwd=self.state, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.TimeoutExpired:
            raise ImageError('E_TIMEOUT', 'Codex timed out; no automatic retry of an ambiguous generation.') from None
        except OSError as exc:
            raise ImageError('E_ROUTE_UNAVAILABLE', str(exc), suggestion='Install or select a working Codex CLI; API is never selected automatically.') from None

    def login(self):
        response = self.command(['login', 'status'], child_env())
        text = (response.stdout+'\n'+response.stderr).strip()
        if re.search(r'API\s*key', text, re.I):
            raise ImageError('E_ROUTE_BILLED', 'Codex is logged in using an API key.', suggestion='Log in with ChatGPT, or select the explicit api route with an approved estimate.')
        if response.returncode or not re.search(r'ChatGPT', text, re.I):
            raise ImageError('E_AUTH', 'A ChatGPT subscription login could not be verified.')
        return 'ChatGPT'

    def codex_image(self, data, stage, ordinal):
        parameters = dict(prompt=data['prompt']+f"\nCanvas: {data['size']}; aspect: {data['aspect'] or data['size']}; {data['quality']} quality (prompt only).",
                          transparent_background=data['transparent'])
        if data['refs']:parameters['referenced_image_paths']=[r['path'] for r in data['refs']]
        instruction = ('Use only the built-in image_generation tool to generate exactly ONE PNG. '
                       'Do not use an API, shell generation, network scripts, or a paid fallback. '
                       'Reference images are attached; inspect them before editing. '
                       'Return a final JSON object {"image_paths":["absolute saved PNG path"]}. '
                       'Use these tool parameters: '+canonical(parameters))
        if data['seed'] is not None:instruction += f"\nCreative seed cue (prompt only): {data['seed']}."
        args = ['exec', '--ephemeral', '--skip-git-repo-check', '--sandbox', 'read-only', '--json',
                '-c', 'approval_policy="never"', '-c', 'forced_login_method="chatgpt"']
        for ref in data['refs']:args.extend(['--image', ref['path']])
        args.append('-')
        for attempt in range(3):
            self.reserve(1)
            response = self.command(args, child_env(), instruction)
            log = stage/f'codex-{ordinal}-{attempt}.jsonl'
            log.write_text(response.stdout+'\n'+response.stderr, encoding='utf-8')
            if response.returncode:
                if re.search(r'quota|rate.?limit|429', response.stdout+response.stderr, re.I):
                    if attempt < 2:time.sleep(5*(attempt+1));continue
                    raise ImageError('E_QUOTA', 'Subscription quota exhausted after two bounded retries.')
                raise ImageError('E_GENERATION', 'Codex generation failed.', log=str(log))
            paths = saved_paths(response.stdout)
            if len(paths) != 1:raise ImageError('E_OUTPUT', 'Expected exactly one saved PNG path from Codex.', log=str(log))
            return paths[0], str(log)

    def api_images(self, data, stage, estimate):
        if data['refs']:
            raise ImageError('E_CAPABILITY', 'This paid PNG generations adapter does not accept references; use the subscription route.')
        token = os.environ.get('OPENAI_API_KEY', '').strip()
        if not token:raise ImageError('E_AUTH', 'No OpenAI API key is configured.')
        parsed = urllib.parse.urlparse(self.api_base)
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost','127.0.0.1','::1')):
            raise ImageError('E_ENDPOINT', 'Use HTTPS or a loopback test server.')
        payload = dict(prompt=data['prompt'], model=estimate['model'], size=estimate['size'], quality=estimate['quality'],
                       n=data['n'], background='transparent' if data['transparent'] else 'opaque', output_format='png')
        self.reserve(data['n'])
        request = urllib.request.Request(self.api_base+'/images/generations', data=canonical(payload).encode(),
                                         headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):return None
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=self.timeout) as response:
                result = json.loads(response.read(128*1024*1024))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise ImageError('E_API', 'Paid request failed; no automatic retry.', reason=type(exc).__name__) from None
        items = result.get('data', [])
        if len(items) != data['n']:raise ImageError('E_COUNT', 'API returned a count different from the approved estimate.')
        paths = []
        for i,item in enumerate(items):
            path = stage/f'api-{i}.png'
            try:path.write_bytes(base64.b64decode(item['b64_json'], validate=True))
            except (KeyError, ValueError):raise ImageError('E_OUTPUT', 'API must return base64 PNG bytes; URL downloads are disabled.') from None
            paths.append(path)
        return paths, result.get('model')

    def generate(self, req, out, approval=None, max_usd=0, no_cache=False):
        data = req.normalized(); cache_key = request_key(data); out = Path(out).resolve()
        out.mkdir(parents=True, exist_ok=True); self.state.mkdir(parents=True, exist_ok=True)
        start = time.monotonic(); entry = self.state/'cache'/cache_key
        manifest = dict(schema_version=1, status='pending', route=data['route'], model='unreported', model_reported=None,
                        quality=data['quality'], quality_control='prompt_only' if data['route']=='codex' else 'native',
                        size_requested=data['size'], size_actual=[], aspect_actual=[], n_requested=data['n'], n_returned=0,
                        elapsed_s=0, prompt_sha=key(data['prompt']), refs_sent=data['refs'], refset_sha=req.refset_sha,
                        feature_used=['png']+(['references'] if data['refs'] else [])+(['transparent_native_requested'] if data['transparent'] else []),
                        cache_key=cache_key, cache_hit=False, no_cache=no_cache, c2pa_present='unknown', c2pa_claim_generator=None,
                        synthid='not_verifiable_locally', subscription_images=0, cost_estimate_usd=0, approval_id=approval,
                        run_id=self.run_id, round_id=self.round_id, experimental=True,
                        route_reason='Explicit paid route' if data['route']=='api' else 'Subscription PNG; never auto-escalate to API',
                        fallback_chain=[dict(route=data['route'])])
        try:
            estimate = self.approve(req, approval, max_usd) if data['route']=='api' else None
            with locked(self.state/'locks'/(cache_key+'.lock')):
                cached = read(entry/'record.json') if (entry/'record.json').exists() and not no_cache else None
                if cached and all((entry/a['file']).is_file() and digest(entry/a['file'])==a['sha256'] for a in cached['assets']):
                    manifest.update(cached['manifest']); manifest.update(cache_hit=True, no_cache=False, subscription_images=0, cost_estimate_usd=0)
                    source_assets = [(entry/a['file'],a) for a in cached['assets']]
                else:
                    if data['route']=='codex':manifest['auth_mode']=self.login()
                    else:
                        self.event(dict(event='approval', **estimate, approval_id=approval))
                        manifest.update(cost_estimate_usd=estimate['cost_estimate_usd'], estimate=estimate, model=estimate['model'])
                    stage = self.state/'attempts'/uuid.uuid4().hex; stage.mkdir(parents=True)
                    paths, logs = [], []
                    if data['route']=='codex':
                        for i in range(data['n']):
                            path, log = self.codex_image(data, stage, i); paths.append(path); logs.append(log)
                        manifest['subscription_images']=len(paths)
                    else:
                        paths, model = self.api_images(data, stage, estimate); manifest['model_reported']=model
                    assets = []
                    for i,path in enumerate(paths):
                        path = Path(path)
                        with Image.open(path) as im:
                            im.load()
                            if im.format!='PNG':raise ImageError('E_OUTPUT', 'Provider did not return PNG.')
                            width,height=im.size
                        target = stage/f'image-{i+1}.png'
                        shutil.copyfile(path,target)
                        assets.append(dict(file=target.name, sha256=digest(target), size=[width,height], **c2pa(target)))
                    manifest.update(n_returned=len(assets), size_actual=[a['size'] for a in assets],
                                    aspect_actual=[a['size'][0]/a['size'][1] for a in assets], logs=logs,
                                    c2pa_present=any(a['c2pa_present'] is True for a in assets),
                                    c2pa_validation='container presence only; signature not verified', status='ok')
                    # Commit only complete validated files. Metadata is the commit marker.
                    entry.mkdir(parents=True, exist_ok=True)
                    for a in assets:shutil.copyfile(stage/a['file'],entry/a['file'])
                    write(entry/'record.json',dict(assets=assets,manifest=manifest))
                    source_assets=[(entry/a['file'],a) for a in assets]
                delivered=[]
                for source,a in source_assets:
                    target=out/a['file']; shutil.copyfile(source,target)
                    delivered.append(dict(a,path=str(target)))
                manifest.update(assets=delivered, run_id=self.run_id, round_id=self.round_id, elapsed_s=round(time.monotonic()-start,4), status='ok')
        except (ImageError, OSError, ValueError) as exc:
            if not isinstance(exc,ImageError):exc=ImageError('E_IMAGE',str(exc))
            manifest.update(status='error',error=exc.error,elapsed_s=round(time.monotonic()-start,4))
            manifest['fallback_chain'][-1]['error']=exc.error['code']
            write(out/'gen-manifest.json',manifest);self.event(dict(event='generation',**manifest));raise exc
        write(out/'gen-manifest.json',manifest);self.event(dict(event='generation',**manifest))
        return manifest


def saved_paths(stdout):
    """Parse final agent JSON/JSONL, never scan a directory or reuse an old PNG."""
    candidates=[]
    def visit(value):
        if isinstance(value,dict):
            if 'image_paths' in value:candidates.extend(value['image_paths'])
            for field in ('text','content','item','message'):
                if field in value:visit(value[field])
        elif isinstance(value,list):
            for item in value:visit(item)
        elif isinstance(value,str):
            text=value.strip().strip('`')
            if text.startswith('json'):text=text[4:].strip()
            try:visit(json.loads(text))
            except (ValueError,RecursionError):
                # Actual CLI final replies may be Markdown links or a saved-path sentence.
                candidates.extend(re.findall(r'(?:[A-Za-z]:[\\/]|/)[^\r\n"<>|]*?\.png',value))
    for line in stdout.splitlines():
        try:
            event=json.loads(line)
            if event.get('type')=='item.completed' and event.get('item',{}).get('type')=='agent_message':visit(event['item'])
            elif 'image_paths' in event:visit(event)
        except (ValueError,AttributeError):pass
    if not candidates:visit(stdout)
    return list(dict.fromkeys(str(Path(p).expanduser().resolve()) for p in candidates if isinstance(p,str) and Path(p).expanduser().is_file()))
