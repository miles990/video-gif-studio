# Stylized redraw over generated motion

**Status: routed from `SKILL.md` and the [transparency mode table](transparency.md).** Tools, bundled styles and checks are described below; [examples/stylized-redraw-seated](../examples/stylized-redraw-seated/README.md) is the accepted worked example (one plate, agent review under user delegation, frame inspection only).

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

### Effect layer by reviewed mask, not separation

An opaque composite does not determine separate character and effect layers ([matte quality](transparency.md#matte-quality)). This route therefore never claims to separate them. It **assigns** each plate pixel to one layer using a reviewed per-frame effect mask:

- Mixed pixels (glow over skin, trails through the body) are not unmixed; the mask gives them to one layer.
- Character regions hidden under effects are not recovered; the character layer has a gap there.
- The redraw needs only shapes and a palette per layer, so it does not require recovered effect RGB or alpha.

`propose_effect_masks.py` produces **candidate** masks for that review: foreground colors not within a per-channel tolerance of any color seen in effect-free reference frames. Reference frames therefore propose nothing by construction. Candidates are `review: pending`; effects that share character colors are missed and unseen character details are included.

Review loop:

1. `review_masks.py` exports the plate and a tinted mask overlay side by side (`frames/`, `overlay.png` APNG at plate timing), a `contact.png` sheet (flagged frames first) and `report.json` with per-frame areas, **isolated** frames (mask shares nothing with either neighbor) and **area jumps** (3x change). Flags are a queue, not verdicts: fast effects legitimately jump. Choose a tint absent from the effects.
2. `apply_mask_edits.py` applies an ordered JSON op list (`add`/`remove` by `rect` or `polygon`, optionally restricted to a `color` and `tolerance`; `clear`), over `"all"` or `[start, end]` frames. `add` never leaves plate foreground. Color-restricted `add` inside a rect recovers effect parts that share character colors without taking the character.
3. Re-run the review on the edited masks. Only a person who watched the result passes `--reviewed-by NAME`; the tool records that sign-off and otherwise leaves `review: pending`.

**Soft effect alpha.** Glows and fading trails often sit below the character's alpha threshold. `--effect-alpha plate --effect-alpha-floor 8` keeps masked pixels down to that floor and stores their measured plate alpha; the renderer then multiplies its fill coverage by it (`effects.alpha`, default `plate` when available, or `solid`). This is measured alpha from the plate's own matte, not unmixed foreground alpha. Lower `--alpha-threshold` on `propose_effect_masks.py` and `apply_mask_edits.py` so masks can reach those pixels. Do not combine a low floor with `binary`: faint pixels would render as solid blocks.

`extract_guides.py --effect-masks` records mask hashes, `mask_review: supplied by caller; not verified`, and the proposal/edit manifest beside the masks (`mask_manifest` with its `review` and `reviewed_by`). It never upgrades a review status.

## Creative styles with measured gates

The route keeps two properties apart: **what is drawn is open to authorship, how it is checked is not.**

- **Style plugins.** `style.plugin` names a bundled style in `scripts/styles/` (for example `paper_cutout`) or a path to an authored `.py` file defining `render(ctx) -> uint8 HxWx4`. `ctx` provides the reference render (`base`), per-layer masks, labels, rings, palette and measured effect alpha, `params` (`style.plugin_params`), frame index/count/canvas/timing, and `noise(key, shape)`: the same key returns the same field on every frame, so textures are stable by default and boil only when the frame index is part of the key. The plugin file hash is recorded in the render manifest. An opaque `background` is applied after the plugin.
- **Declared intent.** `style.intent` states deliberate departures: `boil`, `silhouette_min`, `silhouette_tolerance_px`, `interior_change_max`, `static_majority`, `offcanvas_ok`. Checks measure against that declaration, not against one house look.
- **`qc_redraw.py`** re-renders and requires byte-identical frames; checks timing and canvas; measures two-way silhouette agreement within a tolerance band; measures change in locally still regions **in excess of the reference renderer**, because guides already carry plate label noise; and flags figures cut by the canvas edge. Figure checks run on a background-free render. A check that finds nothing to measure reports `pass: null` and is listed as inconclusive; `auto_checks_passed` requires every check to be `true`.
- **Motion-attached texture.** `extract_guides.py --flow` stores OpenCV DIS backward flow with a forward-backward consistency mask, plus two layers of texture coordinates advected along trusted flow smoothed over the foreground (`smooth_px`, 4). A point is held still when either raw or smoothed flow is under `deadzone_px` (0.5): smoothing bleeds a moving limb's flow into its still neighbors, and raw flow jitters where nothing moved. Newly revealed surface continues from the nearest trusted pixel. The layers are cross-weighted by a per-point **surface phase** that is itself advected and, only while the point moves, advances by (current texture deformation - 0.03) / `--uv-clock` (0.25) per frame. Held, rigid and undeformed points never change weight, so they cannot shimmer; deforming texture cycles and re-anchors while it still moves. A layer re-anchors only at points whose phase wraps, where its weight is about zero, copying the other layer wherever that layer's interior deformation is under 0.015-0.03 (below the clock slack, so copies settle) and restarting coordinates only where texture actually deformed; rigid motion stays glued through resets. Deformation for the clock and the copy is read from interior gradients and carried to the silhouette by normalized convolution, because silhouette pixels meet the background grid and read as torn. Plugins blend per-layer texture by the per-pixel weight maps in `ctx['uv_layers']` (`ctx['uv']` takes the heavier layer per pixel). Deformation uses closed-form 2x2 singular values (60x faster than a batched SVD, identical to 5e-5). Plugins also read `ctx['flow']` and `ctx['flow_valid']`.
- **Texture distortion check.** A texture can stay attached yet deform. `qc_redraw.py` measures the weighted median of summed |log singular values| of each layer's uv Jacobian over trusted interior pixels (`uv_distortion_max`, 0.5). The limit is calibrated on one plate: runaway single-layer advection measured 0.77-1.4, while re-anchored layers through a fast leg switch and chair swivel stayed at or under 0.40, largely real foreshortening that a painted surface would also show.
- **Motion coherence check.** With flow guides, `qc_redraw.py` warps the frame 4 steps back (`motion_span`) along chained measured motion and counts moving interior pixels that land outside a 1 px tolerance envelope, in excess of the reference renderer (`motion_change_max`, default 0.05). Chaining exposes slow sliding that hides inside the tolerance frame by frame. Pixels where the guides' own layer blend changed by more than `blend_change_max` (0.1) over the span are cross-fading by design and are excluded, so attachment is judged where the blend held steady and a sliding texture still has nowhere to hide; transitions with fewer than 500 judged pixels are unmeasured. Sliding textures fail unless `intent.texture_slides` is declared. With flow, "still" for the flicker check means measured motion under the deadzone, because a uniform region can translate with unchanged labels.
- **JavaScript plugins.** A `.js` plugin (`async function render(ctx, api)`) runs in headless Chromium driven over the DevTools pipe with the standard library only (`scripts/js_style_host.py`; browser from `$VGS_CHROME`, Playwright's cache or PATH). It gets the reference render, subject mask and half-resolution `uv`/`flow`/`flowValid` (half-resolution pixel units), draws with Canvas 2D, and `api.noise(key)` replaces the disabled `Math.random`. The render manifest records the browser.
- **Bundled styles.** `paper_cutout` (grain anchored to canvas, centroid or `uv`; drop shadow), `ink_hatching` (pen hatching and hand wobble in texture space on a paper wash; effects keep color with glow) and `manga_action.js` (screentone in texture space; speed lines trailing parts that actually moved, sized by measured flow; declare `silhouette_min` near 0.8).
- **Three separate reviews.** Automatic checks, agent visual notes (`--agent-notes`, recorded as `by: agent`) and human playback sign-off. None substitutes for another; passing the automatic checks is not acceptance.

## Provenance

Record: plate source and generation record; guide extractors and versions; style sheet; renderer source hash, runtime and seeds; any plate-color sampling. The deliverable must state that its pixels are redrawn from a plate, not generator output.

## Spending

Plate generation follows the existing rule: one candidate, at most one focused corrective retry, new spending authority for more. Guide extraction and render iterations are local and do not consume provider quota.

## Acceptance

A stylized redraw is finished only when (a) the plate passed motion review, (b) the render passed the redraw review in step 5 at playback speed, and (c) the decoded output passed the [final quality gate](../SKILL.md#final-quality-gate). Missing any of these means a preview.

## Out of scope for this draft

- Lyric/typography layers and composition space for on-screen text (separate draft).
- Audio-referenced generation for lip-sync or beat-locked motion (depends on provider support; see [music](music.md)).

## First slice (bundled)

Decision: the reference renderer is Python on the existing Pillow/NumPy/OpenCV stack; no new dependency. A headless-browser renderer remains possible later for richer motion-graphics authoring.

```bash
# optional: candidate effect masks from effect-free reference frames, then review/edit them
.venv/bin/python scripts/propose_effect_masks.py run/plate --manifest run/plate.json --out run/fx-proposal --reference-frames 0
.venv/bin/python scripts/review_masks.py run/plate --manifest run/plate.json --masks run/fx-proposal/masks --out run/fx-review
.venv/bin/python scripts/apply_mask_edits.py run/plate --manifest run/plate.json --masks run/fx-proposal/masks \
  --ops ops.json --out run/fx-edit [--reviewed-by NAME]
.venv/bin/python scripts/extract_guides.py run/plate --manifest run/plate.json --out run/guides --colors 4 \
  --effect-masks run/fx-edit/masks --effect-colors 3 [--effect-alpha plate --effect-alpha-floor 8]
.venv/bin/python scripts/render_stylized.py run/guides --style style.json --out run/render
```

- **Input:** numbered RGBA PNG plate frames with real alpha plus a `durations_ms` timing manifest (for example `background_remove.py` output). A plate without alpha is refused.
- **`extract_guides.py`:** thresholded masks, simplified contour rings with holes, and per-frame label maps against **one deterministic palette shared by the whole plate**, so region colors cannot flicker between frames. The manifest records `iou_prev` per frame and the result lists frames below 0.8.
- **Effect layer:** with `--effect-masks`, masked pixels leave the character layer and get their own masks, rings, labels and shared palette under `effects` in the manifest. Without it, `effects` is `null`.
- **`render_stylized.py`:** flat fill (plate palette, palette override or one solid color) plus a tapered contour. Fills come from bilinear-upsampled masks, so area is exact and 1-2 px strokes survive; contours sit on the fill edge. Taper depends on each segment's outward normal against a light direction, never on arc length, so it does not crawl when contour start points change. Rendering is supersampled and deterministic; output is `frames/` plus a manifest with `durations_ms`, style hash, guide hash and renderer hash, ready for the existing export tools.
- **Style keys:** `fill` (`palette` or `#RRGGBB`), `palette` (hex list matching the guide palette), `region_smooth`, `background`, `supersample` (1-8), `line.color`, `line.width`, `line.taper` (0-1), `line.light`. `effects` takes `fill`, `palette`, `region_smooth`, `line` (default no outline), `order` (`over`/`under`), `opacity` (0-1) and `alpha` (`plate`/`solid`); it is refused when the guides have no effect layer.
- **Style plugins and QC:** `scripts/styles/paper_cutout.py` (paper grain anchored to the canvas or the figure centroid, soft drop shadow) and `scripts/qc_redraw.py`, described above.
- **Tests** cover timing/canvas preservation, holes, shared-palette determinism, byte-identical re-renders, integer-translation coherence, effect-layer palettes and compositing, proposal behavior, review flags, ordered mask edits, review-status provenance, soft effect alpha, plugin contract and each QC check including inconclusive results.

### Findings from a local trial (chibi-running-dash APNG, 112 frames at 768x768)

- Contours, holes and motion followed the plate; re-renders were identical. About 0.4 s per frame at supersample 4.
- **Effects lose their color identity in a single layer.** One shared palette remapped pink dust and magenta speed trails into character colors. With an effect layer, both kept their own colors.
- **Proposal tolerance.** A palette-distance heuristic flagged every frame, including the reference, because rare chroma-spill fringe colors were averaged out of the palette. Comparing against every reference color fixed that. Sweeping per-channel tolerance on this plate: 12 and 20 still flagged idle frames; 44 lost most of the dust; 32 (the default) left idle frames empty while catching the dust and the magenta/violet trail portions. White and green trail portions matching the sword and gem were missed, as expected, and need manual mask edits. The trial render used unedited proposals and is not an accepted result.
- **Review loop.** `review_masks.py` on the tolerance-32 proposal (4 s for 112 frames) flagged two isolated frames. Zoomed inspection showed both were false positives on the character: violet shoulder fringe plus a hilt highlight (frame 67) and a speck on a boot that the plate itself had tinted magenta (frame 25). Two `clear` ops removed them and the re-review had no isolated frames. The masks remain `pending`: missing white/green trail parts were not added and nobody signed off.
- **Soft effect alpha.** Slash frame 53 had 5,247 plate pixels below alpha 128. On frames 50-56 with alpha-8 proposals, `plate` mode faded trail tails and faint specks like the plate, while `binary` with the same low floor drew those specks as solid blocks. The white trail body stayed in the character layer because the proposal cannot see it; that is a mask gap, not an alpha issue.
- **QC on a real plate.** The first still-region rule (every label unchanged in a 9x9 window) measured nothing on all 111 transitions: generated video flips a few labels every frame. It is now a majority rule (same label here, at least 90% unchanged nearby), which found 983+ still pixels per transition on frames 0-15, and flicker is measured as excess over the reference renderer. Results: built-in and canvas-anchored paper grain 0 excess (pass); centroid-anchored grain up to 63% of still pixels changed on the 7 transitions where the rounded centroid moved (flagged); per-frame reseeded grain up to 79% on all 15 (flagged). A first run with an opaque background also exposed that figure checks must ignore the background; they now use a background-free render.
- **Texture that stays attached can still rot.** On the 289-frame seated plate, single-layer advected hatching passed every automatic check, but agent review of frame 286 showed straight hatching bent into marble-like waves. Measured uv distortion was already 0.5-0.77 by frame 48 and 1.4 by frame 288: generated-video flow carries per-pixel noise, and advection integrates it. Flow smoothing alone cut growth by only a third. Distortion grows roughly linearly with layer age (about 0.06 at 12 frames, 0.13 at 24 with smoothing), so re-anchored layers bound it, and the new texture-distortion check keeps the regression from passing silently. Getting there took several measured wrong turns, each caught by a check or by looking: a frame clock bounded deformation but 196-209 of 288 frames shimmered in still regions; a travel clock removed the shimmer but deformation ran away again (1.33) because flow noise and revealed-surface seams deform texture without travel; a strain clock failed the same way (1.26); a deformation clock bounded deformation but still shimmered, because smoothing had bled a moving limb's flow into still neighbors so they never counted as held. Declaring stillness from either raw or smoothed flow, then freezing held points and clocking only moving ones, gave deformation max 0.19 on the first 121 frames with no still pixel changing layer weight. Carrying texture through flow that failed the consistency check was also tried and rejected: deformation rose to 1.9. A clock sweep on 121 frames then showed a monotonic trade-off with no shimmer at any setting: clock 0 (one layer) 0 of 109 transitions flagged for motion but deformation 1.13; 3: 24 and 0.79; 0.9: 40 and 0.52; 0.25: 53 and 0.21. Frame inspection favored 0.25 (straight hatching; gradual stroke change while moving), and the motion check was refined to exclude declared cross-fades rather than loosened. Final 289-frame results: manga_action.js passed all seven automatic checks; ink_hatching on uv passed six, with motion flagged on 2 of 11 measurable transitions (a preview); the same hatching pinned to the canvas was flagged on 10 of 11. Only 11 of 246 moving transitions had enough steady-blend pixels to judge, so attachment evidence at this clock is thin. Per-frame warp checks also hid slow sliding (under 1 px per frame, inside the tolerance); chaining flow over 4 frames separated canvas-pinned hatching (144 of 246 measured transitions flagged) from uv-attached hatching (1).
- **`iou_prev` also flags genuine fast travel.** The dash frames were listed as low IoU because the body moves, not because masks flickered. Treat the list as a review queue, not a defect verdict.
- The trial source is pixel art, which this route does not target by default; it was used only as an available RGBA plate.

## Remaining open questions

1. **Interactive mask painting.** JSON ops cover clears, rects, polygons and color-restricted adds; freehand painting over playback would need a small review page.
2. **Soft character edges.** Character layers remain thresholded; motion-blurred limbs may also want measured alpha, which needs care not to reintroduce plate matte noise.
3. **Pose extraction.** Whether to add an optional keypoint extractor, or keep masks and contours only.
4. **Re-anchor pop.** A point re-anchors on the frame its phase wraps, when its layer weight is small but not exactly zero (about twice that frame's phase step).
5. **Routing.** Add the mode row to [transparency.md](transparency.md) and a short entry in `SKILL.md` only after a worked example passes acceptance.
