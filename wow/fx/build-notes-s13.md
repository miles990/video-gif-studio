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
