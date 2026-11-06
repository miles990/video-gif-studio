# The user's taste, measured before and after rendering

This vocabulary is absorbed from the **使用者 wow 詞彙檔**:
`mood-pacing-arc.md` §E; `mastery-signals.md`; `3d-vfx-game-av.md` §I/§K;
`music-sound-design.md`; `cinematic-lighting.md`; `scene-staging-layout.md`.
The original URLs are retained below. These are instruments and planning advice,
not an AI aesthetic score. Technical defects decide technical eligibility;
appeal, restraint, spectacle and recommended defaults belong to the user (U).
The first spot-check preferred burn_through and luminance_melt over their panel
references. Do not reinterpret those choices as a preference for restrained cuts.

## Vocabulary and executable rule IDs

| Term / plain meaning | Good / common failure | Measurement or rule ID | Original source |
|---|---|---|---|
| Unity of intent / explain why an element exists | A specific connection to the core / copied core sentence | `intent_coverage` | [Vignelli Canon](https://www.rit.edu/vignellicenter/sites/rit.edu.vignellicenter/files/documents/The%20Vignelli%20Canon.pdf) |
| Focal hierarchy / where the eye lands | Saliency overlaps the intended subject / a distractor wins | M10, `focal_hierarchy` | [Nodine et al.](https://muse.jhu.edu/article/606664/summary) |
| Economy of means / remove only what contributes nothing | Compare lossless category ablations / equating minimalism with quality | `deletion_test` | [Rams](https://www.vitsoe.com/us/about/good-design) |
| No weak zone / fix the accidental trough | Compare against intended rests / calling every quiet moment bad | `weakest_window` | [Masterpiece](https://en.wikipedia.org/wiki/Masterpiece) |
| Distinct voice / compare against the default | Three autoplan seeds plus human evidence / arbitrary numeric difference | `default_distance` | [Preference typicality bias](https://arxiv.org/abs/2510.01171) |
| Rule of Six / preserve emotion first | Emotion > story > rhythm > eye trace > 2D > 3D / continuity overriding emotion | `eye_trace`, `angle_30`, `axis_180` | [Walter Murch](https://nofilmschool.com/2016/11/6-rules-good-cutting-according-oscar-winning-editor-walter-murch) |
| Eye trace / focus across the cut | Outgoing and incoming gaze align / unexplained diagonal jump | `eye_trace` | [Eye trace](https://www.studiobinder.com/blog/walter-murch-rule-of-six/) |
| Match on action / cut while movement continues | Cut near motion peak / cut after motion ends | M6, `cut_on_action` | [Match on action](https://www.studiobinder.com/blog/what-is-a-match-on-action-cut/) |
| Shot rhythm / distribution, not just average | Purposeful duration changes / unintentional slideshow | M1, `shot_cv`, `shot_size_variation` | [Cinemetrics](https://cinemetrics.uchicago.edu/) |
| J/L-cut / sound bridges the image cut | Source sound enters early or leaves late / every boundary chops both | `audio_bridge` | [J-cut](https://www.studiobinder.com/blog/what-is-a-j-cut-in-film/) |
| Build-up, drop, breakdown / contrast makes a payoff | An intended valley before the hit / always at maximum | M4, M15, `pre_peak_valley`, `effect_budget` | [Drop](https://en.wikipedia.org/wiki/Drop_(music)), [Breakdown](https://en.wikipedia.org/wiki/Breakdown_(music)) |
| Mickey-mousing / synchronized action sounds | Deliberate comedy or selected accents / every movement gets a hit | `mickey_mousing` | [Mickey Mousing](https://en.wikipedia.org/wiki/Mickey_Mousing) |
| Color script / color carries an arc | Coherent per-section palette / unrelated shot grades | `token_lut`, `token_texture` | [Pixar](https://www.khanacademy.org/computing/pixar) |
| Design tokens / an explicitly chosen vocabulary | Consistent typography, transitions, moves and sounds / accidental extra families | `token_font`, `token_transition`, `token_motion`, `token_sfx` | [Vignelli Canon](https://www.rit.edu/vignellicenter/sites/rit.edu.vignellicenter/files/documents/The%20Vignelli%20Canon.pdf) |
| Shot matching / neutral correction before a look | Match exposure and white balance, then LUT / a LUT amplifies mismatches | ΔE2000 before/after | [Resolve color](https://www.blackmagicdesign.com/products/davinciresolve/color) |
| One movement / a readable camera intention | One move and compatible recipe / a push competes with a punch | `one_motion` | [Murch priorities](https://www.studiobinder.com/blog/walter-murch-rule-of-six/) |
| Intensity design / state the intended arc first | Predict, measure, reconcile / fabricate a good-looking curve | M15, `design_curve` | [Hanjalic & Xu](https://doi.org/10.1109/TMM.2004.840618) |
| Cut-to-beat offset / signed timing error | Reviewed beat timestamps / guessed soundtrack timing | M2 | [librosa](https://github.com/librosa/librosa) |
| Onset density / audible events per second | Chosen rhythmic density / unnecessary event multiplication | M3 | [librosa onset](https://github.com/librosa/librosa) |
| Climax exposure / save a lighting contrast | A deliberate brightness payoff / starting at maximum | M4 | [Film lighting](https://en.wikipedia.org/wiki/Film_lighting) |
| Colorfulness / opponent-color statistic | Match the user's color target / treating saturation as quality | M5 | [Hasler–Süsstrunk](https://doi.org/10.1117/12.477378) |
| Motion energy / displacement over time | Appropriate acceleration and stillness / continuous movement without purpose | M6 | [OpenCV optical flow](https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html) |
| Spectral centroid and bass ratio / brightness and weight of sound | Bass supports weight / a hit has only treble | M7 | [librosa spectrum](https://github.com/librosa/librosa) |
| Loudness range / audible dynamics | LRA matches the user's intent / needless compression | M8 | [EBU 3342](https://tech.ebu.ch/docs/tech/tech3342.pdf) |
| Visual clutter and negative space / resting places for attention | Chosen focus hierarchy / uniformly busy frame | M9 | [Rosenholtz et al.](https://doi.org/10.1167/7.2.17), [Negative space](https://en.wikipedia.org/wiki/Negative_space) |
| Saliency / an attention proxy | Concentration and centroid support composition / claiming actual eye tracking | M10 | [Saliency map](https://en.wikipedia.org/wiki/Saliency_map) |
| Silence / a measured breathing interval | Intentional rest / treating silence as a defect | M11 | [FFmpeg silencedetect](https://ffmpeg.org/ffmpeg-filters.html#silencedetect) |
| Cue sheet and button ending / timed events and closure | Align visual and sound punctuation / cut a musical phrase accidentally | M12 | [Cue sheet](https://en.wikipedia.org/wiki/Cue_sheet_(computing)), [Button source, originally unverified forum](https://forums.taxi.com/post256908.html) |
| Contrast range / P1–P99 and clipping | Readable shadows and highlights / crushed or clipped subjects | M13 | [Zone System](https://en.wikipedia.org/wiki/Zone_System) |
| Continuous response / the person's felt curve | Human input explicitly identified / presenting a proxy as emotion | M14 | [Schubert](https://doi.org/10.1525/mp.2004.21.4.561) |
| Novelty / changes in measured features | Detect structural changes / claim semantic understanding from pixels | M16 | [Foote](https://doi.org/10.1109/ICME.2000.869637) |

## Commands and file contract

All commands run offline; output paths below must be outside the repository.
Use the installed skill's Python environment and available FFmpeg, without
installing or writing into that environment. Runtime schema validation uses
`jsonschema` if available, otherwise the existing offline schema validator.

```text
python scripts/taste_report.py film.mp4 --design design.json --out EXTERNAL/taste
python scripts/storyboard_lint.py storyboard.json --out EXTERNAL/preflight --prompts
python scripts/animatic.py storyboard.json --music song.wav --out EXTERNAL/animatic
python scripts/storyboard_lint.py storyboard.json --out EXTERNAL/ready --prompts --animatic-receipt EXTERNAL/animatic/receipt.json
python scripts/fx_lint.py plan.json --tokens tokens.json --storyboard storyboard.json --taste-report EXTERNAL/taste.json --out EXTERNAL/lint.json
python scripts/mastery_lint.py plan.json --out EXTERNAL/ablations
python scripts/shot_match.py plan.json --ref-shot 0 --out EXTERNAL/matched
python scripts/taste_target.py reference1.mp4 reference2.mp4 --out EXTERNAL/target.json
python scripts/taste_pick.py spotcheck --out EXTERNAL/taste.json
python scripts/taste_pick.py ingest --choices choices.json --out EXTERNAL/taste.json
python scripts/taste_pick.py prepare --choices moving-pairs.json --out EXTERNAL/pairs
python scripts/taste_pick.py show --out EXTERNAL/taste.json
python scripts/taste_pick.py reset --out EXTERNAL/taste.json
python scripts/taste_director.py image.png --duration 30 --core "Arrival" --profile EXTERNAL/taste.json --target EXTERNAL/target.json --out EXTERNAL/treatment
```

`taste_director` is the opt-in treatment route. It writes design_curve before
rendering and applies the profile/target to shot timing and recipe density.
The director, report and reference-calibration CLIs accept `--profile PATH`.
The default profile is **`references/taste-user.json` in this checkout**, containing
the user's first eight spot-check answers regenerated through the current family
registry (cross-warp and swirl are `warp`). `VIDEO_GIF_TASTE` overrides the default
location; an explicit `--profile` takes priority. A missing/deleted/reset profile returns factory
defaults. A corrupt profile warns and reads factory defaults; updating preserves
the original, writes `.bak`, and writes a separate `.recovered.json`.

Profiles can store `weights: [motion, cut_rate, short_term_lufs, luminance_delta]`;
values must be finite, nonnegative and have a positive sum. `--weights` overrides
the profile for report/calibration. Targets record requested and effective weights;
`taste_report --target target.json` and the director warn about mismatches.
The director accepts `--brief brief.json` from the director agent. Its authored
`design_curve` points take priority, followed by `design_curve_intent` (`build`,
`calm`, or `settle`). Explicit fields override keywords in `--core`. Without these
fields, core keywords are a fallback. A temporal instruction such as "calm
opening then build" requests a rise; "build a calm meditation ambience" describes
creating an ambience and stays level. Ambiguous wording can use the explicit
`design_curve_intent` field.
The director accepts `--music music.json` with section `start`/`end` seconds (or
`start_ms`) and `energy` in 0..1. Explicit brief intent takes priority;
otherwise section energy shapes the curve. With no explicit arc or music, the
provisional curve is level. A crescendo is generated only when requested.
Missing or undecodable images/footage become silhouette cards and are listed in
`assets/asset-fallbacks.json` and the animatic receipt. Expanded effect windows and
envelopes are clamped to film duration; adjustments are separately listed.

For measured focal checks, add `--movie film.mp4` to `fx_lint` and a grayscale
`subject_mask` path per storyboard shot (relative to the storyboard). Missing
masks are explicitly unassessed. `shot_match --lut look.cube` optionally bakes
a 3D creative LUT **after** matching, with a separate after-LUT ΔE report.
`prepare` accepts at least eight records with id, A/B clip paths, one dimension,
and roles including positive_control/negative_control. It creates an offline
video comparison page and keeps control labels in a separate private key.

Each choice has `id`, `date`, `source`, `choice` (A/B/tie), `dimension`, optional
`judge`, and `options: {A: {...}, B: {...}}`. Numeric preference fields are density,
color, flashiness and caption_scale; a step is bounded to ±15%. Two explicit votes
can change the primary transition family or categorical caption_style. `--context mv/reels` isolates a context
profile. No preference changes technical gates. Ingest is idempotent by choice ID.
Panel agreement follows P-USER Wilson 95% lower bounds, excluding panel ties and
negative controls; low agreement invalidates the appeal ranking, never an effect.
Deliver at least eight moving pairs with hidden positive/negative controls. Do
not fabricate answers or infer density/color preferences from transition votes.

`tokens.json` follows the object returned by `taste_lint.default_tokens`: `color`
(script, one lut, skin_protection, skin_hue_degrees), `type` (fonts, size_ratio,
stroke, shadow), `transitions` (primary/accent), `texture` (effect maxima), `motion`
and `sfx`. Families are explicit metadata in `fx-cards.json`, not inferred from
filenames. Defaults are starting vocabulary, not restrictions on an entire genre.
`taste-styles.json` supplies three selectable token starting points (observational,
spectacle, graphic), without ranking them. `examples/taste-storyboard.json` is a
zero-footage example using the existing shot table and an impact recipe.

## Reproducible instruments and limits

- Times are seconds (rounded to millisecond precision when sampled), frame IDs
  are zero-based. M1 reuses the `fx_reverse` chroma/structure detector, rejecting
  isolated white flashes and detecting coherent cumulative dissolves. Adaptive
  spatial HSV changes additionally find same-palette cuts. Boundary
  events include type/confidence; review ambiguous transitions. Unconfirmed
  transition centers do not trigger frame-exact cut-on-action recommendations.
  Short spatial blends (including 0.2 s card dissolves with overlapping accents)
  use persistent endpoint changes and temporal coherence; exposure-only changes
  are rejected. Some same-palette wipes remain unlocalized. Automatic shot
  numbers are explicitly **provisional on the report front page**; authored
  storyboard timing is used for shot-specific revision advice when supplied.
  CV uses `ddof=0`
  and is null for a single shot. Persistent paired letterbox/pillarbox bands in
  the opening second plus nine distributed samples are excluded; the measured
  active rectangle is recorded. Band detection uses spatial P90 rather than
  maxima, tolerating sigma=3 noise. Fully black samples do not determine the crop.
  Variable aspect ratios can require manual ROI review.
- M4 is BT.709 limited-range Y estimated from decoded RGB. Its jump compares the
  next 0.5 s mean with the preceding 1 s mean. A constant film has no declared peak.
  Single-frame flashes are listed separately in `M4.flash_events` and Markdown;
  they are not represented as a 0.5 s sustained lighting payoff.
  M5 uses the Hasler–Süsstrunk opponent-color formula at source resolution.
- M6 uses pyramidal LK corners at width ≤320, reporting the 90th percentile
  displacement back in original pixels/frame, with bidirectional validation,
  robust noise estimation and floor subtraction. Cut frames are excluded. This
  foreground-motion proxy is not a dense flow mean or a segmentation system.
- M7 uses a 2048-sample Hann FFT, 240-sample hop, 48 kHz, power-weighted centroid
  and energy below 80 Hz. M3 uses 5 ms peak envelopes with a 50 ms refractory
  interval; textured music needs reviewed onset/beat annotations. M8 calls FFmpeg
  `ebur128=peak=true` directly; PLR = true peak − integrated LUFS. No audio yields
  null with a reason. Silent audio and audio shorter than 400 ms have null LUFS/LRA;
  all audio shorter than 10 seconds carries a low-confidence flag. M11 is 5 ms
  RMS below −50 dBFS, a configurable starting point.
- M9 is Canny edge density, not Rosenholtz feature congestion. M10 is blurred
  local Lab contrast against median Lab, top 5% / total. The normalized centroid
  uses only the salient region (top 5%, also at least 25% of the peak), not the
  low-contrast background mass.
  Focal overlap uses its top 10% region and a supplied mask. It is not gaze data.
  M13 records full-resolution per-frame P1/P99 and exact 255 clipping proportion.
- M12 accepts a manifest, retains its `transitions`, and adds neighboring-frame
  brightness and loudness evidence to events. Timed manifest transitions suppress
  redundant local review prompts. Without a manifest, detected flash/flash_cut
  intervals suppress those prompts and are explicitly labelled **assumed designed**
  in the JSON summary and Markdown, rather than claiming authored intent.
  Design-gap deviations remain reviewable.
  M14 stays null without human data. M16 uses adjacent mean-RGB novelty,
  a lightweight feature-difference approximation, not a semantic/self-similarity
  model. These known limitations cannot be turned into aesthetic verdicts.
- M15 at 10 Hz: `smooth_2s(.35*z(motion)+.25*z(cut_rate)+.30*z(short_term_LUFS)+.10*z(abs(deltaY)))`.
  Cut rate counts boundaries within ±0.5 s. z uses whole-film population SD;
  near-constant channels become zero before normalization. Whole-film range must
  exceed original-unit floors: 0.3 px/frame motion, 0.5 cuts/s, 0.5 LU, and 0.5 Y
  luminance delta per 100 ms. Peak eligibility also requires local raw variation
  above a floor within ±1 second, before z-scoring. These instrument noise floors
  are exported in M15; they are not aesthetic thresholds.
  Smoothing is a centered 20-point uniform box,
  offsets −10..9 with edge replication. Nonnegative weights are normalized;
  negatives/zero sum are rejected. Peak/valley ratios are signed z ratios and may
  be negative; zero denominators are null with a reason.
  Each complete trailing three-second EBU window is timestamped at its center
  (`t - 1.5 s`); edge regions hold the nearest complete window. Films shorter than
  three seconds have an unavailable loudness component. Requested and effective
  weights are exported separately; unavailable loudness and constant components
  are removed and remaining weights renormalized. If no requested component
  remains, all effective weights and the proxy are zero. The front page names
  the weight source (`cli` for `--weights`, `user` for profile/API overrides, or
  `default`). Opening exposure fades from black
  are excluded from peak selection, with the detected fade end recorded.
  Raw M8 EBU output is retained. This prevents the meter's −120 LUFS warmup from
  inventing an opening build in a constant soundtrack.
- Comparison uses Pearson r and peak offset only for varying design curves.
  Planning-vs-planning residuals retain original amplitudes. For measured films,
  the already-smoothed M15 proxy is first affinely aligned: its P5 and P95 map
  to the sampled design's P5 and P95. Degenerate quantile spans use full min/max
  spans; a constant proxy maps to the design minimum (no evidenced build).
  There is no time warping or clipping, so shifted peaks and localized deficits
  remain visible. `comparison.measured` and `alignment` export the exact aligned
  samples and anchors used by deviations, weakest-window selection and the plot;
  raw M15 values stay unchanged. Measured two-second residuals within the C-class
  `taste.curve.residual.max` (0.08 planning units) are ignored as alignment/meter
  tolerance, calibrated against encoded clean-film and freeze controls. Above-design
  samples are excluded from shaped-design missing lists; level excesses are labelled
  `exceeds design`. Exact planning matches
  use numerical tolerance only. This is relative shape alignment, not an absolute
  arousal calibration. Peak timing uses the mass centre above a three-sigma band,
  with sigma estimated from second-difference MAD of the measured curve. The band
  is capped at half the range to prevent baseline valleys joining distinct peaks;
  only the contiguous lobe containing the first maximum participates. Offset is
  zero inside an authored maximum plateau, otherwise distance to its nearest edge.
  Designs with only point peaks retain sampled peak timing. Multiple maximum intervals remain
  separate. The bar-limit comparison allows 1e-9 for floating-point error.
  Constant curves have no peak. Noise estimate and authored intervals are exported.
  Film-wide advice has `scope:
  "film"`, a null shot and the full duration; it is not pinned to the first second.
  Zero or rounded-to-zero clipping percentages do not create exposure prompts.
  Designs with SD <0.02 use RMS deviation only for planning-unit predictions
  (review tolerance 0.15). A measured standardized proxy cannot assess flatness:
  measured level designs instead export physical-unit dynamics and review limits:
  LRA 5 LU, short-term loudness P10–P90 5 LU, luminance P10–P90 25 Y units,
  and motion P10–P90 3 original pixels/frame. Unavailable evidence does not
  trigger revision. Automatically filled flat curves are not authored revision
  targets. None of these comparisons requests a missing accent in level intent.
  Absolute arousal cannot be calibrated from a standardized film-relative proxy.
  These are
  disclosed instrument tolerances, not quality gates. Deviations identify seconds,
  overlapping shots and directional actions. Flat/ambient designs relax shot-CV
  and pre-drop dip advice. Sustained energy is a valid intention.
- Report JSON includes a front-page summary; Markdown includes weakest two
  seconds, timestamp/shot-specific review actions and exemption counts.
  The weakest designed window uses only negative measured-minus-design residuals;
  over-measured designed dips cannot win. If no deficit exists it is null.
  Designed/annotated events suppress redundant suggestions, so no minimum
  suggestion count is manufactured for a black or fully annotated film.
  Without a design, a low proxy interval is a review candidate, never a
  mandate to increase energy. Black samples are labelled `no content` and excluded
  from window selection unless the storyboard declares `designed_black: true`.
  If no content-bearing window exists, weakest start/end are null.
  Near-black detection tolerates sigma=3 noise around limited-range Y=16;
  no-content samples have null saliency centroids and produce no eye-trace advice.
- PNG uses Pillow, fixed geometry/colors and no timestamps. It marks peaks,
  preceding valleys and bar labels when a design is supplied. Repeated identical
  analyses are deterministic. `taste-weakest.png` contains three actual extracts.
- A7-2 deletion tests use lossless frames: mean |ΔY| ≤0.5 and PSNR ≥48 dB.
  Identical frames give null PSNR with an infinite-PSNR explanation. Nontrivial
  contributions go to paired review; silence of a visual ablation does not prove
  a sound effect is dispensable. A7-5 default distance uses three seed ranges,
  with P-WIN evidence still required to claim a human preference.
- Matching estimates per-channel gains from linear-light channel quantiles,
  preserving the reference shot and strength-zero sources exactly. Reports use
  D65 Lab and CIEDE2000 before any existing creative LUT. Corresponding charts
  support pixelwise ΔE; unrelated compositions need a shared chart/ROI for a
  meaningful numerical match. Clipped source channels cannot be recovered.
- Reference targets retain only ASL, CV, LRA, onset density, peak/valley ratio and
  colorfulness P10/P90, averaged across 1–3 references. No reference paths, frames,
  waveforms, embeddings, caches or per-frame arrays are exported. Source footage
  for the new film must be independently supplied; targets cannot reconstruct it.

Existing advice boundaries are registered as `taste.*` in `thresholds.json`.
F entries describe the fixed instrument/acceptance definition; U entries are
overridable user advice; C entries remain `calibrate_first`, never eligibility
gates. Algorithm windows/kernels are documented measurement definitions, not
quality grades. No threshold is calibrated on the candidate being judged.

Annotate an intentional break on the relevant shot/element (or the whole film):
`"rule_break": {"rule":"eye_trace","reason":"The reveal deliberately disorients"}`.
The finding remains visible as `annotated` with the original reason. This cannot
waive decoded WCAG, audio, alpha or other technical checks. Sound/structural
readability concerns remain explicit; Rule of Six does not mean every film must
follow the same pace, color, family or amount of spectacle.

Transition and caption objects accept their own `rule_break`. A storyboard-level
`rule_break: {"rule":"*", "reason":"Deliberate installation grammar"}` or
`taste_exemptions: {"enabled":true, "reason":"Deliberate installation grammar"}`
annotates all taste advice while preserving every finding. The summary lists
every declared exception, its scope and the number of affected findings. Empty
reasons do not waive advice. `kind: "jump_cut"` exempts angle, eye-trace and
cut-on-action advice for deliberate discontinuity; technical gates remain separate.
