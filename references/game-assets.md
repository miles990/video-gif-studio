# Experimental game assets (spec-14)

This checkout has no unified `vgs` CLI. Use `python scripts/imagegen.py` with
`character sheet`, `animate`, `sprite-check`, `iconset`, `tile`, `vfx`,
`kf-video`, or `demo game`. All game commands require `--experimental` and
emit the image pipeline's JSON success/error envelope.

Character sheets use `character sheet --prompt TEXT --out DIR --experimental`
with optional `--image`, `--pixel 64`, `--negative PATH...`, `--near-negative
PATH`, and repeated `--asymmetric-feature 'scar above character-left eye'`.
The ten subscription calls reuse accepted output references; size is prompt
text followed by explicit local resampling. Pixel mode records
`fallback: pixel_quantize`. Generated expressions are composited only inside
the recorded face box. Inspect that box for the actual character before use.

The named-character guard offers original alternatives. It is not an exhaustive
IP recognition model: reference art must be original, owned or licensed, and
the operator must reject official art. Never use mirrored assets when
`mirror_ok` is false. Side/back views derived from one reference are inferred.

Identity uses the existing ORB/HSV fallback at the stricter game histogram
threshold, with a palette exception only for side/back. Missing independent
positive, negative, or near-negative evidence means **unassessed**, not pass.
Generated views and expressions retain measured QA and pending human review.

`animate --charsheet DIR/charsheet.json --states idle,run,attack,hurt --out DIR
--pose-plan plan.json --experimental` generates 2–4 reference key poses per
state and fills the intervening frames locally. A plan maps state names to
`key_indices`, optional `keys: [{image, points, refs_sent}]`, `frame_count`,
`durations_ms`, `contacts: [{foot, frames:[first,last], box:[x,y,w,h]}]`,
`foot_boxes` (per-foot/per-frame boxes), `phases`, `events`, `weapon_colors`
and `target_box`. Points must correspond anatomically between keys. Without
annotations the silhouette mesh is a preview fallback, not a joint detector.
No alpha crossfades or horizontal mirroring are used. Pixel interpolation is
nearest piecewise-affine pixel displacement and cannot introduce new colors.

Contact QA samples actual lowest opaque foot pixels, adding declared root
motion for world-space checks. Attack QA finds the first overlap of annotated
weapon colors with the target rectangle; trails must use different colors.
The phase names are anticipation, swing, contact, follow_through, recovery.
Jump QA measures airborne center-of-alpha parabolas and requires preparation
and landing compression. Generated motion remains pending visual review; a
failed report is retained with offending frame numbers, never called seamless.

`sprite-check IMAGE... --experimental [--cleanup --out DIR] [--alpha-mode
straight|premultiplied] [--pixel 64 --palette palette.json --scale 3]` checks
alpha-mode evidence, real transparency, disconnected specks, halo colors,
shared canvas, exact integer grid and new colors. Cleanup preserves opaque
silhouette pixels and intentional gaps. `--particles` exempts deliberate
detached VFX; it does not exempt malformed alpha. Internal holes require an
annotated intended-negative-space mask for semantic classification.

Engine export: `sprite_export.py anim/ --anim-manifest anim/idle/anim.json
anim/attack/anim.json --out export/ --engine godot4,unity,phaser-hash,phaser-array,pixi,aseprite
--pixel --padding 2 --extrude 1 --experimental`. Each output page is decoded
and each crop compared byte-for-byte with its source. Sidecars retain all
per-state timing, event and pivot data, including cross-page state sequences.
Godot resources use format=3 and relative res:// textures. A real Godot test
project and playback checker are included; Unity remains format-only/untested.
Phaser 3.90 durations are full frame periods, as implemented in its pinned
[Animation.getNextTick source](https://github.com/phaserjs/phaser/blob/v3.90.0/src/animations/Animation.js).
Pixi uses the [Spritesheet format](https://github.com/pixijs/pixijs-skills/blob/main/skills/pixijs-assets/references/spritesheet.md).

`iconset --items sword,shield,potion,key,scroll,gem,bow,boot --style-token style.json
--pixel --out DIR --experimental` takes a token with `grid`, `outline_hex`,
`outline_px`, `light_deg` (Cartesian: upper-left = 135), `safe_margin`,
`palette`, and `shading`. `--fix` remeasures existing icons, regenerates only
outlier indices against an accepted icon, and verifies other files keep their
SHA256. A light direction is n/a for genuinely flat shading. Material-color
variation can confound the brightness-plane proxy; inspect retained failures.

`tile texture --prompt "original mossy stone" --size 256 --out DIR --experimental`
uses a referenced subscription image followed by recorded periodic repair.
Wrap differences, Sobel seam ratios, FFT axes, half-image illumination and
retained high-frequency energy are reported. `tile tileset --grid 16 --set
wang16 --out DIR --experimental` builds a procedural terrain transition set;
`blob47` and `min13` are also supported. This first implementation uses a fixed
grass/soil palette; it does not interpret an arbitrary tileset art prompt.

`vfx --kind explosion --oneshot --frames 12 --size 96 --blend add --out DIR
--experimental` produces local original procedural sprites and scene previews.
`magic`, `hit`, and `pickup` are available. `--loop` selects looping motion;
`--pixel` selects the tighter frame budget, retaining graded glow alpha.
The declared blend is used for the preview; additive masters have zero RGB
outside alpha support. One-shots must fade in and out within their budget.

`kf-video --first k0.png --last k1.png --route local --duration 2 --out DIR
--experimental` does local nearest pose interpolation and emits RGBA masters,
GIF/APNG and opaque black-composited MP4. It makes no model/network call.
This is a pose preview, not a physical-motion solver.

For `--route grok|fal`, the first call returns `E_APPROVAL_REQUIRED`, an
input-bound `estimate_id`, and local alternatives. Reviewed `--prices` JSON
contains `route`, `version`, ISO `date`, and `usd_per_second`. Approval binds
the hashes of both endpoints, every reference, prompt, route, duration,
prices and driver, and expires after 30 minutes. After explicit conversation
consent, `--approve-video ID` authorizes that one estimate. Environment keys
never confer approval. A submission receipt prevents automatic duplicates.

The bundled video routes currently cannot transmit first+last+identity refs
together, so approved calls without a verified `--video-driver` fail with
`E_VIDEO_CAPABILITY`. The driver reads one JSON object from stdin:
`route`, `prompt`, `duration_seconds`, absolute `first_frame`, `last_frame`,
`reference_images`, and `estimate_id`. It must send all inputs once, then print
JSON containing local `video`, `first_frame_sha`, `last_frame_sha`, ordered
`refs_sent` SHA256 values, and `network_calls`. A receipt is evidence of
transport only: returned media is decoded, screened, and retained as pending
identity/motion review. No live paid-video validation has been performed.

`demo game --source-pack source-pack.json --out DIR --vendor LOCAL_VENDOR
--godot GODOT4_EXE --experimental` assembles an existing original source pack
without generation. It records camera transforms and source hashes, retains
all source images, and writes a portable pack under `sources/`. Use a fresh
output directory. The source pack contains view transforms, six expression
crop boxes, four pose strips with corresponding anatomical guides, icon crop
boxes, and provenance; the supplied Rimewick pack is the concrete example.

The demo returns `status: experimental_preview`; successful assembly is not
acceptance. Read `qa-summary.json`. Contact intervals omitted by an author
remain unassessed. Strict key-pose identity metrics may also be unassessed;
they are not silently upgraded from a shared palette. The live icon atlas
does not yet meet every outline/value consistency gate.

For actual browser checks, place `phaser-3.90.0.min.js` and optionally
`pixi-8.6.6.min.js` under the local vendor folder, with their licenses. Run
`node scripts/check_game_browser.js DEMO/phaser-demo PLAYWRIGHT_MODULE
CHROMIUM_EXECUTABLE REPORT.json`. The check blocks external requests and
tests hash/array atlas loads, every frame, runtime version, timing metadata,
and events. Missing runtimes stay untested. Windows sandboxes that deny
ancestor traversal may require Node's `--preserve-symlinks
--preserve-symlinks-main` flags. No npm installation or CDN access occurs.

`game_review.review_bundle(demo, out)` prepares eight blinded moving pairs,
including damaged foot/color/seam controls and two identical pairs. The
answer key is separate; do not expose it to reviewers. Automatic checks and
an independent technical reviewer do not supply user taste votes. Wilson
lower bounds remain null until real votes exist.
