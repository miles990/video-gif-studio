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
Phaser durations are additive to its base frame period, as described in the
[Phaser animation documentation](https://docs.phaser.io/phaser/concepts/animations).
Pixi uses the [Spritesheet format](https://github.com/pixijs/pixijs-skills/blob/main/skills/pixijs-assets/references/spritesheet.md).
