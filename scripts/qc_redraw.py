#!/usr/bin/env python3
"""Automatic checks for a stylized redraw, measured against the style's declared intent.

Checks never judge taste. They measure whether a render is reproducible, keeps timing and canvas, follows the
guide silhouettes, stays still where the plate is still, and is not cut by the canvas edge. A style declares
deliberate departures in "intent" (boil, silhouette_min, silhouette_tolerance_px, interior_change_max, offcanvas_ok).
Passing is not acceptance: agent and human visual review remain separate, recorded steps.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import cv2
import numpy as np
from PIL import Image
from extract_guides import distortion_map, load_flow
from render_stylized import render

INTENT = {'boil': False, 'silhouette_min': 0.95, 'silhouette_tolerance_px': 2, 'interior_change_max': 0.01,
          'static_radius_px': 4, 'static_majority': 0.9, 'change_level': 4, 'offcanvas_ok': False,
          'texture_slides': False, 'motion_change_max': 0.05, 'motion_change_level': 16, 'motion_min_px': 1.5,
          'motion_span': 4, 'motion_min_pixels': 500, 'uv_distortion_max': 0.5,
          'blend_change_max': 0.1}


def _frames(directory):
    return [np.array(Image.open(f)) for f in sorted(Path(directory).glob('*.png'))]


def _guide(guides, manifest, i, key):
    layers = [manifest['frames'][i]] + ([manifest['effects']['frames'][i]] if manifest.get('effects') else [])
    return [np.array(Image.open(guides/layer[key])) for layer in layers]


def _agreement(drawn, target, tol):
    # Two-way coverage within a tolerance band: outlines and small offsets pass, missing or extra shapes do not.
    if not drawn.any() and not target.any():
        return 1.0
    kernel = np.ones((2*tol+1, 2*tol+1), np.uint8)
    near_target = cv2.dilate(target.astype(np.uint8), kernel).astype(bool)
    near_drawn = cv2.dilate(drawn.astype(np.uint8), kernel).astype(bool)
    precision = (drawn & near_target).sum()/drawn.sum() if drawn.any() else 1.0
    recall = (target & near_drawn).sum()/target.sum() if target.any() else 1.0
    return float(min(precision, recall))


def _motion(guides, manifest, figure, baseline, intent):
    # Warp the frame `span` steps back along chained measured motion; texture glued to the body should land in place.
    # Chaining matters: slow sliding under 1 px per frame hides inside the tolerance but accumulates over a few frames.
    h, w = figure[0].shape[:2]
    gy, gx = np.mgrid[:h, :w].astype(np.float32)
    flows = [load_flow(guides, manifest, i) for i in range(len(figure))]
    fractions, base_fractions, moving_pixels, crossfading, bad = [None], [None], [None], [None], []
    k3 = np.ones((3, 3), np.uint8)
    for i in range(1, len(figure)):
        span = min(intent['motion_span'], i)
        mx, my, valid = gx.copy(), gy.copy(), np.ones((h, w), bool)
        for j in range(i, i - span, -1):
            bw, ok = flows[j]['backward'], flows[j]['valid']
            valid &= cv2.remap(ok.astype(np.uint8), mx, my, cv2.INTER_NEAREST, borderValue=0).astype(bool)
            step = cv2.remap(bw, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            mx, my = mx + step[..., 0], my + step[..., 1]
        target = np.any([m > 0 for m in _guide(guides, manifest, i, 'mask')], axis=0)
        moving = valid & target & (np.hypot(mx - gx, my - gy) >= intent['motion_min_px'])
        # Where the guides themselves cross-fade texture layers over this span, appearance changes by design;
        # judge attachment only where the blend held steady, so a sliding texture still has nowhere to hide.
        fading = np.zeros_like(moving)
        if len(flows[i]['uv_layers']) > 1:
            then = cv2.remap(flows[i - span]['uv_layers'][0][1], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            fading = moving & (np.abs(flows[i]['uv_layers'][0][1] - then) > intent['blend_change_max'])
            moving &= ~fading
        moving = cv2.erode(moving.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        if moving.sum() < intent['motion_min_pixels']:
            moving[:] = False

        def error(seq):
            warped = cv2.remap(seq[i - span], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            # Tolerate 1 px of misregistration: sharp strokes resampled at subpixel offsets are not sliding texture.
            lo, hi = cv2.erode(warped, k3).astype(int), cv2.dilate(warped, k3).astype(int)
            cur, level = seq[i].astype(int), intent['motion_change_level']
            diff = ((cur < lo - level) | (cur > hi + level)).any(2)
            return float((diff & moving).sum()/moving.sum()) if moving.any() else 0.0

        fraction, base = error(figure), error(baseline)
        fractions.append(round(fraction, 5))
        base_fractions.append(round(base, 5))
        moving_pixels.append(int(moving.sum()))
        crossfading.append(int(fading.sum()))
        if moving.any() and not intent['texture_slides'] and fraction - base > intent['motion_change_max']:
            bad.append(i)
    measured = any(moving_pixels[1:])
    return {'pass': (not bad) if measured else None, 'flagged_frames': bad, 'warp_error_fraction': fractions,
            'reference_warp_error_fraction': base_fractions, 'moving_pixels': moving_pixels,
            'crossfading_pixels_excluded': crossfading,
            'unmeasured_frames': [i for i, n in enumerate(moving_pixels) if n == 0],
            'skipped': 'texture_slides declared' if intent['texture_slides'] else None}


def _distortion(guides, manifest, count, intent):
    # Texture glued to noisy motion can stay attached yet deform into waves; bound the deformation itself.
    values, bad = [], []
    for i in range(count):
        f = load_flow(guides, manifest, i)
        target = np.any([m > 0 for m in _guide(guides, manifest, i, 'mask')], axis=0)
        interior = cv2.erode(target.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
        if i:
            interior &= f['valid']
        deformation = sum(wk*distortion_map(uv) for uv, wk in f['uv_layers'])
        values.append(round(float(np.median(deformation[interior])), 4) if interior.any() else 0.0)
        if values[-1] > intent['uv_distortion_max']:
            bad.append(i)
    return {'pass': not bad, 'flagged_frames': bad, 'weighted_median_distortion': values, 'max': intent['uv_distortion_max']}


def qc(guides, style, render_dir, agent_notes=None, out=None):
    guides, render_dir = Path(guides), Path(render_dir)
    manifest = json.loads((guides/'manifest.json').read_text())
    record = json.loads((render_dir/'manifest.json').read_text())
    intent = {**INTENT, **style.get('intent', {})}
    frames = _frames(render_dir/'frames')
    w, h = manifest['canvas']
    checks = {}

    ok = record['durations_ms'] == manifest['durations_ms'] and len(frames) == len(manifest['frames']) \
        and all(f.shape == (h, w, 4) for f in frames)
    checks['timing_canvas'] = {'pass': bool(ok)}

    with tempfile.TemporaryDirectory() as tmp:
        render(guides, style, Path(tmp)/'again')
        again = _frames(Path(tmp)/'again/frames')
        # Measure the figure before any opaque background; otherwise the whole canvas looks like the subject.
        figure = frames
        if style.get('background'):
            render(guides, {k: v for k, v in style.items() if k != 'background'}, Path(tmp)/'figure')
            figure = _frames(Path(tmp)/'figure/frames')
        # Guides carry frame-to-frame label noise from the plate; only change beyond the reference renderer counts.
        baseline = figure
        if style.get('plugin'):
            render(guides, {k: v for k, v in style.items() if k not in ('background', 'plugin', 'plugin_params')}, Path(tmp)/'baseline')
            baseline = _frames(Path(tmp)/'baseline/frames')
    differs = [i for i, (a, b) in enumerate(zip(frames, again)) if a.shape != b.shape or not np.array_equal(a, b)]
    checks['deterministic'] = {'pass': not differs and len(frames) == len(again), 'flagged_frames': differs}

    scores, bad = [], []
    for i, f in enumerate(figure):
        target = np.any([m > 0 for m in _guide(guides, manifest, i, 'mask')], axis=0)
        scores.append(round(_agreement(f[..., 3] >= 128, target, intent['silhouette_tolerance_px']), 4))
        if scores[-1] < intent['silhouette_min']:
            bad.append(i)
    checks['silhouette'] = {'pass': not bad, 'flagged_frames': bad, 'scores': scores, 'min': intent['silhouette_min']}

    r = intent['static_radius_px']
    fractions, base_fractions, still_pixels, bad = [None], [None], [None], []
    previous = _guide(guides, manifest, 0, 'labels')
    flow_on = manifest.get('flow', {}).get('enabled')

    def changed(seq, i, still):
        diff = np.abs(seq[i].astype(int) - seq[i-1].astype(int)).max(2) > intent['change_level']
        return float((diff & still).sum()/still.sum()) if still.any() else 0.0

    for i in range(1, len(frames)):
        labels = _guide(guides, manifest, i, 'labels')
        same = np.all([(a == b) & (a != 255) for a, b in zip(labels, previous)], axis=0)
        # Locally still: this label is unchanged and most labels within the radius are too; plate noise flips a few.
        near = cv2.blur(same.astype(np.float32), (2*r+1, 2*r+1)) >= intent['static_majority']
        still = same & near
        if flow_on:
            # A uniform region can translate with unchanged labels; with measured flow, still means not moving.
            still &= np.linalg.norm(load_flow(guides, manifest, i)['backward'], axis=2) < manifest['flow'].get('deadzone_px', intent['motion_min_px'])
        fraction, base = changed(figure, i, still), changed(baseline, i, still)
        fractions.append(round(fraction, 5))
        base_fractions.append(round(base, 5))
        still_pixels.append(int(still.sum()))
        if not intent['boil'] and fraction - base > intent['interior_change_max']:
            bad.append(i)
        previous = labels
    # A zero fraction over zero still pixels means nothing was measurable, not that nothing flickered.
    unmeasured = [i for i, n in enumerate(still_pixels) if n == 0]
    measurable = len(frames) < 2 or len(unmeasured) < len(frames) - 1
    checks['static_interior'] = {'pass': (not bad) if measurable else None, 'flagged_frames': bad,
                                 'changed_fraction': fractions, 'reference_changed_fraction': base_fractions,
                                 'still_pixels': still_pixels, 'unmeasured_frames': unmeasured,
                                 'skipped': 'boil declared' if intent['boil'] else None}

    not_run = []
    if manifest.get('flow', {}).get('enabled'):
        checks['motion_coherence'] = _motion(guides, manifest, figure, baseline, intent)
        checks['texture_distortion'] = _distortion(guides, manifest, len(frames), intent)
    else:
        not_run.append('motion_coherence')

    bad = []
    for i, f in enumerate(figure):
        border = np.ones((h, w), bool)
        border[1:-1, 1:-1] = False
        target = np.any([m > 0 for m in _guide(guides, manifest, i, 'mask')], axis=0)
        if (f[..., 3][border] > 0).any() and not target[border].any():
            bad.append(i)
    plate_edge = [i for i in range(len(frames)) if np.any([m[[0, -1]].any() or m[:, [0, -1]].any()
                                                            for m in _guide(guides, manifest, i, 'mask')])]
    checks['canvas_edge'] = {'pass': intent['offcanvas_ok'] or not bad, 'flagged_frames': bad,
                             'plate_touches_edge_frames': plate_edge}

    report = {'kind': 'stylized-redraw-qc', 'intent': intent, 'checks': checks,
              # None means a check could not measure anything; that is not a pass.
              'auto_checks_passed': all(c['pass'] is True for c in checks.values()),
              'inconclusive': [k for k, c in checks.items() if c['pass'] is None],
              'not_run': not_run,
              'render_manifest_sha256': hashlib.sha256((render_dir/'manifest.json').read_bytes()).hexdigest(),
              'agent_review': {'by': 'agent', 'notes': agent_notes} if agent_notes else None,
              'review': 'automatic checks only; agent notes and human playback sign-off are separate and still required'}
    if out:
        Path(out).write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('guides', type=Path)
    parser.add_argument('--render', type=Path, required=True, help='render_stylized.py output directory')
    parser.add_argument('--style', type=Path, help='The style JSON used for the render')
    parser.add_argument('--agent-notes', help='Agent visual review notes, recorded as agent review, not sign-off')
    parser.add_argument('--out', type=Path, required=True, help='Report JSON path')
    args = parser.parse_args()
    report = qc(args.guides, json.loads(args.style.read_text()) if args.style else {}, args.render, args.agent_notes, args.out)
    print(json.dumps({'auto_checks_passed': report['auto_checks_passed'],
                      'failed': [k for k, c in report['checks'].items() if c['pass'] is False],
                      'inconclusive': report['inconclusive']}))
