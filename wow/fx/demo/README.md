# Freeze / cutout / beat — fix round 1

Deliveries: [demo.mp4](demo.mp4), [demo-b.mp4](demo-b.mp4), and silent GIF previews
[demo.gif](demo.gif), [demo-b.gif](demo-b.gif). Both films are 640×360, 9.160 seconds,
with the original soundtrack. MP4 is opaque. The 240×135 GIFs retain 12.5 fps sampling
and exact total time; they are deliberately smaller than the video masters.

From a fresh checkout, with the normal project Python and FFmpeg available:

```powershell
$env:VIDEO_GIF_FFMPEG='C:/Users/User/.codex/skills/video-gif-studio/.venv/Lib/site-packages/static_ffmpeg/bin/win32/ffmpeg.exe'
$env:VIDEO_GIF_FFPROBE='C:/Users/User/.codex/skills/video-gif-studio/.venv/Lib/site-packages/static_ffmpeg/bin/win32/ffprobe.exe'
& C:/Users/User/.codex/skills/video-gif-studio/.venv/Scripts/python.exe wow/fx/demo/build_demo.py
& C:/Users/User/.codex/skills/video-gif-studio/.venv/Scripts/python.exe wow/fx/demo/verify_demo.py
```

`build_demo.py` rebuilds all prepared sources under `work/round1/` from repository
videos and retained `assets/` PNGs. It writes both 19-line plans, both MP4s, bounded GIFs,
the original-plus-effects preview, manifests and `build-results.json`. User FX libraries
are not loaded. No model or optional inference environment is needed for this route.
It creates a new master directory each run; `build-results.json` identifies the current
masters. `verify_demo.py` creates decoded beat sheets, QA, reverse drafts and measurements.
Reverse draft source paths point into that run's scratch directory: rerun verification
to rebuild them after a fresh checkout. `prepare_demo.py` belongs to the superseded demo.

| Measurement | A | B |
|---|---:|---:|
| Render + MP4 + bounded GIF export, excluding source preparation | 57.40 s | 56.05 s |
| Pixel render | 29.69 s / 8.08 fps | 28.63 s / 8.38 fps |
| GIF bytes | 2,928,071 | 2,839,422 |
| Decoded GIF / MP4 duration | 9160 / 9160 ms | 9160 / 9160 ms |
| Smallest GIF exposure | 40 ms | 40 ms |
| Foreground resting / peak height | 176 / 195 px | 178 / 191 px |
| Peak centroid displacement | 19.15 px up | 19.30 px up |
| Freeze mean luma | 51.36 | 65.59 |
| Original retained freeze luma | 65.82 | 95.58 |
| Flash peak timing errors, 740 and 2200 ms | 0 / 0 ms | 0 / 0 ms |
| Flash luma rises against 120 ms before | 128.30 / 123.66 | 118.55 / 102.50 |
| Reverse cut errors, 2920 / 5860 / 7320 ms | 0 / 0 / 0 ms | 0 / 0 / 0 ms |

The freeze is 2920–5860 ms. Beats 8–15 (2920, 3280, 3660, 4020, 4400, 4760,
5120, 5480 ms) all drive the same-shot foreground, with 20 px translation, 1.06 scale,
−3° rotation and 240 ms decay. Its plate is blurred at sigma 12 and multiplied by .55.
The flash_cut enters the freeze; the whip at 5860 ms has no stacked flash. A hex shutter
at 7320 ms leads to closing zoom punches through 8800 ms (360 ms before the end).
A and B plans differ only in material paths. These are editorial card accents, not
newly synthesized fish motion.

Both reverse reports contain exactly three edits with the correct transition types,
and a 2920–5860 ms still in directly validated drafts. Animated-cutout freeze inference
is explicitly `review: true`; the reverse tool cannot recover the separated layers.

Both decoded MP4 QA reports are PASS: [A](qa/report.md), [B](qa-b/report.md). These use
`--timeline` semantics for designed transitions. This does not claim the legacy strict
`--expect-cuts` hard-discontinuity detector recognizes smooth transition midpoints.
The builder viewed every beat's neighbors, every transition at .25/.5/.75, freeze
start/middle/end, and closing frames in `inspection-a-1.jpg` through `inspection-b-7.jpg`.
No replicated-edge streak or extra seam line was seen; the moving boundary between
the adjacent shots is intentional. The hexagonal aperture is visible and the white
card outline remains continuous. Final flash peaks were rechecked after adding their
first decay samples. Playback/listening and independent aesthetic approval remain
unverified; frame inspection and numeric QA are not substitutes for those judgments.

## Retained matte provenance and optional regeneration

A uses neon segment 01 for the opening/freeze and segment 04 for the middle shot.
B uses segment 03 and segment 05. The closing section returns to the opening material.
All video paths are `examples/neon-zen-pv/segment-XX/generation/source.mp4`; music is
`examples/neon-zen-pv/soundtrack.flac`. Nothing under examples/ is modified.
`beats.json` is the recorded Beat This! grid: 163.636 BPM, double-time relative to the
82 BPM RMS estimate. Model timing provenance is included in the JSON.

`assets/freeze-a.png` and `freeze-b.png` are the source frames; `matte-a.png` and
`matte-b.png` retain their RGB exactly and add BiRefNet alpha. The two `check-*.png`
files composite them over green for edge review. Matte SHA256 and exact-RGB checks are
in `verification.json`. They replace the unrelated character sprites from the old demo.

Only to regenerate the TWO mattes, run this separate process, let it exit, then run the
normal build above. The optional environment needs rembg, its ONNX runtime and
opencv-python-headless; point U2NET_HOME at existing BiRefNet weights.

```powershell
$env:NUMBA_DISABLE_JIT='1'
$env:OMP_NUM_THREADS='2'
$env:U2NET_HOME='C:/Users/User/.codex/skills/video-gif-studio/.runtime/models'
& C:/Users/User/src/fx-optdeps/venv/Scripts/python.exe wow/fx/demo/build_demo.py --prepare-only --rematte
```

One CPU session processes A and B sequentially. This run: 41.48 s and 58.25 s inference,
excluding shared model initialization. The coordinator's separate load-inclusive
comparison was u2netp 10.6 s versus BiRefNet 61.6 s (`../live/matte-compare.jpg`).
Keep at most one matting/render/test process active on this shared 16 GB machine.

Round 2 correction: literal qa_media --expect-cuts counts planned flashes and transitions as image discontinuities (cuts). It is not an editorial-boundary oracle. Use --timeline with the emitted manifest to check declared holds and joins, and decoded luminance/difference measurements for accent timing. The round-1 measurements above describe the earlier render; see build-results.json and verification.json for the rebuilt measurements.


## Rebuilt round 2 freeze correction

The retained matte now stays at its original canvas position and size. The background
is inpainted under a 19px dilated matte before sigma-12 blur, so no second fish is visible.
The border is 6px. Ordinary accents move upward 12px with -1 degree rotation and unit
scale; freeze beats 4/8 use 19px, +1.6 degrees and 1.015 scale. The opening has a 1.14
zoom hook. Halation is .65 at sigma 6 / threshold .55; grade sat=1.12, temp=.025,
gain=1.06. These replace the older framing/settings described above.

The rebuilt 9.160s films passed timeline QA for both materials. Initial rebuilt export
wall times were A 61.57s / B 57.70s, GIF sizes 2,924,196 / 2,882,392 bytes. Later
build-results.json supersedes these times if rebuilt with the optimized renderer.
Inspection-a/b-3.jpg shows original-scale float-up and clean background plates; all
inspection sheets were regenerated. Reverse zoom candidates now appear as review:true.
No playback/listening judgment is claimed.
