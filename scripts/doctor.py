#!/usr/bin/env python3
"""Read-only installed skill/runtime capability check. No generation or login."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

from cli_common import VERSION, emit_problem, problem, wants_json
from grok_client import GrokClient
from fal_video import key_present
from media_runtime import locate


def collect():
    root = Path(__file__).resolve().parents[1]
    packages = {name: importlib.util.find_spec(name) is not None for name in ['PIL', 'numpy', 'cv2']}
    report = {
        'schema_version': 1,
        'skill_entry_exists': (root / 'SKILL.md').is_file(),
        'python': sys.executable,
        'python_version_supported': sys.version_info >= (3, 11),
        'packages': packages,
        'ffmpeg': locate('ffmpeg'),
        'ffprobe': locate('ffprobe'),
        'grok_cli': shutil.which('grok'),
        'grok_support': 'bundled',
        'grok_oauth': GrokClient().inspect(),
        'grok_auth_and_generation_quota': 'not checked; no external requests made',
    }
    report['local_gif_runtime_ready'] = report['python_version_supported'] and all(packages.values())
    report['media_runtime_ready'] = bool(report['ffmpeg'] and report['ffprobe'])
    report['ready'] = bool(report['skill_entry_exists'] and report['local_gif_runtime_ready'] and report['media_runtime_ready'])
    report['report_ok'] = True
    report['qa_media'] = {
        'numpy': packages['numpy'], 'PIL': packages['PIL'],
        'ffmpeg': report['ffmpeg'], 'ffprobe': report['ffprobe'],
        'picture_ready': packages['numpy'] and packages['PIL'],
        'video_audio_ready': packages['numpy'] and packages['PIL'] and report['media_runtime_ready'],
        'ffmpeg_only_fallback_available': bool(packages['numpy'] and packages['PIL'] and report['ffmpeg']),
        'note': 'GIF/APNG/PNG need numpy and Pillow. Video/audio use ffmpeg/ffprobe; recent ffmpeg also offers a showinfo timing fallback, verified when QA runs.',
    }
    report['api_key_available'] = bool(os.environ.get('XAI_API_KEY', '').strip())
    report['fal'] = {'support': 'bundled MiniMax H3 Max', 'key_present': key_present(), 'auth_and_quota': 'not checked; no external requests made'}
    report['optional_matting_installed'] = importlib.util.find_spec('rembg') is not None
    try:
        from identity_engine import capability
        report['optional_identity_engine'] = capability()
    except ImportError:
        report['optional_identity_engine'] = {'available': False, 'reason': 'optional identity stack not importable'}
    return report


def format_human(report):
    ok = 'ready' if report['ready'] else 'not ready'
    pkgs = ', '.join(f'{k}={"yes" if v else "no"}' for k, v in report['packages'].items())
    return (
        f"video-gif-studio doctor {VERSION} — local runtime {ok}.\n"
        f"Python {sys.version.split()[0]} ({'supported' if report['python_version_supported'] else 'need 3.11+'}).\n"
        f"Packages: {pkgs}.\n"
        f"FFmpeg: {report['ffmpeg'] or 'missing'}; ffprobe: {report['ffprobe'] or 'missing'}.\n"
        f"Skill entry: {'found' if report['skill_entry_exists'] else 'missing SKILL.md'}.\n"
        "No generation, login, or network calls are made.\n"
    )


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    json_mode = wants_json(argv)
    parser = argparse.ArgumentParser(
        prog='doctor',
        description=(
            'Read-only check of the installed Video GIF Studio skill and local runtime. '
            'It reports Python, Pillow/NumPy/OpenCV, FFmpeg/ffprobe, and optional engines. '
            'It never generates media, never logs in, and never sends network requests.'
        ),
        epilog=(
            'The JSON field ready is true only when SKILL.md, Python 3.11+ with core packages, '
            'and ffmpeg/ffprobe are all present. The process exits 0 after a successful report; '
            'use ready to decide whether the runtime can deliver. Use --json for the report.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--json', action='store_true', help='Write only the JSON report to stdout (default)')
    parser.add_argument('--human', action='store_true', help='Write a short prose summary instead of JSON')
    parser.add_argument('--version', action='version', version=VERSION)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 0
        if json_mode and code not in (0, None):
            return emit_problem(problem('usage', 'Invalid doctor arguments', 'See doctor --help.', exit_code=2 if code else 0))
        raise
    report = collect()
    if args.human and not json_mode:
        sys.stdout.write(format_human(report))
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
