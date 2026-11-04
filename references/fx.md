# Explicit post-production effects

Use this route only when the user asks for post-production effects. Effects never
substitute for physical character motion, invent a jump, or hide a broken source join.
Prepare the source with `gif_pipeline.py`; retain the source animation and its alpha.

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

## Builtins

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
increase coverage and may crop; choose bounds deliberately. The default small transparent
punch is subtle; it does not meet the stronger 5% stripe-growth target in S-2.

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
Edits follow the existing nearest-10ms rule. The renderer defaults to 25 fps; 1..50 is
accepted, with exposures quantized to the exporter's 10ms grid. Beat peaks and edit
boundaries are inserted on that grid so they cannot be skipped by nominal frame sampling.
On an inserted beat frame, evaluate its beat envelope at the exact unrounded beat peak.
Thus output exposures may be variable, including 10ms accents. Video exporters retain
the exact timeline as repeated frames at 100 fps; no motion interpolation is added.
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
Segment duration_ms must be a multiple of 10. Transitions must last at least one requested
output frame. Downbeats must coincide with actual beats (1ms integer-rounding tolerance).
Nearest/pixel sampling warns when crossfade, whip_pan or flash_cut blends new colours.

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
the fixture is explicitly synthetic, not a claim of live model measurement.
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
The composer and this bounded renderer retain frames in memory; use short timelines.

The automatic QA's --expect-cuts checks **hard image discontinuities**, so smooth effects
and a still-to-animation continuation should use --timeline as editorial joins instead.
Do not falsely label that a hard-cut detector passing a transition test. Exact beat peaks
are separately measured from decoded MP4 luminance. The strict acceptance request that
all transition centers pass --expect-cuts remains a known semantic mismatch.
