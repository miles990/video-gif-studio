#!/usr/bin/env python3
"""Export RGBA frames + timing as ProRes MOV, VP9 WebM or opaque H.264 MP4."""
import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image


def export(frames, manifest, target, background="000000"):
    files = sorted(Path(frames).glob('*.png'))
    data = json.loads(Path(manifest).read_text())
    durations = data['durations_ms']
    target = Path(target)
    if target.suffix.lower() not in ('.mov', '.webm', '.mp4'):
        raise ValueError('Choose .mov, .webm or .mp4')
    if target.exists() or target.with_suffix(target.suffix + '.json').exists():
        raise FileExistsError('Use a new output file')
    if not files or len(files) != len(durations):
        raise ValueError('Frame count must match durations_ms')
    if any(not isinstance(t, (int, float)) or not math.isfinite(t) or t <= 0 or abs(t / 10 - round(t / 10)) > 1e-8 for t in durations):
        raise ValueError('Durations must be positive multiples of 10ms from the GIF pipeline')
    # 100 fps repeats existing frames exactly; does not synthesize/interpolate motion.
    repeats = [round(t / 10) for t in durations]
    with Image.open(files[0]) as first:
        w, h = first.size
    for file in files:
        with Image.open(file) as im:
            if im.size != (w, h):
                raise ValueError('All frames must have the same size')
    if len(background) != 6:
        raise ValueError('Background must be six hex digits')
    try:
        bg = tuple(int(background[i:i+2],16) for i in (0,2,4)) + (255,)
    except ValueError:
        raise ValueError('Background must be six hex digits') from None
    webm = target.suffix.lower() == '.webm'
    mp4 = target.suffix.lower() == '.mp4'
    if (webm or mp4) and (w % 2 or h % 2):
        raise ValueError('4:2:0 video requires even dimensions; prepare a shared padded canvas first')
    opts = ['-c:v', 'libvpx-vp9', '-lossless', '1', '-pix_fmt', 'yuva420p', '-auto-alt-ref', '0'] if webm else ['-c:v', 'prores_ks', '-profile:v', '4', '-pix_fmt', 'yuva444p10le', '-alpha_bits', '16']
    if mp4:
        opts = ['-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart']
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        encoded = Path(tmp) / ('encoded' + target.suffix.lower())
        with tempfile.TemporaryFile() as err:
            cmd = ['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgba', '-video_size', f'{w}x{h}', '-framerate', '100', '-i', 'pipe:0', '-an', *opts, str(encoded)]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=err)
            try:
                for file, count in zip(files, repeats):
                    with Image.open(file) as im:
                        rgba = im.convert('RGBA')
                        if mp4:
                            canvas = Image.new('RGBA', rgba.size, bg)
                            canvas.alpha_composite(rgba)
                            rgba = canvas
                        raw = rgba.tobytes()
                    for _ in range(count):
                        proc.stdin.write(raw)
                proc.stdin.close()
                if proc.wait():
                    raise RuntimeError('FFmpeg encode failed; check encoder availability')
            finally:
                if proc.poll() is None:
                    proc.kill(); proc.wait()
            # Explicit libvpx decoding is required to exercise WebM alpha, rather than
            # accidentally validating an opaque decode from another VP9 decoder.
            dec = ['ffmpeg', '-v', 'error', *(['-c:v', 'libvpx-vp9'] if webm else []), '-i', str(encoded), '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1']
            proc = subprocess.Popen(dec, stdout=subprocess.PIPE, stderr=err)
            worst = 0; frames_seen = 0
            try:
                for file, count in zip(files, repeats):
                    with Image.open(file) as im:
                        expected = np.array(im.convert('RGBA'))[:, :, 3].astype('int16')
                    if mp4:
                        expected[:] = 255
                    for _ in range(count):
                        raw = proc.stdout.read(w*h*4)
                        if len(raw) != w*h*4:
                            raise RuntimeError('Truncated decoded timeline')
                        alpha = np.frombuffer(raw, dtype='uint8').reshape(h,w,4)[:,:,3].astype('int16')
                        worst = max(worst, int(np.abs(alpha-expected).max())); frames_seen += 1
                if proc.stdout.read(1) or proc.wait():
                    raise RuntimeError('Unexpected decoded timeline or decoder failure')
            finally:
                if proc.poll() is None:
                    proc.kill(); proc.wait()
            proc.stdout.close()
            if worst > 2:
                raise RuntimeError(f'Alpha verification failed: max error {worst}/255')
        probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(encoded)]))
        actual_ms = float(probe['format']['duration']) * 1000
        if abs(actual_ms - sum(durations)) > 10.01:
            raise RuntimeError('Container duration does not match source timing')
        encoded.replace(target)
    report = {'file': target.name, 'codec': 'H.264' if mp4 else ('VP9 with alpha' if webm else 'ProRes 4444'),
              'transparent': not mp4, 'background': background if mp4 else None,
              'size': [w,h], 'fps': 100, 'source_frames': len(files), 'encoded_frames': frames_seen,
              'source_duration_ms': sum(durations), 'container_duration_ms': actual_ms,
              'alpha_max_error_255': worst, 'audio': False, 'loop': 'single cycle; player controls repeat',
              'timing': 'Exact 10ms timeline through repeated frames; no motion interpolation',
              'limitations': 'YUV conversion may change RGB; target player/engine alpha support must be tested'}
    target.with_suffix(target.suffix + '.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('frames', type=Path)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--background', default='000000', help='MP4 matte color, six hex digits; default black')
    a = ap.parse_args()
    print(json.dumps(export(a.frames,a.manifest,a.out,a.background)))


if __name__ == '__main__':
    main()
