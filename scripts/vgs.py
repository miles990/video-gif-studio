#!/usr/bin/env python3
"""Local media to GIF: automatic flat-background detection, tail trim and QA."""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import tempfile
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageSequence

import gif_pipeline as gp
import qa_media

TOLERANCE = 0.2
SOFTNESS = 0.18


def human_error(exc: BaseException, src: Path | None) -> str:
    text = str(exc).strip()
    if text:
        return text
    where = f'來源 {src}' if src else '這次指令'
    return f'{where} 發生未預期錯誤，沒有完成交付。請檢查輸入後用一個新的 --out 目錄重試。'


def estimate_key(frames: list[Image.Image]) -> tuple[np.ndarray, float, bool]:
    samples = []
    picks = np.linspace(0, len(frames) - 1, min(12, len(frames))).astype(int)
    for i in picks:
        p = np.asarray(frames[i].convert('RGB'))
        border = np.concatenate((
            p[:4].reshape(-1, 3),
            p[-4:].reshape(-1, 3),
            p[:, :4].reshape(-1, 3),
            p[:, -4:].reshape(-1, 3),
        ))[::8]
        samples.append(border)
    samples = np.concatenate(samples).astype(float)
    key = np.median(samples, axis=0)
    confidence = float(np.mean(np.linalg.norm(samples - key, axis=1) < 35))
    return key, confidence, confidence > 0.95


def apply_key_connected(frames, key_rgb, tolerance, softness, keep=False):
    """Key only background that is connected to the frame border."""
    color = np.asarray(key_rgb, dtype=float) / 255
    color = color - color.mean()
    keyed = []
    max_share, max_frame = 0., 0
    for frame_no, im in enumerate(frames):
        a = np.array(im)
        rgb = a[:, :, :3].astype(float) / 255
        chroma = rgb - rgb.mean(axis=2, keepdims=True)
        dist = np.linalg.norm(chroma - color, axis=2)
        soft = np.clip((dist - tolerance) / softness, 0, 1)
        candidate = (soft < 1).astype(np.uint8)
        _num, labels = cv2.connectedComponents(candidate, connectivity=8)
        border = set(labels[0]) | set(labels[-1]) | set(labels[:, 0]) | set(labels[:, -1])
        border.discard(0)
        bg = np.isin(labels, list(border)) if border else np.zeros(labels.shape, dtype=bool)
        interior = (candidate == 1) & ~bg
        chroma_alpha = np.round(soft * 255).astype('uint8')
        share = float(interior.mean())
        if share > max_share:
            max_share, max_frame = share, frame_no
        mask = bg if keep else candidate.astype(bool)
        new_alpha = a[:, :, 3].copy()
        new_alpha[mask] = np.minimum(new_alpha[mask], chroma_alpha[mask])
        a[:, :, 3] = new_alpha
        keyed.append(Image.fromarray(a))
    return keyed, {"threshold": .001, "max_share": max_share, "frame": max_frame, "action": "kept" if keep else "removed"}


def motion_scores(frames: list[Image.Image]) -> np.ndarray:
    small = []
    for im in frames:
        w = 192
        h = max(1, round(im.height * w / im.width))
        small.append(np.asarray(im.resize((w, h), Image.Resampling.BOX), dtype=np.float32))
    vis = [x[:, :, :3] * (x[:, :, 3:4] / 255.0) for x in small]
    scores = []
    for i in range(1, len(vis)):
        delta = np.mean(np.abs(vis[i] - vis[i - 1]), axis=2)
        scores.append(float((delta > 8).mean()))
    return np.asarray(scores, dtype=float)


def trim_tail(frames, fps):
    scores = motion_scores(frames) if len(frames) > 1 else np.asarray([])
    last = len(frames) - 1
    if len(scores):
        window = scores[: max(1, int(len(scores) * 0.6))]
        thr = max(0.012, 0.25 * float(np.median(window)))
        while last > 0 and scores[last - 1] < thr:
            last -= 1
    original = len(frames) / fps
    hold = (len(frames) - 1 - last) / fps
    if hold > 0.7:
        guard = max(1, int(round(0.4 * fps)))
        end = min(len(frames), last + 1 + guard)
        method = 'trim'
    else:
        end = len(frames)
        method = 'none'
    treatment = {
        'method': method,
        'original_duration_seconds': original,
        'new_duration_seconds': end / fps,
        'source_interval_removed_seconds': [end / fps, original] if end < len(frames) else None,
        'last_detected_motion_source_seconds': last / fps,
        'guard_seconds': (end - last - 1) / fps if method == 'trim' else 0,
        'motion_threshold': float(thr) if len(scores) else None,
    }
    return frames[:end], treatment, last


def loop_select(frames, fps, last, standard):
    n = len(frames)
    lo = last + 1 if last < n-1 else max(2, int(n*.7))
    hi = min(n, last+1+int(.5*fps)) if last < n-1 else n
    lo = max(2, min(lo, hi))
    vis = []
    for im in frames:
        w = min(192, im.width)
        a = np.asarray(im.resize((w, max(1, round(im.height*w/im.width))), Image.Resampling.BOX), dtype=np.float32)
        vis.append(a[:,:,:3] * (a[:,:,3:4]/255))
    d = np.array([0.] + [float(np.abs(vis[i]-vis[i-1]).mean()) for i in range(1,n)])
    choices = []
    for end in range(lo, hi+1):
        active = d[1:end][d[1:end]>=.01]
        med = float(np.median(active)) if len(active) else 0
        moving = np.flatnonzero(d[:end]>=.01)
        ratio = (float(d[moving[-1]])*fps+.05)/(float(d[moving[0]])*fps+.05) if len(moving) else 1
        stationary = not len(moving) or max(d[moving[0]],d[moving[-1]])<.25
        seam = float(np.abs(vis[end-1]-vis[0]).mean())
        pos = seam < .45 or seam <= 1.8*med
        speed = stationary or .55 <= ratio <= 1.8
        if pos and speed:
            choices.append((seam, abs(ratio-1), end))
    if choices:
        end = min(choices)[2]
        return end, {'mode':'auto', 'method':'trim', 'searched_frame_range':[lo,hi], 'end_frame_exclusive':end}
    return standard, {'mode':'auto','method':'not_found','searched_frame_range':[lo,hi], 'reason':'position or speed'}


def key_metrics(path):
    ring, share, worst = 0., 0., 0
    with Image.open(path) as im:
        for i, frame in enumerate(ImageSequence.Iterator(im)):
            a = np.asarray(frame.convert('RGBA')); opaque = a[:,:,3] > 0
            r = np.concatenate((opaque[:4].ravel(), opaque[-4:].ravel(), opaque[:,:4].ravel(), opaque[:,-4:].ravel())).mean()
            c = a[:,:,:3]; key = (((c[:,:,0]>180)&(c[:,:,2]>180)&(c[:,:,1]<90)) | ((c[:,:,1]>180)&(c[:,:,0]<90)&(c[:,:,2]<90))) & opaque
            v = float(key.sum()/max(1,opaque.sum()))
            ring = max(ring,float(r))
            if v > share: share, worst = v, i
    return ring, share, worst



def despill_pixel_edges(frames, key_rgb):
    """Suppress chroma spill on 1px opaque silhouette pixels touching alpha=0."""
    k = np.asarray(key_rgb, dtype=float)
    k_chroma = k - k.mean()
    k_norm = float(np.linalg.norm(k_chroma))
    if k_norm < 1e-6:
        return frames
    k_dir = k_chroma / k_norm
    out = []
    for f in frames:
        arr = np.array(f)
        alpha = arr[:, :, 3] >= 128
        # 4-connected neighbors of transparent pixels
        bg = ~alpha
        border_band = np.zeros_like(alpha)
        border_band[1:] |= alpha[1:] & bg[:-1]
        border_band[:-1] |= alpha[:-1] & bg[1:]
        border_band[:, 1:] |= alpha[:, 1:] & bg[:, :-1]
        border_band[:, :-1] |= alpha[:, :-1] & bg[:, 1:]
        if border_band.any():
            rgb = arr[:, :, :3].astype(float)
            c = rgb - rgb.mean(axis=2, keepdims=True)
            proj = np.tensordot(c, k_dir, axes=([2], [0]))
            # only pixels whose chroma leans meaningfully toward the key color
            spill = border_band & (proj > 25.0)
            if spill.any():
                # remove positive projection onto key chroma, keeping brightness neutral
                for ch in range(3):
                    rgb[:, :, ch] = np.where(spill, np.clip(rgb[:, :, ch] - proj * k_dir[ch], 0, 255), rgb[:, :, ch])
                arr[:, :, :3] = np.round(rgb).astype(np.uint8)
        out.append(Image.fromarray(arr))
    return out


def pixel_quantize(frames, colors, scale):
    samples = [np.asarray(f)[:,:,:3][np.asarray(f)[:,:,3]>=128] for f in frames]
    visible = np.concatenate(samples)
    if not len(visible): raise ValueError('鍵色與主體太接近；不寫入檔案。請省略 --key 重試。')
    palette = Image.fromarray(visible.reshape(-1,1,3)).quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    result = []
    for f in frames:
        a = np.asarray(f); q = f.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE).convert('RGB').convert('RGBA')
        q.putalpha(Image.fromarray(np.where(a[:,:,3]>=128,255,0).astype('uint8')))
        result.append(q.resize((q.width*scale,q.height*scale), Image.Resampling.NEAREST))
    return result


def encode_pixel(frames, durations, target):
    images, durations = gp.browser_gif_timing(frames, durations)
    colors = sorted({tuple(c) for f in images for c in np.asarray(f)[np.asarray(f)[:,:,3] >= 128, :3].tolist()})
    if len(colors) > 255: raise ValueError('像素色盤超過上限；無法輸出。請減少 --colors。')
    palette = [v for color in colors for v in color] + [0] * (768 - len(colors)*3)
    lookup = {c:i for i,c in enumerate(colors)}
    encoded = []
    for f in images:
        arr = np.asarray(f); rgb = arr[:,:,:3]; idx = np.full(rgb.shape[:2],255,dtype=np.uint8)
        for color, i in lookup.items():
            idx[(rgb == color).all(axis=2) & (arr[:,:,3]>=128)] = i
        im = Image.fromarray(idx); im.putpalette(palette); encoded.append(im)
    encoded[0].save(target, format='GIF', save_all=True, append_images=encoded[1:], duration=durations,
                    loop=0, transparency=255, background=255, disposal=2, optimize=False)


def checkerboard(size, cell=8, light=(235, 235, 235), dark=(50, 50, 50)):
    w, h = size
    yy, xx = np.indices((h, w))
    mask = ((xx // cell) + (yy // cell)) % 2 == 0
    board = np.empty((h, w, 3), dtype=np.uint8)
    board[mask] = light
    board[~mask] = dark
    return board


def compose_preview(frames, path: Path) -> None:
    picks = [0, len(frames) // 2, len(frames) - 1]
    tiles = [frames[i].convert('RGBA') for i in picks]
    w, h = tiles[0].size
    light = checkerboard((w, h), light=(235, 235, 235), dark=(200, 200, 200))
    dark = checkerboard((w, h), light=(80, 80, 80), dark=(30, 30, 30))
    gap, pad, label_h = 8, 16, 28
    canvas_w = pad * 2 + 3 * w + 2 * gap
    canvas_h = pad * 3 + 2 * h + label_h * 2
    canvas = Image.new('RGB', (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 6), 'light checkerboard', fill=(30, 30, 30))
    draw.text((pad, pad + label_h + h + 6), 'dark checkerboard', fill=(30, 30, 30))
    for row, board in enumerate((light, dark)):
        y = pad + label_h + row * (h + pad + label_h)
        for col, tile in enumerate(tiles):
            x = pad + col * (w + gap)
            base = Image.fromarray(board.copy())
            base.paste(tile, (0, 0), tile)
            canvas.paste(base, (x, y))
    canvas.save(path)


def border_opaque(path: Path) -> float:
    im = Image.open(path)
    rings = []
    for frame in ImageSequence.Iterator(im):
        a = np.asarray(frame.convert('RGBA'))
        alpha = a[:, :, 3] > 0
        rings.append(np.concatenate((
            alpha[:4].ravel(), alpha[-4:].ravel(),
            alpha[:, :4].ravel(), alpha[:, -4:].ravel(),
        )).mean())
    return max(rings) if rings else 1.0


def summarize_loop(report: dict) -> str:
    for check in report.get('checks', []):
        if check.get('name') == 'loop':
            meas = check.get('measurement') or {}
            if check.get('level') == 'PASS':
                return 'loop 量測通過（未經視覺核准）'
            reason = []
            if meas.get('position_pass') is False:
                reason.append('position')
            if meas.get('speed_pass') is False:
                reason.append('speed')
            detail = '/'.join(reason) or check.get('message', 'mismatch')
            return f'loop FAIL：{detail}'
    return 'loop 未檢查'


def make(a) -> int:
    src, out = a.input, a.out
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError(
            f'輸出目錄 {out} 非空；不會寫入或刪除檔案。請改用一個新的空目錄，例如 --out /tmp/vgs-new-output。'
        )
    if not src.exists():
        raise ValueError(
            f'來源 {src} 不存在；無法製作 GIF，不會寫入輸出。請改成正確路徑，例如 python scripts/vgs.py make <video> --out /tmp/vgs-new-output。'
        )
    if src.is_dir() and not a.fps:
        raise ValueError(
            f'PNG 目錄 {src} 缺少 fps；無法確定播放速度，不會寫入輸出。請加上 --fps 24（或來源的真實幀率）。'
        )
    if a.width < 1:
        raise ValueError(f'寬度 {a.width} 無效；無法輸出。請使用 --width 320。')

    if a.key and not re.fullmatch(r'#?[0-9a-fA-F]{6}', a.key):
        raise ValueError('鍵色格式無效；無法輸出。請使用 --key FF00FF（六位十六進位 RGB）。')
    if a.pixel_width is not None and a.pixel_width < 1 or a.pixel_scale is not None and a.pixel_scale < 1 or not 2 <= a.colors <= 255 or a.loop_count is not None and a.loop_count < 1:
        raise ValueError('像素或循環參數無效；不寫入檔案。請使用正整數尺寸、倍率和循環次數，以及 2..255 色。')
    pixel = a.pixel or a.pixel_width is not None
    frames, fps = gp.load_frames(src, a.fps if src.is_dir() else None, None if pixel else a.width, None, TOLERANCE, SOFTNESS)
    if pixel:
        pw = a.pixel_width or 96
        ph = max(1, round(frames[0].height * pw / frames[0].width))
        frames = [f.resize((pw,ph), Image.Resampling.NEAREST) for f in frames]
    if a.fps and not src.is_dir() and abs(a.fps - fps) > 0.001:
        raise ValueError(
            f'來源是 {fps:g} fps，你指定 {a.fps:g} fps；這會改變播放速度。請用 --fps {fps:g} 或省略 --fps。'
        )

    key, confidence, flat = estimate_key(frames)
    sat = float((key.max()-key.min())/max(float(key.max()),1.0))
    detected_key = key.copy()
    if a.key: key = np.array([int(a.key.lstrip('#')[i:i+2],16) for i in (0,2,4)])
    keyed = bool(not a.no_key and (a.key or (flat and sat >= .35)))
    islands = None
    if keyed:
        frames, islands = apply_key_connected(frames, key, TOLERANCE, SOFTNESS, a.keep_interior_key)
        if pixel:
            frames = despill_pixel_edges(frames, key)
        if a.key and all(np.mean(np.asarray(f)[:,:,3]>=128)<.005 for f in frames):
            raise ValueError(f'--key {a.key} 與主體太接近，會挖空主體；不寫入檔案。請省略 --key 重試。')
    trimmed, treatment, last = trim_tail(frames, fps)
    end = len(trimmed)
    loop_treatment = {'mode': a.loop, 'method': 'none'}
    if a.loop == 'auto': end, loop_treatment = loop_select(frames, fps, last, end)
    frames = frames[:end]
    if a.loop == 'crossfade' and len(frames)>2:
        n = min(6, max(2,len(frames)//8))
        for i in range(n-2):
            frames[-n+i] = Image.blend(frames[-n+i], frames[1], (i+1)/(n-1))
        frames[-2] = frames[1].copy()
        frames[-1] = frames[0].copy()
        loop_treatment = {'mode':'crossfade','method':'crossfade','blend_frames':n,'blend_seconds':n/fps,'source_interval_affected':[(end-n)/fps,end/fps]}
    treatment['new_duration_seconds'] = end/fps
    treatment['source_interval_removed_seconds'] = [end/fps,treatment['original_duration_seconds']] if end/fps < treatment['original_duration_seconds'] else None
    treatment['guard_seconds'] = max(0,end-last-1)/fps
    indices, durations = gp.timing(len(frames), fps, [])
    frames = [frames[i] for i in indices]
    pixel_info = None
    if pixel:
        scale = a.pixel_scale or max(1,math.ceil(288/pw))
        frames = pixel_quantize(frames,a.colors,scale)
        pixel_info = {'grid_size':[pw,ph], 'scale':scale, 'output_size':[pw*scale,ph*scale], 'colors':a.colors, 'resample':'nearest','dither':'none'}

    out.mkdir(parents=True, exist_ok=True)
    gif = out / 'animation.gif'
    (encode_pixel if pixel else gp.encode)(frames, durations, gif)
    qc = gp.verify(gif, frames, durations)
    gp.contact(frames, out / 'contact.png')
    compose_preview(frames, out / 'preview.png')
    report = qa_media.qa(gif, out / 'qa')
    for name in ('report.json', 'report.md'):
        (out / name).write_bytes((out / 'qa' / name).read_bytes())

    ring, key_share, key_frame = key_metrics(gif)
    bg_fail = bool((a.no_key and flat) or (keyed and ring > 0.01))
    manifest = {
        'source': str(src),
        'loop_treatment': loop_treatment,
        'interior_key_islands': islands,
        'key_saturation': sat, 'key_saturation_threshold': .35, 'key_saturation_formula': '(max-min)/max',
        'pixel_processing': pixel_info, 'key_share_max': key_share, 'key_share_frame': key_frame,
        'source_fps': fps,
        'source_indices': indices,
        'key_rgb': key.round().astype(int).tolist() if keyed else None,
        'key_hex': '#' + ''.join(f'{int(round(x)):02X}' for x in key) if keyed else None,
        'key_tolerance': TOLERANCE,
        'key_softness': SOFTNESS,
        'key_confidence': confidence,
        'background_flat': flat,
        'background_removed': keyed,
        'foreground_key_color_warning': bool(islands and islands['max_share'] > .001),
        'tail_treatment': treatment,
        'qc': qc,
        'border_opaque_max': ring,
        'qa_level': report['level'],
    }
    if a.sprite:
        import sprite_export
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for i, frame in enumerate(frames):
                arr = np.array(frame); arr[:,:,3] = np.where(arr[:,:,3]>=128,255,0)
                Image.fromarray(arr).save(tmp / f'{i:05d}.png')
            (tmp / 'manifest.json').write_text(json.dumps({'durations_ms':durations,'source_indices':indices}))
            sprite_export.export(tmp, tmp / 'manifest.json', out / 'sprites')
    if a.mp4:
        seconds = sum(durations)/1000
        count = a.loop_count or max(1,round(10.5/seconds))
        if not a.loop_count and seconds <= 15:
            possible = [k for k in range(1, max(2,math.ceil(15/seconds)+1)) if 8 <= k*seconds <= 15]
            if possible: count = min(possible,key=lambda k:abs(k*seconds-10.5))
        w,h = frames[0].size; pad = [w%2,h%2]
        manifest['mp4_padding'] = {'right':pad[0], 'bottom':pad[1], 'color':'#141820'}
        manifest['loop_count'] = count
        with tempfile.TemporaryDirectory() as tmp:
            for i, f in enumerate(frames):
                bg = Image.new('RGB',(w+pad[0],h+pad[1]),'#141820'); bg.paste(f,(0,0),f.getchannel('A')); bg.save(Path(tmp)/f'{i:05d}.png')
            subprocess.run(['ffmpeg','-v','error','-y','-stream_loop',str(count-1),'-framerate',str(fps),'-i',str(Path(tmp)/'%05d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'animation.mp4')],check=True)
        print(f'MP4 重複 {count} 次；補邊右 {pad[0]}、下 {pad[1]} 像素。')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')

    if bg_fail:
        print('背景未去除，不是透明 GIF；平坦背景仍在。交付檢查 FAIL。')
    elif keyed:
        print(f'已去背，鍵色 {manifest["key_hex"]}（容差 {TOLERANCE}，柔化 {SOFTNESS}，信心 {confidence:.3f}）。')
        if islands['max_share'] > .001:
            print(f"警告：內部鍵色區最大比例 {islands['max_share']:.4f}，第 {islands['frame']} 幀；如需保留請加 --keep-interior-key。")
        if a.keep_interior_key: print(f'已保留內部鍵色區；殘留鍵色比例 {key_share:.4f}。')
    elif flat and sat < .35 and not a.no_key:
        hexkey = ''.join(f'{int(round(x)):02X}' for x in detected_key)
        print(f'未去背，原因：邊框雖平坦但為低飽和純底（飽和度 {sat:.2f} < 0.35 門檻）。這是非透明交付。若確定要去背，請加 --key {hexkey}')
    else:
        print(f'未去背，原因：背景非純色或指定保留背景（信心 {confidence:.3f}）。這是非透明交付。')
    print(f'border_opaque_max {ring:.4f}；key_share_max {key_share:.4f}（第 {key_frame} 幀）。')
    if gif.stat().st_size > 15_000_000:
        print(f'大型 GIF {gif.stat().st_size/1e6:.2f} MB；可用 --width 160 或 --pixel 縮小，例如：python scripts/vgs.py make {src} --width 160 --out /tmp/vgs-smaller')

    print(
        f'尺寸 {frames[0].width}×{frames[0].height}；{len(frames)} 幀，'
        f'{sum(durations)/1000:.2f} 秒，{gif.stat().st_size/1e6:.2f} MB。'
        + ('（預設寬度 320）' if a.width == 320 else f'（--width {a.width}）')
    )
    removed = treatment['source_interval_removed_seconds']
    print(
        f'尾端 {treatment["method"]}：原長 {treatment["original_duration_seconds"]:.2f}s，'
        f'新長 {treatment["new_duration_seconds"]:.2f}s'
        + (f'；來源 {removed[0]:.2f} 到 {removed[1]:.2f}s 已裁切，保留約 {treatment["guard_seconds"]:.2f}s guard' if removed else '')
        + f'；最後移動幀 {treatment["last_detected_motion_source_seconds"]:.2f}s。'
    )
    reasons = [f'{c["name"]} {c["level"]}: {c["message"]}' for c in report['checks'] if c['level'] != 'PASS']
    print(f'QA {report["level"]}' + ('；' + '；'.join(reasons) if reasons else '。'))
    loop_summary = summarize_loop(report)
    if a.loop == 'crossfade':
        if '通過' in loop_summary: loop_summary = f'loop 量測通過（經 crossfade 處理，混合 {loop_treatment["blend_frames"]} 幀，未經視覺核准）'
        else: loop_summary += f'（經 crossfade 處理，混合 {loop_treatment["blend_frames"]} 幀，未經視覺核准）'
    if loop_treatment.get('method') == 'not_found': loop_summary = 'loop FAIL：' + loop_treatment['reason']
    print(loop_summary + f'；輸出 {gif}')
    print('視覺核准：未評估，需人看。')
    return 1 if bg_fail else 0


def qa_gif(path: Path) -> int:
    if not path.exists():
        print(f'來源 {path} 不存在；無法檢查。請改成正確的 GIF 路徑。', file=sys.stderr)
        return 1
    ring, share, frame = key_metrics(path)
    failed = ring > .01 or share > .10
    status = 'FAIL' if failed else ('WARN' if share > .02 else 'PASS')
    reason = '背景未去除，不是透明 GIF' if ring > .01 else ('中央或封閉區殘留大面積鍵色' if share > .10 else '')
    print(f'背景檢查 {status}：{reason}；border_opaque_max {ring:.4f}；key_share_max {share:.4f}（第 {frame} 幀）')
    return int(failed)


class HumanParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(f'參數無效：{message}；不寫入檔案。請查看 --help 後修正參數。')


def main(argv=None) -> int:
    parser = HumanParser(
        description='Convert local video or PNG frames to a GIF. '
        'Auto-key only when the border is a stable flat color; trim a long still tail; run QA.'
    )
    sub = parser.add_subparsers(dest='command', required=True)
    make_p = sub.add_parser('make', help='One-command local delivery: auto-key, trim, encode, QA')
    make_p.add_argument('input', type=Path, help='Video file or PNG directory')
    make_p.add_argument('--out', type=Path, required=True, help='New or empty output directory')
    make_p.add_argument('--fps', type=float, help='Required for PNG directories; must match a video’s native FPS')
    make_p.add_argument('--width', type=int, default=320, help='Output width in pixels (default 320)')
    make_p.add_argument(
        '--no-key', '--keep-background',
        dest='no_key',
        action='store_true',
        help='Keep the background. A flat chroma background fails transparent delivery.',
    )
    make_p.add_argument('--loop', choices=['auto','crossfade','off'], default='auto', help='Loop treatment (default auto; crossfade is opt-in)')
    make_p.add_argument('--key', help='Explicit six-digit RGB key; auto-key requires saturation (max-min)/max >= 0.35')
    make_p.add_argument('--keep-interior-key', action='store_true', help='Preserve interior key-colored islands')
    make_p.add_argument('--pixel', action='store_true', help='Pixel preset: 96px grid, 32 colors, nearest scaling')
    make_p.add_argument('--pixel-width', type=int, help='Grid width (default 96; implies --pixel)')
    make_p.add_argument('--pixel-scale', type=int, help='Integer enlargement (default ceil(288 / grid width), minimum 1)')
    make_p.add_argument('--colors', type=int, default=32, help='Pixel palette colors 2..255 (default 32)')
    make_p.add_argument('--sprite', action='store_true', help='Export sprites at output size')
    make_p.add_argument('--mp4', action='store_true', help='Export opaque H.264 on #141820')
    make_p.add_argument('--loop-count', type=int, help='MP4 repetitions; default closest to 10.5s within 8..15s when possible')
    qa_p = sub.add_parser('qa', help='Check opaque 4px border and residual key-colored pixels', description='Check GIF border opacity and residual magenta or green key share; large remnants fail.')
    qa_p.add_argument('input', type=Path, help='GIF to check')
    try:
        args = parser.parse_args(argv)
        if args.command == 'qa':
            return qa_gif(args.input)
        return make(args)
    except ValueError as exc:
        src = getattr(locals().get('args'), 'input', None)
        print(human_error(exc, src), file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 — convert unexpected errors into a human message
        src = getattr(locals().get('args'), 'input', None)
        print(human_error(exc, src), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
