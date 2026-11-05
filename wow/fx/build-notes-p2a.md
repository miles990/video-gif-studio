# P2a ? known defects and default gate kit

Builder work on `p2-gate`, confined to `C:/Users/User/src/vgs-fx`. No commit, push,
stable promotion, spec/acceptance/process edit, dependency installation or model download.
The installed skill and the other source checkout were not edited. Generated media,
model caches and test logs are in the OS temp directory, outside the repository.

## Changes and regression coverage

- Captions: try bounded reduction to about 0.6, then split oversized words at grapheme
  boundaries with proportional display timing and a warning. Original word exports
  remain intact. Tests exercise long English, URL and CJK strings across all four
  presets (12 combinations), and confirm no lost text. Pathological narrow safe zones
  warn if further shrinking is necessary.
- Chinese punctuation: protect Latin identifiers, abbreviations, versions, grouped
  numbers, URLs and times. Automatic and explicit numeric highlighting use complete
  numeric spans; `iPhone15`, `H264`, decimal suffixes and `10:30` are not partial matches.
- Typewriter: timed-word reveal with a persistent, colour-pulsing insertion caret;
  per-character input also works. The caret retains alpha so revealed ink never
  disappears. Clean now has a dark panel. Emoji attach to the preceding word through
  both wrapping and orphan-tail rebalancing, including supplementary and BMP emoji.
- QA: initial spring travel ends at the first physical peak for cut exclusion; real
  planned cuts still win. Full-frame white flashes cannot receive camera exemptions,
  including otherwise-static clips. Tests include a real PNG sequence with a white
  flash at the spring start, in addition to synthetic metric fixtures.
- Defaults: visible drifting warm leak; restrained radial integration (.045); softened,
  geometrically decaying echo trails; resolution-relative grain; sparse dust and short
  scratches; median-cleaned posterization; RGB colour halftone; two-line bold title;
  analytic cover zoom for spin; circular pixel-distance masks; 12 px soft luma wipe.
- Multi-cutout warns and returns unchanged on opaque input. Its performance measurement
  uses RGBA, so the reported cost is the active effect, not the opaque no-op.
- Held-out inputs: 1x1 and 2x3 halftone/kaleidoscope; RGBA parallax conserves alpha sum
  within .001 and ignores hidden RGB; 16-bit PNG masks retain values such as 1000 and
  2000 instead of clipping them to 255; missing masks name their paths; nearest glitch
  preserves the source palette; empty/missing RIFE models give clean path-specific
  errors and no session loads for unused interpolation; text reports missing codepoints,
  rejects empty strings, fits width/height and errors clearly if even minimum-size text
  cannot fit. Font, stroke and shadow scale together on tiny canvases.
- The gate found an additional fractional `push` seam. Adjacent shot coverages now add
  in premultiplied space instead of being attenuated twice by alpha-over. Regression
  covers four directions at three fractional positions.

The existing long-token rejection test was changed to require a warning, bounded line
width and preservation of all characters, matching the new requested behavior. Existing
assertions were not disabled. There are 27 new P2a tests; all passed in 15.259 s. The
24 core FX tests, including cross-process hashes on a 30x20 canvas, passed in 6.474 s.
`doctor.py` reports supported Python, local GIF runtime ready and media runtime ready.

## Reproduction and artifacts

Full command actually run (PowerShell, from this worktree):

```powershell
$env:PATH='C:/Users/User/.codex/skills/video-gif-studio/.venv/Lib/site-packages/static_ffmpeg/bin/win32;'+$env:PATH
& 'C:/Users/User/src/fx-optdeps/venv/Scripts/python.exe' scripts/fx_gate_kit.py --out C:/Users/User/AppData/Local/Temp/p2a-gate-20261105 --models C:/Users/User/.codex/skills/video-gif-studio/.runtime/models
```

Canonical review artifacts:

- `C:/Users/User/AppData/Local/Temp/p2a-gate-20261105/index.html`
- `C:/Users/User/AppData/Local/Temp/p2a-gate-20261105/gate-auto.json`
- `C:/Users/User/AppData/Local/Temp/p2a-caption-evidence/captions.jpg`

The full run was followed by targeted gate-kit refreshes with the same optional Python:

```powershell
python scripts/fx_gate_kit.py --out C:/Users/User/AppData/Local/Temp/p2a-gate-echo-final --items echo
python scripts/fx_gate_kit.py --out C:/Users/User/AppData/Local/Temp/p2a-gate-multi-final --items multi_cutout
python scripts/fx_gate_kit.py --out C:/Users/User/AppData/Local/Temp/p2a-gate-push-final --items push
python scripts/fx_gate_kit.py --out C:/Users/User/AppData/Local/Temp/p2a-gate-text-final --items text
```

The refreshed item directories and JSON records replace their original counterparts
in the canonical kit; all refresh commands and reasons are retained in `gate-auto.json`.
Decoded QA was refreshed across all 144 clips, and opaque-coverage probes were added
across the entire catalog. Choose a new output directory when reproducing: existing
nonempty directories are rejected. No aesthetic scores or quality-status decisions
are made by the kit.

Each of 36 items has four 2 s / 24 fps clips: opaque repo demo footage and the retained
RGBA fish matte, each at 480x270 and 270x480, plus one contact sheet. A common 120 BPM
click accents the clips. The only visual-function overrides are parallax model/cache
resource paths. Source paths and hashes, defaults, seeds, warnings, checks and raw timing
samples are retained in JSON. RGBA previews are checker-composited H.264; alpha checks
operate on the uncomposited float RGBA, not on the MP4.

## Measurements (not aesthetic scores)

All 144 cases pass alpha, determinism and single-frame flicker checks. Each raw sequence
was rendered twice for SHA256 comparison. Alpha range/shape/finite checks cover all 48
frames, colour-only alpha equality covers all frames, and opaque coverage / hidden-RGB
probes sample frames 0, 24 and 47. Flicker uses `qa_media` on decoded clips without event
exemptions. No unexpected black frames were detected: `black_flash` intentionally
produces 48 black frames in each of its four default clips, and those FAIL flags remain.

Edge-gradient warnings are retained, not marked as passed:

| Item / case | Frames | Measurement |
| --- | --- | --- |
| posterize / opaque landscape | 0?4 | maximum stretch ratio 10.41 |
| halftone / opaque landscape | 2, 3, 4, 29, 43 | maximum stretch ratio 21.96 |
| hex_shutter / RGBA landscape | 13, 34 | maximum seam ratio 6.85 |
| hex_shutter / opaque portrait | 5, 42 | maximum stretch ratio 27.45 |

These are normal-gradient heuristics at the canvas edge: seam ratio >6; inverse
stretch ratio >8 with interior gradient >.015. Their flagged contact sheets were
inspected. Quantized bands, screen dots and shutter boundaries can trigger these
heuristics; the raw warnings remain available for independent reviewers.

720p timings below are medians of ten calls after one warm-up, using float32 RGBA at
1280x720. They include the public effect wrapper and warm caches, exclude encoding,
decoding and cold model inference, and use opaque footage except multi_cutout (RGBA).
One heavy job ran at a time. The numbers are not a claim that every item meets 50 ms.

Environment: Windows-10-10.0.19045-SP0; NumPy 2.5.4; OpenCV 5.0.0; Intel64 Family 6 Model 158 Stepping 10, GenuineIntel.

| Item | 720p ms/frame | Edge-warning cases | Black frames |
| --- | ---: | ---: | ---: |
| effect:flash_white | 22.75 | 0/4 | 0/192 |
| effect:grade | 4.88 | 0/4 | 0/192 |
| effect:halation | 57.97 | 0/4 | 0/192 |
| effect:beat_bounce | 9.03 | 0/4 | 0/192 |
| effect:zoom_punch | 9.55 | 0/4 | 0/192 |
| effect:cutout_card | 232.61 | 0/4 | 0/192 |
| effect:shake | 41.66 | 0/4 | 0/192 |
| effect:rgb_split | 49.89 | 0/4 | 0/192 |
| effect:radial_blur | 98.73 | 0/4 | 0/192 |
| effect:echo | 240.51 | 0/4 | 0/192 |
| effect:film_grain | 33.61 | 0/4 | 0/192 |
| effect:vignette | 35.72 | 0/4 | 0/192 |
| effect:light_leak | 63.67 | 0/4 | 0/192 |
| effect:dust_scratches | 38.85 | 0/4 | 0/192 |
| effect:invert_flash | 25.57 | 0/4 | 0/192 |
| effect:black_flash | 12.87 | 0/4 | 192/192 |
| effect:split_screen | 45.22 | 0/4 | 0/192 |
| effect:mirror | 9.59 | 0/4 | 0/192 |
| effect:kaleidoscope | 97.56 | 0/4 | 0/192 |
| effect:posterize | 64.77 | 1/4 | 0/192 |
| effect:halftone | 41.33 | 1/4 | 0/192 |
| effect:multi_cutout | 354.80 | 0/4 | 0/192 |
| effect:text | 124.88 | 0/4 | 0/192 |
| effect:parallax | 142.80 | 0/4 | 0/192 |
| effect:camera_move | 8.47 | 0/4 | 0/192 |
| transition:crossfade | 69.63 | 0/4 | 0/192 |
| transition:whip_pan | 89.41 | 0/4 | 0/192 |
| transition:hex_shutter | 47.51 | 2/4 | 0/192 |
| transition:flash_cut | 28.72 | 0/4 | 0/192 |
| transition:shape_wipe | 95.74 | 0/4 | 0/192 |
| transition:luma_wipe | 98.06 | 0/4 | 0/192 |
| transition:push | 64.49 | 0/4 | 0/192 |
| transition:slide | 82.06 | 0/4 | 0/192 |
| transition:spin | 40.86 | 0/4 | 0/192 |
| transition:zoom_through | 40.35 | 0/4 | 0/192 |
| transition:glitch | 84.85 | 0/4 | 0/192 |

Canonical media kit size including validation logs: 33,361,322 bytes, below 300 MB.

## Frame inspection

Viewed the original material, caption crops for all presets on checkerboard, and
contact sheets for radial blur, echo (including the corrected transparent overlap),
grain, leak, dust, posterize, colour halftone, title, circle/luma wipes, spin, parallax
and the flagged hex shutter. The title refresh was inspected again. Caption crops
show preserved `Node.js`/`10:30`, attached emoji, the typing caret, safe-zone word
fragments and the clean panel. The initial RGBA echo inspection exposed an overbright
trail overlap; compositing ghosts behind the current cutout removed that defect.
Spin shows cover zoom instead of mirrored corners. This is builder frame inspection;
real-time playback review, two independent cross-vendor reviewers and user spot checks
remain pending. All experimental statuses remain unchanged.

## Final full-suite verification

`C:/Users/User/.codex/skills/video-gif-studio/.venv/Scripts/python.exe -m unittest discover -s tests`
completed on the final code: **350 tests in 231.972 s, zero failures, two existing
Windows environment errors, five existing skips**. Relative to the supplied 323-test /
two-error baseline, 27 tests were added with zero new failures or errors. The unchanged
errors are `test_same_source_symlink_is_preserved` (WinError 1314, symlink privilege)
and `test_review_exports_overlay_contact_sheet_and_stability_report` (WinError 32,
locked overlay PNG during temporary-directory cleanup). Full log, targeted log, core FX
log and doctor JSON are retained in the canonical kit.

`git diff --check` passed. Changed/new task files are all below 2 MB; generated media
is outside the repository. The unrelated `wow/fx/thresholds.md` audit appeared in the
shared worktree during the task and was left untouched. No spec, acceptance or process
file was edited; no commit or push was performed.
