# P2b — gl-transitions CPU ports

Date: 2026-11-05. Worktree: `C:/Users/User/src/vgs-fx`, branch `p2-gate`.
Base HEAD: `37a4eb5de5d143a1cb14d6a3ebd602f84fd47adf`; changes are uncommitted.
32 of 193 supplied shaders ported; 161 deliberately not selected. Every port
is EXPERIMENTAL, hidden from the default stable catalog. No commit/push, no
upstream-source or installed-skill edits, and no new media artifacts added here.

## Selection

The set favors distinct, readable short-form edits: directional/curved/arrow
wipes; staggered zooms; rotation; gentle waves, swirl and water; exposure and
burn; pixel, hex, dither and chromatic glitch; multi-aperture patterns; source
color/luminance ordering. Existing crossfade/push/slide/whip/spin/iris/luma
coverage was considered before adding a port. Heavy multi-tap blur, extra
texture dependencies and perspective scenes needing a different coverage
contract were excluded. This is a CPU-port selection, not a claim that every
shader is visually approved or realtime at 720p.

| Port | Selection rationale |
| --- | --- |
| `gl_clock_wipe` | Angular clock reveal; no existing angular mask. |
| `gl_cross_warp` | Spatially staggered zoom exchange, unlike a midpoint zoom cut. |
| `gl_directional_warp` | Directional collapsing seam; adds configurable diagonal motion. |
| `gl_dreamy` | Gentle vertical wave dissolve for restrained edits. |
| `gl_dreamy_zoom` | Combined flash/rotation/zoom, distinct from pure flash_cut or spin. |
| `gl_rotate_scale_fade` | Full-turn spinning zoom dissolve with background; more graphic than spin cut. |
| `gl_swirl` | Radially varying rotation; no existing vortex transition. |
| `gl_water_drop` | Bounded expanding ripple front; selected over the near-duplicate Ripple. |
| `gl_burn_through` | Four-octave glowing burn contour; modest CPU cost versus FilmBurn. |
| `gl_overexposure` | Exposure-weighted dissolve retains image structure through a flash. |
| `gl_fade_grayscale` | Desaturated bridge for tonal or time changes. |
| `gl_color_distance` | Image-dependent color-distance reveal; complements mask-based luma_wipe. |
| `gl_luminance_melt` | Brightness-qualified melting streaks; uses source luminance, not an external mask. |
| `gl_pixelize` | Stepped square pixelation bridge for retro and punch edits. |
| `gl_dither_dissolve` | Ordered Bayer dots, visibly distinct from random block dissolve. |
| `gl_random_squares` | Soft randomly timed grid reveal, suitable for beat-driven edits. |
| `gl_window_slices` | Sweeping vertical slats; stronger rhythm than a single wipe. |
| `gl_wind` | Ragged horizontal edge without spatial displacement of the shots. |
| `gl_pinwheel` | Multiple rotating radial blades; intentionally locally reversing reveal. |
| `gl_polka_dots_curtain` | Origin-driven expanding dot curtain; not a single circular iris. |
| `gl_crosshatch` | Intersecting randomized line reveal; complements solid grids. |
| `gl_perlin_dissolve` | Smooth organic noise dissolve for unobtrusive texture transitions. |
| `gl_glitch_memories` | Channel-offset dissolve; existing glitch is a hard block-displacement cut. |
| `gl_scale_in` | Incoming image alone zooms into place over a stationary outgoing image. |
| `gl_bounce` | Bouncing falling panel with contact shadow; deliberate nonmonotonic motion. |
| `gl_multiply_blend` | Dark multiply bridge rather than a plain dissolve or black flash. |
| `gl_color_phase` | Staggered channel timing for stylized color shifts without motion. |
| `gl_hexagonalize` | Hexagonal sampling cells; unrelated to the existing six-sided shutter. |
| `gl_squares_wipe` | Growing square apertures with a directional sweep, not random switch times. |
| `gl_bow_tie_horizontal` | Two opposed triangular reveals, distinct from centered shape_wipe. |
| `gl_curved_wipe` | Bowed lifting edge with alpha-aware shadow; adds organic directional motion. |
| `gl_arrow_wipe` | Flying notched chevrons with an expanding reveal; graphic short-form accent. |

## Implementation and deviations

The [runtime contract and complete parameter table](../../references/fx.md#p2b-gl-transitions-experimental)
describe sampling, alpha, aspect, seed and endpoint behavior. Each source file
credits the exact original author/license/path and source SHA256. All selected
shaders are MIT; [THIRD_PARTY.md](../../THIRD_PARTY.md) retains the upstream
notice, every selected author and nested noise credits. The two BSD shaders
were excluded. Nothing is downloaded. The original read-only source is
`C:/Users/User/src/vgs-fx-private/third_party/gl-transitions/transitions`.

This is not a byte-identical GLSL emulator: aspect corrections, associated-alpha
blending/thresholds, S-63 original-union matte clipping, deterministic float64
hash evaluation, and saturation at valid alpha are intentional adaptations.
Bounce additionally composites its moving panel over the incoming matte; opaque
output remains byte-identical. This fixes an empty portrait-matte frame found
in the first gate run. A 48-progress sparse-portrait regression covers it.
CLAMP_TO_EDGE matches the texture boundary policy and can produce edge streaks
under strong warps; gate flags remain visible. Hidden RGB tests compare poisoned
and zeroed transparent inputs, a stricter direct test of influence than looking
only for an exact garbage color. No GPU reference PSNR claim is made. Independent
hand-derived landmarks check Bayer occupancy, center zoom blending, grayscale
luma, equal-color distance and multiply; they do not establish full shader parity.

## Validation

- Baseline: `python -m unittest discover -s tests`: 350 tests, 0 failures,
  2 environment errors, 5 skips (217.904 s). See `tests-p2b-baseline.log`.
- New suite: `python -m unittest discover -s tests -p test_gl_transitions.py`:
  165 tests pass (13.507 s after the Bounce fix). All 32 ports independently test exact 640x360 endpoints in
  uint8 and float32; matte poisoning/opaque coverage at p=.25/.5/.75;
  repeated SHA256 and seed changes for random ports; 321x181, 1000x100 and
  181x321 shape/dtype/finite/quantization; 21-point MAD/Spearman.
- Additional tests check original defaults/credits, stable visibility, UV pixel
  centers/edge clamp, and radial circles' pixel-axis ratio within 3% for uniform
  zoom/rotation and swirl on odd, portrait and 10:1 canvases. Deliberate nonlinear
  deformations are not mislabeled as circle-preserving geometry.
- The benchmark additionally checks every port at p=.5 on 1920x1080 and
  1080x1920: correct shape, finite values, range and opaque alpha. All pass.
- Full post-change suite: 515 tests in 231.028 s, **0 failures, same 2 environment errors,
  5 skips**. No new failures/errors versus baseline. The two errors are
  Windows symlink privilege (WinError 1314) and the existing locked
  `overlay.png` cleanup (WinError 32). See [tests-p2b-full.log](tests-p2b-full.log)..
- Heavy work runs serially: baseline, targeted tests, benchmark, gate clips,
  final suite. No parallel encoders or benchmark/test processes.

## 720p measurements

`python wow/fx/benchmark_p2b.py` uses opaque procedural A/B (seeds 1 and 2),
Context seed 19, 1280x720 float32. Median of 15 public calls, five each at
p=.25/.5/.75 after warmup. Includes conversion, premultiplication, sampling,
finish and dtype restore; excludes decode/encode. Cold column is first call
for this port at 720p (shared runtime/grid may already be warm). Machine,
Python, NumPy, OpenCV/thread count, individual samples, checks and hashes:
[benchmark-p2b.json](benchmark-p2b.json). This is measured CPU time, not a
30fps/realtime claim. Full-HD smoke checks are not timed in the median.

| Port | Warm median ms/frame | Cold call ms | Spearman MAD to B | Gate |
| --- | ---: | ---: | ---: | --- |
| `gl_clock_wipe` | 139.000 | 145.522 | -1.0000 | passes <= -0.8 |
| `gl_cross_warp` | 171.374 | 157.867 | -1.0000 | passes <= -0.8 |
| `gl_directional_warp` | 171.248 | 161.882 | -1.0000 | passes <= -0.8 |
| `gl_dreamy` | 132.796 | 124.514 | -1.0000 | passes <= -0.8 |
| `gl_dreamy_zoom` | 142.893 | 163.574 | -0.0688 | documented nonmonotonic |
| `gl_rotate_scale_fade` | 185.042 | 196.482 | -0.2636 | documented nonmonotonic |
| `gl_swirl` | 169.607 | 155.072 | -0.3688 | documented nonmonotonic |
| `gl_water_drop` | 154.008 | 164.124 | -1.0000 | passes <= -0.8 |
| `gl_burn_through` | 167.012 | 799.100 | -0.9925 | passes <= -0.8 |
| `gl_overexposure` | 122.289 | 134.809 | -0.4221 | documented nonmonotonic |
| `gl_fade_grayscale` | 152.886 | 155.496 | -1.0000 | passes <= -0.8 |
| `gl_color_distance` | 144.399 | 160.920 | -1.0000 | passes <= -0.8 |
| `gl_luminance_melt` | 131.825 | 134.881 | -1.0000 | passes <= -0.8 |
| `gl_pixelize` | 150.566 | 161.696 | -0.9091 | passes <= -0.8 |
| `gl_dither_dissolve` | 184.962 | 215.045 | -1.0000 | passes <= -0.8 |
| `gl_random_squares` | 158.506 | 154.303 | -1.0000 | passes <= -0.8 |
| `gl_window_slices` | 133.071 | 125.841 | -0.9994 | passes <= -0.8 |
| `gl_wind` | 147.223 | 167.199 | -1.0000 | passes <= -0.8 |
| `gl_pinwheel` | 157.857 | 156.413 | -0.9935 | passes <= -0.8 |
| `gl_polka_dots_curtain` | 142.996 | 138.280 | -1.0000 | passes <= -0.8 |
| `gl_crosshatch` | 177.726 | 173.216 | -0.9997 | passes <= -0.8 |
| `gl_perlin_dissolve` | 123.035 | 414.987 | -1.0000 | passes <= -0.8 |
| `gl_glitch_memories` | 345.097 | 323.733 | -0.8065 | passes <= -0.8 |
| `gl_scale_in` | 108.520 | 107.574 | -0.8922 | passes <= -0.8 |
| `gl_bounce` | 213.395 | 208.595 | -0.8532 | passes <= -0.8 |
| `gl_multiply_blend` | 96.851 | 114.085 | -0.9909 | passes <= -0.8 |
| `gl_color_phase` | 99.513 | 101.300 | -1.0000 | passes <= -0.8 |
| `gl_hexagonalize` | 221.998 | 233.500 | -0.9351 | passes <= -0.8 |
| `gl_squares_wipe` | 150.804 | 140.607 | -0.9987 | passes <= -0.8 |
| `gl_bow_tie_horizontal` | 145.885 | 147.509 | -1.0000 | passes <= -0.8 |
| `gl_curved_wipe` | 309.097 | 311.157 | -1.0000 | passes <= -0.8 |
| `gl_arrow_wipe` | 169.097 | 165.837 | -1.0000 | passes <= -0.8 |

Four named monotonicity exceptions are deliberate flash/rotation behavior;
every port still has exact B at p=1 and lower mean MAD over the last five samples
than the first five. Local reversal in Bounce/Pinwheel does not fail the overall
rank gate. Noise-field caching and one-row simplex evaluation preserve all 32
benchmark p=.75 output SHA256 values exactly relative to the unoptimized run
([benchmark-p2b-before.json](benchmark-p2b-before.json)).

## Review kit and remaining gate

Command (with the supplied ffmpeg directory on PATH):

```powershell
& 'C:/Users/User/.codex/skills/video-gif-studio/.venv/Scripts/python.exe' scripts/fx_gate_kit.py --gl-transitions --out C:/Users/User/AppData/Local/Temp/vgs-fx-p2b-gate-20261105
```

Completed with exit 0: **32 items, 128 current clips**, 32 contact sheets and an
HTML index. Each item has four material/aspect cases (opaque/RGBA, 480x270 and
270x480), 48 frames at 24fps. The index is outside the repository:
`C:/Users/User/AppData/Local/Temp/vgs-fx-p2b-gate-20261105/index.html`.
[gate-p2b.json](gate-p2b.json) retains complete measurements, hashes, per-case
flags, timing samples, source provenance and artifact root. The directory is
temporary; copy it externally if long-term retention is needed.

The initial Bounce portrait RGBA clip had a fully transparent frame. The
premultiplied-over fix passes a 48-progress sparse-matte regression; rerunning
`--items gl_bounce --out C:/Users/User/AppData/Local/Temp/vgs-fx-p2b-bounce-20261105`
produced four passing replacements. The aggregate index/report now uses those
clips. Original clips remain at `C:/Users/User/AppData/Local/Temp/vgs-fx-p2b-bounce-initial-20261105`;
the original report and old Bounce measurements remain in `gate-auto-initial.json`
and the final JSON's `revisions` entry. The interrupted full regression run was
restarted after the fix. Opaque benchmark output hash remained unchanged;
[benchmark-p2b-bounce.json](benchmark-p2b-bounce.json) records the remeasurement.

Recorded external output: 23,103,129 bytes (under 300 MB).
All 128 final cases PASS alpha/hidden-RGB, determinism, black-frame and flicker checks.
Edge warnings retained for independent review:

- transition:gl_pixelize / opaque [480, 270] / edges: WARN
- transition:gl_pixelize / opaque [270, 480] / edges: WARN
- transition:gl_glitch_memories / opaque [480, 270] / edges: WARN
- transition:gl_glitch_memories / opaque [270, 480] / edges: WARN
- transition:gl_bounce / opaque [270, 480] / edges: WARN
- transition:gl_hexagonalize / opaque [480, 270] / edges: WARN
- transition:gl_hexagonalize / opaque [270, 480] / edges: WARN

Block sampling and displaced boundaries are intentional; warnings are not suppressed.
Builder spot inspection covered CrossWarp, DirectionalWarp, DreamyZoom,
BurnThrough and corrected Bounce contact sheets. This is not an independent aesthetic review.


Technical tests and clips are evidence for later review, not approval. Independent
cross-vendor comparisons and user spot checks remain pending under process.md.
All 32 remain experimental; none is promoted to stable and the stable catalog
is unchanged. Flash/black/edge heuristics are recorded, never silently exempted.

## Not selected (161 / 193)

This is a selection deferral list, not a claim that unported shaders are broken
or cannot ever run on a CPU. Exact author strings are from the supplied headers.

| Original shader | Author | Reason not selected |
| --- | --- | --- |
| `Accordion.glsl` | gre | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `ApertureWipe.glsl` | gre | Shape-mask family already broad; selected ArrowWipe/BowTieHorizontal add more distinct compositions than another centered aperture. |
| `Ascii.glsl` | gre | Text-mode rendering is a separate stylization; dither/pixel ports provide retro edits without another glyph-pattern renderer. |
| `BlockCover.glsl` | gre | Grid/tile family represented by SquaresWipe, RandomSquares, DitherDissolve and Hexagonalize; defer choreography variants. |
| `BlockDissolve.glsl` | nwoeanhinnogaehr | Random reveal family represented by RandomSquares and PerlinDissolve; defer additional grain/cell scales. |
| `BlockSlide.glsl` | gre | Grid/tile family represented by SquaresWipe, RandomSquares, DitherDissolve and Hexagonalize; defer choreography variants. |
| `BloomDissolve.glsl` | gre | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `BokehDissolve.glsl` | gre | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `BookFlip.glsl` | hong | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `BowTie.glsl` | KMojek | Orientation/variant of selected BowTieHorizontal; keep one opposed-triangle reveal. |
| `BowTieVertical.glsl` | huynx | Orientation/variant of selected BowTieHorizontal; keep one opposed-triangle reveal. |
| `Box.glsl` | lql | Shape-mask family already broad; selected ArrowWipe/BowTieHorizontal add more distinct compositions than another centered aperture. |
| `BrushWipe.glsl` | gre | Organic reveal/distortion family represented by PerlinDissolve, BurnThrough, Dreamy and WaterDrop; avoid several similar noise-front variants. |
| `ButterflyWaveScrawler.glsl` | mandubian | Additional lens/psychedelic deformation; prioritize the more restrained Dreamy and readable WaterDrop/Swirl for short edits. |
| `CameraShake.glsl` | gre | Motion accent overlaps existing camera vocabulary/whip_pan; no extra shake or blur variants in this batch. |
| `CardSwipe.glsl` | gre | Layered card/pop composition overlaps existing cutout_card and zoom vocabulary; prioritize general two-shot transitions. |
| `CellDissolve.glsl` | gre | Random reveal family represented by RandomSquares and PerlinDissolve; defer additional grain/cell scales. |
| `Chessboard.glsl` | lql | Grid/tile family represented by SquaresWipe, RandomSquares, DitherDissolve and Hexagonalize; defer choreography variants. |
| `CircleIris.glsl` | Fernando Kuteken | Existing shape_wipe covers this shape/iris family; retain one implementation. |
| `CircleOpen.glsl` | gre | Existing shape_wipe covers this shape/iris family; retain one implementation. |
| `ColorCoords.glsl` | haiyoucuv | Additional lens/psychedelic deformation; prioritize the more restrained Dreamy and readable WaterDrop/Swirl for short edits. |
| `ColorPanelWipe.glsl` | gre | Grid/tile family represented by SquaresWipe, RandomSquares, DitherDissolve and Hexagonalize; defer choreography variants. |
| `ColorWrap.glsl` | Yoni Maltsman @friendlyspinach | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `Comb.glsl` | gre | Stripe/split family represented by WindowSlices; extra orientations or shadow variations do not justify another port here. |
| `CrazyParametricFun.glsl` | mandubian | Additional lens/psychedelic deformation; prioritize the more restrained Dreamy and readable WaterDrop/Swirl for short edits. |
| `CrossZoom.glsl` | rectalogic | 41 paired samples per pixel; CPU remap cost is high and reducing taps would change the shader. Use CrossWarp. |
| `Crumple.glsl` | gre | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `Cube.glsl` | gre | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `Curtains.glsl` | gre | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `CylinderRoll.glsl` | gre | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `DefocusBlur.glsl` | Sergey Kosarevsky | 13 paired Poisson taps; more CPU sampling than this slice targets. Do not substitute a Gaussian and call it the same port. |
| `DiamondWipe.glsl` | gre | Existing shape_wipe covers this shape/iris family; retain one implementation. |
| `Directional.glsl` | Gaëtan Renaudeau | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `DirectionalEased.glsl` | Max Plotnikov | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `DirectionalScaled.glsl` | Thibaut Foussard | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `DirectionalWipe.glsl` | gre | Plain directional mask already expressible by luma_wipe; prioritize CurvedWipe and Wind. |
| `Disintegrate.glsl` | gre | Fragment/tile scene construction needs separate edge/coverage review; selected Pixelize/Hexagonalize cover simpler mosaic edits. |
| `DisplacementMap.glsl` | Travis Fischer | Requires an extra displacement texture and asset contract; this slice accepts only A/B and scalar/vector parameters. |
| `DoomMelt.glsl` | Zeh Fernando | Second column-melt variant; selected LuminanceMelt adds image-dependent brightness ordering. |
| `Doorway.glsl` | gre | Shader creates uncovered canvas during the flip/doors, conflicting with S-63 opaque-in/opaque-out without a new background policy. |
| `EdgeGlow.glsl` | Woohyun Kim | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `EyeBlink.glsl` | gre | Another closing/opening aperture; existing hex_shutter and shape_wipe cover this edit role. |
| `Fade.glsl` | gre | Already covered by stable crossfade; no new editing vocabulary. |
| `FadeColor.glsl` | gre | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `FallOver.glsl` | gre | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `FilmBurn.glsl` | Anastasia Dunbar | 50 paired blur samples plus 13 light accumulations; select four-octave BurnThrough and Overexposure instead. |
| `FilmDissolve.glsl` | gre | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `FilmStrip.glsl` | gre | Motion accent overlaps existing camera vocabulary/whip_pan; no extra shake or blur variants in this batch. |
| `Fisheye.glsl` | gre | Additional lens/psychedelic deformation; prioritize the more restrained Dreamy and readable WaterDrop/Swirl for short edits. |
| `FlameWipe.glsl` | gre | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `FlashFade.glsl` | gre | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `FlowerWipe.glsl` | Fernando Kuteken | Shape-mask family already broad; selected ArrowWipe/BowTieHorizontal add more distinct compositions than another centered aperture. |
| `FlyEye.glsl` | gre | Additional lens/psychedelic deformation; prioritize the more restrained Dreamy and readable WaterDrop/Swirl for short edits. |
| `Fold.glsl` | nwoeanhinnogaehr | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `Gallery.glsl` | gre | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `GlitchBands.glsl` | Yoni Maltsman @friendlyspinach | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `GlitchDisplace.glsl` | Matt DesLauriers | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `GlitchFlicker.glsl` | bread | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `GlowDissolve.glsl` | hjm1fb | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `GooeyWipe.glsl` | gre | Organic reveal/distortion family represented by PerlinDissolve, BurnThrough, Dreamy and WaterDrop; avoid several similar noise-front variants. |
| `GridFlip.glsl` | TimDonselaar | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `Halftone.glsl` | gre | Existing halftone effect plus selected DitherDissolve/PolkaDotsCurtain cover the dotted look. |
| `HeartWipe.glsl` | gre | Existing shape_wipe covers this shape/iris family; retain one implementation. |
| `HeatHaze.glsl` | gre | Organic reveal/distortion family represented by PerlinDissolve, BurnThrough, Dreamy and WaterDrop; avoid several similar noise-front variants. |
| `Hologram.glsl` | gre | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `Honeycomb.glsl` | gre | Grid/tile family represented by SquaresWipe, RandomSquares, DitherDissolve and Hexagonalize; defer choreography variants. |
| `HorizontalClose.glsl` | martiniti | Stripe/split family represented by WindowSlices; extra orientations or shadow variations do not justify another port here. |
| `HorizontalOpen.glsl` | martiniti | Stripe/split family represented by WindowSlices; extra orientations or shadow variations do not justify another port here. |
| `HsvFade.glsl` | nwoeanhinnogaehr | Color bridge family already represented by FadeGrayscale, ColorPhase, ColorDistance and MultiplyBlend. |
| `InkBleed.glsl` | gre | Organic reveal/distortion family represented by PerlinDissolve, BurnThrough, Dreamy and WaterDrop; avoid several similar noise-front variants. |
| `InvertedPageCurl.glsl` | Hewlett-Packard | BSD 3-Clause and involved page/surface visibility; defer a faithful geometry port and its separate notice. |
| `Kaleidoscope.glsl` | nwoeanhinnogaehr | Additional lens/psychedelic deformation; prioritize the more restrained Dreamy and readable WaterDrop/Swirl for short edits. |
| `LeafWipe.glsl` | @Flexi23 | Shape-mask family already broad; selected ArrowWipe/BowTieHorizontal add more distinct compositions than another centered aperture. |
| `LeftRight.glsl` | zhmy | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `LensFlare.glsl` | gre | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `LightRays.glsl` | gre | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `LightStreaks.glsl` | gre | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `LightWipe.glsl` | gre | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `LinearBlur.glsl` | gre | 6x6 paired samples (72 lookups per pixel); not a good CPU default. Defer rather than silently replace with a different blur. |
| `LiquidFill.glsl` | gre | Organic reveal/distortion family represented by PerlinDissolve, BurnThrough, Dreamy and WaterDrop; avoid several similar noise-front variants. |
| `LissajousTiles.glsl` | Boundless <info@boundless-beta.com> | Grid/tile family represented by SquaresWipe, RandomSquares, DitherDissolve and Hexagonalize; defer choreography variants. |
| `LumaWipe.glsl` | gre | Existing luma_wipe already supports procedural and supplied masks; LuminanceMelt adds source-driven luma. |
| `Morph.glsl` | paniq | Additional lens/psychedelic deformation; prioritize the more restrained Dreamy and readable WaterDrop/Swirl for short edits. |
| `Mosaic.glsl` | Xaychru | Fragment/tile scene construction needs separate edge/coverage review; selected Pixelize/Hexagonalize cover simpler mosaic edits. |
| `MosaicBlend.glsl` | Sergey Kosarevsky | Near-duplicate coarse-pixel blend; selected Pixelize plus Hexagonalize provide two distinct cell shapes. |
| `MosaicFade.glsl` | YueDev | Near-duplicate coarse-pixel blend; selected Pixelize plus Hexagonalize provide two distinct cell shapes. |
| `NoiseDissolve.glsl` | towrabbit | Random reveal family represented by RandomSquares and PerlinDissolve; defer additional grain/cell scales. |
| `PaperTear.glsl` | gre | Additional torn/zigzag boundary; selected ArrowWipe, CurvedWipe and Wind cover contrasting edge styles. |
| `PhotoDevelop.glsl` | gre | Color bridge family already represented by FadeGrayscale, ColorPhase, ColorDistance and MultiplyBlend. |
| `PixelStretch.glsl` | gre | Deliberate axis stretching/squeezing conflicts with a literal no-stretch circle gate; defer with an explicit geometry exception policy. |
| `PlasmaDissolve.glsl` | gre | Organic reveal/distortion family represented by PerlinDissolve, BurnThrough, Dreamy and WaterDrop; avoid several similar noise-front variants. |
| `PlusWipe.glsl` | gre | Shape-mask family already broad; selected ArrowWipe/BowTieHorizontal add more distinct compositions than another centered aperture. |
| `PopIn.glsl` | gre | Layered card/pop composition overlaps existing cutout_card and zoom vocabulary; prioritize general two-shot transitions. |
| `PowerKaleido.glsl` | Boundless | Additional lens/psychedelic deformation; prioritize the more restrained Dreamy and readable WaterDrop/Swirl for short edits. |
| `Prisms.glsl` | gre | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `Puzzle.glsl` | gre | Fragment/tile scene construction needs separate edge/coverage review; selected Pixelize/Hexagonalize cover simpler mosaic edits. |
| `RadialWipe.glsl` | Xaychru | Angular/polar reveal family represented by ClockWipe and Pinwheel; defer additional blade/ring variations. |
| `RectangleCover.glsl` | martiniti | Shape-mask family already broad; selected ArrowWipe/BowTieHorizontal add more distinct compositions than another centered aperture. |
| `RectangleIris.glsl` | martiniti | Shape-mask family already broad; selected ArrowWipe/BowTieHorizontal add more distinct compositions than another centered aperture. |
| `Refraction.glsl` | gre | Additional lens/psychedelic deformation; prioritize the more restrained Dreamy and readable WaterDrop/Swirl for short edits. |
| `Revolve.glsl` | bread | Additional lens/psychedelic deformation; prioritize the more restrained Dreamy and readable WaterDrop/Swirl for short edits. |
| `RingsWipe.glsl` | gre | Angular/polar reveal family represented by ClockWipe and Pinwheel; defer additional blade/ring variations. |
| `Ripple.glsl` | gre | Same central ripple family as selected WaterDrop; prefer its bounded advancing wavefront. |
| `Rolls.glsl` | Mark Craig | Overlaps spin and selected RotateScaleFade; no additional rotation variant in this slice. |
| `RotateFade.glsl` | haiyoucuv | Overlaps spin and selected RotateScaleFade; no additional rotation variant in this slice. |
| `RotateScaleVanish.glsl` | Mark Craig | Overlaps spin and selected RotateScaleFade; no additional rotation variant in this slice. |
| `SawtoothWipe.glsl` | gre | Additional torn/zigzag boundary; selected ArrowWipe, CurvedWipe and Wind cover contrasting edge styles. |
| `Shatter.glsl` | lbl | Fragment/tile scene construction needs separate edge/coverage review; selected Pixelize/Hexagonalize cover simpler mosaic edits. |
| `Shred.glsl` | gre | Stripe/split family represented by WindowSlices; extra orientations or shadow variations do not justify another port here. |
| `SimpleFlip.glsl` | nwoeanhinnogaehr | Shader creates uncovered canvas during the flip/doors, conflicting with S-63 opaque-in/opaque-out without a new background policy. |
| `SimpleZoom.glsl` | 0gust1 | Zoom family already covered by zoom_through plus selected ScaleIn/CrossWarp; avoid a large set of similar zooms. |
| `SimpleZoomOut.glsl` | Tianshuo | Zoom family already covered by zoom_through plus selected ScaleIn/CrossWarp; avoid a large set of similar zooms. |
| `SlideAwayRight.glsl` | lizhongjian | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `Slides.glsl` | Mark Craig | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `SmokeDissolve.glsl` | gre | Organic reveal/distortion family represented by PerlinDissolve, BurnThrough, Dreamy and WaterDrop; avoid several similar noise-front variants. |
| `SnakeBlockWipe.glsl` | gre | Grid/tile family represented by SquaresWipe, RandomSquares, DitherDissolve and Hexagonalize; defer choreography variants. |
| `Snapshot.glsl` | gre | Layered card/pop composition overlaps existing cutout_card and zoom vocabulary; prioritize general two-shot transitions. |
| `Sphere.glsl` | gre | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `SpiralBlockWipe.glsl` | gre | Grid/tile family represented by SquaresWipe, RandomSquares, DitherDissolve and Hexagonalize; defer choreography variants. |
| `SpiralWipe.glsl` | gre | Angular/polar reveal family represented by ClockWipe and Pinwheel; defer additional blade/ring variations. |
| `SplatterWipe.glsl` | gre | Organic reveal/distortion family represented by PerlinDissolve, BurnThrough, Dreamy and WaterDrop; avoid several similar noise-front variants. |
| `SplitSlideInHorizontal.glsl` | OllyOllyOlly | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `SplitSlideInOutHorizontal.glsl` | OllyOllyOlly | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `SplitSlideInOutVertical.glsl` | OllyOllyOlly | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `SplitSlideInVertical.glsl` | OllyOllyOlly | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `SplitSlideOutHorizontal.glsl` | OllyOllyOlly | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `SplitSlideOutVertical.glsl` | OllyOllyOlly | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `Squeeze.glsl` | gre | Deliberate axis stretching/squeezing conflicts with a literal no-stretch circle gate; defer with an explicit geometry exception policy. |
| `StarWipe.glsl` | Ben Lucas | Existing shape_wipe covers this shape/iris family; retain one implementation. |
| `StaticFade.glsl` | Ben Lucas | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `StaticWipe.glsl` | Ben Lucas | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `StereoViewer.glsl` | Ted Schundler | BSD 2-Clause card/viewer composition; defer rather than add another license and complex layer model to this batch. |
| `StretchSlide.glsl` | gre | Deliberate axis stretching/squeezing conflicts with a literal no-stretch circle gate; defer with an explicit geometry exception policy. |
| `StripDatamoshGlitch.glsl` | bread | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `Swap.glsl` | gre | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `TangentMotionBlur.glsl` | chenkai | Nested motion-blur sampling loops are a poor CPU fit; retain existing whip_pan for fast motion blur. |
| `TilesWave.glsl` | numb3r23 | Grid/tile family represented by SquaresWipe, RandomSquares, DitherDissolve and Hexagonalize; defer choreography variants. |
| `TopBottom.glsl` | zhmy | Overlaps existing push/slide; select CrossWarp and DirectionalWarp for a genuinely different moving seam. |
| `Tunnel.glsl` | gre | Additional lens/psychedelic deformation; prioritize the more restrained Dreamy and readable WaterDrop/Swirl for short edits. |
| `TvLostSignal.glsl` | mernking (gitlab.com/Godswork) | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `TvRoll.glsl` | gre | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `TvStatic.glsl` | Brandon Anzaldi | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `TvTurnOff.glsl` | gre | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `UndulatingBurnOut.glsl` | pthrasher | Light/burn/fade family represented by BurnThrough, Overexposure, DreamyZoom and existing flash_cut; defer additional light styles. |
| `VerticalClose.glsl` | martiniti | Stripe/split family represented by WindowSlices; extra orientations or shadow variations do not justify another port here. |
| `VerticalOpen.glsl` | martiniti | Stripe/split family represented by WindowSlices; extra orientations or shadow variations do not justify another port here. |
| `VhsTracking.glsl` | gre | Glitch/noise/scanline vocabulary is already represented by existing glitch and selected GlitchMemories; avoid redundant flashing variants. |
| `Vortex.glsl` | gre | Fragment/tile scene construction needs separate edge/coverage review; selected Pixelize/Hexagonalize cover simpler mosaic edits. |
| `WedgeWipe.glsl` | gre | Angular/polar reveal family represented by ClockWipe and Pinwheel; defer additional blade/ring variations. |
| `WhipPan.glsl` | gre | Already covered by stable whip_pan, including blur and adjacent-shot motion. |
| `WhipSpin.glsl` | gre | Motion accent overlaps existing camera vocabulary/whip_pan; no extra shake or blur variants in this batch. |
| `WhipTilt.glsl` | gre | Perspective/panel/surface visibility needs a separate faithful CPU geometry and coverage review; retain RotateScaleFade for this slice. |
| `WindowBlinds.glsl` | Fabien Benetou | Stripe/split family represented by WindowSlices; extra orientations or shadow variations do not justify another port here. |
| `WipeDown.glsl` | Jake Nelson | Plain directional mask already expressible by luma_wipe; prioritize CurvedWipe and Wind. |
| `WipeLeft.glsl` | Jake Nelson | Plain directional mask already expressible by luma_wipe; prioritize CurvedWipe and Wind. |
| `WipeRight.glsl` | Jake Nelson | Plain directional mask already expressible by luma_wipe; prioritize CurvedWipe and Wind. |
| `WipeUp.glsl` | Jake Nelson | Plain directional mask already expressible by luma_wipe; prioritize CurvedWipe and Wind. |
| `ZoomInCircles.glsl` | dycm8009 | Zoom family already covered by zoom_through plus selected ScaleIn/CrossWarp; avoid a large set of similar zooms. |
| `ZoomInOut.glsl` | OllyOllyOlly | Zoom family already covered by zoom_through plus selected ScaleIn/CrossWarp; avoid a large set of similar zooms. |
| `ZoomWipeLeft.glsl` | Handk | Zoom family already covered by zoom_through plus selected ScaleIn/CrossWarp; avoid a large set of similar zooms. |
| `ZoomWipeRight.glsl` | Handk | Zoom family already covered by zoom_through plus selected ScaleIn/CrossWarp; avoid a large set of similar zooms. |
