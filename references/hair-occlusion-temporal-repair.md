# Fine hair, occlusion and temporal repair

Use for crawling hair edges, disconnected strands, popping at hair/garment contact, or noise introduced by keying. This is a diagnosis and acceptance standard, not a universal keyer preset.

## Establish where the defect enters

Compare matched source indices through unkeyed source, current RGBA and decoded delivery. Use a single synchronized A/B movie at original cadence, plus frame stepping. Composite the RGBA back onto the measured source backdrop, and also inspect dark, light and saturated backgrounds. Recomposition similarity alone is insufficient: an opaque copy of the green plate can match perfectly yet fail transparency.

Separate three failures: source hair changes topology or motion implausibly; matting clips an otherwise continuous strand; recovered straight RGB or fractional alpha fluctuates despite stable source detail. A still cannot establish motion. Compare the same strand across neighboring frames, at contact/occlusion events and across the loop seam. Do not claim the source is defective solely because a keyed preview flickers.

## Respect front-to-back structure

A partial hair pixel over opaque clothing does not imply a partial final character pixel. Coverage combines as `A = A_hair + (1 - A_hair) * A_back`; if `A_back = 1`, combined alpha is 1. Preserve the backing garment color, texture and contact shadow. Keep true gaps transparent. RGB alone may not establish whether green between hair and clothing is a real opening or missing generated garment: do not invent a backing layer by filling every gap or infer opacity from green/non-green thresholds alone. Reconstruct missing content only with reviewed structural/source evidence; alpha cannot restore erased texture.

## Local reconstruction without new popping

Start each replacement from a provenance-verified baseline and source, not a chain of rejected candidates. Keep accepted unrelated repairs. Use reviewed per-frame component scopes and protect face, opaque garment interiors, true gaps and intentional blur.

Avoid binary switches between unrelated treatments as RGB, alpha or distance crosses a threshold during motion. Prefer continuous confidence/coverage within the authorized repair band, while retaining exact protected pixels. Donor colors must come from the same material: adjacent white lace, skin and black hair are not interchangeable. Nearest-pixel substitution across material boundaries can make dark notches or flatten cloth shading.

Unmix color and alpha together. Dividing RGB by nearly zero alpha amplifies plate compression noise; clipping the recovered RGB may destroy reconstruction even when alpha appears smooth. Check straight/premultiplied conventions and composite before judging. A gamut feasibility constraint or a noise floor is not automatically correct: tiny background-channel differences can force erroneous opacity, and hard opacity floors can disconnect thin strands. Validate the result on all backgrounds rather than optimizing one metric.

Use motion-compensated temporal treatment only after segmentation is defensible. Reject unreliable flow and new occlusions with forward/backward consistency and source similarity checks. Never blend unrelated positions merely to reduce a flicker score. Source-backed coherent hair motion, protected backing layers and negative spaces take precedence over temporal smoothness.

## Acceptance and reuse

Record source/page/algorithm hashes, frame mapping, reviewed scopes, changed pixels, protected-pixel invariants and rejected candidates. Inspect the complete sequence, not just best stills. Numeric reconstruction error, lossless encoding, contact sheets and perceptual playback acceptance are separate evidence.

For a library, inventory and classify each clip; determine hair/material/occlusion scopes separately. Do not copy one pose's ROI, brightness threshold, donor radius or mask into unrelated poses. A local improvement does not approve all clips or authorize deployment. Keep unresolved source-content gaps, loop transitions and target-player checks visible in the progress ledger.

Observed case: source-based local hair color donors and continuous confidence reduced contour debris compared with stacked thresholded repairs. One candidate still mistook a gray collar shadow for mixed hair: a source pixel `[132,147,132]` whose current alpha was 255 became alpha 219. Reject that cross-material regression even if the outer hair improves. In the subsequently user-accepted 124-frame local repair, a continuous protection ramp reduced the treatment near opaque pixels and all existing fully opaque pixels remained byte-identical. This conservative protection does not establish that every opaque pixel in an arbitrary input is valid; separately diagnosed opaque fringe defects need their own reviewed repair scope. User acceptance applies to the inspected sequence, not a universal mask, threshold or library-wide recipe.
