#!/usr/bin/env python3
"""Assemble reviewed video edits by frame; retain complete original audio independently."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from media_runtime import executable


def run(tool, args):
    return subprocess.run([executable(tool), *map(str, args)], check=True,
                          capture_output=True, text=True).stdout


def probe(path):
    data = json.loads(run('ffprobe', ['-v', 'error', '-count_frames', '-show_streams',
                                    '-show_format', '-of', 'json', path]))
    video = next(s for s in data['streams'] if s['codec_type'] == 'video')
    return {'frames': int(video['nb_read_frames']), 'fps': video['avg_frame_rate'],
            'width': video['width'], 'height': video['height'],
            'audio': any(s['codec_type'] == 'audio' for s in data['streams'])}


def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audio_hash(path):
    return run('ffmpeg', ['-v', 'error', '-i', path, '-map', '0:a:0', '-c:a', 'copy',
                          '-f', 'hash', '-hash', 'sha256', '-']).strip()


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'Expected integer >= {minimum}, got {value!r}')
    return value


def assemble(manifest, output):
    manifest, output = Path(manifest).resolve(), Path(output).resolve()
    spec = json.loads(manifest.read_text())
    if spec.get('version') != 1:
        raise ValueError('Unsupported manifest version')
    def local(name):
        path = (manifest.parent / name).resolve()
        if not path.is_file():
            raise ValueError(f'Missing local input: {path}')
        return path
    source = local(spec['source'])
    source_meta = probe(source)
    fps = Fraction(spec['fps'])
    if fps <= 0 or fps > 240 or Fraction(source_meta['fps']) != fps:
        raise ValueError('fps must match the source CFR timeline (1–240)')
    timestamps = json.loads(run('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_frames',
        '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json', source]))['frames']
    times = [float(frame['best_effort_timestamp_time']) for frame in timestamps]
    if any(abs((b - a) - float(1 / fps)) > 0.00001 for a, b in zip(times, times[1:])):
        raise ValueError('Variable frame rate source: explicitly conform a separate source first')
    total = integer(spec['frames'], 1)
    if total != source_meta['frames']:
        raise ValueError('Expected frame count must match complete source video')
    width, height = source_meta['width'], source_meta['height']
    if width % 2 or height % 2:
        raise ValueError('H.264 delivery requires even source dimensions')
    segments, cursor, inputs = [], 0, []
    for item in spec['segments']:
        path = local(item['path']); meta = probe(path)
        start, count = integer(item['start_frame']), integer(item['frames'], 1)
        if integer(item['timeline_start']) != cursor:
            raise ValueError('Timeline must cover source without gaps or overlaps')
        if Fraction(meta['fps']) != fps and spec.get('allow_fps_conform') is not True:
            raise ValueError('FPS differs: explicit allow_fps_conform required (duplicates/drops frames)')
        segments.append((path, start, count)); cursor += count
        inputs.append({'path': str(path), 'sha256': digest(path), 'media': meta})
    if cursor != total:
        raise ValueError('Segments must cover the complete source')
    regions = spec.get('restore_regions', [])
    for region in regions:
        x, y = integer(region['x']), integer(region['y'])
        w, h = integer(region['width'], 1), integer(region['height'], 1)
        a, b = integer(region['start_frame']), integer(region['end_frame'], 1)
        if x + w > width or y + h > height or not a < b <= total or any(v % 2 for v in (x, y, w, h)):
            raise ValueError('Restore region must be in bounds, even aligned, and have an exclusive end frame')
    report = output.with_suffix('.verification.json')
    if output.exists() or report.exists() or output in [source, manifest, *[s[0] for s in segments]]:
        raise ValueError('Output/report already exists or aliases an input; choose a new candidate path')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.assemble-', dir=output.parent) as temporary:
        temp = Path(temporary); clips = []
        for i, (path, start, count) in enumerate(segments):
            clip = temp / f'{i}.mp4'
            filters = f'fps={fps},trim=start_frame={start}:end_frame={start+count},setpts=PTS-STARTPTS,scale={width}:{height},setsar=1'
            run('ffmpeg', ['-v', 'error', '-i', path, '-an', '-vf', filters,
                           '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', clip])
            if probe(clip)['frames'] != count:
                raise ValueError(f'Segment {i} underflow: no silent freeze, stretch or padding allowed')
            clips.append(clip)
        listing = temp / 'clips.txt'
        listing.write_text(''.join(f"file '{p.name}'\n" for p in clips))
        visual = temp / 'visual.mp4'
        run('ffmpeg', ['-v', 'error', '-f', 'concat', '-safe', '1', '-i', listing,
                       '-map', '0:v:0', '-c', 'copy', visual])
        if regions:
            graph, previous = [], '0:v'
            for i, r in enumerate(regions):
                graph.append(f"[1:v]crop={r['width']}:{r['height']}:{r['x']}:{r['y']}[crop{i}]")
                graph.append(f"[{previous}][crop{i}]overlay={r['x']}:{r['y']}:enable='gte(n,{r['start_frame']})*lt(n,{r['end_frame']})'[out{i}]")
                previous = f'out{i}'
            restored = temp / 'restored.mp4'
            run('ffmpeg', ['-v', 'error', '-i', visual, '-i', source, '-filter_complex', ';'.join(graph),
                           '-map', f'[{previous}]', '-an', '-c:v', 'libx264', '-crf', '18', restored])
            visual = restored
        candidate = temp / 'candidate.mp4'
        # Separate finite-video mux: -frames:v / -t / -shortest here can truncate audio packets.
        run('ffmpeg', ['-v', 'error', '-i', visual, '-i', source, '-map', '0:v:0',
                       '-map', '1:a?', '-c', 'copy', '-movflags', '+faststart', candidate])
        result = probe(candidate)
        if result['frames'] != total:
            raise ValueError('Final frame coverage mismatch')
        # Verify every original audio stream, not only the default track.
        hashes = {}
        streams = json.loads(run('ffprobe', ['-v', 'error', '-select_streams', 'a', '-show_streams', '-of', 'json', source]))['streams']
        for i in range(len(streams)):
            def track_hash(path):
                return run('ffmpeg', ['-v', 'error', '-i', path, '-map', f'0:a:{i}', '-c', 'copy', '-f', 'hash', '-hash', 'sha256', '-']).strip()
            original, final = track_hash(source), track_hash(candidate)
            if original != final:
                raise ValueError(f'Original audio stream {i} changed or truncated')
            hashes[str(i)] = original
        record = {'version': 1, 'manifest': spec, 'source': {'path': str(source), 'sha256': digest(source), 'media': source_meta},
                  'inputs': inputs, 'output_sha256': digest(candidate), 'output': result, 'audio_stream_hashes': hashes,
                  'technical': 'passed', 'identity_motion_effects_review': 'pending', 'normal_speed_review': 'pending',
                  'human_approval': 'pending', 'fps_conformed': any(Fraction(i['media']['fps']) != fps for i in inputs)}
        candidate.rename(output)
        report.write_text(json.dumps(record, indent=2) + '\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    assemble(args.manifest, args.output)
    print(args.output.resolve())
