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
