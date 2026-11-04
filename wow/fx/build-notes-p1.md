# P1 build notes — 2026-11-05

Worktree: `C:\Users\User\src\vgs-fx`, branch `p1-edit`. No commit/push. No writes
to the installed skill or `C:\Users\User\src\video-gif-studio`. Runtime is the
coordinator's skill venv, with its static FFmpeg directory on PATH. Heavy work ran
serially. Models, external downloads and live ASR were not run.

This is an **experimental implementation with offline evidence**, not a claim
that P1's complete acceptance/visual-quality gate has passed. New visible styles
and features require explicit experimental opt-in. No reviewer scores were
invented and nothing was promoted into the stable catalog.

| Item | Implemented and measured | Remaining acceptance / limitations |
| --- | --- | --- |
| S-56 captions | Word JSON, SRT, script fallback, injectable timing engine, optional local-only faster-whisper; four presets; size/font/stroke/shadow/box/highlight/entrance/line/position/safe-zone controls. CJK rules at 8/12/16 units; pixel-safe reflow; cmap missing-glyph warnings + strict caption rejection. Word ink starts at frame 3 for 100 ms at 30 fps; pop 1.22×/180 ms; bounce overshoot and 400 ms settle; editable keywords; SRT export. | Cross-vendor visual gate is **pending** for all four presets. No packaged acoustic forced aligner; SRT/script proportional fallback is explicitly approximate. ASR live accuracy, full BG-HARD contrast/keyword-area acceptance and independent decoded video checks not claimed. ASS export absent. CJK lexicon is intentionally small/documented. |
| S-57 SFX | Six-category rules, user > Kenney > synthesis, recorded source/path/license/hash, same-kind dedup, sample-accurate onset/riser-end placement, existing P0 stereo/limiter/encoded QA. Offline user/Kenney fingerprint tests and decoded PCM ≤10 ms alignment pass. SFX-only delivered MP4 passes -14 ±1 LUFS and ≤-1 dBTP tests. | Kenney live downloader not executed; archive safety/license/provenance tested using authored fixture. Zero bundled third-party audio. Per-event music-relative level riding absent. Very sparse/pathological sound can still fail the delivery gate. |
| S-58 layered beats | Low/mid/high produce **8 / 15 / 31** cuts on SONG64's grid. Section boundaries cut; section effect families differ; accents use non-downbeat beats. Missing downbeats infer every fourth beat and report it. Renderer integration tested; qa_media adds decoded cut-to-downbeat median. | Section data is supplied, not detected. Full 64 s output visual-cut/Jaccard acceptance remains for coordinator. Source slots cycle; music offset must be zero after fitting/remap. |
| S-59 music fit | Three distinct edits **32 / 28 / 30 s** for 30 s target (one-bar tolerance); all musical endpoints on bars. 40 ms zero-crossing blend with smooth shoulders; last 50 ms **-64.83 dBFS** on fixture. Maximum join derivative / source p99.9 **0.918** (limit 1.5); max >8 kHz increase **+2.16 dB** (limit +6). Per-candidate WAV, source joins, sections, text list and remapped beats. No-audio MP4 + unchanged JSON/CSV markers tested. | Measurements use authored two-tone/chirp audio, not a real-song perceptual guarantee. No harmonic/key analysis. Song fitting decodes the bounded source into memory. No three candidates → clear error. |
| S-60 camera moves | Eight names, documented table, plan `move` shorthand, experimental registry, five Penner functions ×101 reference points (<1e-9 error), exact endpoints; analytic under/critical/overdamped spring. Crash/expo/smooth/punch/whip timing checks and alpha centroid ≤2 px test pass. | Independent encoded CHART curve fitting and cross-vendor visual gate pending. Spring time is physical seconds, not duration-normalized. |
| S-61 reframe | Cached grayscale or background_remove/BiRefNet RGBA masks; timeline alignment validation; output-space bounded smooth path, padding, missing-subject report, safe title band 64–79% height. Synthetic 120-frame walk: **2.829 px** max step, **0.274 px/frame²** max acceleration, **0** review flags, min headroom **35.7%** of subject height. Caption + reframe raster integration tested. | Real V-WALK and independent full-size platform measurement pending. Abrupt/large motion is marked needs_review; universal coverage is not claimed. Conservative padding can letterbox significantly. Masks must already be aligned to edited timeline. |
| S-62 proxy review | Offline HTML, thumbnail per recorded shot/effect/caption event, synchronized keep/replace, JSON export, dependency/code hashes, changed-shot cache. Eight-shot measurement: **2 rerendered / 6 reused**, all six untouched PNG sequences byte-identical; changed-shot MAD **0.175 / 0.179**. Wall time **2.844 s → 0.888 s (31.2%)**. Length-change test shifts later times and reuses unaffected PNGs. Silent assembly plan provided. | Independent shots only: rejects cross-shot transitions/history/previous-frame/reframe dependencies. Immutable PNGs hardlink when possible (copy fallback). No automatic beat re-snap after length changes. Final audio is separate. Chrome console check pending. Timing depends on workload/filesystem. |

The measurement JSON and contact sheet are retained:

- [measurements-p1.json](measurements-p1.json)
- [p1-caption-contact.png](p1-caption-contact.png), visually inspected by builder
  for clipping/placement; this is **not** the independent two-reviewer gate.
- [check_p1.py](check_p1.py), reproducible serial fixture harness; temporary media
  goes to the OS temporary directory, not into the repository.
- [tests/test_p1.py](../../tests/test_p1.py): 42 new offline tests; fixture
  [p1_words.json](../../tests/fixtures/p1_words.json) explicitly says it is authored
  timing data, not recorded Whisper inference.

## Regression / runtime evidence

- Initial complete suite: **284 tests, 0 failures, 2 errors, 5 skips**, 197.546 s.
  [tests-p1-full.log](tests-p1-full.log). This includes the first 34 new tests.
- Expanded P1 suite after the fixes: **42 tests pass**, 3.017 s. The final added
  regression proves standalone reframe's 10 ms exposure manifest can be consumed
  by the existing composer (rather than writing unsupported 33.333 ms durations).
- Final full suite: **292 tests, 0 failures, 2 baseline errors, 5 skips**, 197.163 s;
  **285 passed**, including all **42 P1 tests**. No new failures/errors versus the
  supplied 250-test baseline. [tests-p1-final.log](tests-p1-final.log).
- The two baseline environment errors are Windows symlink privilege
  (`test_install.test_same_source_symlink_is_preserved`, WinError 1314) and an
  existing mask-review test leaving `overlay.png` open during temporary-directory
  cleanup (WinError 32). Neither test was changed or silenced.
- `scripts/doctor.py` exits 0: Pillow/NumPy/OpenCV and FFmpeg/ffprobe ready. Optional
  rembg is absent; no model-dependent tests require it.
- `rg 'for (y|x|row|col|px) in range' scripts/fx` finds no per-pixel Python loops.
- `git diff --check` passes. Protected spec/acceptance/process documents have no
  diff. Git status remains uncommitted on `p1-edit`.
- Legacy stable catalog remains exactly the six effects/four transitions from P0;
  existing feature-flag tests pass. No-SFX audio retains its original branch. A
  separate historical-commit golden-video comparison was not run in this slice.

## P0 review documentation fixes

`references/music.md` now states ducking does not engage below approximately 8 dB
speech-to-estimated-floor SNR and explains the detector is an energy heuristic.
`references/fx.md` documents that a jump next to a dropped frame reports their
combined missing interval. Intake now records raw observed PTS gap, nominal frame
period, existing missing length and that interpretation rather than guessing the
unobservable causes separately.

## Coordinator live handoff

1. Optional ASR: use the optional-engine venv with
   `scripts/captions.py --audio SPEECH.wav --model C:\Users\User\.codex\skills\video-gif-studio\.runtime\models\whisper --experimental --out NEW_DIR`.
   After the fix round, `--model` also accepts a single-model cache root, or use
   `--model small --model-cache ROOT`. For Traditional Chinese add `--language zh`
   and (after installing optional OpenCC) `--traditional`.
2. Kenney: run `download_kenney_audio.py --pack interface-sounds --out NEW_DIR`
   (or `--zip` for a manually retrieved official archive), then author sfx-map.json.
   Attribution is in THIRD_PARTY and both audio file headers.
3. Produce two-material clips for all new visible presets/moves, arrange the two
   independent cross-vendor reviews and user 3–5 clip spot checks. Keep experimental
   until those gates pass; this builder cannot supply their judgments.
4. Run the acceptance's real/synthetic phone corpus, decoded CHART/V-WALK/BG-HARD
   measurements, and Chrome review-page interaction. Findings above distinguish
   completed offline coverage from those unrun acceptance steps.

## Fix round

2026-11-05, branch `p1-edit`. This section supersedes the affected implementation
descriptions above. Work and retained evidence are confined to this worktree;
scratch fixtures were created in OS temporary directories. No installed skill or
other source checkout was edited, no commit/push, no model inference/download,
and all heavy runs were serial.

| Review item | Fix and measured evidence |
| --- | --- |
| 1. Reframe | Largest inscribed 9:16 source crop; target is clamped before smoothing, speed adapts to nearby subject velocity, coverage projection takes priority. At **370 source px/s**, small (90×260) and large (360×850) subjects on 1920×1080 both remain fully inside **110/110 frames (100%)**, with **0.0% black pixels**. Maximum output step **21.926 px/frame**; acceleration **2.178 / 3.000 px/frame²**. Acceptance-4 V-WALK (640×360, r=40) measures **100/100 frames inside**, minimum rendered subject area **98.735%** of scaled source area, **0% black**, measured at 270×480. Impossible fits are reported and preserve head over feet. |
| 2. Whip | Returns to the exact original raster at 160 ms; early/truncated intervals are rejected. Edge extension during motion replaces reflected collage. Maximum sampled displacement **0.513 frame widths/frame**; whoosh peak **133.333 ms** after onset, matched to that motion peak within **one 48 kHz sample** in decoded PCM. |
| 3. Whisper | NumPy real scalar times become native floats. FFmpeg decodes both live TTS WAVs to mono **16 kHz float32 arrays** before the injected transcription adapter. Real raw fixtures pass: **19 English / 29 Chinese words**, preserving English spaces. Local snapshot, cache root and model-name + cache routes tested. Added `--language`, `--model-cache`, `--traditional`; optional OpenCC `s2twp` and Apache-2.0 attribution documented. Tests inject the recognizer/converter; live model and installed OpenCC execution remain for coordinator. |
| 4. Caption look | Bold font preference, 112 px default / 8 px stroke at 1920 high; four distinct treatments: yellow pop, mint karaoke/typewriter, restrained clean, navy boxed bounce. Active-word highlight and repeated word entrances; boxes grow with visible text. Raster tests distinguish all four. Actual checkerboard/noise/striped frames were inspected. |
| 5. Line breaking | Sentence-final punctuation and pauses ≥150 ms create boundaries. Width and font-pixel reflow rebalance orphan tails; short phrases can shrink uniformly (≤26%) to keep a final word attached. Version v2.0, comma number 1,234, skin-tone and ZWJ emoji remain atomic. The first visual inspection caught a pixel-reflow orphan; it was fixed, regression-tested and the sheet regenerated. |
| 6. Missing glyphs | Unsupported graphemes are dropped as units with `U+XXXX` warnings and manifest `dropped_codepoints`; no strict caption failure or tofu output. Original word text and timing remain exportable. This implementation chooses the permitted drop-with-warning route rather than promising color emoji font support. |
| 7. Density / QA | SONG64 low/mid/high **8 / 15 / 31 cuts**, **8 / 16 / 32 accents**. Layered auto styles have **0 white flashes**, with hits on selected downbeat cuts instead of all accent kicks. The 8 s delivered demo passes unchanged flash QA (**0 events**). Rhythm scoring excludes bounded known visual impulses while retaining observed shot cuts; demo median **0 ms**. |
| 8. Music / crash_out | Too-short music error names both durations and suggests shortening target or `--no-music`. crash_out begins at **1.0×**, eases into preparation, then exponentially returns to **1.0×**; continuous curve regression peaks at **1.35×** without the first-frame jump. |

Evidence and reproducibility:

- [check_p1_fix.py](check_p1_fix.py): serial harness; no network or model calls.
- [measurements-p1-fix.json](measurements-p1-fix.json): geometry, pixels, density,
  delivered stream and decoded QA measurements.
- [p1-fix-contact.png](p1-fix-contact.png): four caption presets at two reveal
  times on busy backgrounds; small/large fast reframes; whip at 0/33/100/160 ms.
  Builder actually opened and inspected both versions, including the final one.
- [p1-fix-decoded-contact.png](p1-fix-decoded-contact.png): actual decoded frames
  from [p1-fix-demo.mp4](p1-fix-demo.mp4), **1080×1920 / 30 fps / TikTok / 8 s**.
  [manifest](p1-fix-demo-manifest.json), [QA](p1-fix-demo-qa.json). Overall QA is
  WARN (pops/sparse-audio silence), not a blanket PASS; flashes and audio delivery
  checks pass. Temporary source paths in the manifest refer to generated fixtures;
  rerun the harness to regenerate them.
- [test_p1_fixes.py](../../tests/test_p1_fixes.py): **18 new regressions**;
  complete targeted P1 run **60 passed** after visual fixes.
- [tests-p1-fix-full.log](tests-p1-fix-full.log): final suite **310 tests,
  303 passed, 0 failures, 2 baseline environment errors, 5 skips**, **194.376 s**.
  The errors remain Windows symlink privilege (WinError 1314) and the existing
  mask-review overlay.png cleanup lock (WinError 32); neither was changed or
  suppressed. **Zero new failures/errors versus 292 / 2 baseline.**
- Final `git diff --check` passes; branch is `p1-edit`; protected spec*/acceptance*/
  process.md files have no diff. New visible behavior remains experimental.

This is still experimental, **not a declaration that full P1 acceptance or the
cross-vendor “pro short-video” viewing gate has passed**. Adaptive tracking can
exceed the old fixed 12-output-pixel speed ceiling to keep fast subjects inside.
Tall subjects may overlap the title band; no universal ≤2% caption/subject overlap
claim is made. Independent viewing review and coordinator live Whisper/OpenCC
reruns remain outstanding. No spec, acceptance or process document was edited.
