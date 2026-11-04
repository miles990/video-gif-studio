# Fix round 1 — resumed from fabaf61 (2026-11-04)

This section supersedes the original handoff below. Work stayed in
`C:/Users/User/src/vgs-fx`; no commit/push, installed-skill edits, examples/ edits,
required-dependency changes or spec.md/acceptance.md edits. The coordinator's concurrent
progress.md/spec-2.md/acceptance-2.md changes were left alone. Two matte PNGs are retained
under demo/assets for the coordinator's eventual commit; no inference is needed to build.

**Builder status: all eight requested fixes implemented and measured.** Two new films
and frame evidence are ready for independent review. Memorable/striking quality and
music listening are not independently certified. The optional 10 fps benchmark remains
unmet. The old strict QA hard-cut-vs-transition mismatch remains a documented limitation,
not a claim that the old acceptance wording has been waived.

## Per-item result

| Fix | Status | Measured evidence |
|---|---|---|
| 1 — audio accent sampling | Fixed | Onset and energy maxima are sampled on the audio clock/over each output exposure; onset supports decay_ms (default 120). Synthetic alternating clicks, in_ms 0 and 20: loud Y=255, quiet Y=94, gap **161**, all visible beats flash in all four cases. The first untrimmed beat is also asserted. Flash first-decay samples prevent repeated maxima shifting decoded peaks. |
| 2 — both demos | Rebuilt and visually inspected | Same-shot BiRefNet fish, **8/8 freeze beats**, centroid movement **19.15 / 19.30 px**, subject rest **176 / 178 px** and peak **195 / 191 px** on 360px canvas; scale 1.06, rotation −3°, background multiplier .55 and blur 12. Freeze luma **51.36 / 65.59**, versus source frames **65.82 / 95.58**. Hex shutter at 7320 ms; whip at 5860 ms has no stacked flash; closing accents through **8800 ms**, total **9160 ms**. Both films' flash peak errors **0 ms**, luma rises **102.50–128.30**. |
| 3 — whip geometry | Fixed | Adjacent shots pan as one continuous strip; no BORDER_REPLICATE. Both directions tested at **p=.25/.5/.75**; edge marker occupancy ≤2 columns, no stretched edge fill; output alpha 255 for opaque sources. Preview and both films' transition neighbors were viewed: no extra seam line or replicated streak. The moving shot boundary and directional blur are intentional. |
| 4 — fresh rebuild | Implemented and run | build_demo.py extracts all four repository videos, rebuilds cards/plates and both 19-line plans using the two retained matte PNGs. No optional venv needed. Final render/export **57.40 / 56.05 s**, excluding source preparation. GIF **2,928,071 / 2,839,422 bytes** at 240×135 (12.5fps sampling); both below 3,000,000 bytes. Verification is a second reproducible script. |
| 5 — reverse | Fixed on requested evidence | Both new films: exactly **3 cuts**, flash_cut **2920**, whip_pan **5860**, hex_shutter **7320 ms**, all **0 ms** error; **2920–5860 ms still** written in both validated drafts. 1200ms synthetic dissolve: **one crossfade**, center **1600 ms**, duration **1200 ms**. Feature continuity rejects panning-under-flash false cuts; same-palette flash and animated-card holds have offline regression tests. Heuristics remain reviewable, not universal recognition. |
| 6 — validation/library gaps | Fixed | 101ms duration errors (10ms multiples required); 20ms transition errors at 25fps (minimum **40ms**); downbeat 250 against beats [0,500,1000] errors; nearest blending warning names the transition; broken bad.py:1 warns and is skipped, good files load, same-name overrides are still reported. |
| 7 — GIF timing | Fixed | ≤20ms exposures merge with neighbors, preserving total time. Mixed synthetic exposures preserve **220ms** with no short decoded frames. Both actual GIFs decode to **9160ms**, same as MP4: **0ms drift**, minimum exposure **40ms**, alpha mismatch **0 pixels**. |
| 8 — defaults/docs | Fixed | zoom_punch default **1.07**, premultiplied alpha tests retained; original + 6 effects + 12 transition phases = **19 preview tiles**, measured **0.295s**. Human-readable --list plus --json verified. Missing rembg in the normal venv exits **2**, names requirements-matting.txt, no traceback. BiRefNet live comparison and opencv-python-headless documented. Beat This! neon fixture **163.636 BPM**, integer-ms downbeats, double-time caveat. |

## Tests and retained evidence

- `tests-full-round1.log`: **182 tests**, **0 failures**, **2 existing environment
  errors**, **4 skips**, **43.500s**. Errors remain Windows symlink privilege
  (test_install) and open overlay.png cleanup (test_mask_review). No optional engine ran.
- `fix-tests-resumed.log`: final focused **10/10** regression tests pass (including
  the first audio beat and both onset/energy channels). The earlier full FX subset
  also passed. Tests cover requested items 1, 3, 5, 6 and 7 plus reverse false positives.
- `fix-evidence.json`, `catalog.text`, `catalog.json`: long-dissolve, missing-backend,
  catalog and preview evidence; reproduce with `python wow/fx/check_fixes.py`.
- `audio-render-evidence.json`: four actual encoded MP4 renders, decoded again with
  OpenCV (onset/energy × in_ms 0/20). Every visible beat, including the first at 0,
  flashes; loud **255**, quiet **94**, gap **161**, matching the offline pixel tests.
  Reproduce with `python wow/fx/check_audio_render.py`.
- `demo/build-results.json`, `timings.json`, `verification.json`, both reverse reports
  and draft plans: final quantitative evidence. Both MP4 QA reports are **PASS** under
  documented timeline-join semantics. Draft source frames live under ignored work/;
  `verify_demo.py` regenerates them from the delivered MP4s.
- `demo/inspection-{a,b}-1.jpg` through `-7.jpg`: every beat −40/0/+120/+280ms,
  transition neighbors and .25/.5/.75 targets, ending frames. All sheets were viewed;
  final flash-decay neighbors and the 19-tile preview were re-viewed after changes.
- `demo/assets/`: two source freezes, two mattes, green-background checks and provenance.
  Matte RGB equals source RGB exactly. Nearest prepared source frame is **72 (2880ms)**
  in both opening clips; thumbnail MAE **1.40 / 1.70** documents extraction differences.
- Final protected-path diff is empty; `git diff --check` has no whitespace errors.
  Separate coordinator-created second-round files were not changed by this builder.

## Memory and performance

Only one heavy job ran at a time: one BiRefNet session processed two frames sequentially
with NUMBA_DISABLE_JIT=1 and OMP_NUM_THREADS=2, then exited before tests/rendering.
Measured inference was **41.48s / 58.25s**, excluding shared initialization. Coordinator
load-inclusive comparison remains **u2netp 10.6s / BiRefNet 61.6s** in live/README.md.
The normal rebuild uses retained mattes, never loads rembg/torch/Beat This!.

Optional performance target **not fixed**: benchmark-latest.json gives **3.276 fps**,
**90 frames / 27.470s** at 1280×720, 3 effects + crossfade, excluding codecs and PNG I/O.
No performance refactor was mixed into this correctness/visual repair round.

---

# Original handoff (historical; superseded above)
# FX builder handoff — 2026-11-04

Worktree: `C:\Users\User\src\vgs-fx`, fx-framework. No commit/push. No edits to
examples/, spec.md, acceptance.md, requirements.txt or the installed skill. Used only
the installed skill's Python/runtime as read-only dependencies. The changed source and
evidence remain uncommitted for the coordinator's independent review.

**Overall: unfinished acceptance candidate.** The implementation and two films are
reviewable; S-2's strict zoom stripe-growth condition and S-展示's strict hard-cut QA
invocation are not met. Do not relabel the entire delivery as accepted or “wow exceeded”.

## What was built

- scripts/fx/: pure typed registry/decorators, deterministic context, envelope evaluator,
  six single-function effects and four single-function transitions. Internal geometry
  uses premultiplied alpha; public functions preserve uint8/float32 dtype.
- fx_render.py: strict plan validation, source/post effect stages, exact beat accent
  sampling, centered transitions, preview/catalog, plugin override/provenance, user library.
- compose_timeline.py: minimal extraction of resolve_plan/export_timeline. No output
  semantics change for legacy plans. Three plans compared against `git show main` have
  identical per-frame SHA256 and durations: 101, 71 and 64 frames (baseline-parity.json).
- music_sync.py: reusable 10ms native-WAV RMS/onset curves; optional injectable Beat This!
  CPU engine with explicit RMS fallback and no fabricated downbeats.
- background_remove.py: BiRefNet choices with unchanged u2netp default and clean errors.
- fx_reverse.py: clean-room thumbnail heuristics, exact/gradual edits, flashes, directional
  blur, zoom estimates, freezes, beat ratio, shot sheet and directly valid reconstruction
  draft. No rea-video source was accessed. Inferred contaminated frames use reviewable
  clean-sample holds, not an assertion that unseen motion was recovered.
- Documentation, optional dependency provenance and two material demos under demo/.

## Verification

Full suite with the supplied Python and the existing managed FFmpeg directory on PATH:
**172 tests, 0 failures, 2 pre-existing environment errors, 4 existing skips**, 42.255 s.
See tests-full-final.log. The unchanged errors are:

1. test_install.InstallTests.test_same_source_symlink_is_preserved: Windows symlink privilege.
2. test_mask_review.Review.test_review_exports_overlay_contact_sheet_and_stability_report:
   Windows cleanup of an open overlay.png (WinError 32).

All **26 new tests pass with PATH empty**, so non-video FX/reverse tests actually ran
without FFmpeg and without skips (tests-no-ffmpeg.log, 11.287 s). They cover builtins,
cross-process hash seed stability, alpha/palette, envelopes, exact timestamps, all eight
specified validation errors, actual plugin rendering/overrides, downbeats/fallback,
native onset/energy, injected matting, inverse recognition and source-replacement roundtrip.

All eight required invalid-plan CLI probes exit nonzero without traceback or creating
--out, before rendering; maximum wall time 0.470 s (validation-cli.json). Final
`git diff --check` is clean; examples/ status is empty and protected spec/acceptance/
requirements.txt have no diff. Both final demo and reverse reconstruction plans validate.

S-14 MP4 with audio: cuts at 1000, 2040, 3520, 4480, 5200 ms versus truth 1000, 2000,
3500, 4500, 5180; flash 1520 vs 1500; freeze 3520–4480 vs 3500–4500; zoom at 3000,
estimated scale 1.125; beat alignment 4/5. Report and valid draft:
roundtrip-mp4/reverse/. Offline source-replacement rerender is asserted in test_fx_reverse.

Three additional known edit orders (check_reverse.py) produced this measured confusion
table; **these are synthetic fixtures, not a general accuracy claim**:

| Truth \ detected | cut | crossfade | whip_pan | hex_shutter | flash_cut |
|---|---:|---:|---:|---:|---:|
| cut | 3 | 0 | 0 | 0 | 0 |
| crossfade | 0 | 3 | 0 | 0 | 0 |
| whip_pan | 0 | 0 | 3 | 0 | 0 |
| hex_shutter | 0 | 0 | 0 | 3 | 0 |
| flash_cut | 0 | 0 | 0 | 0 | 3 |

Hard cut/flash timing errors are within one 40ms analysis frame. Raw evidence is
reverse-confusion.json. Real neon smoke test completed with 0 candidate cuts (≤12),
reflecting conservative filtering; this does not establish recall of subtle real joins.

720p benchmark: **3.27 fps**, 90 frames in 27.49 s, three effects plus crossfade, excluding
PNG/codec I/O; target 10 fps not reached. Machine/version/method: benchmark.json and
references/fx.md; reproduce with benchmark.py. Final 640×360 demos render at 9.53/9.29
pixel fps; full PNG/GIF/MP4 export takes 44.515/45.021 s. Exact peaks and audio/decoded
QA are in demo/README.md and demo/timings.json.

## S-item status

“Implemented/tested” below means builder evidence, not independent acceptance approval.

| Item | Status | Evidence / remaining gap |
|---|---|---|
| S-1 | Implemented/tested | both dtypes, purity, seed, cross-process stability, ctx, endpoints |
| S-2 | **Partial** | 6+4 builtins and alpha tests; zoom default 1.014 intentionally fails ≥5% stripe-growth condition |
| S-3 | Implemented/tested | constants/keyframes/beat selection/offset, centered edits and exact accents |
| S-4 | Implemented/tested | shared parser/exporter, pixel parity, complete defaults/provenance, audio deliveries |
| S-5 | Implemented/tested | project plugins, override messages, catalog and 18-tile preview |
| S-6 | Implemented/tested | all 8 requested error cases, location/options, pre-render validation |
| S-7 | Measured; speed bonus missed | 3.27 fps at 720p; nearest palette and alpha retained |
| S-8 | Implemented | fx guide, routing, timeline/music and READMEs updated |
| S-9 | Implemented/tested | 26 new passes; 172 total, same 2 environment errors |
| S-10 | Implemented/tested | 10ms linear RMS/onset, native WAV and explicit compressed decoder errors |
| S-11 | Interface/fallback tested | fake engine fixture, downbeats, MIT attribution; live model run pending coordinator |
| S-12 | Options/provenance tested | BiRefNet choices and injected masker; live speed/quality comparison not measured |
| S-13 | Implemented/tested | env-overridable user library, precedence, disable flag, source SHA256 |
| S-14 | Implemented/tested on fixtures | PNG+MP4 roundtrips, reconstruction plan, confusion, real smoke; heuristic review remains |
| S-展示 | **Partial acceptance candidate** | two films, decoded beats/QA pass under timeline joins; strict --expect-cuts fails for transitions |

## Deviations and reasons

- Acting as the requested builder, wrote code directly; the outer coordinator retains
  independent review. An attempted delegated task failed before starting with a thread
  context error; no subagent output was used or represented as review.
- Added source/post stages: border-after-blur created ugly broad streaks; compositing the
  complete card before a transition is the correct layer order.
- Used nearest-10ms event samples in addition to nominal fps: the reused exporter emits
  100fps repeats, so exact accent samples are needed to meet one encoded-frame timing.
- Kept zoom_punch's transparent default conservative (scale=1.014) to meet the default
  alpha-area bound. A strong centered zoom crops an edge-touching stripe; the S-2 SYN
  stripe-width criterion conflicts with that ordinary centered zoom behavior. The strict
  stripe-growth criterion remains **unmet**, not waived; explicit scale=1.2 works for an
  intentionally strong opaque punch and the inverse test.
- QA uses --timeline for designed transitions/continuation joins. The requested strict
  --expect-cuts invocation requires discontinuities that this smooth edit does not have.
  Retained its FAIL report under demo/work/archive-qa-initial/ and marked S-展示 partial.
- Replaced reflected whip edges with edge replication after inspection found a duplicated
  subject at the edge. Horizontal blur and endpoint behavior remain tested.
- A cleanup deletion was rejected by automatic command review (no detailed reason). Older
  generated directories were instead preserved and moved within the verified worktree to
  demo/work/archive-*; no user/source data was deleted. Final masters are master-a/b only.

## Remaining work for acceptance

Resolve the strict zoom/alpha tradeoff and hard-cut-vs-transition acceptance mismatch with
the independent setter/reviewer; do not edit the answer key here. Independent full-film
judgment and actual audiovisual playback are still needed. Run optional Beat This! and
BiRefNet in the coordinator's separate venv; no install or live-model claim was made here.
Performance needs profiling/optimization before claiming the 10fps 720p bonus. Existing
baseline environment errors were not altered as unrelated scope.
