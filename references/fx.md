# Explicit post-production effects

Use this route only when the user asks for post-production effects. Effects never
substitute for physical character motion, invent a jump, or hide a broken source join.
Prepare the source with `gif_pipeline.py`; retain the source animation and its alpha.

## P0 delivery (2026-11-05)

MP4/MOV/WebM now stream rendered frames directly to FFmpeg, defaulting to CFR 30 fps.
Use `--fps 24|25|30|50|60`, or explicit `--fps 100` for the old 10 ms video behavior.
GIF/APNG/PNG retain their legacy timing and supported lengths; no 512 MiB cap is imposed.
Raster export still retains the film in memory, so prefer video for long timelines.
`--platform tiktok|reels|shorts|youtube|square` sets size, bitrate, yuv420p and actual
BT.709-limited conversion. Preset dimensions, safe-zone rectangles and the extra
2%-width text inset are documented in [video delivery](video-export.md#platform-presets)
and recorded under `manifest.delivery`; later caption code can consume those bounds.

`--proxy` renders at one-third resolution with the same video event/cut grid, skips
RIFE and model-backed depth, and reuses bounded image/flow caches. Skipped model
operations are recorded in `delivery.proxy_skipped`; their event timing remains in
the manifest. P1's separate `--review-html` workflow adds an independent-shot cache.
Use `scripts/intake.py` before frame preparation for phone VFR, rotation and HDR.
For opt-in original sound, supply a continuous `source_audio` and `--keep-audio`;
see [measured loudness and ducking](music.md#delivery-audio).

Full serial measurements are in [benchmark-p0.json](../wow/fx/benchmark-p0.json).
The acceptance workload uses zoom_punch, rgb_split and film_grain over moving
textured gradients at 120 BPM. The latter two remain experimental in the existing
registry, so the harness explicitly enables them without changing quality status.

| Workload | Output frames | End-to-end speed | Whole-tree peak (larger RSS / peak working set) |
| --- | --- | --- | --- |
| 1080×1920, 10 s | 300 | 3.42 fps | 504 MB |
| 1080×1920, 30 s, 3 trials | 900 each | 3.39–3.44 fps | 507 MB maximum |
| 720×1280, 30 s | 900 | 7.62 fps | 673 MB |
| Proxy 360×640, 30 s | 900 | 14.13 fps | 139 MB |

These figures include decoding PNG sources, rendering and final encoding; they are
not effect-kernel-only timings. Hardware/runtime details and every 50 ms sample are
in the JSON. At half wall time, the three long encodes had written 49% of final bytes;
10 s versus 30 s peak memory differed by at most 0.55%.
The proxy took 63.67 s, 24.18% of the mean full-render time, with identical event
and cut frame indices in the offline regression test. Windows uses the native
Toolhelp32Snapshot/GetProcessMemoryInfo fallback because this venv lacks psutil.
Run `python wow/fx/benchmark_p0.py --out wow/fx/benchmark-p0.json` to reproduce;
`--stable` measures zoom_punch + grade + halation separately. Run one heavy process
at a time. See [build notes](../wow/fx/build-notes-p0.md) for test results and caveats.

Intake timestamp reports record both `observed_pts_gap_seconds` (raw gap) and
`length_seconds` (gap minus one nominal frame). A timestamp jump adjacent to a
dropped frame is one combined missing interval: **the reported jump length includes
the adjacent dropped frame**. PTS alone cannot separate those causes. The report
also includes `nominal_frame_seconds`, interpretation, and frozen-frame count;
the count excludes the original held frame.

The separate [stable-only benchmark](../wow/fx/benchmark-p0-stable.json) uses
zoom_punch + grade + halation: 1080×1920 / 30 s at **3.965 fps / 499,961,856 bytes**
peak; the 10 s peak is **499,236,864 bytes** (growth **0.145%**). At 720×1280 the
same stable trio runs at **7.251 fps / 268,083,200 bytes** peak. These measurements
also include source decoding and final encoding. Its 360×640 proxy runs at
**13.565 fps / 137,527,296 bytes**, taking **66.35 s (29.23% of full render time)**.

```sh
python scripts/fx_render.py plan.json --out delivery --formats png gif mp4
python scripts/fx_render.py --list --json
python scripts/fx_render.py --preview preview.png --image prepared/frames/00000.png
python scripts/fx_render.py plan.json --validate --formats mp4
```

`--list` alone prints names, readable parameter defaults/descriptions and source files;
add `--json` for the machine-readable catalog. Preview includes an original reference
tile and deliberately visible example settings (stronger than restrained film defaults).

The timeline schema and exporters are shared with `compose_timeline.py`. A plan without
effects/transitions uses that composer directly: pixel values and variable exposures
are unchanged. `music` still requires a video output. Existing output directories are
rejected. Rendering is staged; failed renders do not publish a partial delivery.

## Contract

`@effect()` functions receive `f(frame, t_ms, ctx, **params)`. `@transition()` functions
receive `f(a, b, p, ctx, **params)`, where p runs from 0 to 1. Public decorated functions
accept H×W×4 straight RGBA, uint8 0..255 or float32 0..1, and return the **same dtype**.
The decorator gives the implementation fresh float32 arrays, clips the result, and
preserves caller inputs. Write implementations in 0..1 float32; return a new array or
modify that private copy. Builtins are vectorized NumPy/OpenCV, with no per-pixel Python
loops. Geometry and blends use premultiplied alpha internally; hidden RGB cannot leak.

Construct `Context(width, height, fps=25, beats_ms=[...], t_ms=0, segment={}, seed=0,
downbeats_ms=[], audio={}, sampling='linear')`. Fields include `since_previous_beat`
(0 exactly on a beat), `until_next_beat` (strictly future), segment `index`, `start_ms`,
`end_ms`, dimensions and fps. `ctx.rng` returns a fresh NumPy generator seeded by
`ctx.seed`; identical inputs including seed reproduce output across processes. For
animated random noise explicitly derive a seed from an integer frame/time, never Python
`hash()`. Avoid global RNGs, mutable plugin state and wall clocks.

## Stable

The default catalog contains the six round-one effects and four transitions below.
All round-two operations are **experimental (pending quality gate)**. They are hidden
from `--list` and `--preview` unless `--experimental` is supplied. To validate or render
a plan using them, pass `--experimental` or set top-level `"experimental": true`.
The delivery manifest's `experimental_items` lists used effects (`effect:name`),
transitions (`transition:name`), and features (`speed`, `ramp`, `interpolate:mode`).
Stable-only plans record an empty list; opting in alone does not imply experimental use.

`--list` is the authoritative typed parameter/default/doc/source catalog. The following
defaults are also usable directly as plan fields. Every numeric field accepts envelopes.

| Effect | Parameters and defaults |
|---|---|
| flash_white | amount=1; RGB moves toward white, alpha exact |
| beat_bounce | amount=1, translate_px=8 upward, rotation_deg=2, scale=1.01, sampling=linear |
| halation | amount=.8, radius=6 px Gaussian sigma, warm=true, threshold=.65; alpha exact, never expands coverage |
| grade | lift=0, gamma=1, gain=1, sat=1, temp=0; temp adds red and subtracts blue |
| zoom_punch | amount=1, scale=1.07, sampling=linear; alpha area follows scale squared; premultiplied geometry avoids dark fringes |
| cutout_card | border_px=6, shadow_px=7 down/right, shadow_blur=4, bg='', background='', darken=.4, blur=8, amount=1 |

`cutout_card` uses the source alpha; it does not infer a foreground from an opaque image.
It builds a continuous white silhouette behind the subject and a soft down/right shadow.
Empty `bg` keeps distant pixels transparent. `bg: "142132"` makes an opaque flat backdrop.
`background: "plate.png"` uses a separate image, dimmed by `darken` and blurred by `blur`.
The subject's source RGB is preserved; alpha-over-white removes dark fringe contamination.

| Transition | Parameters and defaults |
|---|---|
| crossfade | none; premultiplied dissolve |
| whip_pan | blur_px=49, direction=left (or right); two adjacent shots pan together through a horizontal blur, without replicated edge stretching |
| hex_shutter | color=121522; six-sided aperture closes then opens |
| flash_cut | none; white midpoint and unchanged endpoints |

Geometry defaults to linear filtering. Set top-level `"sampling":"nearest"` (or the
individual geometry parameter) for pixel art: no new palette colors or soft alpha are
introduced. Explicit preparation must also use nearest enlargement. Large scale changes
increase coverage and may crop; choose bounds deliberately. The default punch is 1.07;
transparent coverage scales geometrically, with premultiplication protecting edge RGB.

## Plans, clocks and envelopes

Add `transition` to the **incoming** segment. Its `duration_ms` window is centered on the
original edit boundary. p=.5 is exactly the boundary; no overlap changes the timeline
length. A transition cannot exceed either neighboring segment's duration. Before the
incoming segment begins, its first frame is extended; after the outgoing segment ends,
its last frame is extended. Source material outside the specified trim is never pulled in.

```json
{
  "beatmap":"beats.json", "fps":25, "seed":7,
  "segments":[
    {"type":"animation","manifest":"a/manifest.json","end_beat":4},
    {"type":"still","manifest":"subject/manifest.json","frame":"first","end_beat":8,
     "transition":{"name":"flash_cut","duration_ms":240}}
  ],
  "effects":[
    {"name":"cutout_card","stage":"source","start_beat":4,"end_beat":8,"bg":"142132"},
    {"name":"flash_white","amount":{"on":"beats","indices":[4],"decay_ms":180,"curve":"ease_out"}}
  ]
}
```

Effect intervals are `[start,end)`; use start_ms/end_ms or start_beat/end_beat, not both
for an endpoint. Omitted bounds span the whole timeline. Beat indices are zero-based.
`music.in_ms` is subtracted from beat and downbeat clocks for both edits and envelopes.
Raster edits follow the existing nearest-10ms rule. Raster rendering defaults to 25 fps; 1..50 is
accepted, with exposures quantized to the exporter's 10ms grid. Beat peaks and edit
boundaries are inserted on that grid so they cannot be skipped by nominal frame sampling.
On an inserted beat frame, evaluate its beat envelope at the exact unrounded beat peak.
Thus raster exposures may be variable, including 10ms accents. Video delivery now
defaults to CFR 30 fps; `--fps 24|25|30|50|60` selects its grid independently of the
legacy plan sampling rate. Events round half-up and record errors in the manifest.
Explicit `--fps 100` retains the old repeated 10ms exposures; see [video delivery](video-export.md).
GIF derivatives merge exposures of 20ms or less with a neighbour, retaining the first
image of a merged group and the exact total duration. This avoids browser 100ms clamping;
PNG and video retain the original sample times. A GIF of total duration <=20ms cannot
represent that timing portably. Use video/APNG for such a short asset.

Effects run in listed order. `stage: "post"` (default) applies after transitions.
`stage: "source"` applies before a transition to each participating source, scoped by
that segment's clamped output clock. Use source-stage bounce then cutout_card so the
card and its background transition together; the white border never follows blur streaks.
Post-stage grade/halation/flash finish the composited result.

Numeric parameter forms:

- Constant: `"amount":0.7`.
- Keyframes: `{"keyframes":[[0,0],[1000,1]]}`; linear interpolation, endpoints clamped.
- Beats: `{"on":"beats","attack_ms":100,"decay_ms":200,"curve":"linear"}`.
  Attack leads **into** the beat; peak stays on the beat. Decay follows it. Defaults are
  attack=0, decay=200, curve=linear. Curves: linear, ease_out (cubic falloff), smooth.
- Selection: `"indices":[1,3]` (`beats` is an alias), or `"every":2`, starting at index 0.
  Optional `min`=0 and `max`=1 rescale the envelope. Overlapping triggers use maximum.
- Downbeats: `{"on":"downbeats"}`; requires actual downbeats_ms. `end_downbeat:k` is
  supported on segments, with the same offset and 10ms rounding as end_beat.
- Strength: `{"on":"onset"}` or `{"on":"energy"}`. The renderer recomputes 10ms RMS
  from music.file, even when an old beats.json only contains peak timestamps/waveform.
  Energy is linear RMS / maximum RMS; onset is positive RMS difference / maximum positive
  difference. Energy interpolates between hops. Onset peaks accept `decay_ms` (default
  120ms), with maximum overlapping decays. Peak sample times are inserted into the
  render grid; audio parameters also take their maximum within each output exposure,
  so changing music.in_ms does not randomly miss clicks. No logarithmic loudness mapping.
  A 12dB quieter click produces approximately one quarter of the strength. Native PCM16
  WAV works without FFmpeg; compressed audio uses media_runtime. Missing music/decoder is
  an actionable error, never an all-zero replacement. `music_sync.py` also records these
  curves under envelopes without changing the existing RMS beat/onset timestamp algorithm.

All plan keys, parameter names/types, envelope keys, ranges of beat indices, transitions,
source canvases and timing are checked before output creation and effect pixel processing.
Unknown keys are errors, including top-level typos. `review` is allowed annotation metadata.
Segment and transition duration_ms must be a multiple of 10. Transitions must last at least one requested
output frame. Downbeats must coincide with actual beats (1ms integer-rounding tolerance).
Nearest/pixel sampling warns when crossfade, whip_pan or flash_cut blends new colours; warnings are retained in the output manifest.

## Your growing library

Save the following eight-line plugin to a project folder; run with `--fx-dir folder`:

```python
from fx import effect

@effect(amount="Inversion blend, 0..1")
def my_invert(frame, t_ms, ctx, amount=1.0):
    """Invert visible RGB while retaining alpha."""
    result = frame.copy()
    result[..., :3] += (1 - 2 * result[..., :3]) * amount
    return result
```

Precedence: builtins < `~/.video-gif-studio/fx/*.py` < repeated `--fx-dir` directories,
left to right; files within a directory load alphabetically. Set `VIDEO_GIF_FX_HOME` to
override the automatic library location; `--no-user-fx` disables it. Missing directories
are ignored and never created. Syntax/import failures warn with filename and line and
skip that file; its partial registrations are rolled back. Other files and builtins remain
available. Plugins are trusted local Python code.
Overrides report the name and both source paths to stderr and the delivery manifest.
Plugins from either library source default to `status="stable"`. Authors can explicitly
declare `@effect(status="experimental")` or `@transition(status="experimental")` to
require the same opt-in. Registry/catalog entries expose `status`; only `stable` and
`experimental` are accepted. A plugin override's own declared status takes precedence.

After a successful film: choose a distinctive name; document parameters with decorator
keyword descriptions and typed defaults; save the .py into the user library; generate
one --preview PNG and retain it with the source film/license notes. The next plan can use
the name directly. Keep media-specific paths in the plan, not in the reusable function.
Manifest entries retain full resolved defaults/envelopes, interval, triggers, source file
and sha256. Nondeterministic manifest fields are render.seconds/render.fps; output paths
and source absolute paths can differ across workspaces. Frame PNG bytes are deterministic.

## Optional audio and matting backends

`python scripts/music_sync.py song.flac --out analysis --engine beat_this` uses CPJKU's
Beat This! CPU File2Beats/minimal postprocessor. Install `beat_this` and CPU PyTorch only
in an optional environment. First live use may download its checkpoint. Import/model
failure warns clearly and records engine=rms plus fallback_reason; no downbeats are
fabricated. A downbeat-dependent plan then fails with the exact plan location and a
`--engine beat_this` instruction. The engine_fn callable is injectable for offline tests;
the injected-engine fixture is synthetic; the separate neon fixture records live output.
The recorded live neon run is `wow/fx/live/beat_this-neon.json`: 82 beats and 20 downbeats
in 30 seconds, 9.8 seconds inference. BPM now derives from model beat intervals (163.64
for that recording, rather than the RMS analyzer's 82). Times are integer milliseconds.
The model may report double-time; inspect the intended pulse before selecting edits.
`tests/fixtures/beat_this_neon.json` retains the corrected timing/BPM fixture.

`background_remove.py --model` accepts u2netp (unchanged default), u2net,
birefnet-general and birefnet-portrait. For a single freeze-frame, prefer BiRefNet's more
expensive quality-oriented models; portrait is for people. For many preview frames,
u2netp is the smaller/faster starting point. Coordinator live CPU measurements, including
model loading: **u2netp 10.6s/frame; birefnet-general 61.6s/frame**. The same fish-frame
comparison in `wow/fx/live/matte-compare.jpg` shows u2netp retaining a neon pillar and
fragments while BiRefNet separates the fish more cleanly. These are single-frame timings,
not a throughput guarantee. The optional venv also needs `opencv-python-headless`
(gif_pipeline imports cv2). Review hair/occlusion and edges regardless of model.
Missing rembg gives a clean requirements-matting.txt error without traceback. No model installs/downloads occur
in tests; injected maskers verify model provenance. Existing read-only weights may be
selected using U2NET_HOME. See THIRD_PARTY.md for project/model licensing caveats.

## Reverse a reference into an editable draft

This is a clean-room implementation inspired only by rea-video's concept; no code was
read or copied from that unlicensed repository. 拆解是為了學結構，不搬運他人畫面、音樂、肖像。

```sh
python scripts/fx_reverse.py reference.mp4 --out breakdown --beats beats.json
python scripts/fx_render.py breakdown/draft-plan.json --validate
```

PNG sequences and GIF/APNG also work offline; --fps defaults to 25 for analysis. With
video audio and no --beats, the existing RMS music analyzer supplies beat candidates.
report.json includes hard/gradual edit candidates, flash peaks, horizontal motion blur,
zoom scale estimates, holds, and the numerator/denominator of edits within one analysis
frame of beats. shots.png labels each shot's time. The draft uses builtins, exact segment
durations (end_beat only for near-exact matches), and review=true on uncertain reconstruction.
All report/draft timestamps and durations are integer milliseconds. Short brightness
peaks between nominal analysis frames are retained; white-mix strengths of .6 and above
are detected relative to nearby clean exposures. Zoom candidates require spatially
distributed similarity-transform agreement, centered expansion rather than dominant
translation, and a subsequent scale decay. Cornerless full-frame stripe graphics use
a separate consistent edge fit across bands. Slow camera zooms and punches at the very
start/end without enough temporal evidence can be omitted; candidates remain reviewable.
Flash-hidden edits compare clean spatial structure across the white peak; bounded
horizontal-detail troughs identify same-palette whips. Coherent cumulative chroma paths
can identify long dissolves. Repeated foreground poses over a static outer plate are
reported as tentative animated-cutout freezes, with `review: true`; a locked camera or
looping action can be ambiguous. In-shot freeze boundaries split the draft into still
segments. This does not recover the original alpha layers or bounce parameters.
Decoded originals remain in source/. Effect-contaminated frames in shots/ are replaced
with nearest clean-sample holds, then inferred effects are applied. These holds are a
reviewable approximation, not recovered unseen motion. Replace source manifests with
licensed clean footage for an actual remake. Natural motion, lighting and dissolves are
ambiguous; low-confidence results require review. No AI/live-action classification,
prompt inversion or vocal separation is offered.

## Measurements and limitations

See `wow/fx/benchmark.json`: Windows 10 build 19045, Intel64 Family 6 Model 158 Stepping 10,
NumPy 2.5.4, OpenCV 5.0.0. Initial 1280×720 / 90-frame run: **3.27 fps**, 27.49 seconds,
three effects (grade, halation, beat_bounce) with a 500ms crossfade over a 3-second timeline,
excluding PNG saving and GIF/MP4 encoding. This misses the 10 fps target. Timings can vary
under concurrent rendering. Full demo timings and decoded QA are in wow/fx/demo/README.md.
The serial fix-round rerun in `wow/fx/benchmark-latest.json` is **3.276 fps / 27.470s**;
the optional 10fps target remains unmet.
Historical numbers above predate P0. Video-only composition/rendering now streams
frames to FFmpeg; raster output retains the film in memory (see P0 delivery above).

The automatic QA's --expect-cuts checks **hard image discontinuities**, so smooth effects
and a still-to-animation continuation should use --timeline as editorial joins instead.
Do not falsely label that a hard-cut detector passing a transition test. Exact beat peaks
are separately measured from decoded MP4 luminance. The strict acceptance request that
all transition centers pass --expect-cuts remains a known semantic mismatch.

## Round 2: source clock and interpolation (experimental)

Segment `speed` (including explicit 1), `ramp`, and interpolation other than `none`
require experimental opt-in. Omit these fields for a stable round-one plan.

`fx_render` accepts segment `speed: 0.5`, `speed: {"keyframes":[[0,1],[1000,0.25],[2000,1]]}`,
or `speed: {"on":"beats","decay_ms":200,"min":0.5,"max":2}`. The output duration and
beat cut do not change. Speed is integrated on a 1ms grid; keyframe times and envelope
beats are absolute output milliseconds. Source time starts at in_ms. Explicit speed=1 and omitted speed are identical. With an implicit out-point, a
shorter output cut trims the source at unity speed; explicit in_ms/out_ms retains
the legacy duration-fit operation.
Use `ramp: {"into_beat":8,"slow":0.3,"hit_ms":200}` instead of speed: from the segment
start to 200ms before beat 8, source speed is .3; the remaining interval runs at 2x.
The beat must lie inside or at the segment end. Ramp never changes the cut time.
Sources that run out hold their final frame; `source_samples[].extended_last_frame`
is true. `source_samples` records output_ms, segment_index, source_ms and actual
interpolation. Frames are never cyclically wrapped by the time-remap layer.

Top-level `interpolate` (or CLI `--interpolate`) accepts **none, blend, flow, rife**;
default **none**. `VIDEO_GIF_INTERPOLATE` is also gated; the CLI override wins and applies
to validation as well as rendering. Only fractional phases at speed <1 are interpolated. none holds the
preceding frame; blend provides a cheap ghosting reference; flow uses bidirectional
OpenCV DIS with coherent translation correction for aperture-ambiguous graphics.
RIFE is optional CPU ONNX: `pip install -r requirements-fx-optional.txt`, then provide
`rife_model` or VIDEO_GIF_RIFE_MODEL pointing to `.runtime/models/rife_v4.25_lite.onnx`.
No automatic model downloads or silent fallback. RGB+RGB+t is float32 [1,7,H,W],
edge-padded to multiples of 32, then cropped. Alpha uses premultiplied interpolation.
Tests inject a fake engine via `interpolate(..., engine=...)`; no real weights are read.

[Same source midpoint comparison](../wow/fx/demo2/interpolation-comparison.jpg):
none repeats a source pose, blend doubles edges, flow estimates local motion, RIFE
uses learned interpolation. Flow can distort occlusions; inspect every ramp rather
than assuming smoother motion is correct. Recorded live 480x270 RIFE midpoint took
665ms including session initialization. The actual paired timings are in
[interpolation-timings.json](../wow/fx/demo2/interpolation-timings.json).

## History and additional operations

Declare `@effect(history=N)`. `ctx.history` contains at most N preceding output
samples, **newest first**, before post effects (after source effects/transitions).
`ctx.history_times_ms` is the parallel tuple of strictly earlier output timestamps.
Inserted 10ms samples count as frames. The buffer resets at each segment boundary;
missing history is omitted. No feedback or future samples. echo requests four frames.
The renderer keeps a bounded three-source-image cache and one flow pair. Video
frames flow directly to FFmpeg; raster exports retain their film in memory.

## Open defects (independent review P2a+P2b, 2026-11-05; fix scheduled in P2c — experimental items only)
- `gl_polka_dots_curtain` lags on wide canvases (at p=0.99 16:9 still 1.5% A, 10:1 66%) — avoid on wide formats.
- On transparent sources `gl_swirl`, `gl_rotate_scale_fade`, `gl_cross_warp`, `gl_dreamy_zoom` are clipped to fragments by the "both transparent → clear" rule; `spin` zoom-fills transparent subjects; `hex_shutter` mid-frames turn opaque dark blue on transparent backgrounds.
- Caption `clean` can break an over-long word into a one-letter orphan line that overlaps the next line by 2 frames.
- gl ports output NaN for non-finite `p` via the Python API; no "blends colours" warning for gl ports in nearest mode.
- `gl_glitch_memories` faithfully reproduces an upstream shader whose block offset is always 0 (whole-image shift only).
- Performance: gl ports 98–324 ms/frame at 720p (offline OK, not for live preview).

## Experimental (pending quality gate)

The catalog below gives defaults; every numeric parameter accepts the existing
beat/keyframe/audio envelope syntax. `--list --experimental --json` provides types and descriptions.

| Framework feature | Opt-in condition |
|---|---|
| speed / ramp | Any explicit segment time remapping, including speed=1 |
| interpolate | blend, flow or rife; none is stable |

| Effect | Parameters / defaults |
|---|---|
| shake | amount=1, distance=9px, seed=7; built-in 220ms beat decay, 2x on downbeats; reflected edge fill |
| rgb_split | amount=1, distance=6px, direction=0 degrees; R +d / B -d, G and alpha unchanged |
| radial_blur | amount=1, distance=.045 radius fraction, samples=12; restrained radial zoom integration; use .22 for a strong impact |
| echo | amount=.65, decay=.55; softened trails weighted by amount × decay^(age+1), newest age=0; opaque plates use positive differences, RGBA ghosts composite behind the current cutout |
| text | content='節奏\nRHYTHM', font='' prefers bold CJK, size=96px, color=FFF2CE, stroke=2px, stroke_color=142132, shadow_px=4 down/right, shadow_color=080F18, x=.5, y=.42, entrance=pop, amount=1, scale=1 |
| film_grain | amount=.025 standard deviation at 720p, seed=17; monochrome noise attenuated by sqrt(clamp(short edge/720,.25,1)) on smaller canvases |
| vignette | amount=.55; center retained, radial corner darkening |
| light_leak | amount=.4, seed=3; warm drifting edge exposure |
| dust_scratches | amount=.5, seed=29, density=.001; sparse dust and one short hairline, pattern held for three frames |
| invert_flash / black_flash | amount=1; negative / dip to black, alpha unchanged |
| split_screen | amount=1, panels=0 auto 1→2→4 on first three beats; explicit panels=1/2/4; whole frame resized into each cell |
| mirror | amount=1, direction=horizontal or vertical; copy left/top half by reflection |
| kaleidoscope | amount=1, sectors=6; polar wedge reflection |
| posterize | amount=1, levels=4 per channel; 3×3 median removes isolated specks inside opaque coverage before quantization |
| halftone | amount=1, size=8px; clustered colour screen with independent RGB dot coverage; supports tiny inputs |
| multi_cutout | amount=1, distance=65px, border_px=6; three overlapping outline cards; opaque input warns and returns unchanged |
| parallax | amount=1 camera progress, distance=18px, depth='', model=.runtime/models/depth-anything-v2-small.onnx, cache=wow/fx/demo2/work/depth |

| Transition | Parameters / defaults |
|---|---|
| shape_wipe | shape=circle (diamond/star/heart), softness=0px; p is revealed area; shared masks module with hex_shutter |
| luma_wipe | mask=linear (radial/cloud or grayscale PNG path), invert=false, softness=12px, seed=7; PNG masks normalized by actual 8/16-bit depth |
| push / slide | direction=left (right/up/down); both shots move / only incoming moves; push sums complementary edge coverage so fractional positions leave no alpha seam |
| spin | turns=.25; analytic rotation-cover zoom prevents reflected corners, exact endpoints |
| zoom_through | scale=1.8; centered zoom through the cut |
| glitch | seed=7, amount=1; animated row blocks and scanlines; nearest sampling omits colour-changing scanline darkening |

Geometry respects sampling=nearest. Color blends, grain, halation and soft wipes
intentionally create colors. Opaque camera moves extend reflected edges to avoid
black wedges; transparent geometry uses premultiplied alpha and constant transparent
borders. The renderer converts to float32 once per sampled source and quantizes once
at output; public function calls still return the input dtype and preserve inputs.

Text searches an explicit font path or VIDEO_GIF_FONT; otherwise bold Microsoft
JhengHei / Noto CJK is preferred when installed, with Windows msjh.ttc, macOS
PingFang.ttc and Linux NotoSansCJK-Regular.ttc as system fallbacks. Missing fonts error
before output creation with these suggestions. No fallback to Hershey or tofu fonts.
The manifest records the resolved font path. Pop/scale entrance lasts 180ms from the
effect's start; a restrained 10% beat scale follows. System font files are not bundled.
Empty titles raise a clear error. Missing glyph warnings list every missing U+ code point.
Long titles shrink to fit 88% of the available width and the height around their anchor, with a warning;
use explicit newlines or shorter titles for readability. If even a 1 px font cannot
fit the width, or a multiline title at minimum size exceeds the available height around its anchor,
rendering raises `text too long to fit canvas`. Text does not paginate or silently crop.
Circle/radial masks use pixel distances, so their contours are circular in either aspect ratio.
RIFE weights are loaded only for an actual fractional slow-motion sample, never for
stills, unity speed or exact source samples. Missing, empty or invalid models name
the path in a clean error; there is no automatic backend substitution.

## Small depth and 2.5D

`parallax` accepts a retained 16-bit depth PNG (`depth`) or a Small ONNX model.
For RGBA cutouts there is no opaque background to reconstruct: the cutout is translated
once as a foreground layer, in whole pixels and constrained to the canvas. This preserves
the alpha sum exactly and excludes hidden RGB; the cutout path needs no depth inference.
Larger depth values mean nearer. RGB is resized to dimensions divisible by 14,
ImageNet normalized, and passed as pixel_values [1,3,H,W]; predicted_depth is resized
back. `depth_map(..., engine=...)` supports fake engines in offline tests.
Derived maps are SHA256-keyed by image bytes and model path in the specified cache;
changing pixels or the model path invalidates the cache. The layer renderer dilates
the foreground mask and inpaints its background plate before moving the foreground
5x farther than the background. Edge extension avoids holes. Two-layer depth is a
stylization and can simplify thin fins/occlusions; inspect the result.

Only **Depth Anything V2 Small (Apache-2.0)** is supported. Names containing base,
large, vitb or vitl are rejected before loading because those variants are CC-BY-NC.
Missing model/runtime errors suggest beat_bounce/zoom_punch. RIFE is MIT. See
[THIRD_PARTY](../THIRD_PARTY.md). The demo retains only a Small-derived PNG and a
RIFE midpoint with provenance; no ONNX weights or fonts are distributed. Live Small
inference at 480x270 took **1.248s**, including session load, on this machine.

## Round 2 performance measurements

Windows 10, Intel64 Family 6 Model 158, NumPy 2.5.4, OpenCV 5.0.0. Serial median of 10 public float32 RGBA calls, 1280x720, including function boundary copies; model loading excluded. Reproduce: python wow/fx/benchmark_effects.py. CPU scheduling on the shared machine affects timings.

| Operation | ms/frame |
|---|---:|
| flash_white | 27.191 |
| grade | 5.39 |
| halation | 66.96 |
| beat_bounce | 10.584 |
| zoom_punch | 10.189 |
| cutout_card | 268.985 |
| shake | 44.685 |
| rgb_split | 54.155 |
| radial_blur | 110.709 |
| echo | 166.963 |
| film_grain | 39.159 |
| vignette | 41.044 |
| light_leak | 75.107 |
| dust_scratches | 42.522 |
| invert_flash | 31.06 |
| black_flash | 15.078 |
| split_screen | 51.362 |
| mirror | 10.923 |
| kaleidoscope | 111.341 |
| posterize | 41.918 |
| halftone | 134.052 |
| multi_cutout | 406.852 |
| text | 127.128 |
| parallax | 70.721 |
| crossfade | 92.236 |
| whip_pan | 121.042 |
| hex_shutter | 64.327 |
| flash_cut | 36.968 |
| shape_wipe | 107.885 |
| luma_wipe | 106.179 |
| push | 92.828 |
| slide | 91.265 |
| spin | 52.291 |
| zoom_through | 49.432 |
| glitch | 102.674 |
| flow | 300.839 |

Slowest three new operations: radial_blur 787.113 → 110.709 ms, multi_cutout 558.225 → 406.852 ms, parallax 181.474 → 70.721 ms. Premultiply once, warp/accumulate with OpenCV, unpremultiply once. Original versus optimized float32 MAD: radial 1.78e-8, multi 0, parallax 7.00e-10. No resolution or sample-count reduction. Several effects remain above the 50ms target.

python -m cProfile -o wow/fx/profile-after.prof wow/fx/benchmark.py: 90-frame render-loop baseline **3.343 fps / 26.918s**, optimized **10.119 fps / 8.894s**. This includes three effects and a 500ms transition; excludes PNG and video encoding. Renderer uses float32 through the effect chain, OpenCV grade/halation/geometry, and one output quantization. Opaque camera geometry now reflects edges (intentional quality improvement; transparent geometry retains coverage). Profiles and benchmark-before.json/benchmark-latest.json retain evidence.

Preview validation: python wow/fx/check_preview.py generated the original plus all effect/transition tiles in **0.779s**. Every available effect tile passed MAD >=4/255 and >=2% pixels differing by >=16/255; the optional parallax tile explicitly reports unavailable without loading a model. Measured values: [preview-measurements.json](../wow/fx/preview-measurements.json). Procedural luma examples: [linear](../wow/fx/masks/linear.png), [radial](../wow/fx/masks/radial.png), [cloud](../wow/fx/masks/cloud.png).

## P1 experimental captions

P2a fixes the reviewed oversized-word, punctuation, numeric-keyword, spring cut,
typing-caret, emoji-wrapping and busy-background defects. Regression and rendered
evidence are recorded in [P2a build notes](../wow/fx/build-notes-p2a.md).

> **Known limitations after P1b (2026-11-05):** ASR can still misrecognize words;
> SRT/script timing remains approximate. Missing system glyphs still produce an
> explicit drop warning; emoji fallback is monochrome and depends on installed
> fonts/shaping support. Independent cross-vendor review and user spot checks
> remain pending. Fixed integrity, punctuation, camera and preset findings are
> recorded in [P1b evidence](../wow/fx/build-notes-p1b.md).

All four caption presets (`pop`, `typewriter`, `bounce`, `clean`), named camera
moves, layered edit styles, SFX and reframe require `--experimental` or plan
`"experimental": true`. None is promoted to stable: independent cross-vendor
quality review and user spot checks remain pending. Preset status is retained in
the manifest; these are not added to the stable effect table.

```json
{
  "experimental": true,
  "segments": [{"type":"still","image":"shot.png","duration_ms":3000}],
  "captions": {
    "words":"words.json",
    "keywords":["真的嗎"],
    "style": {
      "preset":"pop","font":"C:/Windows/Fonts/msjh.ttc","size":96,
      "stroke":6,"stroke_color":"080808","shadow":4,"shadow_color":"080808",
      "box":"111111","color":"FFFFFF","keyword_color":"FFE45E",
      "entrance":"pop","words_per_line":12,"position":"bottom"
    }
  }
}
```

`words.json` is a list (or `{"words":[...]}`) of
`{"text":"台北市政府","start_ms":600,"end_ms":1000}`. Times are finite,
nonnegative milliseconds with ordered starts and positive durations. Inline lists
also work. Put spaces in the text where desired; English words usually include a
leading space after the first word. Timings can be supplied per character for exact
typewriter timing. Typewriter reveals timed words at their onsets with a pulsing
insertion caret; character timings produce character typing. Words stay visible until
the next line/end. Oversized single words split into grapheme chunks with proportional
display timing, while the exported original word timing stays unchanged.

Alternate inputs: `"srt":"speech.srt"`, `"script":"Hello world","duration_ms":3000`,
or `"audio":"speech.wav","model":"/cached/faster-whisper-model"`. SRT cue boundaries
are preserved; words inside a multiword cue are proportionally timed. Plain script
fallback is also proportional and emits a warning. **Neither fallback is acoustic
forced alignment.** For exact alignment supply corrected word JSON, or inject a
`TimingEngine(audio, script=None)` returning words into `load_words`. The optional
faster-whisper adapter requests word timestamps from a CPU int8 model, two threads,
local-files-only. A missing engine gives `pip install faster-whisper` / `--srt`
guidance. Script mismatches error instead of silently replacing user text.

```sh
python scripts/captions.py --srt words.srt --style pop --experimental --out captions
python scripts/captions.py --audio speech.wav --model /cached/whisper --experimental --out transcript
python scripts/captions.py --audio speech-zh.wav --model small --model-cache /cached/whisper --language zh --traditional --experimental --out transcript-tw
```

The CLI exports editable captions.json and word-level captions.srt. Whisper audio
is decoded by FFmpeg to mono 16 kHz float32 and passed as an array, bypassing the
engine's PyAV decoder. NumPy scalar timestamps are normalized to Python floats;
raw Whisper JSON (`word`, `start`, `end` in seconds) is also accepted as `--words`.
`--model` accepts a CTranslate2 directory, a cache root containing one model,
or a model name plus `--model-cache`. Cache roots with multiple models require a
name; no downloads occur. `--language zh-TW` maps to Whisper's `zh`.
Optional `--traditional` uses `pip install opencc-python-reimplemented`
(OpenCC, Apache-2.0), `s2twp` conversion per timed word, preserving timing. It also
sets a Traditional Chinese initial prompt; the conversion, not the prompt alone,
ensures 畫 rather than 画. A missing OpenCC dependency gives an actionable error.
Plan keys are `model_cache`, `language`, `traditional`. Word-level conversion can
miss phrase context across word boundaries; exported text remains editable.
Tests replay `tests/fixtures/live/whisper-raw-{en,zh}.json` and decode the real TTS
WAVs without loading weights. ASS export and a packaged forced aligner are absent.

Size/stroke/shadow are pixels at 1920 output height, scaled with the canvas.
Position is top/center/bottom. `box:null` disables the box. `safe_zone` optionally
supplies fractional x/y/right/bottom bounds; they intersect P0 platform bounds and
its 2%-width text inset, never relax them. Animated maximum extents are included
when laying out. Text reflows to fit the actual font; oversized tokens first shrink
to about 60%, then split at grapheme boundaries with a warning. Bold system fonts are preferred (Microsoft JhengHei Bold /
Noto CJK Bold); the default is 112 px with 8 px dark stroke. `pop` has yellow
keywords and a mint current word; its 1.22×/180 ms pulse scales only that word.
Earlier words retain their positions and size. `typewriter` now reveals whole
timed words at their onsets with a pulsing caret, yellow current word, mint keywords and dark
box. `clean` is 88 px white text with a 10 px dark stroke, 4 px shadow and dark panel;
`bounce` uses a navy growing box, mint current word, amber keywords and a damped
400 ms entrance. `current_word_color` is separate from `keyword_color` and takes
precedence while the word is current. Boxes grow with revealed text. `current_word:false`
disables active-word emphasis independently of keyword selection. These numeric
properties do not substitute for the pending visual-quality gate.

Input timed words stay atomic when they fit after bounded shrinking. Their glyphs
retain its word ID and onset; no merged-string character search reconstructs
timings. Each line takes its start/end from its own words. A sub-frame word gets
at least one delivered frame (the line's display end may extend to that frame's
end); exported word timings stay unchanged. Simultaneous lines are rendered,
not silently clipped to the next line's onset.

Word text is trimmed and internal whitespace collapsed. Between timed words,
use one ASCII space at Latin/number boundaries (including CJK–Latin/number),
none between CJK words, none before closing punctuation or after opening
punctuation. After closing punctuation, insert a space only before Latin/numbers.
For example: `今天 Ship 了 v2.0，共 1,234 位使用者`.
`language:zh` / `zh-TW` or `traditional:true` also maps sentence punctuation
`, . ! ? : ;` to `，。！？：；`; decimal/version dots and numeric grouping commas
inside `v2.0`, `3.14`, `1,234` stay ASCII, as do punctuation inside `Node.js`,
`e.g.`, URLs and `10:30`. JSON/SRT word text has no edge spaces.

Line limits use fullwidth=1, halfwidth=0.5. A timed word may exceed that logical
limit intact; oversized pixel widths first use uniform reduction down to about 60%,
then grapheme splitting with a warning. Extremely narrow safe zones can require
further shrinking, explicitly warned. Emoji stay attached to the preceding word.
Sentence endings and pauses ≥150 ms
start a new line; singleton tails are rebalanced using whole timed words when
possible. SRT/script interpolation still uses the small `captions.LEXICON`
dictionary and atomic English/number/emoji tokens; it is not a general Chinese
segmenter or acoustic aligner. Automatic keywords are 台北市政府 / 開放資料 / 效果
and complete numeric tokens, including `v2.0`, `1,234` and `3.14`; digits inside
`iPhone15`, `H264` or `10:30` are not picked as numeric keywords. An explicit `keywords` list
replaces the keyword selection; `[]` disables keyword highlights. Set
`current_word:false` as well to disable active-word emphasis.

Unicode cmap 4/12 coverage is read without fontTools. The renderer tries installed
Segoe UI Emoji / Noto Emoji for missing primary-font graphemes. On Windows builds
without Pillow libraqm, cached Uniscribe masks join skin-tone/ZWJ sequences into
one monochrome glyph; modifiers are not painted as separate squares. Fonts and
emoji artwork are not bundled. Unsupported graphemes are
dropped as whole units, with a warning listing their `U+XXXX` code points and
`dropped_codepoints` in the manifest. This includes unsupported emoji: no tofu or
partial ZWJ/skin-tone sequence is drawn and the render continues, even if all
text is dropped. Original text/timing remains in the word export. The resolved
font path is recorded; fonts are not bundled.

With SFX enabled, caption pops accent phrase starts: at least 1500 ms between
selected line onsets and never on adjacent lines. This is independent of the
per-word visual pop animation; it does not add audio to every line or word.

## P1 named camera vocabulary (experimental)

Call a move in effects as `{"move":"crash_in","start_ms":500}`; equivalent to
`{"name":"camera_move","move":"crash_in"}`. Unknown names list valid choices.
`duration_ms:0` and `target:0` select table defaults, except `crash_out` uses the
shorter of 600 ms and its effect interval (minimum 300 ms). Optional direction is
left/right/up/down; anchor is center or subject (alpha centroid, center fallback
for fully opaque source). Keep `end_ms` long enough to include the movement.
Truncated whip/crash_out intervals are rejected before rendering, because they cannot land
back on the original framing.

| Move | Target | Default duration | Easing | Use |
| --- | --- | --- | --- | --- |
| crash_in | 1 → 1.35 scale | 100 ms | easeOutExpo | fast emphasis |
| crash_out | 1 → 1.35 → 1 scale | 600 ms (minimum 300 ms) | 40% easeInOutCubic preparation, 60% easeOutCubic reveal | continuous preparation and return |
| expo_in | 1 → 1.30 scale | 800 ms | easeInExpo | accelerating push |
| smooth_in | 1 → 1.20 scale | 1000 ms | easeInOutCubic | restrained push |
| whip | 0 → 0.85 → 0 frame widths/heights | 160 ms | sine-squared excursion | directional whip returning to original framing |
| punch | 1 → 1.18 → 1 scale | 200 ms | sine-squared pulse | beat impact |
| drift | 1 → 1.08 scale, 4% pan | 2000 ms | easeInOutSine | slow motion |
| spring_in | 1 → 1.20 with overshoot | physical seconds | analytic spring | elastic settle |

Penner equations are attributed in source and THIRD_PARTY. Spring is an original
analytic unit-step oscillator, parameters stiffness=180, damping=18, mass=1;
critical and overdamped cases are supported. `duration_ms` does not rescale spring
physics; actual seconds and those physical parameters determine settling.
Opaque zoom borders reflect, transparent imagery uses premultiplied alpha. Whip
uses edge extension and motion-axis blur during its excursion; its first and last
frames are exact originals. To land on another shot use the `whip_pan` transition.
Whip whoosh peak aligns to the maximum delivered frame displacement.
The default crash_out target/duration changes scale by at most 0.16 per frame
at 24/25/30/60 fps (measured maximum 0.13737); explicit targets/durations alter
that bound. QA uses the manifest's named move start, effect end, motion end and
zoom/pan peaks, within one median frame, to exclude intentional camera events
from rhythm and flash scoring. Spring's initial travel through its first physical
peak is also excluded from cut detection; later settling is not broadly exempted.
A white/exposure flash is never exempted just because it coincides with a camera event;
planned shot cuts still win in rhythm scoring. Excluded flash events remain
auditable under `flashes.excluded_camera_events`.

## P2a default gate kit

`python scripts/fx_gate_kit.py --out <outside-repo-directory> [--items light_leak spin]`
renders every stable and experimental registry item with catalog visual defaults.
Omitting `--out` selects a new OS temporary directory. Each item has four 2-second,
24 fps MP4s: repo photographic-looking footage and an RGBA matte, at 480×270 and
270×480, with the same 120 BPM accent; a contact sheet and HTML index link the clips.
RGBA is checked before compositing onto a checkerboard for MP4 viewing.
`gate-auto.json` records full-sequence repeated SHA256, alpha and hidden-RGB probes,
border-gradient seam/stretch heuristics, decoded `qa_media` flicker, visible black
frames, and ten warm 1280×720 float32 call timings. Errors and heuristic flags remain
visible, including intentional black/white flashes. These are measurements, not an
aesthetic score or a promotion decision. Two independent reviewers are still required.
Alpha range/shape/finite checks cover all frames; colour-only effects additionally
retain alpha exactly. Opaque coverage and hidden-RGB probes use frames 0, 24 and 47.
The benchmark uses opaque footage except `multi_cutout`, whose active RGBA path is
measured; the opaque path intentionally warns and returns unchanged.
The tool runs serially and enforces a 300 MB output cap. Use the optional runtime and
`--models <existing-model-directory>` for opaque parallax; the only parameter overrides
are model/cache resource paths, recorded in JSON. No models are downloaded or copied.

## P1 subject-following portrait reframe (experimental)

```json
{"experimental":true,"reframe":{"masks":"subject/manifest.json"}}
```

Combine with `--platform tiktok` (or another 9:16 preset); this renders at the
platform size/fps. Masks must match the source canvas and **edited timeline**,
not an untrimmed source clock. Supply a manifest with positive `durations_ms` and
`masks:["mask-000.png",...]`, or RGBA frames beside the manifest produced by
`background_remove.py --model birefnet-general` / `birefnet-portrait`. Existing
cached masks are read; no model is imported by reframe. A standalone adapter is:

```sh
python scripts/reframe.py prepared/frames --manifest prepared/manifest.json --masks subject/manifest.json --experimental --out portrait
```

The standalone adapter writes prepared PNGs with 10 ms-grid exposures (30/40 ms
alternation at 30 fps), compatible with compose_timeline. Final video delivery
uses P0's CFR clock. The direct plan-integrated path renders straight onto that
CFR grid without this intermediate exposure quantization.

The crop is the largest 9:16 rectangle entirely inside the source; no black
padding is introduced. The path uses symmetric lookahead smoothing, an 8 output
pixels/frame comfort speed that grows to 1.15× nearby measured subject speed,
and a 3 pixels/frame² acceleration target. Projection into the feasible subject
coverage interval and source bounds takes priority over those comfort limits.
Impossible fits preserve the head, cut feet if necessary and set `needs_review`.
Missing subjects use a center target and are listed. Every crop and transformed
bbox is recorded. Captions still intersect the 64–79% title band; tall subjects
may overlap that band, so this does not claim the complete S-61 title/subject or
fixed-speed acceptance gate. Real V-WALK and independent visual review remain open.

## P1 proxy review and changed-shot rendering

```sh
python scripts/fx_render.py plan.json --review-html --experimental --out review-a
# Open review-a/review.html locally, choose Keep/Replace, enter replacement JSON,
# save decisions.json. Replacement paths resolve relative to the ORIGINAL plan.
python scripts/fx_render.py plan.json --review-html --experimental --previous review-a --decisions decisions.json --out review-b
# Encode the already rendered silent proxy pixels:
python scripts/fx_render.py review-b/render-plan.json --formats mp4 --out review-movie
```

Alternatively use `review_shots.py`; `--full` builds/rebuilds full-resolution cached
shots with the same decisions. New output directories are required. The page is
fully offline, has one image per recorded shot-start/effect/caption event, and
downloads `{"version":1,"shots":{"2":{"action":"replace","segment":{"image":"new.png"}},"5":{"action":"replace","effects":[{"move":"punch"}]}}}`.
Indices are zero-based. Keep/replace controls for duplicate events in one shot stay
synchronized. Replace without replacement data errors; it never silently reuses
the same content as a pretend replacement.

Cache keys include effective shot parameters, dependency content hashes, renderer
and FX source hashes, and proxy/full mode. Cached PNGs are verified by SHA256 before
reuse; unchanged shots retain identical PNG bytes. Immutable PNG cache files use
hardlinks when supported, with a copy fallback. Do not edit rendered PNGs in place;
replace the source and rebuild. Changed effects/assets and
renderer code invalidate their dependencies. The report gives rerendered/reused
counts. Proxy assets are resized before effects. Cross-shot transitions, history,
previous-frame references and reframe are rejected because they need neighboring
dependency invalidation; use normal rendering for those plans. Audio is not part
of the preview cache; apply final soundtrack/audio delivery separately. Duration
changes shift subsequent event times but do **not** automatically snap them back
to beats; that optional acceptance item remains open. This is an independent-shot
workflow, not a general NLE cache.


## P2b gl-transitions (experimental)

32 CPU ports are available only with `--experimental` or plan
`"experimental": true`. Use the registry names below on the incoming segment,
for example `{"name":"gl_curved_wipe","duration_ms":400}`. They remain
experimental pending independent visual comparison and user spot checks. A
technical test pass or a generated gate kit is not a promotion decision.

Each port lives in its own `scripts/fx/transitions/gl_*.py`, exposing
`transition(a,b,p,ctx,**params)` through the registry decorator. The prefix avoids
collisions with existing transitions. Scalar/vector names and defaults match
the supplied GLSL; vectors/colors are JSON arrays in plans (Python tuples in
direct calls), bools are JSON true/false. Colors are float 0..1. GLSL integer
parameters are integer-valued numbers; `steps<=0` disables stepping where the
shader supports it. `--list --experimental --json` includes the original
parameter explanations and `@range` annotations. No shader compiler, GPU,
external texture, model, or network is needed at runtime.

UVs are bottom-up, sampled at pixel centers through `cv2.remap`, using bilinear
CLAMP_TO_EDGE or `ctx.sampling='nearest'`. Frames are never resized to square.
Rotations and radial distances use frame-height units; square/dot/noise grids
also use that metric so their cells remain square. Grid counts originally
expressed per normalized width are consequently counts per frame height on
non-square canvases, except `horizontalHexagons`, which retains upstream's
width-based hex metric. Directional wipe coverage still spans the full frame.
These aspect corrections intentionally differ from legacy square-UV shaders.
Intentional nonlinear warps, pixelation and directional scaling remain visible;
"no stretching" does not promise that a distortion effect preserves every shape.

All sampling, blending, color thresholds and additive light use premultiplied
RGBA. RGB is clamped to valid premultiplied coverage, then unpremultiplied once.
S-63's original-union matte rule is enforced: if BOTH original inputs have zero
alpha at an output pixel, it stays zero, even when a warp would transport a
subject there. This can crop moved silhouettes; it deliberately differs from
unrestricted GLSL coverage. Colored backgrounds and shadows do not create
coverage outside that union. Exact p=0/1 guards preserve input hidden RGB as
well as visible pixels; intermediate hidden RGB cannot influence output.
Bounce composites the moving panel over the incoming shot so a transparent
panel reveals the subject beneath it; selecting transparent panel pixels alone
can erase a sparse portrait matte. Opaque Bounce output is unchanged.

Random fields use `ctx.seed` in addition to original shader seed parameters;
seed=0 preserves the original hash expression, evaluated in float64 before
float32 conversion for deterministic CPU results. GLSL implementation-specific
noise pixels can differ. GlitchMemories uses deterministic progress arithmetic,
not random numbers. DreamyZoom retains the source's literal 0.039269908...
rotation multiplier, despite its misleading DEG2RAD comment. Source defaults,
authors and SHA256 are retained in `wow/fx/p2b-provenance.json`.

Documented global MAD monotonicity exceptions: `gl_dreamy_zoom` (white flash),
`gl_overexposure` (exposure peak), `gl_rotate_scale_fade` (full rotating zoom),
`gl_swirl` (spatially varying rotation). These still end exactly at B and have
lower final-quarter than initial-quarter MAD. All other ports meet Spearman
<= -0.8 on the 21-point fixture; Bounce and Pinwheel can still reverse locally.

BurnThrough and PerlinDissolve cache only immutable static noise fields (two
dimension/parameter/seed keys each); the shared UV grid caches four sizes.
LuminanceMelt evaluates its one-dimensional simplex noise on one row and
broadcasts without changing its formula. Cache keys contain no image content;
no random global state or source-frame cache is used. Timings include public
conversion and alpha handling; cold-start timings are recorded separately.

| Registry name | Original shader parameters / defaults |
| --- | --- |
| `gl_clock_wipe` | `startingAngle=90.0` |
| `gl_cross_warp` | none |
| `gl_directional_warp` | `smoothness=0.1`; `direction=[-1.0, 1.0]` |
| `gl_dreamy` | none |
| `gl_dreamy_zoom` | `rotation=6.0`; `scale=1.2` |
| `gl_rotate_scale_fade` | `center=[0.5, 0.5]`; `rotations=1.0`; `scale=8.0`; `backColor=[0.15, 0.15, 0.15, 1.0]` |
| `gl_swirl` | none |
| `gl_water_drop` | `amplitude=30.0`; `speed=30.0` |
| `gl_burn_through` | `burnColor=[1.0, 0.5, 0.0]` |
| `gl_overexposure` | `strength=0.6` |
| `gl_fade_grayscale` | `intensity=0.3` |
| `gl_color_distance` | `power=5.0` |
| `gl_luminance_melt` | `direction=true`; `l_threshold=0.8`; `above=false` |
| `gl_pixelize` | `squaresMin=[20, 20]`; `steps=50` |
| `gl_dither_dissolve` | `dotSize=0.02` |
| `gl_random_squares` | `size=[10, 10]`; `smoothness=0.5` |
| `gl_window_slices` | `count=10.0`; `smoothness=0.5` |
| `gl_wind` | `size=0.2`; `reversed=false` |
| `gl_pinwheel` | `speed=2.0` |
| `gl_polka_dots_curtain` | `dots=20.0`; `center=[0.0, 0.0]` |
| `gl_crosshatch` | `center=[0.5, 0.5]`; `threshold=3.0`; `fadeEdge=0.1` |
| `gl_perlin_dissolve` | `scale=4.0`; `smoothness=0.01`; `seed=12.9898` |
| `gl_glitch_memories` | none |
| `gl_scale_in` | none |
| `gl_bounce` | `shadow_colour=[0.0, 0.0, 0.0, 0.6]`; `shadow_height=0.075`; `bounces=3.0` |
| `gl_multiply_blend` | none |
| `gl_color_phase` | `fromStep=[0.0, 0.2, 0.4, 0.0]`; `toStep=[0.6, 0.8, 1.0, 1.0]` |
| `gl_hexagonalize` | `steps=50`; `horizontalHexagons=20.0` |
| `gl_squares_wipe` | `squares=[10, 10]`; `direction=[1.0, -0.5]`; `smoothness=1.6` |
| `gl_bow_tie_horizontal` | none |
| `gl_curved_wipe` | `direction=[0.0, 1.0]`; `curvature=0.6`; `smoothness=0.02`; `shadow=[0.0, 0.0, 0.0, 0.4]` |
| `gl_arrow_wipe` | `direction=[1.0, 0.0]`; `notch=0.4`; `width=80.0`; `count=1`; `origin=false`; `smoothness=0.004` |

Reproduce measurements with `python wow/fx/benchmark_p2b.py` and the complete
new review kit with `python scripts/fx_gate_kit.py --gl-transitions --out
<new-directory-outside-repo>` (put the command on one line). Omitting the filter
still renders all registry items, including these ports. Gate artifacts are
outside the repository; JSON measurements and exact commands are linked from
[P2b build notes](../wow/fx/build-notes-p2b.md). Full selection/exclusion rationale,
all 161 unselected authors, timing methodology and outstanding visual review
are recorded there. No ffmpeg xfade fast path is introduced.
