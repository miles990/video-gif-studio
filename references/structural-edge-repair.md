# Structure-aware edge repair

Use for reported fragments, dirty hems, fringe, jaggies or edge flicker. First understand the object; a pixel statistic cannot determine whether a detail belongs to it.

## Establish the intended structure

Inspect the full raw frame, then the affected component at useful magnification. Identify material, folded surfaces, trim, true silhouette, cast/contact shadows, overlaps and negative spaces. For a garment, follow the cloth into its hem: lace scallops and fold shadows can be legitimate; a disconnected green/gray layer beneath them may be a keying remnant. Preserve coherent lighting, texture and the chosen style. Pixel-art steps, strands, fur, translucent effects and detached particles are not automatically defects.

Compare the same source index through raw source, matte/RGBA, atlas, encoded video and target player. Inspect RGB and alpha on light and dark backgrounds. Distinguish source artifacts, matting errors, resampling, encoding and playback before changing anything.

## Repair the identified component

1. Define the reviewed repair region, foreground/material evidence and protected regions. Track a moving region when necessary. Coordinate/color thresholds are clip-specific evidence, not universal garment rules.
2. Use the original source to classify unwanted background. Despilled RGB may already have recolored green shadows as gray cloth; it is then unreliable evidence of object identity. Background connectivity is useful but does not by itself prove that every green edge is unwanted.
3. Remove confirmed non-object pixels rather than merely reducing their opacity. Preserve legitimate holes and occlusion boundaries. Resolve the silhouette from its surrounding material/shape, not from island area alone.
4. Repair only the altered boundary. Use limited alpha antialiasing and extend appropriate adjacent foreground RGB into newly partial pixels. Do not replace intact cloth RGB with a constant/nearest color across a broad band; this erases lighting and folds. Do not blur the whole frame or repeatedly smooth an already processed output.
5. Review continuous motion and loop/transition boundaries. If the edge changes incoherently across time, distinguish moving lace from flicker. Motion-aligned temporal treatment is an option only after segmentation is correct; validate occlusion and reject warped mismatches to avoid ghosting. Optical flow cannot establish semantic ownership or repair missing motion.

When the user says fragments remain, reopen structural diagnosis. Increasing erosion, island size or blur strength is not evidence of a better repair.

## Verification and batch operation

- Retain source hashes, frame mapping, canvas/pivot/contact/timing metadata, operation version and the actual region/mask criteria.
- Assert protected interior RGB and pixels outside the repair band are unchanged; separately inspect modified boundary lighting. Zero interior changes does not prove a correct silhouette.
- Decode exported files; verify frame count, timing, alpha and target rendering. A video reaching its end proves playback, not absence of flicker.
- Provide matched A/B previews at the same geometry, background, speed and encoding quality. Keep original, candidate, locally verified and user-accepted states separate. Fix caching with content-derived media versions.
- A library request means inventory every clip and report per-clip status. Group by material/pose only after inspection, use bounded per-component masks, and flag exceptions such as props or colored effects. Do not transfer one fixed ROI/threshold to unrelated frames or label a successful sample as all-library acceptance.
- Process offline; avoid adding runtime filters to compensate for defective assets. Use atomic outputs, resumable per-clip records and a disk-space guard. Keep necessary reversible pixel deltas while comparing/retrying; avoid routine full-application backups. Restore a known pre-filter state on retry/version upgrade rather than accumulating smoothing.

## Observed case: crouched lace hem

A 1080-square, 24 fps, 124-frame character source had dark green floor shadow under pink-white lace. A bright-key distance mask retained shadow; nearest-foreground despill made some of it resemble gray fabric. Source-connected green cleanup improved the result, but global small-island removal and local contour smoothing still left user-observed hem fragments/flicker. A temporal candidate was explored but was not accepted as the solution.

The accepted local preview instead scoped the actual lower hem, identified nearby pale lace in the raw source, and removed connected green backdrop remnants adjacent to that lace. It reconstructed only the affected boundary, protecting cloth interiors and neighboring components. All 124 frames retained protected interior and outside-region pixels; the user then confirmed the visible defect appeared gone. This accepts that preview, not every asset or the entire animation library. No character-specific region, color threshold or media is a default for this skill.

## Bundled repair tool

`python scripts/repair_edges.py --frames rgba-frames --remove-masks reviewed-removal-masks --protect-masks protected-detail-masks --out repaired-run`

All directories contain identically named PNGs. Removal masks mark confirmed unwanted pixels in white; protection masks override removal, preserving accepted light/shadow/material detail. Protection masks are optional, but deciding which pixels belong to the object remains part of the visual review. The tool preserves canvas and untouched pixels, removes the masked pixels completely, limits smoothing to the adjacent band, and losslessly verifies each output. Use `--smooth 0` for intentionally hard/pixel-native contours. Retain the original timing metadata and feed repaired frames to the existing export pipeline. The report deliberately says visual/export review is still needed; it is not a semantic defect detector. Existing video or atlas input should first be extracted at the original frame mapping, then repacked without altering timing/pivots.

## Clipped fine detail needs recovery, not stronger removal

A later enlarged hair check exposed a different failure: a source hair strand was continuous, but the keyed alpha broke its tip into a floating dot. Deleting all small components cannot reconstruct this strand. Compare the exact source frame before classifying it as debris; a lace tip, hair strand or particle may belong to the subject even when the damaged matte makes it detached.

For reviewed neutral/dark fine detail against a green backdrop, `scripts/recover_chroma_detail.py` can reconstruct local alpha and unmix foreground RGB from the original RGB frame. It requires matched source frames, RGBA frames and explicit review masks, plus either measured `--key-rgb R G B` or per-frame `--key-masks`. Optional protection masks preserve accepted lighting and interiors exactly. Example:

```
python scripts/recover_chroma_detail.py --frames rgba-frames --source-frames source-rgb-frames --review-masks reviewed-hair-masks --key-masks known-backdrop-masks --protect-masks protected-interiors --out hair-recovery-candidate
```

This is a bounded green-key color model, not a general matting/semantic model. It assumes neutral/dark detail within the review region; do not apply it to green clothing, broad garment shadows, white trim or an entire character without separate evidence. Sample the actual decoded backdrop: nominal pure green may decode closer to `(5,239,2)`, and using `(0,255,0)` can leave a faint rectangular veil. Limit compression noise with a reviewed opacity floor, preserving real thin strands. Inspect the region boundary, adjacent trim, varied backgrounds and the full motion; a recovered still remains a candidate until its moving contour and export are checked.

## Preserve thin connected structures during antialiasing

A full-library source/original/final comparison found that a 3×3 morphological opening shortened a thin high heel and left a detached-looking endpoint. The original silhouette retained the heel's full length. Global opening is therefore not a safe generic beauty pass: the same problem can affect straps, hair, lace bridges and narrow props.

Use local antialiasing that preserves attached foreground centerlines. Add a regression fixture with a two-pixel-wide attached structure, checking its full length and connectivity, and verify the actual source/current contour at high magnification. Filling a small keying gap is distinct from deleting a spur: only fill when the matching source supports real foreground there. Do not close real holes where the source still shows backdrop. A Gaussian/small-component score alone cannot certify semantic correctness.

If a previous pass damaged structure, rebase from a verified original plus the accepted material repair before trying the replacement; do not stack another smoothing filter onto the damaged output. Version completion markers, make page/journal writes atomic, and require previews/exports to match the replacement version so old successful encodes cannot masquerade as current quality approval.

## Clean chroma, material-aware alpha and coherent geometry

When a clean chroma plate is requested, confirmed background is one specified RGB color, without generated floor shadows, gradients, stains or floating remnants. Preserve the immutable source. Recompose a reviewed repaired RGBA master onto that color for the clean plate; do not globally replace green pixels in clothing or reflective objects. Fully transparent pixels composite to the exact key; antialiased foreground boundaries necessarily mix foreground and key. Exact constant RGB is a lossless-master guarantee, not a guarantee after lossy video compression: inspect the decoded deliverable too.

Assign alpha from coverage and material, not a universal opacity threshold. Opaque skin, opaque cloth and shoes remain opaque; partially covered boundary pixels and genuinely translucent material retain graded alpha. Confirmed empty background is alpha zero. Distinguish a dark fold or cast shadow on the subject from transparency; do not punch holes in shadows or turn lace openings into opaque fabric. Inspect straight versus premultiplied alpha in the actual compositing pipeline to avoid dark/bright halos. RGB under fractional alpha must represent plausible foreground color without key spill. Changing invisible RGB alone does not fix a wrong alpha mask.

Classify edges by component: smooth fabric curves, crisp rigid shoe edges, scalloped lace and fine hair need different contours. Clean does not mean blurred, uniformly rounded, fully opaque or binary alpha. Preserve sharp corners, intentional texture and legitimate negative spaces while removing unmotivated jaggies/debris. Check silhouettes against perspective, foreshortening, cloth attachment, limb anatomy, overlap order and contact with supporting surfaces. Compare adjacent frames: repairs must follow actual motion, not crawl, pulse in opacity, detach or change shape at occlusions. Do not reshape a subject merely to improve a numeric smoothness score.

Record per-clip chroma, alpha/material, contour/geometry and temporal review separately. Encoding tests cannot certify these visual properties. Any unresolved structural or temporal defect keeps the clip in review, even when a single-frame repair looks clean.

## Preserve plausible motion blur

Fast hands, feet, cloth, props and camera movement can produce legitimate blurred contours. Infer whether blur belongs to the motion from the source sequence: direction and extent should follow the visible trajectory and speed, evolve coherently across neighboring frames, and respect occlusion and perspective. Do not demand a crisp frozen silhouette in every frame, classify all soft pixels as debris, or add blur merely to conceal a discontinuity. Honor deliberately stylized blur or sharp motion when requested.

Distinguish exposure-related blur from key spill, disconnected matte fragments, compression ringing, stale-frame trails and interpolation ghosts. Compare the same time through source, RGBA and decoded output. A broad continuous finger sweep in the source that becomes scattered tips after keying needs source-guided alpha recovery, not stronger erosion or isolated-component deletion. Normal-speed playback and enlarged adjacent frames answer different questions; inspect both when available.

Preserve fractional coverage through the blurred boundary and plausible foreground RGB beneath it. Remove green contamination without turning the sweep into opaque skin, erasing its outer extent, changing protected interior lighting or imposing an abrupt mask boundary. Use a region that follows the moving component; a fixed hand ROI from one frame is not a general mask. Recheck entry/exit of the repair region, overlap with clothing/face and loop/transition boundaries for new flicker. Binary GIF alpha cannot fully retain soft motion coverage: keep an RGBA master and verify the actual delivery format rather than claiming identical softness.

## Reject unintended flicker and position jumps

Unless explicitly requested as a style or deliberate action, flashes, disappearing frames, abrupt position/scale jumps and crawling alpha are defects. Check inside each clip, its repeated boundary, and reachable inter-clip transitions. Endpoint overlap alone does not certify continuous velocity, support/contact or plausible motion.

Trace source → repaired frames → layout metadata → decoded delivery → actual player. Share the same pivot, support reference, scale registration and fractional coordinates across exports and runtime; independent rounded placement can create a seam even with identical images. Correct proven reference mismatches with stable clip-level registration, never per-frame silhouette recentering or rescaling that erases intended movement. Re-export when metadata changes, and include layout dependencies in cache fingerprints.

For a buffered player, retain the previous rendered image until the incoming decoder has presented a frame. Arm presentation observation before starting playback; a fulfilled play/load promise or elapsed fixed timeout is not proof of visible pixels. A timeout should preserve the prior image and report/retry the failure, not expose an empty buffer. Review target-player changes separately from source-motion repairs.

## Library acceptance and delivery gate

Maintain one current inventory of requested clips and reachable transition paths, with separate evidence for repaired contours/material alpha, alignment, full-speed motion, loop closure, inter-clip joins and target playback. Record source/output revisions and the actual scope inspected. A middle-frame board, a decoded-frame count, a sampled carousel route or successful unit tests must not mark unexamined motion or paths as accepted. Include user-triggered interruptions, entry/exit and held states when the application supports them; report sampled route coverage separately from exhaustive coverage.

Review support points and apparent body scale in a shared camera coordinate system. Check joint paths, weight transfer, contact, near/far limb identity, occlusion and clothing/prop attachment through each transition, not only matching endpoint silhouettes. Preserve intentional motion, perspective changes and requested effects. Diagnose unexplained flashes, jumps or scale pulses through source, matte, layout and player before changing them; do not hide a broken path with repeated recentering, ghosted crossfades or stronger erosion.

After a repair, revalidate the changed clip and its affected loops/adjacent transitions, rebuild dependent previews and target exports, and verify that the served/installed output is that revision. Keep candidate, repaired, encoding-verified, motion-reviewed and accepted states distinct. Regenerate status reports from current evidence; remove obsolete running-process claims and invalidate acceptance when its dependent pixels, metadata or playback implementation change. An unrepaired visible defect or an unperformed required review remains unfinished.

When the user explicitly says “commit and push after everything passes,” treat that condition as part of delivery. Complete the requested repairs and relevant checks first, inspect the staged diff for unrelated edits, temporary candidates or sensitive source data, then commit and push the authorized deliverables and verify the remote result. Do not commit an incomplete asset batch as finished or claim a code/skill commit delivered repaired runtime assets. Separate local validation, commit, push, packaging and release status; commit/push does not authorize a release. This is a conditional user workflow, not a requirement to use Git or ask for approval in every media task.
