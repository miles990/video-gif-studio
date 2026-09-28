#!/usr/bin/env python3
"""Export a side-by-side review of effect masks over the plate: APNG overlay, contact sheet and stability report.

This is a review aid. It flags frames worth a look; it does not judge whether a mask is correct.
"""
import argparse
import json
from pathlib import Path
import tempfile
import cv2
import numpy as np
from PIL import Image, ImageDraw
from gif_pipeline import natural


def _load(frames, manifest, masks):
    files = sorted(Path(frames).glob('*.png'), key=natural)
    mask_files = sorted(Path(masks).glob('*.png'), key=natural)
    durations = json.loads(Path(manifest).read_text())['durations_ms']
    if not files or len(files) != len(durations) or len(mask_files) != len(files):
        raise ValueError('Plate frames, timing manifest and masks must have matching counts')
    plate, mask = [], []
    for f, m in zip(files, mask_files):
        with Image.open(f) as im, Image.open(m) as mk:
            plate.append(np.array(im.convert('RGBA')))
            mask.append(np.array(mk.convert('L')) > 0)
        if mask[-1].shape != plate[-1].shape[:2] or plate[-1].shape != plate[0].shape:
            raise ValueError('Shared canvas required for plate and masks')
    return files, mask_files, durations, plate, mask


def _checker(h, w, size=8):
    y, x = np.mgrid[:h, :w]
    return np.where(((x//size + y//size) % 2)[..., None] == 0, 96, 128).astype(np.uint8).repeat(3, 2)


def _over(rgba, bg):
    a = rgba[..., 3:].astype(np.uint32)
    return ((rgba[..., :3]*a + bg*(255-a) + 127)//255).astype(np.uint8)


def _panel(plate, mask, tint):
    bg = _checker(*mask.shape)
    left = _over(plate, bg)
    right = left.copy()
    right[mask] = ((left[mask].astype(np.uint16) + tint)//2).astype(np.uint8)
    edge = mask & ~cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    right[edge] = tint
    return np.hstack([left, right])


def _stability(mask, near=2):
    kernel = np.ones((2*near+1, 2*near+1), np.uint8)
    grown = [cv2.dilate(m.astype(np.uint8), kernel).astype(bool) for m in mask]
    areas = [int(m.sum()) for m in mask]
    isolated, jumps = [], []
    for i, m in enumerate(mask):
        if not areas[i]:
            continue
        neighbors = [grown[j] for j in (i-1, i+1) if 0 <= j < len(mask)]
        if neighbors and not any((m & g).any() for g in neighbors):
            isolated.append(i)
        if i and max(areas[i], areas[i-1]) >= 16 and max(areas[i], areas[i-1]) >= 3*max(min(areas[i], areas[i-1]), 1):
            jumps.append(i)
    return areas, isolated, jumps


def review(frames, manifest, masks, out, tint='#00E5FF', max_tiles=36, tile_width=256):
    out = Path(out)
    if out.exists():
        raise FileExistsError('Use a new output directory')
    files, mask_files, durations, plate, mask = _load(frames, manifest, masks)
    tint = np.array([int(tint.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)], np.uint16)
    areas, isolated, jumps = _stability(mask)
    marked = [i for i, a in enumerate(areas) if a]
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        stage = Path(tmp)/'review'
        (stage/'frames').mkdir(parents=True)
        panels = []
        for i, (p, m) in enumerate(zip(plate, mask)):
            panel = Image.fromarray(_panel(p, m, tint))
            panel.save(stage/'frames'/f'{i:05d}.png')
            panels.append(panel)
        panels[0].save(stage/'overlay.png', save_all=True, append_images=panels[1:], duration=durations, loop=0)
        # Flagged frames first, then an even spread of the remaining masked frames.
        flagged = sorted(set(isolated) | set(jumps))
        rest = [i for i in marked if i not in flagged]
        room = max(0, max_tiles - len(flagged))
        tiles = sorted(flagged[:max_tiles] + [rest[int(k*len(rest)/room)] for k in range(min(room, len(rest)))])
        h, w = mask[0].shape
        th = max(1, round(h*tile_width/w))
        cols = max(1, min(6, len(tiles)))
        sheet = Image.new('RGB', (cols*tile_width, max(1, -(-len(tiles)//cols))*(th+16)), (32, 32, 32))
        draw = ImageDraw.Draw(sheet)
        for n, i in enumerate(tiles):
            x, y = n % cols*tile_width, n//cols*(th+16)
            sheet.paste(panels[i].crop((w, 0, 2*w, h)).resize((tile_width, th), Image.NEAREST), (x, y+16))
            note = ' isolated' if i in isolated else ''
            note += ' jump' if i in jumps else ''
            draw.text((x+4, y+2), f'#{i} area {areas[i]}{note}', fill=(255, 64, 64) if note else (230, 230, 230))
        sheet.save(stage/'contact.png')
        report = {'kind': 'effect-mask-review', 'review': 'pending', 'areas': areas, 'frames_with_mask': marked,
                  'isolated_frames': isolated, 'area_jump_frames': jumps, 'contact_frames': tiles,
                  'masks': [str(m) for m in mask_files],
                  'note': 'flags are a review queue, not verdicts; fast effects legitimately jump and move'}
        (stage/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        stage.rename(out)
    return {'frames': len(files), 'out': str(out), 'frames_with_mask': len(marked),
            'isolated_frames': isolated, 'area_jump_frames': jumps}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('frames', type=Path, help='Plate RGBA frames')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--masks', type=Path, required=True, help='Numbered effect masks (proposal or edited)')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--tint', default='#00E5FF', help='Overlay color; pick one absent from the effects')
    args = parser.parse_args()
    print(json.dumps(review(args.frames, args.manifest, args.masks, args.out, args.tint)))
