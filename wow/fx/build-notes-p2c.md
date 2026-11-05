# P2c build notes - defects, threshold registry, pairwise controls

Worktree `C:/Users/User/src/vgs-fx`, branch `p2c-gate`. No commit/push. Installed
skill and the other source checkout were not modified. All gate media are outside
the repository. One heavy workload was run at a time.

## Implemented behavior

| Item | Change and regression coverage |
| --- | --- |
| Polka dots | Radius uses farthest-corner/diagonal normalization and cell-corner radius; p=.99 coverage tested at 16:9, 10:1, portrait. |
| All 32 GL ports | Exact final delivered frame equals B; endpoint limits, dtype, matte, determinism and progress regressions. |
| Displacement alpha | Twelve sampling/displacement ports exempt from original-union clipping. Moved coverage and hidden-RGB invariance tested. |
| Spin | Cover zoom restricted to opaque sources; transparent border for cutouts, no reflected duplicate silhouettes. Padding tends to zero at endpoints. |
| Hex shutter | Midpoint preserves selected source alpha, never fills the transparent background. |
| Caption clean | Minimum three-grapheme pieces, Latin continuation hyphen, proportional bounded piece times, unique display piece IDs, no line overlap. Original timed text preserved. |
| Validation | Mask errors name the resolved path. Non-finite p raises ValueError in public/owned APIs. GL nearest-mode warnings in plan/manifests and direct calls. |
| Additional endpoint defects | Pixelize/Hexagonalize blend in their first quantization step; SquaresWipe assigns collapsed cells zero coverage. |
| GL performance | Opaque association/division bypass; contiguous spatial mixes; GlitchMemories samples one coherent RGBA block-offset field; CurvedWipe shades only its band. |
| Thresholds | Shared JSON/schema, F/R/C/U calibrator, deferred activation, all-anchor decisions/flips, drift freeze, controls, history/audit, bounded U defaults. |
| Pairwise kit | Same-family stable mapping, independent B shot, broken and style controls, 2 s details + 10 s contexts, stills/crops/sheets, judge-compatible pairs/criteria. |

## Serial performance measurements

Same machine and interpreter, OpenCV one thread; deterministic independent random
opaque A/B textures at 1280x720 float32, p=.37; one warmup then median of 20 public
calls, including input copies/output clipping and excluding decoding/encoding.
Raw samples and environment are in `benchmark-p2c-before.json` and
`benchmark-p2c-after.json`. No concurrent test suite or gate renderer was running.

Median per-port speedup **2.45x**; aggregate summed medians **2.33x**. 24/32 ports exceed 2x. The common-path target is met; individual geometry-heavy ports remain below 2x and are listed without hiding them.

| GL item | Before ms/frame | After ms/frame | Speedup |
| --- | ---: | ---: | ---: |
| gl_clock_wipe | 138.48 | 49.17 | 2.82x |
| gl_cross_warp | 165.77 | 77.11 | 2.15x |
| gl_directional_warp | 171.26 | 82.24 | 2.08x |
| gl_dreamy | 136.16 | 55.55 | 2.45x |
| gl_dreamy_zoom | 150.18 | 83.74 | 1.79x |
| gl_rotate_scale_fade | 189.33 | 105.18 | 1.80x |
| gl_swirl | 166.74 | 86.33 | 1.93x |
| gl_water_drop | 129.12 | 52.52 | 2.46x |
| gl_burn_through | 159.52 | 70.11 | 2.28x |
| gl_overexposure | 123.57 | 42.26 | 2.92x |
| gl_fade_grayscale | 150.77 | 75.63 | 1.99x |
| gl_color_distance | 149.52 | 49.57 | 3.02x |
| gl_luminance_melt | 127.82 | 38.36 | 3.33x |
| gl_pixelize | 156.79 | 76.09 | 2.06x |
| gl_dither_dissolve | 183.66 | 99.23 | 1.85x |
| gl_random_squares | 156.06 | 71.74 | 2.18x |
| gl_window_slices | 129.44 | 40.99 | 3.16x |
| gl_wind | 151.32 | 61.40 | 2.46x |
| gl_pinwheel | 164.59 | 66.84 | 2.46x |
| gl_polka_dots_curtain | 146.53 | 50.89 | 2.88x |
| gl_crosshatch | 177.81 | 83.85 | 2.12x |
| gl_perlin_dissolve | 122.03 | 33.17 | 3.68x |
| gl_glitch_memories | 353.96 | 58.18 | 6.08x |
| gl_scale_in | 111.53 | 33.29 | 3.35x |
| gl_bounce | 211.17 | 129.48 | 1.63x |
| gl_multiply_blend | 99.06 | 20.94 | 4.73x |
| gl_color_phase | 100.15 | 30.90 | 3.24x |
| gl_hexagonalize | 229.12 | 150.42 | 1.52x |
| gl_squares_wipe | 147.33 | 60.18 | 2.45x |
| gl_bow_tie_horizontal | 147.00 | 57.04 | 2.58x |
| gl_curved_wipe | 316.39 | 170.67 | 1.85x |
| gl_arrow_wipe | 170.23 | 79.77 | 2.13x |

The glitch adaptation intentionally replaces upstream's always-zero normalized
block index and three mismatched RGBA channel samples with one seeded pixel-block
sample. It is not a claim of bit-identical upstream GLSL. CurvedWipe omits shadow
contributions below 1/65535; source/default/author attribution is retained.

## Registry scope and guardrails

Controls are `anchors` entries with positive/negative roles, matching the supplied
schema (no illegal extra `controls` property). Audio normalization and encoded QA
read target/tolerance/true-peak values; caption reports read fill/stroke contrast.
Runtime helpers evaluate onset contrast, sharp4, rolling budget and supplied camera
jerk samples. `qa_media --threshold-metrics` consumes measured channels, including
memory. Manifests/QA/gate evidence record registry version, round, hash and values.
There were no pre-existing visibility/budget/jerk runtime constants on this branch;
these channels are introduced as **calibrate_first**, with explicit GUESS provenance.
Synthetic control fixtures are instrumentation tests, not perceptual or user labels.
The memory ceiling is the recorded stable workload's 499,961,856 bytes x 1.3 =
649,950,412.8 bytes. Do not compare a different workload against that ratchet.

F is immutable. R requires three improvements beyond 2 sigma and caps tightening at
10%; C uses held-out good/bad distributions, >=25% pooled-sigma margin on both sides,
>=10% sample growth, and independent audit attribution. U clamps each choice step
to 15% and hard bounds; fewer than five distinct choices only change defaults.
Registered instrument versions must match evidence. Proposals rejudge all anchors,
require best < benchmark < worse in the appropriate direction, reject benchmark
ceiling contact, list flips and require explicit flip confirmation. Current or
proposed control failures invalidate the instrument; drift >2 sigma or unexplained
baseline decision flips freeze it. No pending proposal changes a current-round read.
Activation requires a strictly later round before candidate work starts. Every
accepted/blocked proposal carries evidence, approver, trigger, values and decisions
in history/audit. Production calibration still requires independently retained real
anchors; no human labels or quality-gate outcome are fabricated in this slice.

## Gate protocol and tool compatibility

Output: `C:/Users/User/AppData/Local/Temp/vgs-fx-p2c-gate-20261105`.
`pairs.json` contains absolute directories of numbered PNGs accepted by the installed
quick judge. `criteria.json` asks: "Would a professional editor use this default
as-is in a short-form edit?" Controls/answers are in `controls.json`, separate from
blind context. Each item has 12 cells (two materials x two aspect ratios x three
phases), each with benchmark/broken/style comparisons. A stable self-reference is
allowed only as a known-good positive control; experimental self-reference is not.
Every case retains a 10 s MP4 per variant, 12 chronological keyframes, three native
crops and a <=1280 px, JPEG quality-90 contact sheet. Phase pairs include their local
frames plus the flash/crops so a gold defect cannot disappear between sampled stills.
B is an independent animated geometric shot, never an A mirror. Broken versions
contain a replicated four-pixel edge and a one-frame white/black exposure/alpha
flash chosen to contrast the local frame; detection is required before export.
Restyling changes hue slightly while preserving geometry/alpha/timing.

Auto checks cover swapped A/B, first/last limit discontinuities, >=4 px replicated
edge strips, isolated flash controls, alpha, hidden RGB, black frames, determinism
and warm 720p timings. Intentional shutter/flash events remain flagged. Flags are
review evidence, not a stable promotion or an aesthetic score.

Compatibility limitation found by reading the installed tool: quick judge `--sheet`
always recompresses at JPEG q80 and has no quality option. Its default thumb=320,
cols=6 also exceeds 1280 px. Use `--thumb 200 --cols 6` for size. Generated q90 sheets
and lossless native PNGs meet the kit requirement; the external judge's compression
must be raised/preserved before a **protocol-compliant formal review**. No installed
judge files were modified, and no model judges were called or votes fabricated.
The exported README preregisters controls, >=2/3 win/tie rule, significant-loss rule,
family/order handling and no rerolling. Automatic checks do not promote any GL item.

## Verification

- Baseline: 515 tests, two environment errors, five skips, zero assertion failures.
- First full post-change run: 541 tests, same two environment errors, five skips,
  zero assertion failures (308.632 s).
- Earlier targeted GL/P2c: 196 tests passed (9.914 s), followed by further guard tests.
- Environment errors: Windows symlink privilege in `test_install`; locked Pillow
  image during temporary-directory cleanup in `test_mask_review`. Both reproduced
  before edits; neither is hidden or newly introduced.
- Final full suite: 549 tests in 306.326 s, same two environment errors, five skips,
  zero assertion failures. Doctor exits 0; local media runtime is ready.
- Final mapping/export validation and judge dry-run results are recorded below.
- No protected spec/acceptance/process/thresholds Markdown files changed. All new
  or changed repository files are below 2 MB. Pre-existing oversized example/demo
  media were left untouched. No commit or push was performed.

## Exported per-item gate checks

All 34 items exported 36 pairs each. Across the four material/aspect cases per
item, alpha, black-frame, flicker and determinism checks all pass. Counts below
are flagged cases, not aesthetic judgments. Exact endpoints pass throughout.
Bounce has an existing RGBA start-limit jump: 0.00670 landscape / 0.01364 portrait
mean associated-RGBA error at p=1e-5; actual delivered-step checks pass.

| Item | Stable reference | Pairs | Edge flags / 4 | Endpoint flags / 4 |
| --- | --- | ---: | ---: | ---: |
| hex_shutter | hex_shutter | 36 | 2 | 0 |
| spin | whip_pan | 36 | 0 | 0 |
| gl_clock_wipe | hex_shutter | 36 | 0 | 0 |
| gl_cross_warp | whip_pan | 36 | 0 | 0 |
| gl_directional_warp | whip_pan | 36 | 0 | 0 |
| gl_dreamy | whip_pan | 36 | 0 | 0 |
| gl_dreamy_zoom | whip_pan | 36 | 0 | 0 |
| gl_rotate_scale_fade | whip_pan | 36 | 0 | 0 |
| gl_swirl | whip_pan | 36 | 1 | 0 |
| gl_water_drop | whip_pan | 36 | 1 | 0 |
| gl_burn_through | crossfade | 36 | 0 | 0 |
| gl_overexposure | flash_cut | 36 | 0 | 0 |
| gl_fade_grayscale | crossfade | 36 | 0 | 0 |
| gl_color_distance | crossfade | 36 | 0 | 0 |
| gl_luminance_melt | crossfade | 36 | 0 | 0 |
| gl_pixelize | whip_pan | 36 | 2 | 0 |
| gl_dither_dissolve | hex_shutter | 36 | 2 | 0 |
| gl_random_squares | hex_shutter | 36 | 0 | 0 |
| gl_window_slices | hex_shutter | 36 | 2 | 0 |
| gl_wind | hex_shutter | 36 | 0 | 0 |
| gl_pinwheel | hex_shutter | 36 | 0 | 0 |
| gl_polka_dots_curtain | hex_shutter | 36 | 1 | 0 |
| gl_crosshatch | hex_shutter | 36 | 1 | 0 |
| gl_perlin_dissolve | crossfade | 36 | 0 | 0 |
| gl_glitch_memories | whip_pan | 36 | 1 | 0 |
| gl_scale_in | whip_pan | 36 | 0 | 0 |
| gl_bounce | whip_pan | 36 | 1 | 2 |
| gl_multiply_blend | crossfade | 36 | 0 | 0 |
| gl_color_phase | crossfade | 36 | 0 | 0 |
| gl_hexagonalize | whip_pan | 36 | 2 | 0 |
| gl_squares_wipe | hex_shutter | 36 | 2 | 0 |
| gl_bow_tie_horizontal | hex_shutter | 36 | 0 | 0 |
| gl_curved_wipe | hex_shutter | 36 | 0 | 0 |
| gl_arrow_wipe | hex_shutter | 36 | 0 | 0 |

Artifact validation: 1,224 unique pairs, 408 detected broken controls, 408 style
controls, 1,632 valid pair directories and 578 contact sheets at the required
quality/size floor. The kit has 680 MP4s and 20,128 PNGs (~1.23 GB). See
`gate-p2c-summary.json` and the external `artifact-validation.json` for evidence.

Final revalidation after mapping corrections passed at 2026-11-05 04:18:20 UTC.
FadeGrayscale uses Crossfade; BowTieHorizontal uses HexShutter. Their identical
stable-reference renders were reused from existing same-input kit cells; all 156
copied files per item were SHA-256 checked against their source. Candidate, broken,
and style renders were unchanged. The report records this reference provenance.

The final 34 P2c regression tests pass in 1.579 s, including explicit category
mapping assertions. The installed judge's sheet builder successfully consumed
the sample REF/BAD/STYLE triplet and built six sheets (exit 0). The complete CLI
dry-run is **environment-blocked** before reading pair inputs: Node's realpath
resolution raises EPERM on `C:/Users/User` in this sandbox, including with loader
symlink-preservation flags. See `judge-dry-run-p2c.json` and
`judge-sheet-smoke-p2c.json`. No model judges were called. The independent q80
compression limitation described above also remains a formal-review prerequisite.
