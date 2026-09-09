"""Resolve system or skill-managed FFmpeg without downloading during a render."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess


def locate(name):
    if name not in ('ffmpeg', 'ffprobe'):
        raise ValueError('Unknown media executable')
    override = os.environ.get('VIDEO_GIF_' + name.upper())
    if override:
        path = Path(override).expanduser()
        if not path.is_file() or not os.access(path, os.X_OK):
            raise RuntimeError('Invalid VIDEO_GIF_' + name.upper() + ' executable')
        return str(path.resolve())
    system = shutil.which(name)
    if system:
        return system
    try:
        from static_ffmpeg.run import get_platform_dir
        path = Path(get_platform_dir()) / (name + ('.exe' if os.name == 'nt' else ''))
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    except (ImportError, OSError):
        pass
    return None


def executable(name):
    path = locate(name)
    if not path:
        raise RuntimeError('Media runtime missing; run scripts/media_runtime.py --install')
    return path


def setup(managed=False):
    paths = {name: locate(name) for name in ('ffmpeg', 'ffprobe')}
    if managed or not all(paths.values()):
        from static_ffmpeg.run import get_or_fetch_platform_executables_else_raise
        ffmpeg, ffprobe = get_or_fetch_platform_executables_else_raise()
        paths = {'ffmpeg': ffmpeg, 'ffprobe': ffprobe}
    for path in paths.values():
        subprocess.run([path, '-version'], check=True, timeout=30,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return paths


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--managed', action='store_true', help='Fetch/verify managed binaries even if system tools exist')
    args = parser.parse_args()
    print(json.dumps(setup(args.managed) if args.install else
                     {name: locate(name) for name in ('ffmpeg', 'ffprobe')}))
