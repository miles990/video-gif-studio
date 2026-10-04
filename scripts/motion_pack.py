#!/usr/bin/env python3
"""Verify a Laceframe control ZIP before encoding a silent CFR guide. Never runs pack commands."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import zipfile
from PIL import Image
from media_runtime import executable


def verify(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) > 3000:
            raise ValueError('duplicate entries or excessive entry count')
        for item in z.infolist():
            p = PurePosixPath(item.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in item.filename or item.file_size > 20_000_000:
                raise ValueError('unsafe ZIP member')
        if sum(i.file_size for i in z.infolist()) > 500_000_000:
            raise ValueError('pack exceeds 500 MB unpacked limit')
        manifest = json.loads(z.read('pack.json'))
        if manifest.get('schema') != 'laceframe.motion-pack.v1':
            raise ValueError('unknown pack schema')
        clip = manifest['clip']
        fps, count, duration = clip['fps'], clip['frames'], clip['durationSec']
        if not isinstance(fps, (int, float)) or not math.isfinite(fps) or not 1 <= fps <= 60:
            raise ValueError('invalid frame rate')
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 1800:
            raise ValueError('invalid frame count')
        if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0 or abs(count-duration*fps) > .50001:
            raise ValueError('duration/frame count mismatch')
        records = manifest['controlFrames']['records']
        if len(records) != count:
            raise ValueError('record count mismatch')
        frames, size = [], None
        for index, record in enumerate(records):
            expected = f'control/frame-{index+1:04d}.png'
            if record['path'] != expected or abs(record['atSec']-index/fps) > .00011:
                raise ValueError('frame sequence or timestamp mismatch')
            data = z.read(expected)
            if hashlib.sha256(data).hexdigest() != record['sha256']:
                raise ValueError(f'frame hash mismatch: {expected}')
            with Image.open(io.BytesIO(data)) as image:
                if image.format != 'PNG' or image.width > 4096 or image.height > 4096:
                    raise ValueError('unsupported control image')
                image.verify()
                if size and image.size != size:
                    raise ValueError('inconsistent frame dimensions')
                size = image.size
            frames.append(data)
        return manifest, frames, size


def encode(pack, output):
    output = Path(output)
    if output.exists() or output.with_suffix('.verification.json').exists():
        raise ValueError('output already exists')
    manifest, frames, size = verify(pack)
    with tempfile.TemporaryDirectory(prefix='motion-pack-') as tmp:
        root = Path(tmp)
        for i, data in enumerate(frames):
            (root / f'frame-{i+1:04d}.png').write_bytes(data)
        candidate = root / 'control.mp4'
        subprocess.run([executable('ffmpeg'), '-v', 'error', '-framerate', str(manifest['clip']['fps']), '-i', str(root/'frame-%04d.png'), '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-an', str(candidate)], check=True)
        probe = json.loads(subprocess.check_output([executable('ffprobe'), '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', str(candidate)]))
        if len(probe['streams']) != 1 or int(probe['streams'][0]['nb_read_frames']) != len(frames):
            raise ValueError('encoded frame count mismatch')
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('xb') as target:
            target.write(candidate.read_bytes())
    report = {'schema':'video-gif.motion-verification.v1','sourceSha256':hashlib.sha256(Path(pack).read_bytes()).hexdigest(),'output':str(output.resolve()),'frames':len(frames),'fps':manifest['clip']['fps'],'sourceSize':size,'controlOwnership':manifest.get('controlOwnership','camera-body'),'audio':'intentionally absent in control guide; preserve original audio separately for final delivery','creativeApproval':'pending'}
    output.with_suffix('.verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pack', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.output:
        print(json.dumps(encode(args.pack,args.output),indent=2))
    else:
        m, frames, size = verify(args.pack)
        print(json.dumps({'valid':True,'frames':len(frames),'size':size,'controlOwnership':m.get('controlOwnership','camera-body')}))

if __name__ == '__main__':
    main()
