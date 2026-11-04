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
