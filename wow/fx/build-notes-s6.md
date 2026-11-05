# S6 build notes — director-usable effect layer

2026-11-05. Worktree `C:/Users/User/src/vgs-fx`, branch `s6-director-fx`, base
`4447bc077437f02f96083b5c981125d7ea7f620b`. No commit or push. Specs, acceptance
documents, process.md and thresholds.md were not edited. No installed skill or
other video-gif-studio checkout was modified. Render and test jobs ran serially.

**This slice is implemented but is not acceptance-complete.** Independent gates
were not fabricated, C thresholds were not activated on the candidate, and the
cutout calibration's small range is reported honestly.

| Item | Implementation and measured evidence | Remaining acceptance gap |
| --- | --- | --- |
| S-70 | 43/43 inherited stable items have cards; six effects, 37 transitions. Additive JSON metadata, draft-2020-12 schema, controlled intents, requirements, use/avoid guidance, conflicts, 720p cost, technical provenance, style tags and preview paths. 43 two-second previews; 0 decoded WCAG violations after demonstration-plate repair. Offline catalog bundle **6,295,847 bytes**. | Nine inherited stable items have no independent technical record: six original effects plus crossfade, whip_pan, flash_cut. Cards explicitly say pending review. Mobile CSS is responsive; independent first-reader/mobile review was not run. |
| S-71 | **66 rows**, 11 per effect. Raw dY/area8/SSIM/Farneback/general/red flash/sharpness; reproducibility from two empty caches under seeds **0 and 123** has maximum absolute perceived difference **0.0 for all six effects**. A new dim plugin automatically produced 11 monotonic rows, max perceived 1.0. Registry links the table. | Cutout's identity-to-default mix only reaches **0.021052**, below the required .10 grid maximum. No inflated score. Withheld perceptual ranking/2AFC has not run. STD-HK has anchor measurements, not a complete second calibration table. |
| S-72 | **14 JSON recipes**, all ingredients stable, 11 with staggered multi-layer composition, explicit substitutions, 3 intentional silent recipes, shaped build/breathe. **14/14** validate and render. Recipe previews: **0 WCAG violations**, 123.22 s total serial render/check time. One-line plan expansion and measured visual-peak SFX alignment work. | All 14 combinations remain experimental pending independent technical gates. Visibility is inconclusive while its C instrument is inactive. freeze_card requires a freeze source; title_pop requires precomposed text. |
| S-73 | Fixed F-class general and saturated-red flash checks, per-pixel opposing transitions, cumulative fades, sliding one-second windows; qa_media blocks violations. Paired decoded reference analysis, motion-relative onset, sharp4 + SSIM persistence, texture/transition exceptions, manifest/QC reports. Predeclared anchors exclude recipes. | Visibility anchor distributions overlap: good **0.083946..2.503454**, weak/cut **0.087931..0.530130**. No valid single onset cutoff was activated. The explicit STD-P sharpness controls separate at a proposed **0.289032**, margin **0.064520**; independent audit/next-round activation still required. |
| S-74 | Registry-driven U budgets per section energy, 4-second sums, per-bar density, conflicts, sustained flash warnings, conservative WCAG preflight. Tests cover sparse/quiet/dense/drop plans and a doubled calibration table. | Taste defaults are declared defaults, not claimed to be learned from user reference films. |
| S-75 | Three source-backed key-moment proxies, thumbnails, decoded measures, costs, HTML comparison and selected-plan/storyboard annotation. Pairwise peak thumbnail dY **21.27485, 18.00206, 23.11823**, all >4. Selected derivative validates. | Candidates use source timeline samples and do not bake in existing effects/transitions. Recipe review still needs experimental opt-in; unknown visibility is not a pass. |
| S-76 | Deterministic effect/recipe query; numeric intent/gate/cost/diversity reasons. 40 intent/section/needs combinations tested, repeated query bytes equal across hash seeds; 12-choice diversity test passes. | Normal queries correctly exclude the 14 unpromoted recipes. Gate ranking uses technical evidence, never AI appeal. |
| S-77 | 35 new unit tests plus serial media/calibration integration evidence. Representative legacy main/current render: **25/25 PNG SHA-256 values identical**. | Full final suite result is recorded below; withheld independent questions and all historical demo-plan SHA comparisons have not been executed. |

## Validation

Original-suite run: **561 tests**, **0 failures**, **2 environment errors**,
**5 skips**, 315.963 s (`test-s6-full.log`). The two errors are the documented
Windows symlink privilege failure in `test_install` and a locked `overlay.png`
cleanup in `test_mask_review`. The latter does not belong to this slice.

The final **35 new unit tests passed in 5.278 s** (`test-s6-unit.log`), including
the repeated-recipe-instance/audio-anchor regression.
Final suite: **596 tests in 324.640 s, 0 failures, the same 2 environment
errors, 5 skips** (`test-s6-final.log`). That is **35 additional tests and zero
new failures/errors**. The test command exits 1 because the two baseline
environment errors remain; it is not described as an all-green run.

`jsonschema` is not installed in the supplied environment. No package was
installed into that environment. The shipped schemas are standard draft 2020-12;
the offline validator exercises their used vocabulary and fails closed on unknown
assertions. Independent validation with the third-party jsonschema package remains
available to the acceptance runner; it is not represented as having been run here.

Evidence files:

* `references/fx-calibration.json`: rows, raw quantities, source hashes, machine,
  versions and warmed timing. Costs span **9.42435..233.73930 ms/frame** at 720p.
  OpenCV one thread, 3 warm-ups and 20 timed frames per item; Windows system CPU
  utilization sampled before the serial benchmark (0.0% for this run).
* `s6-calibration-repro.json`, `test-s6-calibration.log`: fresh-cache reruns and
  automatically discovered plugin.
* `references/fx-instrument-anchors.json`: declared control measurements and
  proposals. A visibility label is not treated as a non-destructive-blur label;
  the sharp4 proposal uses A6-1's explicit STD-P negative controls.
* `gate/s6-recipes.json`, `test-s6-recipes.log`: all 14 decoded recipe results;
  technical review status remains pending and appeal is not scored.
* `s6-integration.json`, `test-s6-integration.log`: actual plan compilation,
  render, QA, SFX, legacy SHA comparison, candidates, and chosen derivative.
* `s6-preview-repairs.json`: five original checkerboard demonstrations triggered
  flash detection during fast transforms. A declared low-frequency demo plate
  fixes the catalog presentation. Original evidence is archived outside the repo;
  calibration and gate materials were not substituted.
* `s6-summary.json`: current catalog count, bundle size and cost range.

## Delivery and reproduction

Catalog:
`C:/Users/User/AppData/Local/Temp/vgs-fx-s6/catalog-bundle/catalog.html`

Recipe review page:
`C:/Users/User/AppData/Local/Temp/vgs-fx-s6-v3/recipes/index.html`

The exact selected candidate plan path is in `s6-integration.json`. Preview media,
matched references, source fixtures and temporary fresh calibration tables stay
outside the repository. The active catalog bundle includes only HTML, 43 videos
and 43 thumbnails. Generated files added to the repository are below 2 MB each.

Use the specified interpreter:
`C:/Users/User/.codex/skills/video-gif-studio/.venv/Scripts/python.exe`.
Put its `Lib/site-packages/static_ffmpeg/bin/win32` on PATH. Then, serially:

```text
python -B scripts/fx_render.py --list --json --no-user-fx
python -B scripts/fx_calibrate.py --force
python -B wow/fx/verify_s6_calibration.py
python -B wow/fx/measure_s6_anchors.py
python -B wow/fx/verify_s6_integration.py
python -B -m unittest discover -s tests
```

Use a new preview output directory when repeating render scripts. Read
`references/director-fx.md` for CLI semantics, formulas, registry classes, recipe
controls, query score, output schema, and known limits.

## Safety fixes and unresolved gates

Sparse SFX uncovered AAC reconstruction above the existing -1 dBTP ceiling.
The SFX-only delivery retry now reduces limiter headroom when measured encoded
peak fails; it never changes the F boundary. Music/source-only legacy output is
unchanged. A new U value (`audio.sfx.codec_headroom=.2 dB`) records the reserve.
Recipe previews include a declared quiet procedural soundtrack; very short clicks
alone cannot always meet a programme loudness target under a fixed peak ceiling.

The wow-judge CLI is present at
`C:/Users/User/.agents/skills/wow/tools/wow-judge.mjs` even though it is absent
from PATH. No independent panel was executed. A completed render or numeric
screen is not a panel verdict. Follow-up needs the required contextual REF/BAD/
STYLE evidence and independent technical/2AFC review, then audited next-round C
activation. No aesthetic disagreement should delete an effect.

## Fix round

2026-11-05, independent NOT-mergeable review follow-up. This section supersedes
the earlier implementation claims where they differ. Work remains in the
`s6-director-fx` worktree, without commit/push or installed-skill changes. Media
jobs and tests run serially; generated media stays outside the repository.

| Review item | Fix and evidence |
| --- | --- |
| 1. Flash boundary | Rational integer frame/PTS clocks and half-open `[t,t+1 s)` windows in decoded QA and lint. Exactly 3 flashes/s passes; 30 fps / 9-frame periods fail. Repetitions are counted per pixel before applying the area threshold, preventing adjacent parts of one gradual flash from being counted repeatedly. General, saturated-red, equal-luma red-only, spatially staggered flashes and decoded timing tests. No bypass flag was added. |
| 2. Library isolation | Recipe JSON validation and Python plugin import are per-file transactions; malformed refs/cards/defaults are excluded with file/item/ref, experimental marker, suggestions and intent vocabulary. Later files and JSON queries/listings keep working. |
| 3. Missing cards | Authored metadata is required. Cardless plugins (including overrides of builtin names) are `card: missing`; partial cards are incomplete. Both are excluded from complete-stable coverage and query. `--list --coverage --json` exposes them. |
| 4. Lint/query | CLI uses the renderer's segment timing resolver; segment transitions enter conflict checks with the same half-up frame quantization. Invalid section intervals warn with indices; events keep their real times and count against the closest valid neighbour. Empty query results include a per-constraint removal count. |
| 5. Preview/provenance | `gl_glitch_memories` preview declares a fixed block field (preview context seed `6 - floor(24 * progress)`) and decodes to 0 flashes/s. Six repaired transition cards link `gate/p2-tech-recheck.md`. All 9 inherited items passed mandatory `fx_gate_kit` checks in 4 material/aspect cells each; `gate/s6-legacy-auto.json` and details record advisory edge warnings and independent review pending. A failing auto record becomes needs-review and is excluded from query. |
| 6. Recipes | All 14 default labels now equal measured decoded proxy peaks, including build 0.095772 instead of nominal 0.6. The declared measurement is 480x270/30 fps STD-MOV, three seconds, at 500 ms; alpha recipes use STD-A. Breathe/outro_settle/freeze_card are explicit textures with exemption notes. Recipe status remains experimental; technical-axis REF/BAD/STYLE evidence is generated through `fx_gate_kit --recipes`. |
| 7. Visibility | CIELAB chroma/Delta E reporting, reference-texture normalization for geometry, bounded scene masking and separate tonal/motion candidate cutoffs. The C entry remains calibrate_first. Unknown is reported as unknown. `fx_anchor_harness.py` accepts future independent 2AFC votes without inventing labels or activating thresholds. STD-P/HK zoom scores .4180/.3236 differ by 1.29x. |
| 8. Portability/cutout | Card previews are relative to the documented persistent default root `~/.video-gif-studio/catalog`; `VIDEO_GIF_FX_PREVIEWS` and explicit catalog paths relocate the whole bundle. Cutout's measured 0.021052 mix range is retained, but perceived inversion is explicitly unsupported and snippets use native controls. |

Fix-round external output overrides:

* `%TEMP%/vgs-fx-s6-fix-catalog`: measured recipe/glitch previews and matched references.
* `%TEMP%/vgs-fx-s6-fix-legacy`: nine inherited items' automatic technical kit.
* `%TEMP%/vgs-fx-s6-fix-recipe-gates`: experimental recipe contexts and triplets.

The persistent default is outside the repository. This restricted build uses
explicit writable external overrides; copying a complete catalog folder preserves
its relative media links. Nothing changes the legacy effect pixels by default;
the glitch port's native parameter contract and default 24-step seed clock are
unchanged. Only the preview context compensates that clock. Perceived labels remain provisional, material-specific measurements, not a
guarantee of human salience on arbitrary footage. Independent technical review
and human visibility calibration remain pending by design.

Fix-round validation and final artifact counts are recorded below.

Reproduction (supplied Python/FFmpeg runtime, serially, new empty external gate
directories; set `VIDEO_GIF_FX_PREVIEWS` to the chosen catalog folder):

```text
python -B scripts/fx_gate_kit.py --auto-only --items flash_white grade halation beat_bounce zoom_punch cutout_card crossfade whip_pan flash_cut --out LEGACY_KIT
python -B wow/fx/fix_s6_evidence.py --legacy LEGACY_KIT --previews
python -B scripts/fx_gate_kit.py --recipes --out RECIPE_KIT
python -B wow/fx/fix_s6_evidence.py --catalog --recipe-gates RECIPE_KIT
python -B scripts/fx_anchor_harness.py --out wow/fx/s6-fix-anchors.json
python -B -m unittest discover -s tests
```

The evidence helper can finish a partially generated catalog. It never overwrites
an existing encoded clip: it verifies declared preview parameters and decodes the
clip again against its retained reference. Use a fresh root after changing visual
source implementations. The ordinary `--cards` generator also requires fresh
output media paths. The initial catalog attempt hit this existing-file guard at
the already-generated glitch preview; the resumed verification is recorded in
`test-s6-fix-catalog-final.log`.

The complete catalog also exposed a second flash false-positive:
`gl_overexposure`'s single smooth exposure curve was reported as four flashes
because different pixel groups completed it on adjacent frames. The counter now
tracks per-pixel repetitions over the rational window before applying the fixed
area threshold. This preserves detection of repeated staggered strobes while
allowing a single gradient flash. `recheck_s6_flash.py` re-decodes all existing
catalog previews and automatic gate detail clips and refreshes their WCAG records without changing media;
`s6-fix-flash-recheck.json` records before/after counts. The old single-frame
defect detector remains separate from WCAG and still detects the BAD controls.

Final media evidence: **57 cards** (43 complete stable cards plus 14 experimental
recipes), **6,650,299 bytes** in the portable catalog bundle including references
and reports. **149 decoded clips, zero WCAG violations** after the repaired
counter: 57 catalog previews, 36 inherited-item gate details, and 56 recipe gate
details. `gl_glitch_memories` is 0 flashes/s; the single smooth overexposure
preview is correctly 1, instead of the false 4. All nine inherited items pass
mandatory auto checks, with the existing advisory edge WARNs retained.

The recipe kit contains **504 comparison pairs / 168 REF-BAD-STYLE triplets**,
with 10-second contexts, chronological stills, and native crops. All 14 input
recipe SHA-256 values match the gate records, all mandatory detail auto checks
pass, and all broken controls are detectable. These are prepared technical-axis
artifacts, not independent verdicts. `gate/s6-recipes.json` records gate readiness,
artifact roots, references, hashes and pending independent review.

The **38 fix-round regression tests passed** in 19.213 s
(`test-s6-fix-targeted-final.log`). Full-suite results follow below.

The first full-suite run exposed a lost `file:line` diagnostic (plus one cascading
registry-inventory failure) and the experimental addition of a glitch uniform.
The diagnostic format is restored. The native glitch signature is unchanged;
the catalog uses context-seed compensation instead. All three compatibility
checks pass (`test-s6-fix-compatibility.log`). The replacement preview has exactly
the same decoded SHA-256 as the fixed-field preview (`s6-fix-context-seed.json`),
so its zero-flash result and existing media evidence remain valid.

Final full suite: **634 tests in 343.909 s; 0 failures, 2 baseline environment
errors, 5 skips** (`test-s6-fix-full-final.log`). Relative to 596 / 2 environment
errors, this adds **38 tests with zero new failures/errors**. Exit status is 1
because the existing WinError 1314 symlink privilege error in `test_install` and
WinError 32 locked overlay cleanup in `test_mask_review` remain. No existing test
was weakened or skipped to obtain this result.

Fix-round base HEAD is `21dd3913d7a826b277cdec7f64c49e15ca7649e8`. New auto records
explicitly identify themselves as uncommitted, with that source revision and
per-item source hashes. Final audit: no protected spec/acceptance/process/thresholds.md
changes; no added/modified repository file exceeds 2 MB; no commit/push and no
installed-skill or sibling-checkout writes. The largest changed artifact is the
recipe auto-detail JSON (263,091 bytes). See `s6-fix-audit.json`.

## Fix round 2 — independent re-review closure

2026-11-05. This section supersedes the earlier pending recipe statuses and
per-pixel flash claims. Base HEAD `ec509b4a049f2eea908c4c7ea0d10169fb8fa3ab`,
branch `s6-director-fx`. No commit/push, installed-skill or sibling-checkout writes,
or protected spec/acceptance/process/thresholds.md edits. Heavy jobs ran serially.

| Item | Fix and evidence |
| --- | --- |
| 1. Flash | Simultaneous, same-direction, area-qualified relative-luminance cohorts replace the per-pixel repetition map. Monotone extrema and cohort retention merge gradual flashes. Strict near-exact camera translation registration avoids interpreting scene edges as photometric changes; its SDR scope is documented in `references/director-fx.md`. F boundaries and rational half-open windows are unchanged. Held-out STD-MOV 3/s = **3 PASS**; 3.33/s = **4 FAIL**; red 125 ms = **4 FAIL**. Decoded synthetic pans 1.5/3/6/9 px/frame = **0/0/0/1**, all PASS. Real footage and a separately panned real-footage control = **0 PASS**. Smooth gl_overexposure = **1**. Direct counter and qa_media paths exercised. See `s6-round2-regressions.json`, `s6-round2-flash.json`. |
| 2. Sparse SFX | SFX-only limiter release is 5 ms; music/source mixtures retain 50 ms. Up to 24 encoded gain/headroom adjustments keep the external **−14 ±1 LUFS / ≤−1 dBTP** limits. No short-track exemption or bed injection in user plans. Both recipes deliver in one CLI call at 500/1000 ms, including `--loudnorm off`: **−15.0..−14.8 LUFS**, **−2.2..−1.0 dBTP**. `freeze_card` declares an onset anchor in plans and previews, instead of following a late displacement plateau. Decoded audio/visual onset skew **≤0.125 ms**, below one 30 fps frame; both moving-preview clicks land at **500 ms**. See `s6-round2-regressions.json#recipes`. |
| 3. Tiny inputs | Either dimension <32 returns `perceived:null`, `perceived_status:unsupported`, and native-control guidance. Raw diagnostics remain, flow is skipped, classifier propagates unsupported, and perceived-addressed plans/resolution-aware inverse reject the size. Tests cover 1×1 and 16×16 across zoom_punch, beat_bounce and halation. |
| 4. Pixel art | `warp` honors nearest context despite legacy linear parameter defaults. Separate 720p, 11-point rows for all six effects in both modes; nearest lives at `sampling_modes.nearest.effects`. Mode-aware lookup and plan expansion fail closed if that mode is absent. Cache provenance includes mode, source and engine digests. Tests verify palettes, measured rows, distinct mode values and plan inverse selection. |
| 5. Visibility | Registry candidates: tonal **.19**, motion **.25**, combined/default **.22**, with reviewer 17-anchor provenance. Class **C**, `calibrate_first`, and unknown decisions remain unchanged. No enforcement or invented 2AFC votes. |
| 6. Promotion/memory | **14/14 recipes stable**, including the seven required names. Twelve independent SOUND verdicts remain untouched; two NEEDS-FIX cases are closed by decoded regressions, not relabeled as new independent verdicts. Original/current hashes, base revision and evidence links are in `gate/s6-round2-promotions.json`. The Windows fallback memory sampler followed stale Toolhelp parent PIDs after PID reuse, potentially adopting older unrelated orphans. It now checks process creation times. Deterministic recycled-PID and unreadable-parent tests cover this defect. The old run retained no process identities, so this concrete mechanism is consistent with, but cannot prove the cause of, its transient ~976 MB excess. |

New targeted suite: **12 tests, 46.577 s, PASS**
(`test-s6-round2-targeted.log`). The pre-promotion inherited fix-round suite also
passed all 38 tests (`test-s6-round2-existing.log`). Existing promotion assertions
now require stable gate links; experimental exclusion uses an actual unreviewed
fixture instead of assuming built-in impact must stay experimental. No external
gate or test coverage was removed.

Full suite: **646 tests in 400.554 s; 0 failures, 2 baseline environment errors,
5 skips** (`test-s6-round2-full.log`). This adds 12 tests to the 634-test baseline
with zero new failures/errors. Exit code remains 1 for test_install's WinError
1314 symlink privilege and test_mask_review's WinError 32 overlay cleanup. The
memory regression passed at **87,130,112 / 88,764,416 bytes** for 2/6 seconds.
Final paired preview decode confirms freeze_card's visible onset and click at
**500.0 / 500.0 ms**; pre-event encoding residual max .0676 versus onset 3.5319.

Final audit: `s6-round2-audit.json` records unchanged HEAD/branch, no protected
changes, no added/modified file or persistent artifact >2 MB, current calibration
engine hashes, matching promoted recipe hashes, and validation log links.

Persistent artifacts: `C:/Users/User/src/vgs-fx/run-s6-round2/evidence` and
`C:/Users/User/src/vgs-fx/run-s6-round2/extra`. These ignored worktree folders hold
plans, delivered clips, moving previews and decoded QA, outside locked Temp.
All newly written files are <2 MB. Existing large source assets were read, not
copied or modified. Held-out clips were read from the independent review folder.

Reproduce serially with the supplied Python and FFmpeg on PATH:

```text
python -B scripts/fx_calibrate.py --force --no-costs --sampling linear
python -B scripts/fx_calibrate.py --force --no-costs --sampling nearest
python -B wow/fx/verify_s6_round2.py --out run-s6-round2-new
python -B -m unittest discover -s tests -p test_s6_round2.py
python -B -m unittest discover -s tests
```

`verify_s6_round2.py --review-root PATH` selects the held-out fixture root.
Explicit `--resume` reuses completed QA from an unchanged-instrument run after a
later audio failure; the new unit suite independently renders all four user-path
cases again. Every delivered candidate passes the ordinary encoded audio gate.
The original reviewer verdict JSON remains untouched.
