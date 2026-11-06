"""Shared experimental image contracts; no provider imports or network on import."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / '.scratch' / 'image-state'


class ImageError(ValueError):
    def __init__(self, code, message, location='image', suggestion='Inspect the request and retry.', **details):
        super().__init__(message)
        self.error = dict(code=code, message=message, location=location, suggestion=suggestion, **details)


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def key(data):
    return hashlib.sha256(canonical(data).encode('utf-8')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    stage.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(stage, path)


@contextmanager
def locked(path, timeout=900):
    """OS-held lock survives threads/processes and releases on process death."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b'0'); stream.flush()
        start = time.monotonic()
        while True:
            try:
                stream.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() - start > timeout:
                    raise ImageError('E_CACHE_BUSY', 'Timed out waiting for an active image request.') from None
                time.sleep(.05)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def c2pa(path):
    """Detect containers only, never claim authenticity or a generator identity."""
    raw = Path(path).read_bytes()
    present = False
    if raw.startswith(b'\x89PNG\r\n\x1a\n'):
        offset = 8
        while offset + 12 <= len(raw):
            length = struct.unpack('>I', raw[offset:offset+4])[0]
            if offset + length + 12 > len(raw):
                return dict(c2pa_present='unknown', c2pa_claim_generator=None, c2pa_validation='malformed container')
            present |= raw[offset+4:offset+8] == b'caBX'
            offset += length + 12
    elif raw[:2] == b'\xff\xd8':
        offset = 2
        while offset + 4 <= len(raw) and raw[offset] == 255:
            marker = raw[offset+1]
            if marker in (0xDA, 0xD9):break
            length = int.from_bytes(raw[offset+2:offset+4], 'big')
            if length < 2 or offset + length + 2 > len(raw):break
            present |= marker == 0xEB and b'jumb' in raw[offset+4:offset+2+length]
            offset += length + 2
    else:
        present = 'unknown'
    return dict(c2pa_present=present, c2pa_claim_generator=None, c2pa_validation='container presence only; signature not verified')
