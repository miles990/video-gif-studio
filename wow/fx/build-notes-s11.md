# spec-11 builder notes

Worktree: `C:\Users\User\src\vgs-fx`, branch `s11-brief`. No commit or push.
Specification, acceptance keys, `process.md` and `thresholds.md` were not edited.
The Python runtime is the supplied skill venv; FFmpeg is selected through
`VIDEO_GIF_FFMPEG`. Work products and generated fixtures are under `.scratch/`.
Heavy verification/render jobs run sequentially. No paid model or live reference
network request was made.

## Item accounting

| Item | Implementation | Evidence / remaining gate |
|---|---|---|
| S-130 | `scripts/brief.py`: six modes, deterministic skeleton, agent-authored content overlay, named fenced aesthetic, inline 5+3 reference roles, assets/forks, music anchors, JSON/Markdown parity, schema/ERR envelope. Uses the existing user taste loader. | Eight recorded one-liners and 20 classification cases; proposals still require the independent whole-proposal reading. No claim that templates replace an agent's creative judgment. |
| S-131 | `brief_refs.py`: user → taste/refstat → vetted local library → optional provider for gaps; cassette/transport interfaces; are.na channels/umbrellas/connections/combined search, bounded downloads, Sketchfab metadata/routes, timestamped contact sheets. | Offline/NET-BLOCK equivalence, empty-slot lookup counts, licence/provenance checks, pHash/ORB positive and negative controls. No live web reference quality claim. |
| S-132 | Brief → existing storyboard schema → existing FX renderer; stable recipes/transitions, one camera owner, reference-use field mappings, explicit unsupported-mechanism fallback, owned footage sampling, aspect-preserving default proxy. | Eight brief plan-validation cases plus encoded drop/footage scenarios. Source references are kept out of plan inputs; CC-BY credits are separate. |
| S-133 | `brief_lint.py`: aesthetic, reference use/citations, mechanism/turn timing, hold, hero/text scale, fork, bilingual word limits, provenance/licences, meaningful exemptions. | Positive/negative and boundary fixtures; identical Markdown/JSON findings. Author-experience numbers added as C entries in `references/thresholds.json`; no existing threshold values changed. |
| S-134 | `brief_edit.py`, `brief_render.py`: structured target/magnitude/axis/phase/keep, six delta examples, frame/time image feedback, measured source luma, immutable per-shot render cache and transition dependency diff. | Unaffected PNG hashes remain identical. Music-aware slowdown retains total duration/downbeat anchors and explicitly shortens camera travel; without music the target shot length grows. |
| S-135 | `brief_bench.py` and `brief-benchmark-registration.json`: immutable topic registration, same-context receipts, blind moving-pair presentation, hidden controls, independent technical axis, user Wilson intervals and panel agreement. | **Pending external gates:** two evaluator-held prompts, preregistration commit, independent defect panel and actual user votes. User explicitly forbids a commit, so the commit requirement is reported pending. Official benchmark not run. Conclusion: **未證明更好**. |
| S-136 | `THIRD_PARTY.md` contains author, local snapshot date/hash and full MIT text, including `Copyright (c) 2026 Cekura, Inc.`. | All five absorbed source documents carry attribution at each section heading. Finder logic is explicitly identified as rewritten. No source media or README marketing copied. |
| Director homogeneity | Shared `brief_structure.py` supplies editorial timing, sizes, moves, transition families and recipes; explicit reference statistics override timing. | Contrasting sports/Japanese-fresh/watch regression checks shot count, ASL, CV, transition families and recipe sets for both routes. Neutral legacy/reference-only previews retain the established cut-readable defaults. |

Measured ten-second expanded storyboard structures (same inputs except the brief):

| Brief | Shots | ASL | CV | Transition family | Recipe set |
|---|---:|---:|---:|---|---|
| Sports hype | 10 | 1.000 s | 0.600 | energy | build, drop, hook_snap, impact |
| Japanese fresh | 4 | 2.500 s | 0.250 | dissolve | soft_hit, warm_memory |
| Precision watch ad | 3 | 3.333 s | 0.499 | geometric | hero_glow, outro_settle |

The legacy director with the actual stored user profile also differs: at 30 seconds
the three briefs produce 30 / 12 / 9 shots, ASL 1.000 / 2.500 / 3.333 s and
CV 0.600 / 0.248 / 0.471, with the same three distinct transition families.

## Source absorption

Read the full local blank-page `SKILL.md`, all four `references/*.md`, and all of
`scripts/find_refs.py`. The complete worthwhile procedure, roles, fence rules,
templates, vocabulary, correction lessons and worked examples are retained in:

- `references/blank-page-method.md`
- `references/blank-page-finding-references.md`
- `references/blank-page-vocabulary.md`
- `references/blank-page-examples.md`
- `references/blank-page-patterns.md`

These documents distinguish the source author's corpus counts from our own evidence.
The adapted executable contract is `references/brief.md`; `SKILL.md` routes the
director to it before storyboard/treatment work. There is no unified `vgs` entry
in this checkout, so the accepted standalone `scripts/brief.py` mapping is documented.

## Integration decisions

Reference acquisition never installs a network client or calls a model implicitly.
Providers return candidates; only vetted records fill reference slots. No candidate
means an honest placeholder with the query tried. Real user cards carry `uN` origin
handles, and turn/composition takes select matching user assets rather than merely
cycling unrelated source files. Reference statistics never pretend to be images.

The general SFX router is still experimental. Stable visual-only plans omit recipe
SFX and write `sound-policy.json`; supplied music remains available. A recipe's
camera layer owns the camera movement. Unsupported mechanisms become explicit
warnings naming the substitute, not hidden reinterpretations. Recipe tails stop
at their owning shot, making direct plans and the local shot cache agree on scope.

RMS music analysis is labelled an unreviewed 4/4 candidate grid. Authoritative
`beats_ms/downbeats_ms/drop_ms` JSON remains the preferred route for difficult music.
The synthetic 120 BPM fixtures verify the known 2 s / 6 s drop boundaries; that is
not evidence of universal downbeat recognition.

The renderer cache hashes source content, local actions, recipe/renderer code,
resolution and sampling policy. Absolute timeline position is not a pixel dependency.
Changed shots are recalculated; unaffected local frames are reused by hash. Boundary
blends depend on both neighboring shots. Final assembly still encodes the new movie.

Running the existing gate-kit fixtures under the user's scratch-only constraint
exposed an older blanket ban on repository output paths. The guard now permits only
descendants of the resolved, git-excluded `.scratch/` directory in addition to its
existing external paths; ordinary repository paths remain rejected. The existing
positive/negative path tests cover this compatibility change.

## Verification record

- Baseline: **784 tests**, **0 failures**, **2 environment errors**, **4 skipped**.
  Errors: Windows symlink privilege in `test_install`, and a Windows open-image
  cleanup lock in `test_mask_review`.
- Focused existing/new regression pass: **113 tests, all passed**.
- Initial slice pass: **24 tests, all passed**, including five encoded scenarios.
- Repaired gate-kit + brief + all taste scenarios: **65 tests, all passed**.
  Reference-calibrated encoded ASL/CV: fast 0.697674 / 0.514004;
  slow 3.000000 / 0.302418, within the original scenario assertions.
- An intermediate full run exposed the scratch path restriction and neutral
  reference-preview cut-detection regression. Both were repaired; its failed run
  remains in `.scratch/full.log` instead of being hidden.
- Final full suite: **808 tests, 0 failures, the same 2 environment errors,
  4 skipped**, in 741.504 s. Evidence: `.scratch/final-full.log` and
  `.scratch/final-full.json`. No new failures or errors against the baseline.
- Final scenario suites: **5 brief + 14 taste scenarios passed** in the full run.
  A subsequent brief-only pass after the portrait preview label adjustment ran
  **24 tests, all passed**, in 13.738 s (`.scratch/final-slice.log/json`).
- Doctor passes: supported Python, local image runtime and FFmpeg/FFprobe ready
  (`.scratch/s11-doctor.json`). No authentication/quota network check was made.
- `git diff --check` passes; branch is `s11-brief`; `.scratch/` is git-excluded.
  No protected specification/acceptance/process/thresholds Markdown file changed.
  All changed source/document files and new preview artifacts are below 2 MB;
  pre-existing scratch media was left untouched. No commit or push.

Commands are reproducible with the supplied interpreter and FFmpeg environment:

```text
python -B -m unittest discover -s tests -v
python -B -m unittest discover -s tests -p "test_brief*.py" -v
python -B -m unittest discover -s tests -p test_taste_scenarios.py -v
python -B scripts/doctor.py
```

The local runner `.scratch/run_tests_s11.py` pins `tempfile.tempdir` and TEMP/TMP
to `.scratch/`, sets the required FFmpeg path and writes machine-readable summaries.

## Review artifacts and limits

Moving pipeline previews and measured structure tables are in
`.scratch/s11-demo-final/review.html`, with `structure.json` and
`legacy-structure.json` beside it. Four playable clips cover sports, Japanese
fresh, watch, and a warm portrait cafe; their brief JSON/Markdown, storyboards,
plans and timestamped contact sheets are included. They are labelled silhouette/previsualization examples,
not finished client films or before/after appeal evidence. The official S-135
comparison cannot be claimed complete without the withheld topics and human votes.
Live reference vetting and the independent whole-proposal reading also remain open.

## Fix round

2026-11-06, builder worktree `C:/Users/User/src/vgs-fx`, branch `s11-fix`,
base `4cbf5790db5b0b1ad7755cbc5855ead2d0a2d96a` (also `origin/main`).
Spec-11 remains **EXPERIMENTAL**. No promotion or push was performed.

| Item | Change | Evidence |
| --- | --- | --- |
| 1 | Prior shots/beats required for delta and housekeeping; incidental version asides retain brief mode. | Context/no-context routing regressions. |
| 2 | Relative energy-change drop candidates; long-song onset fit; complete comparison windows; no-drop bar disclosure; silent/phrase sound fields without invented drops. | Known WAV drops plus 90-second 123 BPM no-drop signal, checked at beat 170. |
| 3 | Generic draft transformation extraction replaces README-sentence branches; source transformation owns the turn; original constraints pass into beats, shots and plan review metadata. | Chinese powder-to-logo and monochrome-to-color, English dissolving, named product, no faces and logo-last fixtures. |
| 4 | Unauthored output is `skeleton`, with a creative fork; conversion refuses it unless `--allow-skeleton`; source hard constraints are non-exemptible lint requirements. | Default rejection, explicit previs override, authored content and missing-constraint tests. |
| 5 | Agent `ref_uses`, aesthetic-derived defaults, distinct reference paths, generated still/motion sheets and `ref_missing`; documentation uses repository adapters instead of nonexistent CLIs. | Five distinct local images, authored material use, real sheet path and missing-reference warnings. |
| 6 | Source crops implement shot size; shots rotate footage and reserve identified logo assets for the end; calm structure and level intensity; original stable director retained behind default-off `--experimental-structure`. | Six encoded genres, all 15 pairwise frame differences above 1 intensity level on the 0..255 scale; direct WS/MS/CU/ECU crop controls; legacy-default comparison. |
| 7 | Multiple quantities yield one question; bare shot numbers, Chinese multipliers and roll directions; decoded screenshot matching; expected/observed no-visible-effect reports; bounded Windows rename retry. | Target grammar, clockwise/counter-clockwise, pixel-to-time match within one frame, no-op and transient/permanent rename-lock tests. |
| 8 | Combined aesthetic separators/known concatenations, numeric routine forks without the second-hand false positive, meaningful waiver reasons, original-media fingerprint minimum of 720 px short side and inset feature pyramid. | Positive/negative lint controls; low-resolution rejection; full/graded/scaled embedding controls and unrelated high-resolution imagery. |

Validation uses the supplied skill Python and managed FFmpeg path, with TEMP/TMP
and all generated fixtures under `.scratch/`. Heavy processes run sequentially.
The 169-test brief/taste pass had zero failures/errors (`.scratch/fix6.json`).
The final full-suite and scenario receipts are recorded below after completion.

Commit limitation: **no local commits were created**. Git cannot create
`C:/Users/User/.codex/skills/video-gif-studio/.git/worktrees/vgs-fx/index.lock`
because that worktree metadata is outside the writable roots. Both `git add` and
`git commit` returned Permission denied; this builder created no commit or branch update.
Eight ordered recovery patches and matching requested commit-message files are in
`.scratch/fix-snapshots/`. They are patches, not commits; the final patch includes
integration corrections and this validation record. This does not satisfy the
requested one-local-commit-per-item requirement until Git metadata becomes writable.

The tests establish routing, timing, provenance separation and measurable rendered
differences, not human aesthetic preference or promotion to stable. Contact sheets
use synthetic owned test media. Visual inspection through `view_image` was denied
by that tool's filesystem access; decoded frame comparisons provide the recorded
image evidence.

Final validation:

- Full suite: **820 tests, 0 failures, the same 2 environment errors, 4 skipped**,
  803.839 seconds. Receipt: `.scratch/fix-round-full-final.log` / `.json`.
  The two errors are `test_install` symlink privilege and `test_mask_review`
  Windows open-image cleanup; neither is a new regression against 808 / 2.
- Scenario suites included in that final run: **5 brief + 14 taste passed**.
  Receipt: `.scratch/fix-round-scenarios.json`.
- Ordered recovery-patch stages: **25 / 26 / 27 / 28 / 29 / 31 / 34 / 36 tests**,
  respectively, all passing (236 total executions). Each stage was reconstructed
  under `.scratch/` from the original HEAD and tested in a fresh Python process.
  Receipt: `.scratch/fix-snapshots/stage-tests.json`.
- All eight patches apply sequentially with Git and reproduce the final worktree;
  receipt: `.scratch/fix-snapshots/patch-validation.json`. No index or branch was
  changed to perform this verification.
- Final six-genre evidence:
  `.scratch/s11-fix-genres-2lvqsyn_/evidence.json`, with six timestamped sheets and
  encoded clips. The minimum of all 15 pairwise frame mean-absolute differences is
  **34.516** on the 0..255 intensity scale (required test floor: 1).
- `git diff --check` passes. Protected specs, acceptance files, `process.md` and
  `thresholds.md` are unchanged by this builder. See the external HEAD movement below.
- Earlier failed/interrupted exploratory test logs remain in scratch; the final
  receipts named above supersede them. The 90-second music regression exposed and
  fixed both cumulative beat-slot drift and a partial end-window false drop.

Outstanding requested work: create the eight local commits once the worktree's
Git metadata is writable. No push is authorized or performed.

External movement observed during final verification: `s11-fix` advanced from
`4cbf579` to `c2ccd0273b329aec3841512bce24f967161d69f7`, an externally created,
Claude-authored spec-13 commit. It adds only `wow/fx/spec-13.md`; no source, test or
file touched by these fixes changed. It was preserved and is not counted as a
builder fix commit. `origin/main` was also externally advanced to `b185890`.
The final test evidence remains applicable because the external commit is spec-only.
