#!/usr/bin/env python3
"""Run JavaScript style plugins in headless Chromium over the DevTools pipe, using only the standard library.

A JS plugin defines `async function render(ctx, api)` and returns ImageData or an (Offscreen)Canvas of the frame
size. ctx: index, count, width, height, params, base (ImageData of the reference render), mask (Uint8Array, subject
coverage), and when flow guides exist uv/flow (Float32Array, interleaved x,y at uvWidth x uvHeight = half size) and
flowValid (Uint8Array, same grid). api.noise(key) returns a seeded PRNG; Math.random is disabled so renders stay
reproducible. Browser: $VGS_CHROME, else Playwright's cached headless shell or Chromium, else chromium/chrome on PATH.
"""
import base64
import glob
import hashlib
import io
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import numpy as np
from PIL import Image

BOOT = r"""
(() => {
  const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const f32 = s => new Float32Array(b64(s).buffer);
  async function image(s) {
    const bmp = await createImageBitmap(new Blob([b64(s)], {type: 'image/png'}));
    const c = new OffscreenCanvas(bmp.width, bmp.height), g = c.getContext('2d');
    g.drawImage(bmp, 0, 0); return g.getImageData(0, 0, bmp.width, bmp.height);
  }
  function fnv(s) { let h = 2166136261; for (const ch of s) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
  function mulberry(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  Math.random = () => { throw new Error('Math.random is disabled; use api.noise(key) for reproducible randomness'); };
  window.__frame = async (payload) => {
    const p = JSON.parse(payload);
    const ctx = {index: p.index, count: p.count, width: p.width, height: p.height, params: p.params,
                 base: await image(p.base), mask: (await image(p.mask)).data.filter((_, i) => i % 4 === 0),
                 uv: p.uv ? f32(p.uv) : null, flow: p.flow ? f32(p.flow) : null,
                 flowValid: p.flowValid ? b64(p.flowValid) : null, uvWidth: p.uvWidth, uvHeight: p.uvHeight};
    const api = {noise: key => mulberry(fnv(p.seed + ':' + JSON.stringify(key)))};
    let out = await window.__render(ctx, api);
    if (out instanceof ImageData) { const c = new OffscreenCanvas(out.width, out.height); c.getContext('2d').putImageData(out, 0, 0); out = c; }
    if (!out || out.width !== p.width || out.height !== p.height) throw new Error('JS plugin must return a frame of the input size');
    const blob = await out.convertToBlob({type: 'image/png'});
    const bytes = new Uint8Array(await blob.arrayBuffer());
    let s = ''; for (let i = 0; i < bytes.length; i += 32768) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 32768));
    return btoa(s);
  };
})();
"""


def find_browser():
    if os.environ.get('VGS_CHROME'):
        return os.environ['VGS_CHROME']
    caches = [Path.home()/'Library/Caches/ms-playwright', Path.home()/'.cache/ms-playwright']
    for pattern in ('chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell',
                    'chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium', 'chromium-*/chrome-linux*/chrome'):
        found = sorted((p for c in caches for p in glob.glob(str(c/pattern))), reverse=True)
        if found:
            return found[0]
    for name in ('chrome-headless-shell', 'chromium', 'chromium-browser', 'google-chrome'):
        if shutil.which(name):
            return shutil.which(name)
    raise RuntimeError('No headless Chromium found; set VGS_CHROME or install Playwright Chromium')


class ChromeHost:
    """One headless page driven over --remote-debugging-pipe (fd 3 in, fd 4 out, NUL-delimited JSON)."""

    def __init__(self, browser=None, timeout=120):
        self.browser, self.timeout, self._id, self._buf = browser or find_browser(), timeout, 0, b''

    def __enter__(self):
        self._profile = tempfile.mkdtemp(prefix='vgs-chrome-')
        to_r, to_w = os.pipe()
        from_r, from_w = os.pipe()

        def child():
            os.dup2(to_r, 3)
            os.dup2(from_w, 4)
        # subprocess closes non-pass_fds after preexec_fn, so keep the child-side numbers 3 and 4.
        self._proc = subprocess.Popen([self.browser, '--headless', '--remote-debugging-pipe', '--disable-gpu',
                                       '--no-first-run', '--no-default-browser-check', f'--user-data-dir={self._profile}',
                                       'about:blank'], preexec_fn=child, pass_fds=(3, 4),
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(to_r)
        os.close(from_w)
        self._out, self._in = os.fdopen(to_w, 'wb', buffering=0), os.fdopen(from_r, 'rb', buffering=0)
        self.version = self.call('Browser.getVersion')
        target = self.call('Target.createTarget', {'url': 'about:blank'})['targetId']
        self._session = self.call('Target.attachToTarget', {'targetId': target, 'flatten': True})['sessionId']
        self.evaluate(BOOT)
        return self

    def __exit__(self, *exc):
        try:
            self._proc.terminate()
            self._proc.wait(10)
        finally:
            shutil.rmtree(self._profile, ignore_errors=True)

    def call(self, method, params=None, session=None):
        self._id += 1
        message = {'id': self._id, 'method': method, 'params': params or {}}
        if session:
            message['sessionId'] = session
        self._out.write(json.dumps(message).encode() + b'\0')
        while True:
            while b'\0' not in self._buf:
                if not select.select([self._in], [], [], self.timeout)[0]:
                    raise RuntimeError(f'Browser did not answer {method} within {self.timeout}s')
                chunk = self._in.read(1 << 20)
                if not chunk:
                    raise RuntimeError('Browser closed the DevTools pipe')
                self._buf += chunk
            raw, self._buf = self._buf.split(b'\0', 1)
            reply = json.loads(raw)
            if reply.get('id') == self._id:
                if 'error' in reply:
                    raise RuntimeError(f"{method}: {reply['error']}")
                return reply['result']

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', {'expression': expression, 'awaitPromise': True, 'returnByValue': True},
                           self._session)
        if 'exceptionDetails' in result:
            details = result['exceptionDetails']
            raise ValueError(f"JS plugin error: {details.get('exception', {}).get('description') or details.get('text')}")
        return result['result'].get('value')


def _png(array):
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format='PNG', compress_level=1)
    return base64.b64encode(buffer.getvalue()).decode()


class JSStyle:
    """Adapter giving a .js plugin the same render(ctx) call shape as a Python plugin."""

    def __init__(self, path, seed):
        self.path, self.seed = Path(path), seed
        self.code = self.path.read_text()

    def __enter__(self):
        self.host = ChromeHost().__enter__()
        self.host.evaluate(f'window.__render = (() => {{ {self.code}\n; return render; }})(); typeof window.__render')
        if self.host.evaluate('typeof window.__render') != 'function':
            raise ValueError(f'JS style plugin {self.path} must define render(ctx, api)')
        return self

    def __exit__(self, *exc):
        self.host.__exit__(*exc)

    def record(self):
        return {'path': str(self.path.resolve()), 'sha256': hashlib.sha256(self.path.read_bytes()).hexdigest(),
                'runtime': 'headless Chromium via DevTools pipe', 'browser': self.host.version.get('product'),
                'browser_path': self.host.browser}

    def render(self, ctx):
        h, w = ctx['base'].shape[:2]
        mask = ctx['character']['mask'].copy()
        if ctx['effects'] is not None:
            mask |= ctx['effects']['mask']
        payload = {'index': ctx['index'], 'count': ctx['count'], 'width': w, 'height': h, 'params': ctx['params'],
                   'seed': str(self.seed), 'base': _png(ctx['base']),
                   'mask': _png(np.dstack([mask.astype(np.uint8)*255]*3 + [np.full((h, w), 255, np.uint8)]))}
        if ctx['uv'] is not None:
            # Half-resolution motion data keeps each frame's payload near a megabyte.
            half = (w//2, h//2)
            payload['uv'] = base64.b64encode(np.ascontiguousarray(
                cv2_resize(ctx['uv'], half)/2, np.float32).tobytes()).decode()
            payload['uvWidth'], payload['uvHeight'] = half
            if ctx['flow'] is not None:
                payload['flow'] = base64.b64encode(np.ascontiguousarray(cv2_resize(ctx['flow'], half)/2, np.float32).tobytes()).decode()
                payload['flowValid'] = base64.b64encode(cv2_resize(ctx['flow_valid'].astype(np.uint8), half, nearest=True).tobytes()).decode()
        data = self.host.evaluate(f'window.__frame({json.dumps(json.dumps(payload))})')
        out = np.array(Image.open(io.BytesIO(base64.b64decode(data))).convert('RGBA'))
        if out.shape != (h, w, 4):
            raise ValueError('JS plugin returned the wrong frame size')
        return out


def cv2_resize(array, size, nearest=False):
    import cv2
    return cv2.resize(array, size, interpolation=cv2.INTER_NEAREST if nearest else cv2.INTER_AREA)
