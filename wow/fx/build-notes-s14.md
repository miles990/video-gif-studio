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
