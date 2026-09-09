# Transparency and delivery choices

Select sensible defaults from the intended use; do not ask users to choose technical clipping/blending settings without context. When engine-specific assets matter and the target cannot be inferred, ask for the engine/platform while preparing generic RGBA frames. Keep an explicit requested format even when also providing a higher-fidelity master.

## User-selectable workflow modes

| Mode | Behavior | Boundary |
| --- | --- | --- |
| Auto (default) | Preserve source frames. Use existing alpha, a separable color key, or suitable temporal matting for a complex background. | Matting must be available and validated; the bundled keyer handles uniform backgrounds; optional local `background_remove.py` offers rembg framewise masks, not a temporal model. Do not silently substitute redraw when extraction fails. |
| Preserve artwork | Do not redraw the subject or invent replacement detail. Keep original RGB except disclosed, narrowly scoped spill correction; adjust alpha from the source. | Report unseparable areas and missing details rather than promising perfect extraction. |
| AI repair/redraw | Use available image tools for the user-requested local repair or redraw, preferably limited to the affected area. | Explain potential changes to identity, anatomy, weapon paths and particle placement before switching from preservation when the user has not already selected repair. Recheck every affected transition. |

These are direction modes, not `gif_pipeline.py` switches. Existing authorization for repair applies; do not ask again. Image generation is generally more useful for a clean starting character than for indiscriminately regenerating the entire final animation. A request to remove only the background is not proof that a model preserves every other pixel.

Do not require or claim GPT-Image-2.5 when the active tool does not expose that model. Verify the actual image model/version and whether returned pixels contain real alpha; never infer transparency from a checkerboard appearance. Preserve provenance and report an unexposed version as unknown. No model name guarantees animation consistency or correct transparency.

For pixel-art requests, apply [pixel-native handling and repair](pixel-art.md) by default.

## Matte quality

Prefer genuine source alpha when available. For opaque generated video, choose a constant backdrop distinguishable from both the character and the intended effects. Avoid blanket thresholds that remove matching costume or particle colors. Complex scenes need temporal segmentation/matting, not a uniform color key applied as if it were segmentation.

Estimate graded alpha and handle background-color spill separately. Do not binary-threshold RGBA masters merely because the subject is pixel art. Hard-edged pixel silhouettes may intentionally use binary alpha; luminous effects, smoke and disappearing particles may require fractional alpha even on a discrete pixel grid. Choose edge treatment by content and style. Inspect hair, metal, interior gaps, particles and temporal stability on black, white and a representative target background.

A single opaque composite generally does not uniquely determine foreground RGB and alpha, especially for glow mixed with a colored backdrop. Changing containers or asking an image model to redraw cannot guarantee recovery of lost information. Plan independent character/effect sources when an editable layered game asset is needed. Do not claim reliable separation of character and effects from an already-composited Grok video. Cleanup is not permission to invent or overlay new effects; retain the skill's default Grok effect provenance.

## Output by use

- **Soft-alpha animation:** preserve full-color RGBA PNG frames and export APNG (`--apng`). The target player must support it. APNG preserves existing fractional alpha; it cannot restore alpha already discarded upstream.
- **GIF requested / compatibility sharing:** supply GIF plus an RGBA/APNG master where useful. GIF transparency is binary. The current encoder maps alpha below 128 to transparent and the rest to opaque; this conversion belongs only to the GIF derivative. Do not promise alpha blending in GIF.
- **Game assets:** prefer RGBA PNG frames and, when actually produced, an engine-compatible sprite sheet/atlas with timing and placement metadata. A sprite is not a file format and a sprite sheet does not itself improve a bad matte. GIF/APNG are previews, not substitutes for the requested engine integration.

The bundled tools write RGBA PNG frames, GIF, optional APNG, transparent ProRes MOV / VP9 WebM via [video_export.py](video-export.md), and optional multi-page sprite sheets with timing/placement JSON. See [sprite export](sprites.md). Engine importers, independent VFX-layer extraction and temporal matting are not bundled. Game events, collision data and root-motion tracks require separate implementation and verification. Animated WebP is not a bundled output option.

For game delivery, establish frame sizes, a stable pivot, crop offsets/padding, per-frame durations, action phases/events and how gameplay handles displacement. Preserve visual travel unless the agreed contract separates root motion into a movement track; never remove it by naive per-frame centering. Avoid double movement from both the sprite and gameplay transform. Choose straight versus premultiplied alpha to match the target material/importer, documenting the convention; neither is universally superior. Pixel-nearest filtering and soft alpha are independent choices. Additive/emissive VFX may need a separate layer/material and are not the same as ordinary alpha blending. Validate borders, atlas sampling and representative backgrounds in the target engine before calling the asset game-ready.
