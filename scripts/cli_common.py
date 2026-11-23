"""Shared CLI version, --json, and RFC 9457 problem details."""
from __future__ import annotations

import json
import sys

VERSION = '1.0.0'
PROBLEM_TYPE_BASE = 'urn:video-gif-studio:problem:'


def problem(code, title, detail, status=400, exit_code=2):
    return {
        'type': PROBLEM_TYPE_BASE + code,
        'title': title,
        'status': status,
        'detail': detail,
        'exit_code': exit_code,
    }


def emit_problem(payload, stream=None):
    stream = stream or sys.stderr
    stream.write(json.dumps(payload, ensure_ascii=False) + '\n')
    stream.flush()
    return int(payload.get('exit_code') or 2)


def wants_json(argv):
    return '--json' in list(argv or [])
