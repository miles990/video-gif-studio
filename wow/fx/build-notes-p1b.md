# P1b — caption integrity and P1 polish

2026-11-05, worktree `C:\Users\User\src\vgs-fx`, branch `p1b-fix`.
All product/evidence changes are confined to this worktree. No commit, push,
model download or edits to either installed skill/source checkout. Heavy runs
were serial; temporary videos/frames stayed in OS temporary directories.
Protected spec*, acceptance* and process.md files were not edited.

| Review item | Change | Measured result / regression |
| --- | --- | --- |
| 1. Caption integrity | Logical wrapping and pixel reflow retain timed word IDs and complete words; no substring search reconstructs timing. Lines derive start/end from their own words, and overlapping lines are rendered. Sub-frame words receive a full display frame without rewriting exported timings. All presets reveal a complete timed word at its onset. | **56 words × 4 presets = 224 onset checks**: 8 mixed zh/en/number/emoji words, 19 English and 29 Chinese real Whisper fixture words. **0 dropped words**, positive line durations, all words drawn at the first eligible 30 fps frame; maximum onset delay **29.667 ms / 0.89 frame**. Logical widths **3/8/40** and actual font reflow preserve the input order and IDs. Raster tests remove each current word's ink while retaining layout to prove it contributes pixels. |
| 2. Whitespace / punctuation | Trim word text and collapse internal whitespace; insert one space at Latin/number boundaries, including CJK–Latin; none between CJK words, before closing marks or after opening marks. After closing marks, space only before Latin/numbers. For zh / Traditional, convert sentence punctuation to `，。！？：；` while protecting numeric punctuation. | JSON and SRT text has **0 leading/trailing spaces**. Regression checks all **6 punctuation mappings**, both language and Traditional routes, and exact mixed output. The installed optional OpenCC also passed a real **29-word** fixture replay: **畫**, **2 full-width commas**, **0 edge spaces**, no model inference. Numeric commas/decimal points and input start/end timings remain intact. |
| 3. Keyword units | Use the complete version/decimal/grouped-number token for automatic keyword selection and highlighting. | Exact keyword list **`["v2.0", "1,234", "3.14"]`**; no `2.0`, `1`, `234` fragments. CJK keyword selection and explicit overrides remain covered by prior tests. |
| 4. crash_out | Default **600 ms**; omitted duration uses the shorter of 600 ms and the effect interval, minimum **300 ms**. Reject shorter or truncated intervals. Use 40% cubic preparation and 60% cubic return. | Starts/ends at **1.0×**, peak **1.35×**. Maximum adjacent-frame scale changes at **24/25/30/60 fps: 0.137369 / 0.123148 / 0.125819 / 0.066274**, all below the regression bound **0.16** for the default target/duration. |
| 5. Manifest-aware QA | Use named move start, effect end, movement end and meaningful extrema within one median frame. No blanket exemption for the full interval. Real shot boundaries win in rhythm scoring; excluded flashes are recorded. | Real encoded/decoded **4 s, 30 fps, 9:16** clip with crash_in, punch, crash_out and whip: **0 ms** cut-to-downbeat median and flash **PASS**. All **8 named moves** have edge/extrema regression coverage. A separate injected flash away from those events remains **FAIL**; excluded events are auditable. |
| 6. Preset polish | Pop scales only the current word, keeping earlier glyphs fixed. Current/keyword colors are separate in every enabled preset. Caption SFX selects nonadjacent lines at least **1500 ms** apart. Clean uses **88 px text / 10 px stroke / 4 px shadow** at 1920 high. | Previous-word keyword pixels are **byte-identical** at the next word's 0 ms / 90 ms pulse samples. Tests verify distinct highlight colors, density for fast and slow lines, and dark-outline pixels over checkerboard. The mixed clip uses **1 pop across 4 pop-preset lines** (3 lines in each other preset), rather than a pop on every line. |

## Visual inspection and retained evidence

The builder opened and inspected the actual contact sheet, then fixed a visual
issue the first pass exposed: this Windows Pillow lacks libraqm, so a font cmap
check alone allowed a skin-tone modifier to render as a detached square. The
installed Segoe UI Emoji font now uses cached Windows Uniscribe masks for whole
graphemes. A regression bounds the joined emoji width to **≤1.2×** the base glyph
width. It is a **monochrome** rendering; no color-emoji appearance is claimed.
The normal Pillow path remains available when libraqm supplies shaping.

The regenerated sheet was opened again: `👍🏽` is one visible glyph with no detached
modifier, `v2.0` / `1,234` remain intact, prior words do not pulse with the current
word, and clean text retains an outline on the alternating bright/dark background.
The final row displays actual English/Chinese Whisper fixture text. The four
caption clips were encoded at **1080×1920 / 30 fps**, decoded and inspected at six
timestamps each. Their numeric QA checks are all **PASS**. This frame inspection
does not claim independent viewing review or a normal-speed playback gate.

The final review also checks that dropping an unsupported edge grapheme cannot
leave a display-space/keyword-index mismatch. Spring QA uses its actual physical
extrema, not the nominal 700 ms table value (which does not control spring timing).

- [p1b-contact.jpg](p1b-contact.jpg): **1,772,734 bytes**, below 2 MB; 24 decoded
  portrait frames plus 4 live-fixture raster samples, all preserving 9:16 framing.
- [measurements-p1b.json](measurements-p1b.json): per-preset text/line/SFX counts,
  caption QA, decoded camera QA, onset and scale measurements. Temporary media
  paths are provenance only; rerun the harness to regenerate that media.
- [check_p1b.py](check_p1b.py): serial reproducible render/QA/contact-sheet harness.
- [test_p1b.py](../../tests/test_p1b.py): **13 new regression tests**.
- [tests-p1b-targeted.log](tests-p1b-targeted.log): **73 P1 tests passed**.
- [tests-p1b-full.log](tests-p1b-full.log): complete-suite result recorded below.

## Regression status

Final full suite: **323 tests, 316 passed, 0 failures, 2 baseline environment
errors, 5 skips**, **202.911 s**. This includes all **13 new regressions** and the
final per-word raster-difference assertions. **Zero new failures/errors** against
the supplied **310 tests / 0 failures / 2 environment errors / 5 skips** baseline.
The unchanged errors are `test_install.test_same_source_symlink_is_preserved`
(Windows symlink privilege, WinError 1314) and
`test_mask_review.test_review_exports_overlay_contact_sheet_and_stability_report`
(existing `overlay.png` cleanup lock, WinError 32). Neither was silenced or edited.
Final `git diff --check` passes; the protected-document diff is empty and the
branch remains `p1b-fix`, uncommitted and unpushed.
Existing tests were not disabled: the two old crash_out endpoint assertions now
use its requested new 600 ms default, and the style-field test supplies actual
separate timed words so its wrapping assertion respects the new atomic-word
contract. Its animation comparison uses pop, since typewriter now reveals whole
timed words at their input onsets.

Known limitations remain documented in `references/fx.md`: ASR semantic errors,
approximate script/SRT timing, missing-glyph warnings, and font/platform-dependent
emoji rendering. Oversized indivisible words must fit the safe zone through the
bounded size reduction or fail explicitly. New visible behavior remains
**experimental**; this slice does not promote P1 or claim the independent
cross-vendor/user viewing gates have passed.
