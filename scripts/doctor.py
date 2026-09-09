#!/usr/bin/env python3
"""Read-only installed skill/runtime capability check. No generation or login."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

root=Path(__file__).resolve().parents[1]
config_file=root/'local-settings.json'
config=json.loads(config_file.read_text()) if config_file.exists() else {}
adapter=os.environ.get('VIDEO_GIF_GROK_ADAPTER') or config.get('grok_adapter')
packages={name:importlib.util.find_spec(name) is not None for name in ['PIL','numpy','cv2']}
report={'skill_entry_exists':(root/'SKILL.md').is_file(),'python':sys.executable,
        'python_version_supported':sys.version_info >= (3,11),'packages':packages,
        'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe'),
        'grok_cli':shutil.which('grok'),'grok_adapter_present':bool(adapter and Path(adapter).is_file()),
        'grok_auth_and_generation_quota':'not checked; no external requests made'}
report['local_gif_runtime_ready']=report['python_version_supported'] and all(packages.values())
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['skill_entry_exists'] and report['local_gif_runtime_ready'] else 1)
