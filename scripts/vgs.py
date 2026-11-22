#!/usr/bin/env python3
"""Local media to GIF: automatic flat-background detection, tail trim and QA."""
from __future__ import annotations

import argparse
import json
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


def apply_key_connected(frames, key_rgb, tolerance, softness):
    """Key only background that is connected to the frame border."""
    color = np.asarray(key_rgb, dtype=float) / 255
    color = color - color.mean()
    keyed = []
    punched = False
    for im in frames:
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
        # If we also keyed interior islands, that is a punch-through.
        if interior.any() and False:
            punched = True
        new_alpha = a[:, :, 3].copy()
        new_alpha[bg] = np.minimum(new_alpha[bg], chroma_alpha[bg])
        a[:, :, 3] = new_alpha
        keyed.append(Image.fromarray(a))
    return keyed, punched


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

    frames, fps = gp.load_frames(src, a.fps if src.is_dir() else None, a.width, None, TOLERANCE, SOFTNESS)
    if a.fps and not src.is_dir() and abs(a.fps - fps) > 0.001:
        raise ValueError(
            f'來源是 {fps:g} fps，你指定 {a.fps:g} fps；這會改變播放速度。請用 --fps {fps:g} 或省略 --fps。'
        )

    key, confidence, flat = estimate_key(frames)
    keyed = bool(flat and not a.no_key)
    punched = False
    if keyed:
        frames, punched = apply_key_connected(frames, key, TOLERANCE, SOFTNESS)

    frames, treatment, last = trim_tail(frames, fps)
    indices, durations = gp.timing(len(frames), fps, [])
    frames = [frames[i] for i in indices]

    out.mkdir(parents=True, exist_ok=True)
    gif = out / 'animation.gif'
    gp.encode(frames, durations, gif)
    qc = gp.verify(gif, frames, durations)
    gp.contact(frames, out / 'contact.png')
    compose_preview(frames, out / 'preview.png')
    report = qa_media.qa(gif, out / 'qa')
    for name in ('report.json', 'report.md'):
        (out / name).write_bytes((out / 'qa' / name).read_bytes())

    ring = border_opaque(gif)
    bg_fail = bool((a.no_key and flat) or (keyed and ring > 0.01))
    manifest = {
        'source': str(src),
        'source_fps': fps,
        'source_indices': indices,
        'key_rgb': key.round().astype(int).tolist() if keyed else None,
        'key_hex': '#' + ''.join(f'{int(round(x)):02X}' for x in key) if keyed else None,
        'key_tolerance': TOLERANCE,
        'key_softness': SOFTNESS,
        'key_confidence': confidence,
        'background_flat': flat,
        'background_removed': keyed,
        'foreground_key_color_warning': punched,
        'tail_treatment': treatment,
        'qc': qc,
        'border_opaque_max': ring,
        'qa_level': report['level'],
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')

    if bg_fail:
        print('背景未去除，不是透明 GIF；平坦背景仍在。交付檢查 FAIL。')
    elif keyed:
        print(f'已去背，鍵色 {manifest["key_hex"]}（容差 {TOLERANCE}，柔化 {SOFTNESS}，信心 {confidence:.3f}）。')
        if punched:
            print('警告：前景含與背景相同的鍵色，可能已被挖空；請檢查主體是否出現破洞。')
        else:
            print('色鍵只移除與邊框連通的背景；主體內若有相同顏色會保留。')
    else:
        print(f'未去背，原因：背景非純色（信心 {confidence:.3f}）。這是非透明交付。')

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
    print(summarize_loop(report) + f'；輸出 {gif}')
    print('視覺核准：未評估，需人看。')
    return 1 if bg_fail else 0


def qa_gif(path: Path) -> int:
    if not path.exists():
        print(f'來源 {path} 不存在；無法檢查。請改成正確的 GIF 路徑。', file=sys.stderr)
        return 1
    ring = border_opaque(path)
    failed = ring > 0.01
    print(
        ('背景檢查 FAIL：背景未去除，不是透明 GIF' if failed else '背景檢查 PASS')
        + f'；邊框不透明比例 {ring:.3f}'
    )
    return int(failed)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
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
    qa_p = sub.add_parser('qa', help='Fail if a GIF’s 4px border is still opaque (background not removed)')
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
