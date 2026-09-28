# Stylized redraw over generated motion (design draft)

**Status: design draft.** Not yet routed from `SKILL.md`, not listed in the transparency mode table, and no renderer is bundled. Do not present this route as implemented or verified until those steps and an accepted worked example exist.

## Intent

Use a generated or supplied video as a **motion plate**, then author every delivered pixel with a renderer (canvas/SVG/procedural code, or reviewed per-frame drawing). The plate contributes timing, poses, contacts, camera and occlusion; it never appears in the delivered frames. This follows traditional rotoscoping: shoot first, draw over it.

It is a fourth direction mode beside Auto, Preserve artwork and AI repair/redraw:

| Mode | Delivered pixels come from | Fixes |
| --- | --- | --- |
| Auto / Preserve artwork | Source frames | Matting, timing, encoding |
| AI repair/redraw | Source frames, with reviewed local replacements | Localized defects |
| Stylized redraw (draft) | A renderer driven by guides measured from the plate | Look/style; plate texture and edge noise become irrelevant |

## When to use

- The user asks for a style a video model cannot hold consistently: paper cut-out, flat vector, ink line, limited-palette motion graphics or similar.
- The plate's motion is accepted, but its texture, fine edges or matte cannot reach the requested finish without extensive repair.
- The deliverable needs authored alpha, resolution independence or editable layers that an opaque composite cannot provide (see [matte quality](transparency.md#matte-quality)).

Do not use it:

- To rescue bad motion. Redrawing preserves the plate's joint paths, contact errors and timing. Regenerate or retime first ([motion](motion.md)).
- As an unrequested default. Users who asked for the generated look get Auto/Preserve artwork.
- For pixel art unless requested; pixel-native handling ([pixel-art](pixel-art.md)) remains the default there.

## Pipeline

1. **Accept the plate for motion only.** Apply the normal motion, contact, loop and playback review to the plate. Matte cleanliness, edge noise and fine texture are not plate acceptance criteria; anatomy, travel, occlusion order and cadence are. Record the plate's provider provenance as usual.
2. **Measure guides.** Extract per-frame data the renderer will consume: silhouette masks (chroma key or `background_remove.py`), region/color segmentation, contours, and optionally pose keypoints or optical flow when an extractor is available. Record each extractor, model and version. Guides are measurements and flicker like any framewise mask; review them over playback and smooth only measured noise, never real motion.
3. **Write a style sheet.** Palette, line weight and taper, fill and texture treatment, shape simplification rules, layer order and effect language. Test it on three representative frames before a full run: an extreme pose, the fastest motion frame and the hardest occlusion.
4. **Render deterministically.** The renderer reads guides, not raw plate pixels (sampling plate color is an explicit, recorded option). Fix seeds so re-renders are identical. Texture must be temporally coherent: intentional line boil is a style choice declared in the style sheet; unplanned per-frame noise is a defect. For browser renderers, step frames under controlled virtual time and read the canvas per frame; never screen-record realtime playback, which drops or duplicates frames.
5. **Review the redraw.** At playback speed and against an onion-skin overlay of the plate, check: shape popping, contour crawl, identity drift across the shot, occlusion order at crossings, contact placement (feet and hands on their surfaces), and loop boundaries. A redraw can introduce defects the plate lacked; it inherits none of the plate's acceptance.
6. **Export.** Render straight RGBA frames at the shared canvas and timing, then use `gif_pipeline.py`, `video_export.py` or `sprite_export.py` as usual. Authored alpha is exact, so the decoded-output gate verifies encoding against the renderer's frames, not against a matte estimate.

## Effects

Requested effects from the generator become guides like the body: their paths, timing and dissipation extents are measured from the plate and redrawn in the style sheet's effect language. Keep full effect extents on canvas. Do not invent unrequested effects because the renderer makes them cheap. Record that effect shapes are redrawn and which plate provider designed their motion.

## Provenance

Record: plate source and generation record; guide extractors and versions; style sheet; renderer source hash, runtime and seeds; any plate-color sampling. The deliverable must state that its pixels are redrawn from a plate, not generator output.

## Spending

Plate generation follows the existing rule: one candidate, at most one focused corrective retry, new spending authority for more. Guide extraction and render iterations are local and do not consume provider quota.

## Acceptance

A stylized redraw is finished only when (a) the plate passed motion review, (b) the render passed the redraw review in step 5 at playback speed, and (c) the decoded output passed the [final quality gate](../SKILL.md#final-quality-gate). Missing any of these means a preview.

## Out of scope for this draft

- Lyric/typography layers and composition space for on-screen text (separate draft).
- Audio-referenced generation for lip-sync or beat-locked motion (depends on provider support; see [music](music.md)).

## Open questions before implementation

1. **Renderer runtime.** Python (Pillow/skia-python, no new heavy dependency) versus a headless-browser canvas renderer (needs a managed Chromium; see [dependencies](dependencies.md)). A Python reference renderer is lighter to bundle; a browser renderer supports richer motion-graphics authoring.
2. **Pose extraction.** Whether to add an optional keypoint extractor, or rely on masks and contours only for the first version.
3. **Bundled scope.** Minimal first slice: `extract_guides.py` (masks, contours, per-frame bounding data into a manifest) plus one reference style (flat fill with tapered contour) and tests for determinism and canvas/timing preservation.
4. **Routing.** Add the mode row to [transparency.md](transparency.md) and a short entry in `SKILL.md` only after a worked example passes acceptance.
