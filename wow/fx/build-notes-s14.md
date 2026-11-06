# Slice 14 build notes — original game assets and character animation

Built only in `C:/Users/User/src/vgs-fx`, branch `s14-assets`, on `9a26408`.
Status: **implemented experimental pipeline; full live acceptance remains
incomplete**. No spec, acceptance, process or threshold file was edited. No
commit, merge or push was attempted. Incremental patches and commit messages
are under `.scratch/commits/`; `.git` was not written.

## Per-item implementation and evidence

| Item | Implemented | Evidence and remaining boundary |
|---|---|---|
| S-160 | Four canonical views, six face-only expressions, exact palette card, portable refset, strict ORB/HSV identity with negative and near-negative controls, asymmetry regions, named-IP alternative guard | Live Rimewick view identity, expression and asymmetry measurements pass. Positive-view histogram distances 0.126–0.174; negative 0.933; near-negative 0.269. Side/back use the scoped palette exception; other ORB thresholds remain 25. Missing independent controls stay unassessed. Named-IP recognition is a finite guard, not an exhaustive visual IP classifier. |
| S-161 | Seven state templates; 2–4 reference keys per state; authored anatomical guides; nearest piecewise-affine and separate-limb inbetweens; contacts/root motion, ground/bob, jump parabola, hit contact, phase order, loop position/speed, canvas/pivot, hurt return and death hold QA | Demo has 34 frames across idle/run/attack/hurt and 16 actual reference keys. All 16 key identity measurements pass. Idle/run measured contacts and decoded loop position/speed pass. Attack hit is frame 4 at 320 ms. Attack/hurt contact intervals are unassessed, not passed. Jump/slide/duplicate/truncated-loop/contact controls are tested synthetically. Physical cadence remains pending playback review. |
| S-162 | Straight/premultiplied checks, real-alpha/checkerboard rejection, isolated translucent speck cleanup, halo and palette/grid/nearest checks, fixed shared canvas/pivot | Live 64×64 masters share pivot [32,60], 16-color palette, binary sprite alpha, zero new colors and clean borders. Nearest 2×/3× previews included. Arbitrary semantic holes need author masks; opaque silhouette pixels are preserved by generic cleanup. |
| S-163 | Native Godot 4 SpriteFrames, Unity PNG+.meta, Phaser hash/array, PixiJS and Aseprite JSON, per-state fps/loop/durations/events/pivots, padding/extrusion and exact RGBA crop round-trip | **Actual Godot 4.7.2 and Phaser 3.90 Chromium playback pass.** Godot loads every atlas region and observes every frame. Phaser hash/array loads observe every frame and hit event, with zero console errors. Corrected 3.90 frame duration semantics against its real runtime. Unity YAML parsed by PyYAML 6.0.2, bottom-left rects/IDs checked; Unity and Pixi engine loads remain untested. Godot 3 optional export not added. |
| S-164 | Shared style tokens; outline, light, grid/margin, color and group-outlier measurements; first accepted icon reference; `--fix` regenerates selected indices only and checks other hashes | Offline eight-icon repair scenario passes. Correct Cartesian light direction is regression-tested. Live revised atlas has coherent materials but still fails exact 2 px outline width on five icons and a bow value outlier. It was co-generated as one atlas, not eight independent first-icon-reference calls. S-164 live acceptance is not passed. |
| S-165 | Periodic texture repair; four-edge/Sobel/FFT/gradient/detail checks; complete Wang16, blob47 and min13 procedural tilesets with compatible edges | Live 256² texture passes; horizontal/vertical half-luma deltas 0.032/0.002 on the 0–255 scale, Sobel ratio 0.814, FFT cross ratio 1.172. Tests cover incomplete variants and edge compatibility. Tileset material palette is currently fixed grass/soil; no arbitrary art-prompt interpretation or native terrain-resource export is claimed. |
| S-166 | Local original explosion/magic/hit/pickup VFX; graded alpha, additive and opaque-black previews, GIF/APNG, one-shot fade and frame-budget QA | Synthetic tests and local magic-loop/explosion output pass. No pixelfx/Grok provenance is fabricated; these effects are implemented locally. |
| S-167 | Input/hash/route/price/driver-bound 30-minute estimates; exact `--approve-video` guard before child imports/dispatch; one-submission receipt; local pose interpolation and MP4/GIF/APNG | Missing/mismatched/expired approval makes zero model calls even with credential env vars. Explicit offline fake-driver scenario receives all inputs once. No real paid video call was authorized or made. Bundled Grok/fal cannot preserve first+last+identity refs together, so approved use needs a verified driver or fails `E_VIDEO_CAPABILITY`. Returned model-video identity remains a review gate. |
| S-168 | Portable original-character source pack; sheet, four animated states, engine projects, eight icons, texture, provenance, review pairs and deterministic rebuild | Demo: `.scratch/demo/rimewick/`. Rebuild from its portable pack generates zero images: 201 original asset/metadata files match SHA256, zero mismatches. Independent blinded reviewer chooses all six clean variants and ties both identical controls. Full acceptance is blocked by the explicit live icon/contact/playback gaps; user taste votes and the three-model wow-judge panel remain pending. |

Command and driver contracts: [game-assets.md](../../references/game-assets.md).
The standard `imagegen.py` surface dispatches game commands, all requiring
`--experimental`; existing image routes and `sprite_export.py` behavior remain
available. There is no separate `vgs` executable in this checkout.

## Demo provenance and measured review

Rimewick is an original amber fox wayfinder: teal scarf, navy tunic, crescent
belt, magenta stitch over the character's left eye, ice sword in the right
hand and cream tail tip. No existing-game artwork or spec-13 fox images were
used. Side/back designs are inferred from the original front reference.

The subscription CLI initially failed its auth preflight without dispatch.
The built-in subscription image tool then produced **13 images of the allowed
40**: four views, four four-pose strips, one six-expression sheet, two icon
atlases (one rejected/replaced), one texture and one different-character
negative control. The local near-negative recolors the scarf and removes the
stitch; it is not counted as generation. Every source is retained with SHA256
and actual reference hashes; model identity is unreported, not guessed.
No paid-image or model-video network request occurred.

Subscription dimensions are prompt-only. Actual source dimensions and local
64×64 quantization are recorded. The pack declares `pixel_quantize`; this is
not claimed as hand-authored native pixel art. Each animation strip uses one
fixed scale/ground transform, never a per-frame bbox recenter. Anatomical
guides and occluded leg layers are explicit author data. Inbetweens sample
nearest source pixels, with no crossfade or horizontal mirroring.

Independent review first rejected squeezed faces, detached recovery fragments
and a hollow run shin. Separate limb layers and corrected inverse sampling
addressed those visible defects. The final reviewer inspected run f0–7 and
decoded GIF frames and found no detached limb/confetti; actual cadence was
not available to that reviewer. Attack f6→7 at 0.48→0.56 s still needs motion
review. GIF/APNG media QA reports no FAIL, but pop WARNs remain documented for
playback inspection. Idle/run loop position and speed both pass. Automated
scores do not establish natural weight transfer.

The blinded defect comparison is in `review-pairs/independent-review.md`.
Choices were B, B, B, A, B, B, tie, tie; six damaged controls and both identical
controls were identified correctly. This is one independent technical agent,
not the requested three-model `wow-judge panel`. User taste votes are empty;
Wilson lower bound is null. No user preference score is inferred from tests.

All four local VFX kinds and all three procedural tileset topologies also
pass their specialized generated-output QA; retained at
`.scratch/s14-extended-assets/`. General media screening flags standalone
VFX frame 0 as black/flat: one-shots deliberately begin empty, and the magic
layer has one RGB color with graded alpha. Those decoded-media FAIL reports
are retained, not advertised as a general media PASS. The magic loop's
decoded position and speed checks pass. A separate scene preview honors
declared alpha versus additive blending; APNG retains the glow alpha.
The installed-main `fx_render.py` smoke renders a 6-second, 152-frame GIF
without changing the installation (`.scratch/s14-installed-fx/`).

Godot executable SHA256:
`c8f0a6bc45a19b33541501e57f6f7cd972ab18453743266339d495cbbe846643`.
Version: `4.7.2-stable (official)`. Both the frame checker and full sample
scene execute successfully. Godot logs a sandbox root-certificate-store
warning; no network operation is needed. Engine user data is redirected to
the demo scratch directory. `godot-evidence.json`, actual load log,
`browser-load.json`, runtime SHA256, Chromium screenshots, exact timing and
crop checks are in the demo. Phaser 3.90 was fetched from its official tagged
GitHub distribution through the connector; its MIT license is bundled. No
CDN fetch occurs during demo playback. Pixi 8.6.6 could not be obtained here
and remains untested. Unity remains format-only by design.

## Validation and patches

Use the supplied skill Python and static FFmpeg directory. Baseline main:
906 tests, zero failures, two environment errors, five skips. The errors are
Windows symlink privilege (`test_install...same_source_symlink_is_preserved`)
and a locked overlay PNG during cleanup
(`test_mask_review...exports_overlay_contact_sheet_and_stability_report`).
The first complete build run had 927 tests; a later complete run had 929.
Both had zero failures and the identical two baseline errors, four skips.
The final suite and scenario counts are recorded below after completion.

Final focused game suite: 29 tests, zero failures/errors. Existing image/taste/brief
scenario suites: 22 tests, zero failures/errors. Offline game cassette
scenarios cover ten-call character reference chaining and cache replay,
opaque/fake alpha rejection, isolated icon repair, and exactly-once approved
fake-video dispatch. The approved-driver test explicitly mocks media decode;
it does not claim a live model or video-quality result. Doctor reports local
GIF and media runtimes ready; auth/entitlement checks do not make requests.

Patches are ordered and incremental, with paired `.txt` commit messages:

1. `01-s160-s14.patch` — original character contracts and identity controls.
2. `02-s161-s14.patch` — reference poses, inbetweens and motion QA.
3. `03-s162-s14.patch` — transparent/pixel sprite screening and cleanup.
4. `04-s163-s14.patch` — native atlas adapters and real Godot checks.
5. `05-s164-s14.patch` — icon style tokens and isolated retries.
6. `06-s165-s14.patch` — periodic textures and complete tilesets.
7. `07-s166-s14.patch` — soft-alpha VFX and one-shot previews.
8. `08-s167-s14.patch` — explicit video estimates/approval and local fallback.
9. `09-s168-s14.patch` — live demo assembler, review/browser checks, regression
   fixes and these notes.

Apply them in order to `9a26408`; no demo binaries enter the patches. The
source pack and generated evidence remain in git-ignored `.scratch/`. The
replay check applies the patches into an isolated scratch tree and runs the
available game tests after each slice. Full-suite environmental errors are
not hidden or changed to skips.

Final broad run: **934 tests, zero failures, the same two baseline
environment errors, 4 skips** (`.scratch/s14-delivery-full.json`).
After that suite was collected, Godot userdata isolation, the alpha-blended
VFX scene preview, the offline taste picker, asymmetry status propagation
and native texture-size provenance received final refinements. The final
focused game run has **29 tests, zero failures/errors**
(`.scratch/s14-final-targeted.json`); the patch replay reruns those final tests.
No baseline error is counted as a new failure or relabeled as passing.

## Fix round — independent spec-14 review (2026-11-06)

Base: `a03d1e1c807e82edfba0cab4902131ddaebd815c` (s14-fix/main, including
spec-13 fix round 2). Read the independent `review-s14/report.md` in full.
All work stayed in this checkout. No spec, acceptance, process or threshold
policy document was edited; no Git index/commit was written. The initially
absent `.scratch/commits` directory now contains incremental patches and paired
commit messages. The feature remains EXPERIMENTAL.

### Changes and regression evidence

1. Character identity uses spec-13 reference-set spread and negative controls,
   with front/profile/back expectations. Overlapping evidence is unassessed;
   the existing explicit human override is recorded. Added pose-tolerant,
   saturation-weighted circular hue ranking, without an absolute BH gate or a
   palette-only identity pass. The reviewer's actual **single** wolf front is
   used, not just the easier front extracted from the turnaround. Its side
   distance is 0.1301, held-out back 0.1650, recoloured/scar-removed near negative
   0.7595. Raw BH/ORB still prefer that lookalike; they remain visible evidence,
   and overall semantic identity stays unassessed. Hue ranking cannot verify
   scars, anatomy or an achromatic copy.
2. CLI character generation detects large subject components, isolates the
   requested canonical cell, and matches echoed reference cells when a model
   reorders its sheet. Ambiguous layouts retry once. `isolate_single_subject`
   is on the actual generation path. A live attack exposed wide weapons being
   mistaken for a ground rule; a failing regression now ensures a horizontal
   weapon cannot sever the head. Only near-ground rules can be removed.
3. Isolated source images are retained under `identity/`; comparisons happen
   before 64-pixel conversion. Source size, SHA256 and measurement stage are
   recorded for sheets and animation keys. A generated pose grid keeps each
   high-resolution source cell separately from its converted key.
4. Standing keys register to a common ground and body height. The prompt demo
   uses one camera transform across each pose strip, preserving intended flight
   and crouch. Contact intervals are scanned across all frames, with left/right
   stride and contact-duration comparison. Reviewer WALK-LIMP and the two-frame
   WALK-JUMPSEAM fail; WALK-8 passes with measured intervals [0,3] and [4,7].
   Export blocks recorded QA FAIL unless `--allow-qa-fail` records the override.
   Automatic screen-side foot boxes and silhouette guides are proxies, not
   anatomical tracking or a physical-motion solver.
5. Pixel conversion integrates area, applies median color cleanup, quantizes a
   palette, maps to nearest palette entries and cleans small color islands.
   Dithering is off. Nearest sampling is reserved for established grids and
   enlargement. The isolated-color metric catches the old raw-NEAREST output.
6. Named franchise characters, common Chinese variants and targeted game-style
   requests are guarded. Alternatives vary by the request and preserve intent
   while changing species, silhouette, palette and prop. Review original
   controls (e), (f), (g) are not refused. This remains a bounded named-entity
   guard, not exhaustive legal/IP recognition.
7. A generated style-token anchor references the first icon; accepted output
   references later icons. Padding, outline width and light are checked, with
   a whole-set deviation report. A live first sword returned a shield: that
   rejected source was retained and one replacement consumed the spare slot.
8. Halo QA compares black/white composites and contaminated opaque-rim pixels
   connected to outside haze; clean internal highlights are not treated as an
   outside halo. Uniform white inputs take the matting path. Trimmed frames need
   explicit valid offsets and are padded before packing; errors name the file.
   Chinese state names, including 攻擊, map to engine state names.
9. Video estimates have independent route/input-bound files. Tileset colors
   follow explicit hex colors or supported English/Chinese color terms. No
   paid-video request was made.

Every item began with a failing regression before implementation. The final
integration also tests direct prompt orchestration, texture-panel recovery and
resuming an existing export. Resumed exports retain earlier versions under
`export-history/`, and preserve original transport reference receipts.

### Calibration and held-out results

Small original images from both sets, reviewer motion controls, original icon
style tokens and source hashes live in `tests/fixtures/live-s14/`. Every PNG is
under 0.6 MB (largest 469,078 bytes). Reproduce measurements with
`python scripts/calibrate_game_assets.py`; its intermediate images stay under
`.scratch/s14-calibration/`. `calibration.json` preserves failures and limitations.

Character front/side samples from BOTH families form calibration inputs; each
back is held out. Identity boundaries come from reference spread and negatives,
not a tuned absolute BH value. Noise uses isolated-color fraction 0.12; halo
uses contaminated-rim fraction 0.15 with outside-haze topology. The held-out
backs were not used to tune these thresholds.

| Held-out class | Rimewick | Reviewer wolf/control |
| --- | --- | --- |
| Back identity ranking | 0.0663 < training negative 0.4529 | 0.1650 < training negative 0.7575 |
| Old/new pixel noise | 0.1742 / 0.0407: old FAIL, new PASS | 0.5781 / 0.0872: old FAIL, new PASS |
| Clean / injected rim halo | no false positive / detected | no false positive / detected |
| Final icon (7 / 3) | FAIL, outline +1 px | FAIL, outline -1 px |
| Original texture | FAIL, y wrap ratio 1.626 | slate PASS |
| Motion | original idle PASS | SLIDE, AIR, DUPSEAM all FAIL as expected |

Reviewer good walking and damaged limp/jump-seam controls were calibration
checks. The builder's old run also passes numeric checks, but its overlapping
legacy foot boxes do **not** validate anatomical left/right identity. This
limitation is recorded rather than relabelled as successful foot tracking.
Existing style/texture gates were evaluated without retuning them to the
held-out outputs. All six front/side/back noise/halo pairs produce the expected
clean-versus-damaged result. These are small regression samples, not population
accuracy claims or independent taste votes.

### One-line live CLI and delivered pack

The active built-in image-tool host uses the explicit queue transport because
native nested Codex appserver initialization is denied in this sandbox. Login
status succeeded; the failure was not presented as missing entitlement. Set
`VGS_IMAGE_TOOL_QUEUE` to `.scratch/s14-tool-queue` and put the supplied static
FFmpeg directory on PATH. The actual one-line CLI is:

```powershell
& C:\Users\User\.codex\skills\video-gif-studio\.venv\Scripts\python.exe scripts/imagegen.py demo game --prompt 'Original Rimewick fox swordsman with amber fur, teal scarf, ice sword and one magenta scar above the character-left eye. Crisp readable pixel clusters, original fantasy adventure assets.' --out .scratch/s14-fix-live --state .scratch/s14-fix-live-state --round s14-fix-live-complete --cap 20 --timeout 1800 --codex C:/Users/User/src/vgs-fx/scripts/image_tool_bridge.py --godot C:/Users/User/src/vgs-fx-private/tools/godot4/Godot_v4.7.2-stable_win64_console.exe --vendor .scratch/s14-vendor --allow-qa-fail --resume --experimental
```

The CLI owns generation, slicing, registration, conversion, QA and export. No
hand-assembled source pack or authored crop/pose plan is an input. A live host
must service the bridge; an unattended native-Codex run remains unverified in
this sandbox. Local correction/resume runs reused source receipts and generated
zero additional images. Original transmitted hashes remain in those receipts
when local preprocessing changes the derived reference pixels.

Actual use: **20 subscription images total**, including one rejected shield;
**$0**, **zero AI video calls**. Accepted sources comprise four views, one
six-expression atlas, four pose grids, one style anchor, eight icons and one
texture source. The last source was a whole presentation board instead of a
full-frame texture. A measured rectangle detector recovered the largest framed
slate swatch; original source and crop coordinates remain in its manifest.
The final texture passes numeric seam QA; semantic material review is pending.

Open `.scratch/s14-fix-live/export/project.godot`. Godot 4.7.2 actually loaded
and traversed every exported frame, producing `S14_GODOT_PASS`. The local root
certificate-store warning remains in the log; it did not prevent playback.
Other engine adapters are emitted but this round does not claim their runtimes
were tested. The portable ZIP excludes Godot caches/userdata and prior exports.

The **measured overall QA is FAIL**, and the explicit override is retained:

- Character height registration passes; expression differentiation fails.
  Identity/asymmetry remain unassessed.
- Idle fails its loop seam. Run fails left/right contact duration (240/80 ms,
  ratio 3.0). Attack has two-pixel late foot sliding, unassessed weapon/target
  contact and double-silhouette warnings. Hurt has measured foot sliding.
- Icons fail some outlines, light angles and cross-item value consistency.
  Whole-set median outline delta is 0 px, padding shortfall 0 px, and light
  deviation about 27.99 degrees (7 items assessed). Passing medians do not
  erase per-item failures.
- The cropped/repaired slate texture passes numeric QA.

The contact sheets were visually inspected. The head-severing preprocessing
bug is fixed, but mesh inbetweens still distort some poses. This is a usable
engine preview for review, **not an artistically accepted production pack**.

### Validation and patch replay

Validation completion and patch replay results are appended below.

Final broad suite: **992 tests, zero failures, the same two baseline environment
errors, 5 skips** (`.scratch/s14-fix-full-delivery.log`). The unchanged errors are
`test_install.InstallTests.test_same_source_symlink_is_preserved` (Windows
symlink privilege) and
`test_mask_review.Review.test_review_exports_overlay_contact_sheet_and_stability_report`
(locked overlay PNG during cleanup). The full run was collected before the
last wide-weapon regression and resume-export refinement; those final changes
were covered by the subsequent **38-test spec-14 suite** and **29-test game
suite**, both green. Final scenario suites: **26 tests**, green. Earlier full
runs (988 and 990 tests) also had zero failures and only those two errors.

Live export without the override returned `E_QA_FAIL` and created no directory
(`.scratch/s14-fix-export-gate.log`). The exported ZIP was unpacked to a different
scratch directory and passed actual Godot playback again
(`.scratch/s14-fix-portable-check.json`). There are exactly 20 distinct generated
source hashes, including the rejected image; the final resume generated zero.

Incremental patch order (each has a matching `.txt` commit message):

1. `01-relative-identity.patch`
2. `02-single-subject.patch`
3. `03-source-identity.patch`
4. `04-motion-registration.patch`
5. `05-pixel-conversion.patch`
6. `06-originality.patch`
7. `07-icon-anchor.patch`
8. `08-alpha-trim-states.patch`
9. `09-estimates-tiles.patch`
10. `10-prompt-demo-live-validation.patch`

The first nine were applied in order to an archived base under
`.scratch/s14-fix-replay`, with game/spec-14 tests green after each patch. The
final integration patch receives the same replay checks; the machine-readable
latest results are in `.scratch/s14-fix-validation.json`, with complete replay
history in `.scratch/s14-fix-replay.json`. An initial patch-08 path/newline
packaging error was corrected before delivery and its successful replay is
recorded. These patch files are ready for the owner to commit; no commit was
attempted from this sandbox.
