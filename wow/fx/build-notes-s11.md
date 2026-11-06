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
