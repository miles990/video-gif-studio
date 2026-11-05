"""Bounded video encoding and measured audio delivery. No optional model imports."""
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
from PIL import Image
from media_runtime import executable

FPS = (24, 25, 30, 50, 60, 100)
PLATFORMS = {
    name: dict(size=size, fps=30, bitrate=bitrate, safe_zone=margins)
    for name, size, bitrate, margins in [
        ('tiktok', (1080, 1920), '10M', (.05, .10, .10, .20)),
        ('reels', (1080, 1920), '10M', (.05, .10, .10, .20)),
        ('shorts', (1080, 1920), '10M', (.05, .10, .10, .20)),
        ('youtube', (1920, 1080), '10M', (.05, .05, .05, .05)),
        ('square', (1080, 1080), '8M', (.05, .10, .05, .10)),
    ]
}


def rate(fps):
    if fps not in FPS:
        raise ValueError('fps: choose 24, 25, 30, 50, 60 or explicit 100 (legacy)')
    return int(fps)


def quantize(ms, fps):
    frame = math.floor(ms * fps / 1000 + .5)
    actual = frame * 1000 / fps
    return dict(requested_ms=ms, frame=frame, quantized_ms=actual, error_ms=actual-ms)


def settings(size, fps=30, platform=None, proxy=False):
    rate(fps)
    if platform is not None and platform not in PLATFORMS:
        raise ValueError('platform: choose ' + ', '.join(PLATFORMS))
    if platform and fps==100:
        raise ValueError('Legacy 100 fps cannot be combined with a platform preset; choose 24, 25, 30, 50 or 60')
    preset = PLATFORMS.get(platform, {})
    width, height = preset.get('size', size)
    if proxy:
        factor = min(1/3, 540/min(width, height))
        width, height = (max(2, round(v*factor/2)*2) for v in (width, height))
    left, top, right, bottom = preset.get('safe_zone', (0, 0, 0, 0))
    return dict(size=[width, height], fps=fps, platform=platform, proxy=proxy,
                bitrate=None if proxy else preset.get('bitrate'), safe_zone={
                    'x': math.ceil(width*left), 'y': math.ceil(height*top),
                    'right': math.floor(width*(1-right)), 'bottom': math.floor(height*(1-bottom)),
                    'text_inset_px': math.ceil(width*.02)},
                color='legacy encoder conversion (untagged)' if fps==100 else 'BT.709 limited', background='000000')


def run(args):
    result = subprocess.run([executable('ffmpeg'), '-nostdin', '-hide_banner', *args], capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[-2500:])
    return result.stderr.decode(errors='replace')


def probe(path):
    return json.loads(subprocess.check_output([executable('ffprobe'), '-v', 'error',
        '-show_streams', '-show_format', '-of', 'json', str(path)],stderr=subprocess.PIPE))


def encode_frames(images, target, config, background='000000'):
    """Consume exactly one frame at a time. Unpublished file removed on every failure."""
    target = Path(target)
    if target.exists() or target.with_suffix(target.suffix+'.json').exists():
        raise FileExistsError('Use a new output file')
    if not re.fullmatch('[0-9a-fA-F]{6}', background):
        raise ValueError('Background must be six hex digits')
    width, height = config['size']; fps = rate(config['fps'])
    suffix = target.suffix.lower()
    if suffix not in ('.mp4', '.mov', '.webm'):
        raise ValueError('Choose .mp4, .mov or .webm')
    opaque = suffix == '.mp4' or bool(config['platform'])
    if (opaque or suffix == '.webm') and (width % 2 or height % 2):
        raise ValueError('4:2:0 video requires even dimensions')
    bg = tuple(int(background[k:k+2], 16) for k in (0, 2, 4)) + (255,)
    opts = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23' if config.get('proxy') else '18']
    if config.get('legacy_100fps'): opts=['-c:v','libx264','-crf','18']
    if suffix == '.webm':
        opts = ['-c:v', 'libvpx-vp9', '-lossless', '1', '-auto-alt-ref', '0']
    elif suffix == '.mov' and not opaque:
        opts = ['-c:v', 'prores_ks', '-profile:v', '4', '-alpha_bits', '16']
    if opaque and suffix != '.webm' and config['bitrate']:
        b = config['bitrate']
        opts = ['-c:v', 'libx264', '-preset', 'veryfast', '-b:v', b, '-minrate', b,
                '-maxrate', b, '-bufsize', b, '-x264-params', 'nal-hrd=cbr:force-cfr=1:filler=1']
    pix = 'yuv420p' if opaque else ('yuva420p' if suffix == '.webm' else 'yuva444p10le')
    if not config.get('legacy_100fps'): opts += ['-threads', '2']
    opts += ['-pix_fmt', pix]
    conversion=[]
    if not config.get('legacy_100fps'):
        opts += ['-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv']
        conversion=['-vf','scale=in_range=full:out_range=limited:out_color_matrix=bt709,setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709']
    if suffix != '.webm': opts += ['-movflags', '+faststart']
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.stem + '.partial' + suffix)
    if partial.exists(): raise FileExistsError('Partial output already exists; use a new output file')
    count = 0
    try:
        with tempfile.TemporaryFile(dir=target.parent) as errors:
            proc = subprocess.Popen([executable('ffmpeg'), '-v', 'error', '-nostdin',
                *([] if config.get('legacy_100fps') else ['-filter_threads', '1']),
                '-f', 'rawvideo', '-pixel_format', 'rgba',
                '-video_size', f'{width}x{height}', '-framerate', str(fps), '-i', 'pipe:0',
                '-an', *conversion,
                *opts, '-flush_packets', '1', str(partial)], stdin=subprocess.PIPE, stderr=errors)
            try:
                for image in images:
                    if image.size != (width, height):
                        raise ValueError('Streaming frame dimensions changed')
                    if image.mode != 'RGBA': image=image.convert('RGBA')
                    if opaque:
                        matte = Image.new('RGBA', image.size, bg)
                        matte.alpha_composite(image)
                        image = matte
                    proc.stdin.write(image.tobytes())
                    count += 1
                proc.stdin.close()
                if proc.wait():
                    errors.seek(0)
                    raise RuntimeError(errors.read().decode(errors='replace')[-2500:])
            finally:
                if proc.poll() is None:
                    proc.kill(); proc.wait()
                try:
                    if not proc.stdin.closed: proc.stdin.close()
                except BrokenPipeError:
                    pass  # Preserve the render/encoder exception during cleanup.
        if not count: raise ValueError('No video frames')
        stream=next(s for s in probe(partial)['streams'] if s['codec_type']=='video')
        if stream['r_frame_rate']!=f'{fps}/1' or stream['avg_frame_rate']!=f'{fps}/1':
            raise RuntimeError('Encoded video is not the requested constant frame rate')
        if stream.get('nb_frames') and int(stream['nb_frames'])!=count:
            raise RuntimeError('Encoded frame count does not match the supplied timeline')
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    report = dict(config, encoded_frames=count, transparent=not opaque, background=background if opaque else None,
                  container_duration_ms=count*1000/fps, audio=False, streaming=True,
                  measured_stream={k:stream.get(k) for k in ('r_frame_rate','avg_frame_rate','nb_frames','pix_fmt','bit_rate','color_space','color_transfer','color_primaries','color_range')})
    target.with_suffix(suffix+'.json').write_text(json.dumps(report, indent=2))
    return report


def duck_envelope(args, speech_filter, root, seconds):
    """Detect activity above the noise floor and write a bounded PCM gain track.

    This is an energy-based presence detector, not linguistic classification.
    Reject steady backgrounds and isolated clicks before bridging syllable gaps.
    """
    pcm = root/'speech.f32'
    run([*args, '-filter_complex', speech_filter+'[detect]', '-map', '[detect]',
         '-ac', '1', '-ar', '48000', '-f', 'f32le', str(pcm)])
    levels = []
    with pcm.open('rb') as stream:
        while raw := stream.read(480*4):
            x = np.frombuffer(raw, dtype='<f4')
            levels.append(float(np.sqrt(np.mean(x*x))))
    levels = np.asarray(levels)
    # Ignore apad silence when estimating a short source's actual noise floor.
    audible = levels[levels > 1e-7]
    noise_floor = float(np.percentile(audible, 20)) if len(audible) else 0
    # Genuine silence within the source is also useful evidence of its floor.
    nonzero = np.flatnonzero(levels > 1e-7)
    if len(nonzero):
        noise_floor = float(np.percentile(levels[:nonzero[-1]+1], 20))
    threshold = max(float(np.max(levels, initial=0))*.05, noise_floor*2.5, 1e-7)
    active = np.flatnonzero(levels > threshold)
    bursts = []
    for k in active:
        if bursts and k == bursts[-1][1]: bursts[-1][1] = int(k)+1
        else: bursts.append([int(k), int(k)+1])
    intervals = []
    for first, last in bursts:
        if last-first < 4: continue  # At least 40 ms; CLIP-A clicks last 10 ms.
        start, end = first*.01, min(seconds, last*.01)
        if intervals and start-intervals[-1][1] <= .15+1e-8:
            intervals[-1][1] = end
        else:
            intervals.append([start, end])
    # One second at a time, independent of clip length/number of intervals.
    # Stereo gain preserves the music's channel layout through amultiply.
    envelope = root/'duck-gain.f32'
    cursor = 0
    with envelope.open('wb') as stream:
        for first in range(0, round(seconds*48000), 48000):
            t = np.arange(first, min(first+48000, round(seconds*48000)))/48000
            depth = np.zeros(len(t))
            while cursor < len(intervals) and intervals[cursor][1]+.5 < t[0]: cursor += 1
            for start, end in intervals[cursor:]:
                if start > t[-1]: break
                pulse = np.clip(np.minimum((t-start)/.05, (end+.5-t)/.5), 0, 1)
                np.maximum(depth, pulse, out=depth)
            gain = np.power(10, -.5*depth).astype('<f4')
            stream.write(np.repeat(gain[:, None], 2, axis=1).tobytes())
    return envelope, dict(
        depth_db=10, attack_ms=50, release_ms=500, presence_intervals=intervals,
        threshold_rms=threshold, noise_floor_rms=noise_floor, envelope='stereo PCM float32, 48000 Hz, numpy blocks',
        detection='10 ms RMS; max(peak -26 dB, noise floor +8 dB); 40 ms minimum; 150 ms gap bridge')


def audio_delivery(movie, duration_ms, music=None, source=None, duck=False, normalize=True, sfx=None):
    """Mix a timeline-aligned source track and music; normalize then gate encoded audio."""
    movie = Path(movie); seconds = duration_ms/1000
    if not music and not source and not sfx: return {'audio': False}
    with tempfile.TemporaryDirectory(dir=movie.parent) as folder:
        root = Path(folder); mixed = root/'mixed.wav'
        args = ['-v', 'error']; graph = []; labels = []; duck_report = None
        for index, (kind, spec) in enumerate(([("speech", source)] if source else []) + ([("music", music)] if music else [])):
            args += ['-i', str(spec['file'])]
            filt = (f'[{index}:a:0]atrim=start={spec.get("in_ms",0)/1000},asetpts=PTS-STARTPTS,'
                    f'volume={spec.get("gain_db",0)}dB,aresample=48000,'
                    f'aformat=channel_layouts=stereo,apad,atrim=duration={seconds}')
            for edge in ('in', 'out'):
                fade = spec.get('fade_'+edge+'_ms', 0)/1000
                if fade: filt += f',afade=t={edge}:st={0 if edge=="in" else max(0,seconds-fade)}:d={fade}'
            graph.append(filt+f'[{kind}]'); labels.append(kind)
        if len(labels) == 2:
            if duck:
                automation, duck_report = duck_envelope(args, graph[0].removesuffix('[speech]'), root, seconds)
                args += ['-f', 'f32le', '-ar', '48000', '-ac', '2', '-i', str(automation)]
                graph += ['[music][2:a:0]amultiply[bed]',
                          '[speech][bed]amix=inputs=2:normalize=0[out]']
            else: graph += ['[speech][music]amix=inputs=2:normalize=0[out]']
        elif labels: graph += [f'[{labels[0]}]anull[out]']
        if sfx:
            # Duck detection only sees speech; sound effects are mixed afterwards.
            if labels:
                graph[-1]=graph[-1].removesuffix('[out]')+'[bedout]'
            else:
                graph=[]
            index=sum(1 for value in args if value=='-i')
            args += ['-i',str(sfx['file'])]
            graph += [f'[{index}:a:0]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={seconds}[sfx]']
            graph += ['[bedout][sfx]amix=inputs=2:normalize=0[out]' if labels else '[sfx]anull[out]']
        run([*args, '-filter_complex', ';'.join(graph), '-map', '[out]', '-c:a', 'pcm_f32le', str(mixed)])
        measured = None; filt = 'anull'; second = None
        from threshold_registry import value, default_value
        target=value('audio.loudness.target');tolerance=value('audio.loudness.tolerance')
        limiter=default_value('audio.limiter.ceiling');limit=10**(limiter/20)
        if normalize:
            log = run(['-i', str(mixed), '-af', f'loudnorm=I={target}:TP={limiter}:LRA=11:print_format=json', '-f', 'null', '-'])
            measured = json.loads(log[log.rfind('{'):log.rfind('}')+1])
            gain = target-float(measured['input_i'])
            if not math.isfinite(gain): gain = 0  # Intentionally silent track.
            # Oversample so the lookahead limiter catches intersample peaks.
            # Disable its default makeup gain and compensate its 5 ms latency.
            filt = (f'volume={gain}dB,aresample=192000,'
                    f'alimiter=limit={limit:.10f}:attack=5:release=50:level=false:latency=true,aresample=48000')
            second = dict(normalization_type='linear', gain_db=gain,
                          limiter=dict(ceiling_dbtp=limiter, sample_rate=192000, attack_ms=5, release_ms=50,
                                       auto_level=False, latency_compensated=True))
        candidate = root/movie.name
        log = run(['-i', str(movie), '-i', str(mixed), '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy',
             '-af', filt, '-c:a', 'libopus' if movie.suffix=='.webm' else 'aac', '-b:a', '256k', '-ar', '48000', '-ac', '2',
             '-t', str(seconds), *([] if movie.suffix=='.webm' else ['-movflags','+faststart']), str(candidate)])
        from qa_media import analyse_audio
        checks = analyse_audio(candidate, {'audio': True}, [0, seconds])
        # Sparse impacts lose integrated level at the limiter. Only the opt-in
        # SFX path retries measured gain; legacy music/source-only bytes are unchanged.
        retries=[]
        if sfx and normalize:
            for _ in range(4):
                loud=next((c.get('lufs') for c in checks if c['name']=='loudness'),None)
                if loud is None or abs(loud-target)<=tolerance: break
                correction=target-loud;gain+=correction;retries.append(dict(measured_lufs=loud,correction_db=correction))
                filt=(f'volume={gain}dB,aresample=192000,'
                      f'alimiter=limit={limit:.10f}:attack=5:release=50:level=false:latency=true,aresample=48000')
                run(['-y','-i',str(movie),'-i',str(mixed),'-map','0:v:0','-map','1:a:0','-c:v','copy',
                     '-af',filt,'-c:a','libopus' if movie.suffix=='.webm' else 'aac','-b:a','256k','-ar','48000','-ac','2',
                     '-t',str(seconds),*([] if movie.suffix=='.webm' else ['-movflags','+faststart']),str(candidate)])
                checks=analyse_audio(candidate,{'audio':True},[0,seconds])
            second.update(gain_db=gain,sfx_gain_retries=retries)
        if any(c['level']=='FAIL' for c in checks):
            raise RuntimeError('Audio delivery QA failed: '+json.dumps(checks))
        candidate.replace(movie)
    return dict(audio=True, source=source, music=music, duck=bool(duck and source and music),
                ducking=duck_report,
                first_pass=measured, second_pass=second, linear_requested=normalize,
                normalization_note='Measured stereo mix; constant loudness gain followed by oversampled lookahead peak limiting; encoded audio gated', checks=checks)
