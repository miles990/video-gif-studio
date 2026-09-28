# Example: Stylized Redraw with Motion-Attached Texture

**English** | [繁體中文](README.zh-TW.md)

![Accepted render, contact sheet](contact.jpg)

The [seated leg-switch GIF](../seated-leg-switch/README.md) is used here only as a **motion plate**. Every delivered pixel is redrawn from guides measured on it; no plate pixel is delivered. This example documents the [stylized redraw route](../../references/stylized-redraw.md) end to end, including what did not pass.

## Deliverables

- [final.mp4](final.mp4): the accepted `manga_action.js` render on paper, 289 frames at the plate's own timing (9.93 s). Screentone is laid out in texture coordinates advected with the motion, so dots ride on the chair, dress and cape. Speed lines are drawn from the plate's measured optical flow: they appear only while the right leg uncrosses and trail behind the foot.
- [comparison.mp4](comparison.mp4): plate, `ink_hatching` on advected texture coordinates (a preview, see below) and the accepted render, side by side.
- [evidence.png](evidence.png): the measured re-anchoring trade-off and the per-check results for all three renders.

## Status

| Render | Automatic checks | Status |
| --- | --- | --- |
| `manga_action.js` (JS, headless Chromium) | all seven pass | **accepted** |
| `ink_hatching`, texture on advected uv | motion coherence flagged on 2 of 11 measurable transitions | preview |
| same hatching pinned to the canvas (control) | motion coherence flagged on 10 of 11 | control: texture slides |

Acceptance was decided by Claude as the agent reviewer, under the user's delegation, from frame inspection of contact strips and consecutive frames through the leg switch. Real-time playback was not available. The review record is in [manifest.json](manifest.json). Only 11 of 246 moving transitions had enough steady-blend pixels for the attachment check, so attachment evidence at this clock setting is thin.

## Reproduce

```bash
# plate: numbered RGBA frames and a durations_ms manifest extracted from ../seated-leg-switch/final.gif
.venv/bin/python scripts/extract_guides.py plate --manifest plate.json --out guides --colors 8 --flow
.venv/bin/python scripts/render_stylized.py guides --style examples/stylized-redraw-seated/style-manga.json --out render
.venv/bin/python scripts/qc_redraw.py guides --render render --style examples/stylized-redraw-seated/style-manga.json --out qc.json
```

`manga_action.js` needs a headless Chromium (`$VGS_CHROME`, Playwright's cache or PATH). Guides with flow for this plate take about 750 MB; renders about 50 MB each.

## What the checks caught along the way

- **Texture that stays attached can still rot.** One layer of advected coordinates passed every early check, yet frame 286 showed hatching bent into marble-like waves (deformation 1.4). A texture-distortion check was added so this cannot pass silently again.
- **Re-anchoring on the wrong clock.** A frame clock bounded deformation but made 196-209 of 288 frames shimmer in still regions; travel and strain clocks let deformation run away (1.26-1.33). The shipped clock advances each point's phase with its measured texture deformation, and only while it moves.
- **Stillness was misread.** Smoothing had bled a moving leg's flow into still neighbors. Declaring stillness from either raw or smoothed flow removed the remaining shimmer: no still pixel changes layer weight.
- **The attachment check could not tell cross-fading from sliding.** It now excludes pixels whose layer blend changed and still flags canvas-pinned texture.

These are one plate's measurements, not universal settings.
