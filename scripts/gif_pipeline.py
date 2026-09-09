#!/usr/bin/env python3
"""CFR video/RGBA frames -> deterministic global-palette GIF plus decoded QC."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageSequence


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def natural(path):
    return [int(v) if v.isdigit() else v for v in re.split(r'(\d+)', path.name)]


def load_frames(source, fps, width, key, tolerance, softness):
    frames = []
    if source.is_dir():
        paths = sorted(source.glob('*.png'), key=natural)
        if not fps:
            raise ValueError('PNG input requires --fps')
        raw = (Image.open(f).convert('RGBA') for f in paths)
    else:
        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise ValueError('Cannot decode input video')
        native = cap.get(cv2.CAP_PROP_FPS)
        if fps and abs(fps-native) > .001:
            raise ValueError('Do not relabel video FPS; conform VFR externally or use speed phases')
        fps = native
        def decoded():
            try:
                while True:
                    ok, frame = cap.read()
                    if not ok:
                        break
                    yield Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert('RGBA')
            finally:
                cap.release()
        raw = decoded()
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError('Invalid source FPS')
    for im in raw:
        if width and im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
        if key:
            a = np.array(im)
            # Chromatic distance ignores modest exposure shifts of a flat screen.
            rgb = a[:, :, :3].astype(float) / 255
            color = np.array(key, dtype=float) / 255
            chroma = rgb - rgb.mean(axis=2, keepdims=True)
            color = color - color.mean()
            dist = np.linalg.norm(chroma - color, axis=2)
            alpha = np.clip((dist - tolerance) / softness, 0, 1)
            a[:, :, 3] = np.minimum(a[:, :, 3], np.round(alpha * 255).astype('uint8'))
            im = Image.fromarray(a)
        frames.append(im)
    if not frames or any(f.size != frames[0].size for f in frames):
        raise ValueError('Empty input or changing canvas size')
    return frames, fps


def timing(count, fps, phases):
    previous = 0
    for phase in phases:
        start, end, speed = (float(phase[k]) for k in ('start', 'end', 'speed'))
        ramp = float(phase.get('ramp', .25))
        if not all(np.isfinite(v) for v in (start, end, speed, ramp)):
            raise ValueError('Non-finite phase')
        if start < previous or end <= start or end > count/fps or speed <= 0 or ramp < 0:
            raise ValueError('Invalid/overlapping phase ranges')
        previous = end
    indices, durations, accumulated = [], [], 0.
    for i in range(count):
        t = (i + .5) / fps
        rate = 1.
        for phase in phases:
            if phase['start'] <= t < phase['end']:
                ramp = phase.get('ramp', .25)
                blend = 1. if ramp == 0 else min(1., (t-phase['start'])/ramp, (phase['end']-t)/ramp)
                blend = .5 - .5*np.cos(np.pi*blend)
                rate = 1 + (phase['speed']-1)*blend
                break
        accumulated += 1000 / fps / rate
        # Most GIF viewers clamp very short frame times; keep >=20ms.
        if accumulated >= 20:
            indices.append(i)
            durations.append(accumulated)
            accumulated = 0.
    if accumulated:
        if not durations:
            raise ValueError('Output shorter than 20ms cannot be represented reliably')
        durations[-1] += accumulated
    edges = np.round(np.cumsum([0.] + durations) / 10) * 10
    return indices, np.diff(edges).astype(int).tolist()


def encode(frames, durations, target):
    # Fixed-size sampled training bounds palette-training memory, not output quality dimensions.
    samples = []
    for frame in frames:
        thumb = frame.copy()
        thumb.thumbnail((96, 96))
        a = np.array(thumb)
        samples.append(a[:, :, :3][a[:, :, 3] >= 128])
    visible = np.concatenate(samples)
    if not len(visible):
        raise ValueError('No visible foreground')
    # 255 visible colors, final entry duplicated then RESERVED for transparency.
    train = Image.fromarray(visible.reshape((-1, 1, 3)))
    palette = train.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    colors = (palette.getpalette() + [0]*768)[:765]
    colors += colors[:3]
    palette.putpalette(colors)
    result = []
    for frame in frames:
        arr = np.array(frame)
        q = np.array(frame.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE))
        q[q == 255] = 0
        q[arr[:, :, 3] < 128] = 255
        im = Image.fromarray(q)
        im.putpalette(colors)
        result.append(im)
    result[0].save(target, format='GIF', save_all=True, append_images=result[1:],
                   duration=durations, loop=0, transparency=255, background=255,
                   disposal=2, optimize=False)


def verify(target, frames, durations):
    decoded = []
    actual_durations = []
    with Image.open(target) as gif:
        for frame in ImageSequence.Iterator(gif):
            decoded.append(np.array(frame.convert('RGBA')))
            actual_durations.append(frame.info.get('duration', 0))
    if sum(actual_durations) != sum(durations):
        raise ValueError('Decoded GIF duration mismatch')
    # Encoders may coalesce truly identical adjacent frames; compare by timeline.
    mismatch, errors, index, elapsed, end = 0, [], 0, 0, actual_durations[0]
    for frame, duration in zip(frames, durations):
        while elapsed >= end and index+1 < len(decoded):
            index += 1
            end += actual_durations[index]
        if elapsed + duration > end:
            raise ValueError('Unexpected decoded frame timing boundary')
        source, output = np.array(frame), decoded[index]
        if source.shape != output.shape:
            raise ValueError('Decoded canvas mismatch')
        visible = source[:, :, 3] >= 128
        mismatch += int(np.count_nonzero(visible != (output[:, :, 3] > 0)))
        if visible.any():
            errors.append(float(np.abs(source[:, :, :3].astype(float)-output[:, :, :3])[visible].mean()))
        elapsed += duration
    if mismatch:
        raise ValueError(f'Decoded GIF integrity failure: alpha={mismatch}')
    return {'decoded_frames': len(decoded), 'source_output_frames': len(frames),
            'duration_ms': sum(actual_durations), 'alpha_mismatch_pixels': mismatch,
            'mean_visible_rgb_error': float(np.mean(errors)) if errors else 0,
            'technical_pass': True, 'visual_motion_approval': 'not assessed by script'}


def contact(frames, target):
    count = min(12, len(frames))
    board = Image.new('RGB', (4*240, ((count+3)//4)*270), '#dddddd')
    draw = ImageDraw.Draw(board)
    for j, idx in enumerate(np.linspace(0, len(frames)-1, count).astype(int)):
        im = frames[idx].copy()
        im.thumbnail((232, 240))
        x, y = j % 4 * 240, j // 4 * 270
        draw.rectangle((x,y,x+239,y+245), fill='#171717' if j%2 else '#eeeeee')
        board.paste(im, (x+(240-im.width)//2,y), im)
        draw.text((x+6,y+248), f'output frame {idx}', fill='black')
    board.save(target)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--fps', type=float, help='Required for PNG input, not a retiming override')
    ap.add_argument('--width', type=int, default=640)
    ap.add_argument('--pixel-width', type=int, help='Optional raster grid width; overrides --width and never changes aspect ratio')
    ap.add_argument('--pixel-scale', type=int, default=1, help='Integer nearest-neighbor enlargement after keying; requires --pixel-width')
    ap.add_argument('--key', help='Uniform background hex RGB, e.g. FF00FF; omit to preserve alpha')
    ap.add_argument('--tolerance', type=float, default=.15)
    ap.add_argument('--softness', type=float, default=.12)
    ap.add_argument('--phases', type=Path, help='JSON array of start/end/speed/ramp in SOURCE seconds')
    ap.add_argument('--apng', action='store_true')
    args = ap.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        ap.error('Use an empty/new output directory; source assets are never overwritten')
    if args.width < 1 or args.tolerance < 0 or args.softness <= 0:
        ap.error('Invalid width or key settings')
    if args.pixel_scale < 1 or (args.pixel_width is not None and args.pixel_width < 1):
        ap.error('Pixel width and scale must be positive integers')
    if args.pixel_scale != 1 and args.pixel_width is None:
        ap.error('--pixel-scale requires --pixel-width')
    key = tuple(bytes.fromhex(args.key.lstrip('#'))) if args.key else None
    if key and len(key) != 3:
        ap.error('Key must have six hexadecimal digits')
    phases = json.loads(args.phases.read_text()) if args.phases else []
    all_frames, fps = load_frames(args.source, args.fps, args.pixel_width or args.width,
                                  key, args.tolerance, args.softness)
    raster_size = all_frames[0].size
    if args.pixel_width and args.pixel_scale != 1:
        all_frames = [im.resize((im.width*args.pixel_scale, im.height*args.pixel_scale),
                                Image.Resampling.NEAREST) for im in all_frames]
    indices, durations = timing(len(all_frames), fps, phases)
    frames = [all_frames[i] for i in indices]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'frames').mkdir()
    for j, im in enumerate(frames):
        im.save(args.out/'frames'/f'{j:05d}.png')
    encode(frames, durations, args.out/'animation.gif')
    qc = verify(args.out/'animation.gif', frames, durations)
    if args.apng:
        frames[0].save(args.out/'animation.png', save_all=True, append_images=frames[1:],
                       duration=durations, loop=0, disposal=0, blend=0)
    contact(frames, args.out/'contact.png')
    parents = [{'file': str(f.resolve()), 'sha256': sha(f)} for f in
               (sorted(args.source.glob('*.png'), key=natural) if args.source.is_dir() else [args.source])]
    manifest = {'parents': parents, 'source_fps': fps, 'source_frames': len(all_frames),
                'source_indices': indices, 'durations_ms': durations, 'phases': phases,
                'key_rgb': key, 'key_tolerance': args.tolerance, 'key_softness': args.softness,
                'size': frames[0].size, 'transparency_index': 255,
                'pixel_processing': {'requested_width': args.pixel_width,
                                     'raster_size': raster_size, 'integer_scale': args.pixel_scale,
                                     'enlargement': 'nearest' if args.pixel_width else None},
                'script_sha256': sha(Path(__file__)), 'gif_sha256': sha(args.out/'animation.gif'), 'qc': qc}
    (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(qc))


if __name__ == '__main__':
    main()
