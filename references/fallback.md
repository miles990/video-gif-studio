# Fallback when video generation is unavailable

For new motion, use Grok by default when available unless the user chooses another route. Enter this fallback workflow when Grok is unavailable or explicitly skipped; do not prefer keyframes merely because they are easier.

Do not stop at a provider failure before checking usable resources. Preserve the user's subject, style, format, transparency request and quality requirements. Report the actual route and any reduced motion scope. An outage does not authorize extra paid services or silently switching OAuth to API-key billing.

1. **Existing suitable video or frames:** reuse and edit them locally. Preserve source provenance and do not claim a new generation.
2. **Available image generation:** for simple actions, create reference-consistent keyframes, inspect the source layout, split/alignment-process them and assign meaningful exposure times. Good candidates include blinking, facial expressions, small object changes and intentionally discrete sprite animation. Read the available image-generation skill; use a sprite skill when appropriate. Raw visual changes must come from image generation or user-supplied art, not code-drawn substitutes. A compact multi-row sheet can improve consistency; inspect its actual grid before slicing. Use only limited measured global alignment; do not warp anatomy or recenter intentional travel.
3. **Existing layered art and local tools:** animate actual separable parts for limited motion when this meets the request. Do not pretend a moving crop of a flat image demonstrates articulated motion. Honor image-editing tool instructions and distinguish local compositing from new artwork.
4. **Other video provider:** only use it when available and authorized; disclose provider/cost changes before a new paid route. A named alternative service is not automatically installed or funded.

If complex movement cannot meet the user's requirement with available resources, prepare a concrete partial asset and state the missing capability. Ask only when the alternative materially changes a strict requirement or requires new spending authority. A user who already accepts keyframe fallback need not approve it again. Do not arbitrarily simplify a specifically requested action without saying so.

## Failure handling

A spending-limit, quota, permission or terminal provider rejection must not trigger repeated submissions, an account switch, or an authentication refresh loop. Ambiguous submissions must retain/recover the original job first. Record the original failure and chosen fallback; do not mark the rejected job completed. Existing generation authorization covers an appropriate available image-tool alternative unless the user required that exact provider or continuous-video route.

## Keyframe delivery and QC

Save the reference, generated sheets/images, actual grid, frame order, alignment transforms, exposure times and output checks. Use the bundled `gif_pipeline.encode` / `verify` functions or the prepared-frame timeline composer for variable durations, global palette and decoded-frame verification. PNG/APNG masters preserve partial alpha. Do not key dark eyes/shadows away merely because the backdrop is dark.

Check identity, eye/limb counts, facial landmarks, silhouette, lighting and palette across frames. Use longer rest poses and shorter moving phases where appropriate; more repeated frames do not add new movement. Do not label a four-pose animation as 24 distinct generated poses per second. Do not use optical-flow or crossfades to conceal missing anatomy. Reusing closing eyelid poses in reverse order can be a deliberate simple blink; reversing an attack/walk does not invent a natural recovery.

A loop needs compatible pose and velocity at the join. Equal first/last artwork and technical GIF checks alone do not establish full-speed seamlessness. State when only frame inspection was available. Label the result **image-generated keyframe animation**, not a Grok video or equivalent-quality continuous motion. Retain the original effect requirements; when a non-Grok fallback makes effects, record the actual source rather than claiming Grok generated them.
