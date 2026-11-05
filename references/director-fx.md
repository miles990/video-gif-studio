# Director-usable FX layer (S6)

Use the existing skill Python and FFmpeg runtime. Run one render, calibration,
benchmark or test process at a time. All commands below run from the worktree.

```text
python scripts/fx_render.py --list --json --no-user-fx
python scripts/fx_calibrate.py --force
python scripts/fx_calibrate.py --fx-dir MY_PLUGINS --out MY_CACHE/calibration.json
python scripts/fx_calibrate.py --effect zoom_punch --perceived 0.3 --no-costs
python scripts/fx_render.py --cards
python scripts/fx_query.py --intent hit --needs subject alpha --max-cost 30 --section drop --json
python scripts/fx_lint.py plan.json --out lint.json
python scripts/fx_candidates.py plan.json --moment drop --experimental --out MY_KIT
python scripts/fx_check.py output.mp4 --reference untreated.mp4 --events events.json --fps 30 --out fx-qa.json
```

The persistent default catalog root is `~/.video-gif-studio/catalog`, outside
the repository; override it with `VIDEO_GIF_FX_PREVIEWS` or `--cards PATH`.
All card video/thumbnail paths are relative to that catalog root (the folder
containing catalog.html and catalog.json). Copy the entire folder to move a
catalog; no drive letter or temporary path is embedded in card preview links.
Explicit catalog output puts media beside the HTML. The fix-round build used
a writable external override recorded in `wow/fx/s6-fix-previews.json`.
Nothing downloads assets. The page uses muted autoplay/loop, native controls,
intent filtering, comparable 0..1 meters, use/avoid guidance and escaped plan
JSON. At 390 px it uses one column. It has no network dependency.

## Cards and status

Metadata lives in `fx-cards.json`; `fx-card.schema.json` is draft 2020-12.
Additional properties are allowed to retain status, params, doc, source and the
integer history field. `fx_catalog.validate_card` additionally checks that the
two duration bounds increase, because JSON Schema cannot compare sibling values.
The vocabulary is `hit`, `reveal`, `breathe`, `build`, `drop`, `transition-match`,
`transition-energy`, `texture`, `title`, `conceal`, `play`, `distort`.
Needs are `subject`, `motion`, `alpha`, `text` and mean conditions the source
provides. In particular, an opaque source is not a prepared cutout.

Cards include recommended duration bounds, sound types, conflict names, measured
`cost_ms_per_frame@720p`, a timing record, technical gate provenance, style tags,
and video/thumbnail paths. Cost is null for an unmeasured plugin; queries exclude
it until calibration. `@effect(card={...})` / `@transition(card={...})` accepts
metadata separately from function parameters. A plugin without authored metadata
is listed as `card: missing`, excluded from queries and complete-stable counts.
Partial cards are marked `incomplete`. `--list --coverage --json` and generated
coverage.json list both categories. Calibration discovers new amount-based effects.
Recipe JSON and plugin Python files load independently: errors name the file,
recipe/item, offending refs, experimental status, suggestions and intent vocabulary
on stderr; the remaining library and JSON stdout remain usable. Invalid plugin
registrations roll back the entire offending file, including earlier decorators.

P2-reviewed cards retain their technical provenance; the six repaired transitions
link directly to `wow/fx/gate/p2-tech-recheck.md`. The nine inherited original
items have new `fx_gate_kit` automatic records in `wow/fx/gate/s6-legacy-auto.json`
and full details beside it. They retain stable only when mandatory auto checks
pass; otherwise the card becomes `needs-review` and queries exclude it. Advisory
edge WARNs remain visible. These records explicitly say independent review pending.
The gate never fabricates wins, losses, p-values or numeric appeal scores.
Style tags copy the existing transition metadata and remain user-editable.

Preview paths are deterministic, but files only exist after generating the
catalog. `grade` is an identity at its original defaults: its catalog explicitly
uses `temp=.15` as a demonstration override. `gl_glitch_memories` declares
`context.seed = 6 - floor(24 * progress)` for its catalog preview: this
compensates the native seed clock and yields a smooth fixed block field, avoiding
24 random updates squeezed into 1.2 seconds. The native port parameters and
default seed behavior are unchanged.
Decoded fix-round preview maximum is zero flashes per second. Other static effects use a sliding
before/after view. Reference videos remain alongside previews for remeasurement.

## Calibration and fixed raw methods

`references/thresholds.json.calibration_tables.fx_perceived` points to
`references/fx-calibration.json`. `VIDEO_GIF_FX_CALIBRATION` selects an alternate
table for lookup, lint and query. The table stores 11 points on [0,1], raw
measurements, maximum reachable intensity, material, date, source digest and
base commit. `--force` repeats measurements; cache reuse requires a matching
source and measurement-engine digests and the sampling mode. `--fx-dir` automatically calibrates new plugins without manual
table edits. Timings use the public uint8 path at 1280×720, seed 6, t=1000 ms,
3 warm-up frames then the median of 20, with OpenCV limited to one thread.
Machine, NumPy, OpenCV and FFmpeg versions accompany every cost. CPU load is
recorded when the optional system monitor is available, otherwise explicitly null.

Calibration is separate for `--sampling linear` and `--sampling nearest`.
The default linear rows remain in `effects`; nearest rows are in
`sampling_modes.nearest.effects`. Both contain their sampling mode and canonical
1280×720 resolution. `inverse`/`interpolate` accept `sampling=`, and plans select
the matching table automatically. A missing mode is an error, never a linear
fallback. Nearest context also takes precedence over legacy `sampling='linear'`
function defaults in `warp`, so direct API and recipe calls preserve palettes.

Perceived calibration is **unsupported when either input dimension is below
32 pixels**, including 1×1 and 16×16. Raw dY/SSIM remain available, flow is skipped,
and reports carry `perceived: null`, `perceived_status: unsupported` and a reason.
Perceived-addressed plans fail with guidance to use native controls; native
rendering remains available. This avoids silently returning zero or saturated
flow scores outside the instrument's spatial support.

STD-P is the seed-6 board with noise **after** its subject and details (A6-1).
STD-HK uses the prescribed high-key transform; STD-A has the soft circular matte
and garbage RGB under zero alpha. Measurement composites straight alpha over
#808080 before computing:

* BT.709 sRGB luma `Y=255*(.2126R+.7152G+.0722B)` and mean absolute paired dY;
  `area8` is the fraction of pixels whose absolute luma change exceeds 8.
* SSIM: luma, 11×11 Gaussian sigma 1.5, C1=(.01×255)², C2=(.03×255)²;
  report `1-mean(SSIM)` across the full frame.
* Farneback: `(0.5,4,21,3,5,1.1,0)` on luma; mean vector magnitude, scaled to
  720p for proxy reports. Calibration itself uses native 720p.
* General flash fraction: linearized sRGB luminance change at least .10,
  with the darker state below .80. Red flash uses linear R/(R+G+B) at least .8
  at either endpoint and a change greater than 20 in max(0,R-G-B)×320.
* `center_sharp` is the central 200×200 Laplacian variance ratio (raw only).
  `sharp4` is the full-frame variance ratio after area resizing to one quarter.
  A flat reference returns null, never infinity or a made-up destructive verdict.

The documented **provisional** combination is
`clip(max(dY/64, ssim_loss, disp/24, flash_area),0,1)`.
The normalization constants are C entries, awaiting independent 2AFC ranking.
They are usable for reproducible numeric lookup, not proof of human perception.
Perceptual ranking must still pass the withheld ≥8-item amended panel test.

`amount` is the primary control except `grade.temp`. For cutout_card the director
control is a premultiplied identity-to-default `mix` on STD-A; the original
`amount` remains opacity. Its maximum measured full-frame intensity is small;
the table exposes that rather than amplifying its score. Requests beyond a
table's measured maximum raise an error. Lookup never silently clips .7 to an
unreachable value. The small cutout range does not meet S-71's ≥.10 grid maximum.

## Visibility, harshness, and flash checks

`fx_check` decodes both the delivered file and the timeline-matched untreated
reference. Around onset, three matched residual frames before/after are averaged.
The v2 instrument uses CIELAB D65 residuals, including chroma; `deltaE76` and
`chroma_delta` are reported separately from the unchanged provisional perceived
lookup. Geometry uses the reference local L* texture deviation (Gaussian sigma 3,
floor 1 L*) to normalize both residual and scene signal. Tonal changes retain
physical Lab magnitude. High-pass magnitude (sigma 2) plus .1 times magnitude is
divided by the noise floor plus bounded untreated temporal masking (at most
3 times the floor). Thus scene motion alone cannot create a 22x score multiplier.
The reviewer-derived provisional cutoff contexts are tonal=.19 and motion=.25
(combined candidate .22). The 17-anchor review separated tonal 13/13 and motion
4/4 at these candidates. Both remain
class C, `calibrate_first`, **not enforced**. Their numbers are candidates, not
human-calibrated visibility boundaries. Flat images still provide little evidence
about geometric displacement. The STD-P/HK zoom anchor scores are .4180/.3236
(1.29x); these fixture observations do not establish perceptual validity.

`fx_anchor_harness.py --out anchors-v2.json` measures declared controls, and
`--labels panel.json` accepts independent `[{"id": "anchor-id", "observer":
"panelist-id", "choice": "effect"}]` votes; choices are effect/reference/tie.
Unknown IDs and duplicate observer votes are rejected. Fixture expectations and
panel votes remain separate. The harness never changes threshold activation.

`measure_s6_anchors.py` measures only predeclared controls: weak light leak at a
synthetic cut, strong light leak, default halation/zoom, old/current radial blur,
and grain on STD-P/HK. No candidate recipe enters its threshold proposal. It
records separation and a 25% pooled-standard-deviation margin in
`fx-instrument-anchors.json`. The synthetic cut is **not** a replacement for the
independently labelled demo2 context. Missing independent 2AFC labels and auditor
approval leave existing C thresholds `calibrate_first`. They return unknown,
never a visibility pass. The existing `calibrate.py` proposal/activation protocol
is still the only way to activate an audited boundary in a later round.

Once an audited boundary is active, invisible onset is a warning; destructive
blur requires both low sharp4 and high SSIM loss persisting at least four frames.
Declared transition windows are exempt from destructive-blur classification.
Texture intent is exempt from the visibility requirement, but **never** from
flash safety. Reports carry raw quantities, instrument status and a suggested
repair. An uncalibrated visibility result has `status: unknown`, never `ok`.
A texture exemption is documented explicitly and never waives flash checking.

General and red flash checks run independently on every decoded frame. Each
leg must change simultaneously in the same direction over area ≥.111, and the
opposite leg must overlap that qualifying cohort over ≥.111. No repetition map
accumulates unrelated pixels across time. Rising and falling cohorts are tracked
separately, so opposite halves cannot cancel. Monotone extrema capture gradual
changes; holding a cohort until its reversal merges adjacent parts of a single
smooth flash. Event histories retain only a rational one-second window.

Near-exact camera translations are registered before forming luminance pairs,
preventing moving checkerboard edges from becoming photometric flashes. This
uses phase correlation (response >.5, translation <10% of the smaller dimension),
with a 95th-percentile linear-luminance residual <.025 and a mean residual less
than half the unregistered difference. A qualifying flash-sized photometric
change does not meet that residual check and still follows the ordinary path.
This is an implementation safeguard for the tested SDR pan controls, not a
general motion/flash exemption or a photosensitivity certification.
More than three pairs in any sliding one-second
window **[t, t+1 s)** is a WCAG 2.3.1 error. Exactly 3/s passes;
10-frame periods at 30 fps pass, 9-frame periods (3.33/s) fail. Both general
and saturated-red rules have boundary tests. CFR uses integer frame indices
over rational fps; video QA uses integer presentation ticks and the stream
time-base (including the FFmpeg-only fallback). A completion exactly one second
after an earlier one is outside that earlier window, without floating-point
epsilon guesses. No flash override or hidden exemption is enabled. All six boundaries are F entries and no C/U update
can weaken them. This is the answer key's WCAG 2.x red definition, not a claim
to implement the newer CIE-chromaticity supplement or certify HDR material.
Source: [W3C explanation of SC 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html).

`qa_media.py` includes decoded general/red checks and exits nonzero for unsafe
flashing. A plan with `"fx_checks": true` also emits `fx-qa.json`, manifest
event visibility and QC data by rendering its no-effect reference sequentially.
This optional paired pass is expensive; ordinary legacy rendering is unchanged.
Use `fx_check` directly when a matching untreated reference already exists.

## Recipes and one-line plans

Fourteen JSON recipes live in `recipes/`, validated by
`fx-recipe.schema.json` plus cross-field checks. All visual ingredients are
stable. Substitution notes state when stable zoom, halation or precomposed
typography replaces experimental shake, radial blur, vignette or text.
`freeze_card` decorates a freeze source; it does not extract/freeze a moving
subject by itself. `title_pop` animates precomposed text, not a text generator.
Every layer has explicit offsets, durations, and envelope keyframes. `build`
has four increasing pulses; quiet recipes omit sound with a reason (three total).

The 14 bundled recipes are **stable on the technical axis**. Twelve have SOUND
verdicts in `wow/fx/gate/s6-recipe-tech-verdicts.json`; hook_snap/freeze_card have
follow-up decoded regressions resolving the two reported defects. Promotion
provenance and hashes are in `wow/fx/gate/s6-round2-promotions.json`. No appeal or
human visibility verdict is implied. New combinations remain experimental until
their own review. Decoded reports in `wow/fx/gate/s6-recipes.json` retain the
earlier automatic evidence. Fix-round default targets equal the decoded peak measurement
on a declared 480x270, 30 fps, three-second STD-MOV preview, starting at 500 ms
(STD-A for alpha recipes). These labels are material/resolution specific; for
example build is 0.095772 on this decoded proxy, not the old nominal .6.
`breathe`, `outro_settle`, and `freeze_card` explicitly use `texture` intent with
an exemption note; they make no hit/reveal salience claim.
`fx_gate_kit.py --recipes --out EXTERNAL_DIR` prepares technical REF/BAD/STYLE
triplets, four material/aspect cases, 10-second contexts, stills and native crops.
The generator does not promote combinations. Stable ingredients do not imply a
stable combination.

```json
{"recipe":"impact","at_beat":16,"perceived":0.6}
```

Place that object in `effects`; unreviewed combinations require `--experimental`. The compiler
expands the JSON into ordinary effect envelopes and records `recipe_events`.
`perceived` scales the recipe's envelopes relative to its target; it is a target,
not a guarantee that a nonlinear composition achieves that measured value.
`VIDEO_GIF_RECIPE_HOME` supplies extra JSON; duplicate names warn before override.
Rendering uses the existing SFX priority: user folder, Kenney, procedural fallback.
Preview audio uses a quiet procedural 220/330 Hz bed and aligns SFX onset to its
measured decoded MEAS peak (riser ends there); plan rendering tracks paired MEAS
per active recipe instance and aligns its SFX to the measured pre-encode peak.
`freeze_card` instead declares `sfx_anchor: onset` in both paths: the click lands
on the frame where the card appears, without following a late optical-flow
plateau. The stored perceived peak remains an intensity measurement.

Click-only delivery keeps the external −14 ±1 LUFS and −1 dBTP gates. SFX-only
tracks use a 5 ms limiter release (music/source mixtures retain 50 ms), then
bounded encoded gain/headroom retries. Every candidate is decoded and measured;
there is no short-track exemption, silent bed injection, or relaxed target.
An unachievable custom track still fails. Recipe SFX enforce normalization even
with `--loudnorm off`, as before.
Read the decoded measurements before delivery; source-specific sound alignment
must not be inferred from a recipe's nominal `peak_ms` alone.

## Budget and deterministic query

Sections use `name`, `start_ms`, `end_ms`, `energy` (0..1); a beatmap may provide
them. Current **U-class defaults**, not external standards, are:

* Sliding 4-second perceived allowance = `.4 + 5.5*energy`.
* Events per bar = `max(1,floor(1+4*energy))`; default bar length 2000 ms.
* Energy ≤.4 warns/errors on repeated flashes; energy ≥.8 permits an eight-flash
  accent run, while sustained flashing warns. The WCAG bound always remains fixed.
* Breathe query results have default perceived ≤.25.

Lint reads these from the registry and uses the selected calibration table for
event sums. It reports section, beat range, used/allowed numbers and repair text.
The defaults are not represented as learned user taste. Same-frame conflicts are
checked in both directions, including real `segments[i].transition` cuts.
The CLI resolves source durations, trims and beat timing through the renderer.
Zero-length/reversed sections warn with their zero-based section index. Events
are assigned to the closest valid neighbour (following section wins a distance
tie), retain their timestamps, and count against that neighbour's budget. A plan-only flash precheck is conservative because
the final affected area is not yet known; decoded QA decides actual WCAG failure.

Query filters unmet needs, unmeasured/over-limit costs, `avoid_for` sections and
breathe energy before sorting. Recipe cost is the sum of all layer costs.
Exact intent match=1; hit also admits drop/play/transition-energy at .5.
Technical gate evidence=1 for recorded stable, 0 for pending review. The score is
`4*intent_match + technical_gate_pass - .01*cost_ms - 10*history_occurrences`.
Each component is returned numerically in `reason`. With ≥3 eligible choices,
the last two selections are withheld from top-1; remaining ties use name then
kind. This eligibility tier is returned separately from score. `--history` is a
JSON list of names or objects with `name`; queries never mutate it. No time,
random seed or hash iteration order affects output. Empty CLI results return
`{results: [], explanation: {candidates, removed, remaining, method}}`. Counts
are sequential and mutually exclusive for card/status, unknown cost, max cost,
needs, section, energy and intent filters, so they sum to the original pool.

`fx_candidates` chooses 2–3 distinct eligible recipes for `drop` or `hook`,
uses timeline source frames in the event −1s..+3s window (clipped to duration),
and limits the short side to 540. It saves MP4s, peak thumbnails, paired decoded
measurements, timing/cost, a deterministic set id, and an offline HTML comparison.
These alternatives sample the resolved source; they do not bake in the old
effects or transitions. `--choose 2 --reason TEXT` writes `selected-plan.json`
with a `director_choices` record and the selected recipe. The source plan is
preserved. Independent recipe gates and perceptual distinctness remain required
before these are treated as production recommendations.
