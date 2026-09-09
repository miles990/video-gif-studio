# Reference packs and continuation chains

This is a Codex-coordinated workflow, not an implemented automatic chain runner. Keep source video, APNG preview/master, PNG frames and provenance together. APNG is not a replacement for the source video or a supported multi-frame model input by assumption. Supply separately selected static PNGs to image-reference routes.

## User-selectable reference modes

| Mode | Selection and use |
| --- | --- |
| Suitable keyframes, up to seven | Distinct, legible states relevant to the next task: preparation, load transfer, acceleration, action extreme, landing, recovery. Useful for reinterpretation or a new sequence. Do not assume image order enforces motion order. |
| Last frame plus consistency references | Preferred for requested continuation: pin the previous endpoint as the next first frame, plus a small set of stable character/costume/weapon/style references where the provider supports the combination. Retain an original identity reference instead of relying only on recursively generated frames. |
| Last frame only | Simple short continuation using the endpoint as the new first image. Record missing velocity context and increased risk of appearance drift across repeated segments. |

The seven-image reference-list limit does not establish how separate first/last pins count toward a combined request. Verify the current model's limits for the exact input combination. Never claim nine images are allowed by adding two pins to seven references without confirmation.

## Select suitable frames

1. Inspect the actual video and the intended next edit/action. Preserve source timestamps, original frame indices and any retimed output mapping.
2. Select for purpose, not equal intervals. For appearance edits favor sharp, unobscured views of the relevant parts. For motion choose distinct support, weight and pose states. For continuation prioritize the endpoint and useful preceding motion context, plus stable identity references.
3. Reject duplicate poses, deformed anatomy, clipped effects and frames whose occlusion makes the intended subject unreadable. Do not fill all seven slots unnecessarily. Automated difference/scene scores may nominate candidates but do not replace visual review.
4. Do not silently replace a flawed true endpoint with an earlier frame. If an earlier clean boundary is preferable, record the deliberate trim and its timestamp, preserving the original source. A final still alone cannot encode velocity or weight transfer; describe these from the preceding motion.
5. Keep an identity/master reference separate from action references. Review original-grid consistency for pixel art. Do not smooth or independently recenter reference frames.

Create `reference-pack/` with selected PNGs, a labeled contact sheet, the next-step prompt and a portable JSON record. For each image include relative path, hash, source video/frame timestamp, role, selection reason and any known defects. Include parent source hash, APNG path, selected mode, intended action, duration, invariant appearance/camera constraints, verification status and next-step instructions. Do not include credentials or signed URLs. Source and output times must not be conflated after retiming.

## Choose the actual provider route

- **Edit the original video:** submit the original video plus changes through a verified video-edit endpoint. Do not assume reference images can be combined with video editing. Check unchanged content against the original; generated edits need not preserve every other pixel.
- **Generate from references:** use a verified multi-reference route with PNGs and explicit action order/timing. Reference poses are guidance, not exact intermediate keyframe constraints. Pin endpoints only when the model supports it.
- **Continue the action:** use a supported video-extension route when appropriate, or pin the last frame as an image-to-video start (with consistency references if supported). Record which method was actually used; a new clip from a still is not a true video-extension call.
- **Convert only:** use the existing local RGBA/APNG/GIF/sprite pipeline; do not request another generation merely to change output format.

The bundled `grok_video.py` currently supports one start image. Multi-reference, first/last pins, video editing and extension require a verified task-specific adapter or future CLI implementation. The running-dash example used a production-local pinned-frame adapter; that does not establish general CLI support. Validate requests against current official [reference-to-video](https://docs.x.ai/developers/model-capabilities/video/reference-to-video), [video editing](https://docs.x.ai/developers/model-capabilities/video/editing) and video-extension documentation before implementing a route. Reuse the bundled client's safe authentication and job ledger semantics rather than printing tokens or blindly retrying ambiguous submissions.

## Execute, review and hand off

Allow **reference pack only** or **continue generation**. Preserve the user's selected mode and existing authorization. Do not launch a generation from a documentation-only request. A one-segment continuation does not authorize unbounded generations. For repeated chaining establish a target duration, segment count or budget; stop at the agreed bound or when a segment fails review. Preserve prior accepted segments and redo only the rejected segment within the authorized retry limit.

At each join compare pose, support/contact, velocity, camera/scale, palette, pixel grid and effects already in flight. Review repeated playback when possible and record when unavailable. Never conceal discontinuity with a blind blend, reversed action, snap or per-frame recentering. Keep unresolved review status in the handoff; an encoding pass is not creative acceptance. Join accepted segments into a long video when requested; use short APNG/GIF previews rather than assuming unbounded animations are practical.

The next skill receives the reference pack, source lineage, requested task and unresolved issues. Codex reads and follows the next installed skill; files do not execute another skill themselves. Do not automatically create a new Codex task or publish assets as a side effect of chaining.

## One-request long-video production

“One request for a long video” means Codex runs this skill repeatedly for bounded segments, reviews each join and combines accepted segments into a video. It is not one unlimited Grok generation. Retain a shared project brief, stable identity references, segment lineage and agreed duration/segment/budget limits across invocations. A segment can use the chosen keyframe, endpoint-plus-references or endpoint-only mode. Reuse accepted source artifacts rather than generating earlier segments again.

A final long-video export is separate from generation: conform canvas, frame rate, codec and color/alpha conventions, join reviewed segments, preserve intended timing and verify joins plus total duration. Do not remove duplicate boundary frames blindly if they are intentional holds. MOV/WebM are optional outputs; GIF remains the default for ordinary short-animation requests. The bundled video exporter handles a prepared frame timeline; it does not itself orchestrate generation, join arbitrary source clips, handle audio or implement the full chain runner.

Prepared segments may now be joined with timed stills using the bundled [local timeline composer](timeline.md). This composes existing frames and optional video exports; it does not implement automatic Grok generation or arbitrary source-video ingestion.
