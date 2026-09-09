#!/usr/bin/env python3
"""Read-only installed skill/runtime capability check. No generation or login."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

root=Path(__file__).resolve().parents[1]
from grok_client import GrokClient
from media_runtime import locate
packages={name:importlib.util.find_spec(name) is not None for name in ['PIL','numpy','cv2']}
report={'skill_entry_exists':(root/'SKILL.md').is_file(),'python':sys.executable,
        'python_version_supported':sys.version_info >= (3,11),'packages':packages,
        'ffmpeg':locate('ffmpeg'),'ffprobe':locate('ffprobe'),
        'grok_cli':shutil.which('grok'),'grok_support':'bundled', 'grok_oauth':GrokClient().inspect(),
        'grok_auth_and_generation_quota':'not checked; no external requests made'}
report['local_gif_runtime_ready']=report['python_version_supported'] and all(packages.values())
report['media_runtime_ready']=bool(report['ffmpeg'] and report['ffprobe'])
report['api_key_available']=bool(os.environ.get('XAI_API_KEY','').strip())
report['optional_matting_installed']=importlib.util.find_spec('rembg') is not None
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['skill_entry_exists'] and report['local_gif_runtime_ready'] and report['media_runtime_ready'] else 1)
