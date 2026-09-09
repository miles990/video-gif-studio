---
name: video-gif-studio
description: Create and refine continuous-motion GIFs from generated or existing video, with optional image references. Includes motion direction, phase-specific timing, chroma-key or alpha processing, alignment, global-palette encoding and decoded-frame QC. Use for animated characters, objects and transparent GIF deliverables; use a sprite skill for intentionally discrete pixel-art animation.
---

# Video GIF Studio

Deliver an inspectable animation, its source lineage and a reproducible export. Preserve the user's latest motion, appearance and camera preferences. Reference images are optional; an existing video can be sufficient. Do not inherit this skill's founding character, pose, color, duration, or chair constraints into unrelated work.

## Defaults unless the user specifies otherwise

- Motion follows plausible physics and visible cause and effect: support and weight transfer drive the body, the hand drives a held weapon, and cloth/particles follow with appropriate inertia. Effects never substitute for missing physical movement.
- Let the action produce reasonable whole-body travel by default: stepping, lunging, advancing, retreating and returning to balance are allowed when motivated. Show coherent support, push-off, pelvis movement, weight acceptance and recovery. Do not prescribe stationary feet or an immobile lower body merely to simplify alignment or looping; a fixed camera/canvas does not mean a fixed character. Honor an explicitly requested in-place animation or movement limit while retaining plausible weight transfer within it.
- Human characters retain coherent anatomy, limb proportions, joint ranges, muscle and soft-tissue tension, perspective, foreshortening and occlusion throughout the motion. These defaults also apply to pixel art and stylized humans; explicitly requested exaggeration or nonphysical behavior overrides the relevant default.
- When effects are requested, let **Grok design and generate them in the video**. Specify the action, causal timing, readability and background-separation constraints; leave effect shapes, colors and details to Grok unless the user supplies art direction. Do not invent effects for a task that did not request them. Local work defaults to matting, sampling, timing and encoding, not drawing or layering new effects. Record any user-requested exception and actual effect provenance.
- Keep the entire character, weapon and effects visible by default, including trails, expanding particles and their complete dissipation. Frame for the maximum extent over the whole action, not just the starting pose. Do not crop effects at the canvas edge or cut their decay short to fit an export. Respect explicitly requested off-screen action/cropping; otherwise treat lost effect content as an unfinished deliverable.
- A seamless-loop request remains an acceptance requirement through later revisions. Repeated playback is not seamlessness. A preview with a visible boundary mismatch is unfinished, even if encoding checks pass.
- For a loop that returns to its starting location, include a natural recovery and return path. Do not replace that path with per-frame recentering, position snapping or locked feet. Preserve intentional character travel during export.

## Requirements

For installation requests, follow [references/install.md](references/install.md). Use this skill folder's `.venv/bin/python` (Windows: `.venv/Scripts/python.exe`) for its scripts; do not assume the current shell Python has the dependencies. `scripts/doctor.py` reports local readiness without spending generation quota.

The complete AI generation workflow requires **Codex + Grok**: Codex runs this skill, directs the motion, uses available image generation when needed, and processes/verifies the output; Grok supplies generated continuous video. Grok must be authenticated and have usable video-generation entitlement/quota. This version includes its own OAuth REST client, using the official Grok CLI for sign-in and credential refresh as described in [references/grok.md](references/grok.md). Do not imply the repository provides accounts, subscriptions or credits. Existing video/RGBA conversion can run locally without a new Grok call. Alternative providers are an explicit adaptation, not a bundled dependency.

## Select the route

- **Existing video:** inspect it first; keep actual continuous frames when the action is usable. Diagnose before regenerating.
- **Reference images:** view them and assign roles (identity, costume, proportions, pose, camera, palette). Record exactly which references are actually sent to the provider. A prompt description of a photo is not an uploaded photo.
- **No reference:** author an original subject and motion brief. When a stable character is useful, generate a start image using the available image-generation tool, inspect it, then animate it. Direct text-to-video is an alternative only if the active provider supports it; do not claim an untested route is verified.
- **Natural articulated movement:** prefer a continuous video source over independently generated pose sheets. Independent images, crossfades and optical-flow interpolation cannot reliably invent missing joint paths.

For generated raster art, follow the available image-generation tool's instructions; do not replace requested artwork with procedural placeholders. For a chosen video provider, check its live capabilities, authentication, supported inputs and pricing exposure. Read [references/grok.md](references/grok.md) for the bundled Grok client and its limits. A missing provider must be reported, not hidden behind an unrelated static animation.

## Direction and generation

Read [references/motion.md](references/motion.md) when designing or revising action. Write a concise visible plan and one executable prompt. Separate:

1. Appearance/camera invariants and reference roles.
2. Ordered action phases, support/contact, anticipation, travel, contact and recovery.
3. Approximate phase durations and playback intention.
4. Secondary motion and motivated camera/prop movement.
5. Background/lighting requirements and intended loop behavior.

Use the user's existing authorization; do not insert a generic approval gate. Ask only for a consequential missing choice, new spending authority, or a required missing input. Generation authorization does not authorize publication or messages to others. Default to one candidate; allow one focused corrective retry within authorized scope, then reassess from pixels rather than blindly resubmitting. Do not retry ambiguous submissions without recovering the existing job ID first.

Preserve source files. Save prompts, ordered input roles and hashes, model/settings, job ID, provider status, actual duration/dimensions and reported usage. Keep auth tokens and signed delivery URLs out of shared artifacts. A provider response saying `done` proves generation, not correct anatomy or natural motion.

## Inspect and refine

For background removal or output selection, read [references/transparency.md](references/transparency.md). Default to **Auto**, preserving source motion and character pixels; keep graded alpha in RGBA masters and use APNG for soft-alpha animation, with GIF as a compatibility preview. Honor an explicit format request. Users may choose **Preserve artwork** or **AI repair/redraw**; these are workflow choices, not CLI flags. Do not automatically redraw every frame with GPT-Image-2.5 or another image model. Verify actual model access and alpha capability, and recheck temporal consistency after any requested repair. A game-use request should lead to PNG frames and an engine-appropriate asset plan, not a GIF-only delivery. The bundled `scripts/sprite_export.py` packs uniform RGBA frames into multi-page sheets with timing and fixed-pivot metadata; see [references/sprites.md](references/sprites.md).

Watch the complete source at playback speed when a playback surface is available; separately inspect transition frames at useful resolution. Contact sheets cannot establish cadence. State when only frame inspection was available. Check joint paths, limb identity, contact, occlusion, shape continuity, subject detail, camera and prop motion. Use user feedback as evidence: do not "fix" a chair swivel or body counterbalance the user accepts as natural.

When motion is slow, distinguish **moving phase** from **settling pause**. "Natural speed" is not automatically 1× generated speed. Apply smooth phase retiming when the path is sound; regenerate when the path is absent or anatomically wrong. Do not mask a bad transition with a cut, ping-pong playback or blended ghost limbs. Read [references/export.md](references/export.md) for exact CLI input and output behavior.

For transparent output, prefer a separable constant background chosen to avoid subject colors, or source alpha. Magenta is useful, not mandatory. The included keyer is for uniform chroma backgrounds only; complex scenes need a temporal matting tool. Preserve interior negative spaces. Do not flood-fill every interior hole or erode the subject as a universal repair. Check masks over both dark and light backgrounds.

Keep a shared canvas. Only stabilize measured unwanted camera drift; never recenter every frame by its bounding box, reshape anatomy, or pin a naturally moving prop without justification. Keep original camera/prop movement unless the brief calls for a change. Loop closure requires compatible pose, velocity and contact; do not label a visible end/start jump seamless.

Read the loop and causal-review guidance in [references/motion.md](references/motion.md) before accepting articulated actions, effects or a requested seamless loop. Review actual weapon paths separately from effect trails. If a bounded corrective retry still fails, retain the unfinished status and explain the specific remaining defect rather than relabeling a preview as complete.

## Export and verify

Run `scripts/gif_pipeline.py` from this skill folder. Dependencies: Python 3, Pillow, NumPy, OpenCV; FFmpeg/ffprobe for VFR video conforming and optional delivery formats. Export into a new run directory, never the skill directory. The helper accepts a CFR video or a numerically named RGBA PNG directory.

Essential GIF invariant: reserve a palette index exclusively for transparency. Quantize visible colors independently and assign transparent pixels from alpha explicitly. Never choose the "nearest magenta" palette color as transparency; this can punch holes in skin shadows. All frames share one palette. Use explicit disposal and verify the **decoded GIF**, not just source PNGs.

The helper validates every decoded alpha mask against its source threshold, dimensions, frame count and total duration. Inspect skin/fabric color error and edges as well. This proves export integrity, not matting truth, no source flicker, anatomy, natural cadence, or target-app rendering. For a reported defect, compare raw source → RGBA → decoded GIF at the same source index and timing; use [references/failure-modes.md](references/failure-modes.md).

Deliver the GIF inline, a download link and concise changes/limits. Retain source, masks/frames, timing, contact sheets and provenance. Offer APNG or video when gradients, alpha softness or file size matter. Never rename a lossy GIF limitation as a stylistic success. If the source remains flawed, deliver only a clearly identified preview plus the unresolved issue.

## Worked production example

When an actual reference-to-video-to-GIF case or transparency regression example would help, read [examples/seated-leg-switch/README.md](examples/seated-leg-switch/README.md). It contains the actual uploaded reference, full prompt, source video, final corrected GIF, timing and hashes. These are examples, not default character design, pose, speed or duration settings. Do not load its large media for unrelated tasks.

For a no-user-reference example, see [examples/robot-wave-no-reference/README.md](examples/robot-wave-no-reference/README.md): an original start image, a real generation through the bundled Grok client, and a verified transparent GIF. Distinguish zero user references from the generated image used as the video's starting frame.

For a pixel-style running attack with Grok-generated effects and identical pinned endpoints, see [examples/chibi-running-dash/README.md](examples/chibi-running-dash/README.md). It includes GIF/APNG, source, prompt, timing and verification; playback-speed seamlessness remains unverified.

## Pixel-art defaults

When pixel art is requested, default to pixel-native processing: work on the established logical pixel grid, preserve intentional color clusters, stepped contours and limited palette, and use integer nearest-neighbor presentation scaling. Do not blur, smooth, add antialiasing, use optical-flow inbetweens or regenerate every frame to conceal a bad key. Fractional alpha remains valid for intentionally soft or fading effects; pixel art does not imply globally binary alpha. Pixel-style AI video may lack a consistent native grid: report that limitation instead of claiming nearest-neighbor export creates hand-authored pixel art. Read [references/pixel-art.md](references/pixel-art.md) for edge repair and validation. Honor explicitly requested mixed styles or filtering.

## Optional delivery formats

Users may select any combination of **GIF**, **APNG**, **RGBA PNG frames**, **Sprite Sheet**, or **complete asset pack** (frames, sheets, metadata and previews). Treat these as output choices, independent of Auto / Preserve artwork / AI repair. Honor explicit selections; do not require a format questionnaire for every task. With no selection, use GIF plus an RGBA/APNG master for sharing and PNG frames plus sheets/metadata for game use. Ask about a target engine only when an engine-specific importer/material is required; generic sprites can be prepared immediately.

Read [references/sprites.md](references/sprites.md) for sprite export. Keep all frame canvases and the pivot stable, preserve full effects and fractional alpha, and retain intentional displacement. A user may choose page size, padding, native pixel scale and pivot. Infer reasonable defaults and record them. Never claim generic sheets are engine-tested resources, infer hitboxes from glow, or invent gameplay events/root-motion tracks. For looping actions, pinned first/last provider inputs are an available generation technique when supported, but pose/contact/velocity and actual repeated playback still require review.
