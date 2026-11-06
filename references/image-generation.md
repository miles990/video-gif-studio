# Experimental image integration

`scripts/imagegen.py` maps to `vgs image` (no unified vgs executable exists in
this checkout). All generation requires `--experimental`. CLI results are one
JSON object; failures use `ok:false,error:{code,location,message,suggestion}` and
exit 2. Use the skill Python. Scratch, cache, attempts, and ledgers default to
`.scratch/image-state/`; retain that state for the whole round.

```text
python scripts/imagegen.py generate --experimental --prompt "Mia at the cafe" --aspect 9:16 --size 1080x1920 --out .scratch/image --json
python scripts/imagegen.py probe --out .scratch/probe --json
python scripts/imagegen.py usage --json
```

The default `codex` route runs noninteractive `codex exec`, verifies ChatGPT login,
strips OPENAI_* and CODEX_API_KEY from its child environment, and forces ChatGPT
authentication. `auto` stops on subscription failure. API-key Codex login is refused;
use the explicit paid adapter instead. Native image model selection/reporting,
GIF, masks/markup, SVG, and quality controls are unavailable on this route.
Sizes/aspects/quality are prompt instructions, not native tool parameters.
The November 6 probe evidence is mapped in `image-capabilities.json`; `probe`
exports this recorded table without implying it ran a new live probe.

Paid PNG requests require a reviewed `--prices` table, `--approve-spend` matching
the exact request/endpoint/price fingerprint, and `--max-usd` (default zero).
The calling agent must obtain explicit conversational consent before supplying
the flag. No price is invented. Table shape:
`{version,date,rows:[{model,quality,size,unit_usd}]}`. `estimate` performs no request.
`draft` maps to flare/low and `final` to sunburst/high on the explicit API route;
these are requested models, never falsely reported models. Paid references and
native GIF/SVG/edit are rejected; this build does not verify those live features.

Cache keys hash NFC/whitespace-normalized prompts (case and punctuation retained),
all generation parameters and ordered reference bytes. OS locks deduplicate across
processes. Failed requests are not cached. PNG bytes are verified before the cache
commit marker is written. `--no-cache` forces a fresh attempt. Quota failures retry
at most twice after 5 and 10 seconds; timeouts never automatically retry. Every
dispatch reserves an image against the round's cap (default 60, can be lowered).
Failures/ambiguous requests consume the conservative reservation, preventing retries
from exceeding the cap. Use a single state directory/round ID across processes.

Protocol references: [noninteractive Codex](https://learn.chatgpt.com/docs/non-interactive-mode),
[image generation](https://developers.openai.com/api/docs/guides/image-generation),
[PNG generation endpoint](https://developers.openai.com/api/reference/resources/images/methods/generate).
Delivery lineage marks AI-generated images. C2PA detection reads PNG caBX/JPEG APP11
containers only; signature validity and SynthID are not locally verified.

Storyboard and identity commands:

```text
python scripts/imagegen.py refset build --name mia --images pose1.png pose2.png --negative other.png --out .scratch/mia.json --json
python scripts/storyboard.py keyframes storyboard.json --refs .scratch/mia.json --experimental --out .scratch/kf --json
python scripts/animatic.py storyboard.json --keyframes .scratch/kf --out .scratch/animatic
python scripts/imagegen.py refset check --refs .scratch/mia.json --image keyframe.png --json
python scripts/imagegen.py refset review --refs .scratch/mia.json --same yes --comment "user response" --json
```

Every shot prompt includes shot size, composition, light, colour swatch and aesthetic.
`--shots 2 4` upgrades only those shots. Keyframes retain original timing, failed
shots retain labelled cards, and `brief_render` fingerprints the generated pixels.
Aspect fitting uses uniform contain/padding, never stretching or silently cropping
heads. Final short edge is at least 1080; draft at least 720. Palette ΔE2000 and
subject-mask framing metrics are recorded. Opaque images without a supplied subject
mask are framing-unassessed, not automatically declared correct. Human framing,
composition and aesthetic review remain required.

The identity library records up to 16 actual ordered paths/hashes/roles/sources.
The local CLIP cache contains tokenizer/config files, not usable model weights, and
the skill runtime has no torch/transformers. No embedding model is downloaded.
The fallback uses masked HSV Bhattacharyya distance plus ORB Lowe-ratio matches.
Every verdict reruns distinct-pose positive and different-identity negative controls;
failed controls stop assessment. Mixed libraries are refused. A library without
controls can still supply references but cannot claim measured identity consistency.
Failed keyframe identity gets one corrective generation, then a visible
`identity_fail` label. Human review is recorded separately and never auto-approved.

Local motion and GIF input:

```text
python scripts/imagegen.py motion --keyframes start.png end.png --size 352x352 --frames 48 --frame-ms 40 --out .scratch/loop --json
python scripts/gif_pipeline.py ingest input.gif --out .scratch/ingest --json
```

The PNG route cannot generate native GIF. `motion` creates a cyclic cosine dissolve
between keyframes (or a periodic camera zoom for one image), using premultiplied
colour interpolation. This is local keyframe animation, not synthesized articulated
motion. GIF encoding/decoded-alpha verification, qa_media loop checks and lossless
sprite packing use the existing pipeline. `image_motion.repair_loop` offers a
cosine-time ping-pong repair and records discarded frames. Ingest preserves Pillow's
disposal-composited RGBA and every original delay; the sprite JSON has those same
delays. Browser preview encoding may merge <=20 ms exposures, as documented by the
existing GIF pipeline. Grok/fal video generation is a separate user-approved step.

Transparent generation (`generate --transparent`) attempts native alpha first,
removes isolated alpha components <=1% of the largest subject, and despills
semi-transparent edge colours using nearby opaque subject pixels. It preserves
graded alpha. QA measures border transparency, isolated components/holes, black
background outer-band brightness, and CIEDE2000 edge colour continuity. RGB
checkerboards are detected from periodic neutral patterns on at least three edges;
an interior patterned tablecloth is a negative control. Opaque/fake-alpha output
gets one explicit solid-background regeneration and local chroma matting, recorded
as `alpha_source:matted`. A failed QA result is not delivered as a final sticker.
Output includes RGBA, binary-alpha PNG/GIF and black/white/magenta composites.
`alpha_qa.py image.png --json` is read-only; add `--cleanup --out new.png` to repair.

Local edits:

```text
python scripts/imagegen.py edit --experimental --image original.png --region 380,1100,320,360 --instruction "replace cup with latte" --out .scratch/edit --json
python scripts/imagegen.py delta storyboard.json --draft "第二鏡的杯子改成拿鐵" --experimental --out .scratch/v2 --json
```

The source is sent as an actual reference. `--markup` accepts a same-sized RGBA
annotation (closed outlines are filled); `--region` accepts bbox x,y,width,height
or a JSON polygon. Delta resolves named objects through shot `image_regions`,
e.g. `{"杯子":[380,1100,320,360]}`, or an explicit markup layer. Missing object
locations return E_REGION_REQUIRED, never a guessed box. `brief_edit.parse` and
`apply_changes` also retain structured image edits as pending work.
Regeneration is aligned using ORB/RANSAC or ECC translation with <=1 px measured
residual. A changed canvas is rejected. Only the selected mask plus a 2%-short-edge
margin is composited; inward feathering is <=8 px and all outside bytes are copied
exactly. Reports include raw outside drift and inside CIEDE2000 change; a no-op is
rejected. Semantic correctness and visible feather seams remain human review items.
Only changed shots receive new keyframe hashes; `brief_render.render_version`
reuses unchanged shot frames and recomposites neighboring transitions.

SVG fallback:

```text
python scripts/imagegen.py vectorize graphic.png --out .scratch/title.svg --colors 6 --json
python scripts/svg_safe.py .scratch/title.svg --json
python scripts/svg_render.py .scratch/title.svg --sizes 512,2048,4096 --out .scratch/title-renders --json
```

OpenCV contour tracing emits palette-filled even-odd polygon paths; no raster
payload, font dependency, scripts or external links. The safety parser uses stdlib
Expat with DTD/entity/external/processing-instruction handlers that reject before
ElementTree parsing (defusedxml is not installed). It rejects text until outlined,
foreignObject/image, event attributes, external href/CSS URLs and import syntax.
The FX/timeline image entry points validate SVG before rendering. The bundled
renderer supports flattened polygon paths and basic shapes at arbitrary sizes
with 2x antialiasing; curves, transforms and gradients require flattening or an
independently installed rasterizer. Safe unsupported geometry fails explicitly.
This is a flat-graphic tracing fallback, not native model SVG or font recovery.

Variants and picks:

```text
python scripts/imagegen.py variants --experimental --storyboard storyboard.json --shot 2 --n 4 --refs .scratch/mia.json --out .scratch/variants --json
python scripts/variants_pick.py .scratch/variants --choose v3 --json
python scripts/imagegen.py pick .scratch/variants --record .scratch/downloaded-picks.json --json
```

Each candidate is separately cached and carries its direction/fork ID, identity
measurement and real animated GIF preview (2.56 seconds). `pick.html` works offline,
shows a 9:16 safe area, supports keys 1–8, and downloads a user pick record. Local
storage preserves the click; applying the downloaded record or an explicitly
requested `--choose` writes append-only picks and `storyboard-picked.json`.
No AI ranking selects a candidate. Pairwise pHash distances flag insufficiently
different candidates, and failed identities cannot be applied as user picks.

Usage and provenance:

```text
python scripts/imagegen.py usage --state .scratch/image-state --round spec-13 --since 2026-11-06 --json
python scripts/imagegen.py generate --experimental --cap 30 --prompt "flat title graphic" --format svg --out .scratch/title --json
python scripts/imagegen.py generate --experimental --start-image frame.png --format gif --size 352x352 --out .scratch/loop-from-image --json
```

`--format gif|svg` invokes the recorded local fallback after PNG generation;
`--start-image` reuses existing material without any provider request. GIF parameters
are checked before generation. These options do not request a native GIF or SVG.
Usage groups append-only generation/reservation records by date, round and run.
Counts distinguish returned images, conservative reservations, failures and cache
savings. The route manifest schema is `image-manifest.schema.json`; derivative
manifests add `derived_from`, native/fallback method and downstream QA. Each source
PNG is preserved byte-for-byte, including original C2PA containers; derived PNGs
retain lineage rather than implying the original signature signs edited pixels.

The reused alpha probe exposed attached fragments as well as isolated specks.
Cleanup removes isolated components <=1% of the main subject and, only for a
near-binary sticker (>90% of visible alpha >=240), opens/erodes the silhouette by
1–3 pixels and applies a narrow 0.4 px antialias envelope. Soft artwork skips this
silhouette step. The original probe's black outer-band luma decreased from 12.74
to 3.17, with zero remaining speck ratio; the source remains untouched.
