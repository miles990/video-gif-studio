# Slice 13 build notes — GPT-Image integration

Built in `C:/Users/User/src/vgs-img`, branch `s13-image`, using the supplied skill
Python and FFmpeg; patch base `b4c517c5aad1818556ddde0deadff3dc551abaea`.
Status: **experimental; independent acceptance and user visual
review pending**. No spec, acceptance, process, threshold, or example files changed.
No commits, merges, pushes, paid provider API calls, or new live images were made.

## Implemented slices

| Item | Implementation | Evidence / boundary |
|---|---|---|
| S-150 | Noninteractive Codex subscription adapter; ChatGPT auth guard; scrubbed child environment; no automatic paid escalation; exact paid estimate/approval/budget guard; ordered-reference content cache with OS process locks | Fake Codex and loopback HTTP sentinel; concurrent threads and separate CLI processes generate once; cache/failure/quota tests. Model recorded as `unreported`, reported model null. |
| S-151 | Shot-size/composition/light/colour/aesthetic prompts; per-shot keyframes; 9:16 uniform fitting; incremental regeneration; animatic and brief render integration; failed-shot cards; reference/keyframe contact sheet | Six-shot scenario, unchanged shot clocks, only changed shot cache misses. Opaque photos without a reliable local subject mask remain framing-unassessed and visibly labelled. |
| S-152 | Up to 16 hashed, sourced, role-labelled references; mixed-library rejection; controlled ORB + HSV identity checks; one corrective identity retry; explicit human review record | Distinct-pose positive and different-identity negative controls. Local CLIP cache lacks weights, and the venv lacks torch/transformers; no model download. |
| S-153 | Cyclic keyframe dissolve/camera motion; faithful disposal-aware GIF ingest; loop repair; decoded position/velocity seam gate; existing GIF encoder and sprite export | Broken/good loop controls, variable GIF delays, pixel-exact sprite reconstruction. Grok/fal comparison recorded as not run, with reasons; AI video is a separate user-approved operation. |
| S-154 | Native alpha first; isolated/attached fragment cleanup; edge despill; RGB checkerboard detection; one solid-background matting fallback; RGBA, binary-alpha GIF and background composites | Synthetic controls plus reused real alpha probe. Final alpha QA passes; graded alpha remains in the master. |
| S-155 | Actual source reference regeneration; bbox/polygon/markup masks; ORB/ECC registration; bounded feathering; exact outside-region pixels; brief delta and timestamped image-feedback hooks | Six-shot incremental edit rerenders only shot 2. Reused probe outside difference is exactly zero; inside ΔE2000 15.7455; registration residual 0.2042 px. Missing object location returns a concrete region requirement. |
| S-156 | Local palette/contour SVG tracing; static SVG checks before FX/timeline rendering; portable outlined glyphs; 512/2048/4096 renders | Seven unsafe fixture classes rejected; no scripts, external resources, raster payloads or font dependencies. Bundled renderer supports flattened polygon paths/basic shapes; unsupported curves/transforms/gradients fail explicitly. |
| S-157 | 2–8 individually cached directions; fork IDs; pairwise pHash checks; offline moving GIF picker; keyboard 1–8; explicit user choice saved/applied to storyboard | No automatic pick. Duplicate candidates flagged. Actual human aesthetic selection remains pending; test picks are simulated only. |
| S-158 | Append-only attempt/approval/reservation ledger; daily/round/run summaries; cap <=60; lower build cap supported; cache savings; C2PA container presence and derivative lineage | Atomic cap test; C2PA-added/stripped controls; schema checks for success/failure. Failed/ambiguous dispatch reservations conservatively count toward the cap. |

CLI mapping and exact commands: [image-generation.md](../../references/image-generation.md).
Capabilities: [image-capabilities.json](../../references/image-capabilities.json).
Manifest schema: [image-manifest.schema.json](../../references/image-manifest.schema.json).

## Capability and billing decisions

The supplied 2026-11-06 real-probe table takes precedence over earlier feature
claims. The subscription route exposes prompt, reference paths and transparency;
it returns PNGs and does not report/select an image model. Size, aspect and quality
are prompt-only controls. No native GIF, markup/mask or SVG is claimed.

The paid adapter implements the PNG generations protocol, tested only against a
fake local API. A reviewed, dated price table is required; no price is invented.
The exact request, model, quality, count, size, endpoint and price version bind the
estimate ID. Conversational spending consent remains the caller's prerequisite
before supplying the approval flag. Paid native GIF/SVG/edit and paid reference
requests are intentionally not represented as supported by this adapter.

The CLI's native binary can be read and its command-line help inspected here, but
`login status` cannot load the home directory in this sandbox. The npm Node wrapper
also has an EPERM home-resolution failure. No attempt was made to bypass those
restrictions. Existing probes supply real-image integration evidence; **0/30 new
live images** and **0 paid API requests** were used for this build.

## Verification

- Baseline: 808 tests, 0 failures, 2 environment errors, 5 skips (984.7 seconds).
- First integrated full run: 842 tests, 0 failures, the same 2 environment errors,
  4 skips (1015.9 seconds).
- Latest focused image suite: 40 tests, all pass (includes three encoded scenario tests).
- Existing brief and brief-scenario regression: 24 tests, all pass.
- Existing storyboard/taste regression: 50 tests, all pass.
- Final full-suite result: 848 tests, 0 failures, the same 2 environment errors,
  4 skips (1113.3 seconds). The final focused suite covers the last decoded-loop
  hardening changes. No new failures.
- `doctor.py`: passed; local GIF/video runtime ready; no OpenAI API key configured.
- Numbered patches 001–009 replayed sequentially against HEAD in an isolated
  `.scratch/patch-replay` copy, with image tests passing after every patch.
  Patch 010 also passed all 40 focused image tests after replay. The 40 affected paths
  reconstruct identically to the builder worktree (newline-normalized text).
- `git diff --check`: passed. Protected documents unchanged. No generated images
  or cache/ledger files are included in patches.

Baseline environment errors: Windows symlink privilege in
`test_install.InstallTests.test_same_source_symlink_is_preserved`, and an open-file
cleanup failure in
`test_mask_review.Review.test_review_exports_overlay_contact_sheet_and_stability_report`.
No attempt was made to modify those unrelated tests or system privileges.

Logs and generated evidence live under `.scratch/`:
`baseline-tests.log`, `final-current-tests.log`, `final-current-result.json`,
`image-final-focused.log`, `image-scenarios.log`, `brief-regression-s13.log`,
`doctor-s13.json`, `patch-replay-results.json`, `patch-content-verification.json`,
and `commits/*-tests.log`.

## Reused real-probe results

[Tracked measurements](image-probe-reuse-s13.json) preserve fixture hashes and
provenance. The original source PNGs remain unchanged in the private probe folders.
The inspectable preview is `.scratch/probe-reuse/index.html`.

- Transparent cat: zero speck ratio after cleanup; transparent fraction 50.31%;
  border fully transparent; edge-colour fraction 1.0; black outer-band luma 3.175.
- Café matcha-to-latte local composite: all pixels outside the expanded region
  identical; original regenerated outside drift 6.423/255; inside ΔE2000 15.746.
- Local café loop: 32 frames, 2.56 seconds; decoded alpha mismatches 0; existing
  loop QA passes position and velocity (seam ratio 1.439, speed ratio 1.033).
  An earlier loop failed the velocity check; the final code selects the wrap from
  decoded GIF frames and now rejects a delivery if that check fails.
- Outlined Chinese title “晨光咖啡”: static SVG, 529 vertices, 5,421 bytes, safe;
  renders at short edges 512/2048/4096 without needing a font at render time.
  Direct 512 vs reduced 4096 SSIM is 0.99523 (mean RGB difference 0.397/255).

## Remaining independent review

These are engineering results, not a claim of passing the complete live answer
key. The live Mia six-shot/refset run, human identity/shot-size/colour/composition
judgements, semantic edit/seam judgement, and the user's actual variant selection
remain pending. ORB is a controlled proxy and can refuse low-texture or strongly
changed-viewpoint material; no semantic object detector is claimed. Local loops
cannot invent articulated motion. SVG tracing is for flat graphics and must be
visually checked for lettering and contour quality. C2PA detects container presence
only, not signature validity or SynthID.

Every supplied feature remains behind the experimental generation gate. No quality
threshold or capability claim was relaxed to label an untested live result as passed.


## Fix round

This round uses 46 real subscription-output fixtures in
`tests/fixtures/live-s13/`. `provenance.json` records source paths, original SHA-256
hashes and dimensions. PNG fixtures are downscaled to at most 768 pixels on the
long edge and below 1 MB each. No provider is called by these regressions.

1. Local edits now estimate a similarity transform with ORB/RANSAC across changed
   canvas sizes, report residual, scale, rotation, inlier count and fraction, and
   refuse weak or spatially concentrated alignment. The native 1080x1920 edit
   has 696 inliers, median residual 1.62 px and a reported resolution-aware
   tolerance of 2.16 px (max(1 px, 0.2% of the short edge)). The expanded composite-region
   mask remains explicit; every pixel outside it is copied exactly from the source.
2. Identity uses alpha, uniform-background subtraction or existing local saliency
   support. The live positive histogram distance is 0.3393 and the negative is
   0.7183 (separation 0.3790). The positive threshold is 0.40 with a required 0.10
   control margin. Failed controls and inconclusive scene/pose matches are
   `unassessed`; only a separated negative-identity match permits automatic retry.
   Saliency is a foreground proxy, not a semantic subject detector.
3. An identity retry blocked by the image cap retains the first generation and
   labels its identity result with the retry error and `generation_retained:first`.
4. Large clear enclosed gaps are designed negative space, including antialiased
   outlines. Small or semi-transparent holes remain defects. The real sprite's
   roughly 1% detached specks are cleaned without filling its arm/body gap.
5. Loop QA now checks subject colour, timing/speed discontinuity and transparent
   canvas-edge clipping, and blocks failed delivery. Repair keeps duration within
   10%. Single-image motion uses fixed-scale sway and is explicitly a
   **breathing/sway placeholder**. Real idle animation requires multiple key poses
   (spec-14); no articulation is claimed.
6. Aspect differences requiring over 20% padding/cropping are refused as
   `aspect_unfixable`; differences up to 3% are uniformly cropped. Subject-region
   measurement also handles subjects touching the lower canvas edge.
7. Storyboard variants derive their prompt before validation. Login/CLI failures
   list alternatives. Partial keyframes exit non-zero while retaining successes.
   SVG refusal preserves the standard error code and asset path. Manifests retain
   native fake-transparency evidence, and mixed-refset errors list every image
   involved in suspicious pairs.
8. This checkout contains no reviewed price file. The strict-table alternative is
   implemented: nonempty version, ISO date within 30 days, no future date, and
   positive finite price and rounded total. A strictly positive `--max-usd` is
   required independently of the estimate, so default zero cannot authorize API
   dispatch. No prices or paid approval are invented.

Baseline: 875 tests, zero failures, two existing Windows environment errors
(symlink privilege and open overlay-file cleanup), five skips. Each fix has a
regression that failed before its implementation.

Final verification:
- Full suite: **906 tests, zero failures, the same two baseline environment errors,
  five skips**; `.scratch/full-verified.log`.
- Scenario suites: **22 passed**; `.scratch/scenarios-final.log`.
- Real-output regressions: **31 passed**; `.scratch/live-final.log`.
- All eight patches apply in order to commit
  `0935b2dec40f608e72640306295d1c8bc80fcb94`, with green checks after every item.
  The final stage runs **71 image and live-regression tests**; per-item logs sit
  beside the patches in `.scratch/commits/`.
- The two unchanged environment errors are
  `test_install.InstallTests.test_same_source_symlink_is_preserved` (Windows
  symlink privilege) and
  `test_mask_review.Review.test_review_exports_overlay_contact_sheet_and_stability_report`
  (open-file cleanup on Windows).
- Native-size edit and sprite checks also pass. The native edit has zero outside
  pixel drift; the native sprite has zero residual specks and preserves 12,171
  negative-space pixels. A delivered 24-frame sway has zero clipped frames.
  Inspect `.scratch/fix-round-review/` for the edit comparison, GIF and QA evidence.
- Largest fixture: 628,728 bytes. Fixtures include keyframes, both positive refs,
  negative refs, sprite, loop frames, local edit and all three supplied probes.

The eight patch/message pairs are listed in
`.scratch/commits/s13-fix-series.json`. Protected spec/acceptance/process/threshold
files were not changed; no commits were created in the read-only Git directory.

## Fix round 2

Built from `9a26408f17a992d956ed34aa255d4fbdc6a1108d` in the `s13-fix2`
worktree. The route remains EXPERIMENTAL. All provider calls in this round were
offline fakes; no new live generation or paid request was made. Source evidence
is the independent `review-s13-r2` run. Thirteen resized, provenance-hashed PNG
fixtures were added under `tests/fixtures/live-s13-r2/`; the largest is 498,955
bytes. Alpha fixtures use nearest-neighbour sampling to retain the original
low-alpha values. Native-resolution checks separately use the review originals.

Every item started with a failing regression. Seven sequential patch/message
pairs are in `.scratch/commits/`; no Git metadata was written. Old delivery files
were moved to `.scratch/commits-before-r2/` because deletion was denied by the
environment. Protected spec, acceptance, process and threshold files are unchanged.

| Item | Result and evidence |
| --- | --- |
| Alpha | Alpha 1–10 is treated as empty for hole analysis. Delivery removes remote haze while retaining colour-consistent coverage within two pixels of opaque material. Geometric wall profiles distinguish thin rings/limb gaps from deep body holes; area alone never authorizes a hole. Both native akimbo sprites and the key pass. Native removed-haze counts: 66,685 / 109,097 / 21,063; preserved gap areas: 11,678 / 19,197 / 93,322 pixels. Deliberate alpha-zero body-hole injections fail. |
| Identity | Reference-pair spread and ORB evidence are compared with all supplied negatives. No absolute fox-derived identity distance remains. Fox spread/nearest negative: 0.3393 / 0.7183; frog: 0.5565 / 0.8035. Frog A/B builds successfully. No-controls libraries remain unassessed rather than being rejected based on pose distance. Contradictory supplied controls still reject mixed libraries. `--identity-override same\|different` is available for refset build/check and generation, with the decision recorded. Refset approval does not automatically approve subsequent generated subjects. |
| Shot size | Saliency is never treated as a subject detector. Only supplied mattes, alpha or isolated uniform-background support can establish shot size. Support boxes over 85% of the frame are unassessed. All seven scene keyframes are unassessed for WS/MS/CU; isolated-subject controls still measure. |
| Loop | Holds are checked for signed motion reversal. Quantized ease-in/out at extrema passes; mid-motion holds, colour jumps and clipping still fail. Both fixture sets pass clean 48-frame amplitude-6/12 and 32-frame amplitude-3 bobs, including opaque composites. Repairs of 12×40, 24×40, 24×80 and 48×40 ms sources pass both loop QA systems and preserve duration. |
| Aspect | A 2:3 response to 9:16 is cropped only with isolated subject support that fits the crop. Scenes/oversized subjects are unfixable. Flat padding over 5% is never success, including integer-rounding overshoot. Both rounds exercise crop and refusal paths. |
| Small guards | E_GENERATION as well as E_CAP preserves the first identity-failed generation and records the retry error. CLI alternatives include Grok and local silhouette cards. All-failed keyframes report zero kept shots. Exact price-file SHA256 must be in the repo-reviewed list, currently empty; custom tables require explicit `--price-table-trusted`, recorded and bound to the estimate alongside SHA256. Fresh dates, tiny positive prices and positive budgets cannot confer trust. |
| Edit | ORB initialization is followed by ECC and independently measured forward/backward LK correspondence residuals. Acceptance remains ≤1 px; larger residuals are explicitly `needs_review`, including storyboard status. The native round-2 edit remains above acceptance: original ORB reprojection 1.5456 px; LK before ECC 2.9466 px, after ECC 2.7266 px (P95 5.6561, 597 validated points). These are different measurements, not a claim that ORB residual improved to subpixel. Outside the expanded mask remains bit-identical. Feathered boundary extra-gradient mean/P95 is 0.2683 / 1.3333 in 8-bit RGB channel levels over 856 edges. Coordinator visual review is still required. |

Calibration and held-out results:

| Decision | Both-set calibration / constraint | Held-out result |
| --- | --- | --- |
| Near-zero alpha 10, edge support 2 px | Sweeps at 6/8/10/12 all passed both calibration sprites; 10 covers the reported 1–9 haze. Explicit adjacent-edge and remote-haze controls verify retention/removal. | Key-ring positive excluded from threshold calibration: PASS, 11,990 gap pixels at fixture size, 93,322 native. |
| Hole geometry | A clear core plus thin-ring wall ≤ core radius; otherwise a limb gap must occupy ≥1.4 times its inscribed disk area and have either elongation ≥1.4 with wall ≤2× radius, or minimum radial wall < half median wall. Enclosed cores of radius ≥2 px that fail these tests are defects. Calibrated with round-1 arm gap and round-2 first akimbo. Circular body-hole injections at 20/35/50% of local opaque depth are rejected in both rounds, including the key shaft. | Second akimbo initially FAILED the first shape-only implementation. It was then used to revise wall profiles and is a regression, **not an untouched holdout**. Key-ring positive stayed excluded from calibration; subsequent artificial shaft-hole negatives exposed an overbroad wall-only rule, which was constrained by shape extent without changing the ring predicate. This additional use is disclosed in fixture provenance. |
| Relative identity | Histogram margin is half the refset's measured positive/negative separation; ORB floor is the midpoint of positive-minimum and negative-maximum matches. Both fox and frog controls separate without a fixed image-distance cutoff. Missing/overlapping controls do not produce verdicts. | Three fox scenes, four frog scenes, and the same-palette impostor are unassessed. Zero false identity failures on scenes and zero false impostor passes; this is conservative fallback, not semantic identity recognition. |
| 85% subject box | Requested conservative ceiling, checked with full-frame and isolated matte controls. Both live scene sets fail semantic isolation before any size verdict. | Round-2 square keyframe and round-1 cafe: unassessed. |
| Motion extrema | Direction dot product <0 establishes reversal; no new fitted speed/hold cutoff. Existing timing/colour/seam limits remain. Round-1 live sprite calibrates quantized trajectories. | Round-2 second sprite: all three bob schedules and opaque composites pass without further threshold changes. |
| 5% padding | User-required maximum, independent of content tuning. Both sprites fit a narrow crop; both scene sets are refused when subject safety is unknown. Existing 3% rounding-crop and 20% gross-aspect refusal limits remain. | Round-1 cafe and round-2 square scene forced to returned 2:3: both E_ASPECT_UNFIXABLE; round-2 sprite safely crops with zero padding. |
| Edit 1 px | User-required acceptance, never increased. LK round-trip consistency ≤1 px validates tracks without discarding tracks by their measured displacement. ORB support/inlier and ECC correlation gates retain the existing limits. Synthetic fractional shift, ±4/7° rotation and scale pass; 12° and nonuniform scale refuse. First-round edit calibrates the procedure and is now honestly flagged where local residual exceeds 1. | Second-round native edit: needs_review with residual/seam evidence above. No threshold was tuned to turn this holdout into a pass. |

Full numeric measurements are in `wow/fx/build-evidence-s13-r2.json`, including
alpha sensitivity, identity controls and each held-out verdict. The geometry
tests are heuristics with human review still pending; a transparent component's
artistic intent cannot be proven from alpha alone. The changed older assertions
remove the reviewed incorrect contracts (large body holes passing, saliency
framing, untrusted prices, and inflated native-edit tolerance).

Final verification (resumed after the interrupted run):
- Full suite: **926 tests, zero failures, the same two baseline Windows
  environment errors, five skips**; `.scratch/full-r2-resumed.log`.
  Errors are the symlink-privilege and open-overlay-file cleanup cases named in
  the previous round; no unrelated test or system privilege was changed.
- Scenario suites: **22 tests passed**; `.scratch/scenarios-r2-final.log`.
- All seven patches apply sequentially to the base commit above. Each item's
  focused tests pass (16 / 18 / 11 / 11 / 17 / 24 / 10 tests respectively).
  Per-item replay logs and commit messages sit beside the patches.
- Replayed files match the working tree (text normalized to LF, binary exact).
  All 13 fixture source hashes and the 600,000-byte per-file limit were checked.
  `git diff --check` passes; protected files and Git metadata are unchanged.
- `.scratch/commits/series.json` records patch hashes, messages, changed paths,
  replay test logs, and fixture hashes. No new provider requests were made.

Holdout limitation: there is no pristine alpha-silhouette image left in these
two supplied sets after the second akimbo and key-shaft counterexamples were
used for refinement. The unchanged key-ring predicate passing its positive
control does not make that source image independent again. Consequently the
strict untouched-image-per-class requirement remains unfulfilled for alpha;
an additional unseen silhouette is needed before claiming that validation.
The other held-out verdicts above remain valid for their stated checks.
