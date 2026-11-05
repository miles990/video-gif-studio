# P2d — technical repairs, promotion and style tags

Date: 2026-11-05. Worktree: `C:/Users/User/src/vgs-fx`, branch `p2c-gate`.
No commit or push. Installed skill/source checkouts are not modified.

The revised section “2026-11-05 使用者抽查後修訂” in `process.md` makes
technical soundness the status gate. Appeal affects defaults/recommendations and
style tags; it does not remove technically sound transitions. This slice uses
`gate/p2-tech-verdicts.json` as its independent review evidence, not the superseded
preference-based decision file. No spec, acceptance, process or thresholds Markdown
was edited. Effects keep their previous statuses.

## Repairs

| Item | Diagnosed defect and repair | Regression |
| --- | --- | --- |
| `gl_bounce` | B is revealed only where `d>0`; shadow only in `0<d<=h`. Eliminates the RGBA start jump and blackened B beneath the outgoing panel. | endpoint limit, hidden incoming coverage, shadow band and unshaded region |
| `gl_multiply_blend` | Separable multiply uses union alpha `a+b-ab`; uncovered source colours survive, and multiplication contributes only in the overlap. | disjoint mattes plus hand-calculated fractional overlap |
| `gl_color_phase` | Mix straight per-channel colours; cross-fill missing colours from the visible source; time alpha separately and then premultiply. | original PM output inspected before clipping, missing-colour invariance, hidden-RGB poisoning |
| `gl_dreamy_zoom` | Blend the separately transformed/whitened RGBA shots through `.45–.55`; opaque path unchanged. | midpoint coverage, interval endpoints and default-transform continuity at both boundaries and midpoint |
| `hex_shutter` | Blend premultiplied source coverage through `.47–.53` under the shutter; opaque path unchanged. | midpoint coverage and continuity in both aspects |
| `gl_glitch_memories` | Bound each block's rigid translation by its full extent, including partial boundary cells, before sampling. No mirrored border. | sample-coordinate bounds and block rigidity, landscape/portrait/small partial cells |

`tests/test_p2d.py` was added before the six repairs. `tests-p2d-red.log` records
all six defect regressions failing, plus the gate controls. The final tests allow
small subpixel movement at Bounce's limiting endpoint and float-coordinate error
at DreamyZoom's identity transform; neither tolerance admits the original defect.
`tests-p2d-green.log` records the passing repaired controls and promotion checks.

## Registry and availability

All 28 SOUND items and all six repaired items are stable. `hex_shutter` was already
stable and is reaffirmed with repair evidence; the other 33 are newly promoted.
`gate/p2-status.json` records each item, status, evidence path and date. All 32 GL
ports validate without experimental opt-in. The default catalog is six effects
and 37 transitions. Other transitions and effects retain their existing status.

Each transition registry/catalog entry now carries an editable `style_tags` list.
The 34 reviewed items use the verdict labels exactly, including composite labels.
Unreviewed entries default to an empty list. Tags are metadata, never render
parameters or quality scores. Builtins declare them in their decorators; plugins
can provide or override tags. `references/fx.md` documents the vocabulary.

Legacy visibility/count assertions were updated for the larger stable catalog.
Reference mapping still rejects experimental anchors, and now accepts the newly
stable GL anchors. Effects' stable inventory remains asserted unchanged.

## Gate instrumentation

The previous global mean-gradient heuristic could confuse a partial grid cell or
a shape meeting the border with a copied row. Edge warnings now require dense
tangential texture replicated across at least four pixels in overlapping local
16-pixel windows. This also catches a single broken GlitchMemories block that a
whole-edge average could miss. Raw seam/stretch ratios and high-ratio frame indices
remain advisory in reports; they alone no longer raise an edge warning.

Controls include flat/shape/grid negatives, existing three-/four-/eight-pixel edge
controls, the original unbounded GlitchMemories sampler as a broken control,
repaired GlitchMemories, broken endpoint controls and repaired Bounce. Endpoint
thresholds are unchanged. These remain heuristics: textured intentional edge
repetition can still need review, and low-texture replication may not be measurable.
No effect-name exemption or appeal filter was introduced.

## Validation

Python: `C:/Users/User/.codex/skills/video-gif-studio/.venv/Scripts/python.exe`.
FFmpeg directory on PATH:
`C:/Users/User/.codex/skills/video-gif-studio/.venv/Lib/site-packages/static_ffmpeg/bin/win32`.
`PYTHONDONTWRITEBYTECODE=1`; one heavy process at a time.

Commands, from this worktree:

```powershell
$python = 'C:\Users\User\.codex\skills\video-gif-studio\.venv\Scripts\python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PATH = 'C:\Users\User\.codex\skills\video-gif-studio\.venv\Lib\site-packages\static_ffmpeg\bin\win32;' + $env:PATH
& $python -m unittest discover -s tests -p test_p2d.py -v
& $python -m unittest discover -s tests -v
& $python scripts/doctor.py
```

| Check | Result | Evidence |
| --- | --- | --- |
| Original defect reproduction | All six defect tests fail before repair (nine failing tests including gate controls) | `tests-p2d-red.log` |
| P2d regressions, controls and promotion | 12 pass, 1.388 s | `tests-p2d-green.log` |
| Final full suite | 561 tests, zero failures, two unchanged environment errors, five skips; 312.290 s | `tests-p2d-full.log` |
| Doctor | Exit 0; local GIF and media runtime ready | `doctor-p2d.json` |
| Diff/scope/size | `git diff --check` clean; protected files and effect implementations unchanged; no added/changed file exceeds 2 MB | final worktree audit |

The supplied baseline was 549 tests with the same two environment errors and five
skips: `test_same_source_symlink_is_preserved` needs Windows symlink privilege
(WinError 1314); `test_review_exports_overlay_contact_sheet_and_stability_report`
hits the existing Windows `overlay.png` cleanup lock (WinError 32). This slice adds
12 passing tests and no new failures/errors. The first full run is retained in
`tests-p2d-full-initial.log`: its only new failure was the already-loaded legacy
preview count of 18 versus the promoted catalog's 117 calls. That assertion now
derives the count from the stable catalog; the final full run passes it.

All six diagnosed transition defects are closed by reproducing regression tests.
Independent verdicts cover defaults; this does not assert that arbitrary custom
parameters have had the same visual review. Effects review and taste-based
recommendations remain future work. No new visual gate movie pack is claimed.
