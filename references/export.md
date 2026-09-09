# Export interface

Choose preservation/repair mode and delivery format using [transparency.md](transparency.md). The CLI exports selected RGBA frames, GIF and optional APNG; it does not redraw frames, run temporal matting, create engine resources. The separate [sprite exporter](sprites.md) packs sheets with timing and pivot metadata. Preserve fractional alpha upstream; the GIF encoder's binary cutoff does not apply to saved RGBA/APNG frames.

From the skill root (replace paths with actual input and a new output directory):

```sh
python3 scripts/gif_pipeline.py ./source.mp4 --out ./run-01 --key FF00FF --width 640 --apng
python3 scripts/gif_pipeline.py ./rgba-frames --fps 24 --out ./run-02 --phases ./timing.json
```

The first route keys a flat chroma background; omit `--key` for opaque video or existing alpha PNGs. The OpenCV video decoder does not preserve video alpha. For alpha video, extract RGBA PNGs with a suitable decoder first. Directory inputs must contain only the desired numbered frames. The keyer uses chromatic distance, default tolerance 0.15 and softness 0.12; these are starting points, not a validated matte for every image. If subject colors overlap the key, use better source separation or segmentation. It does not automatically despill RGB fringes.

Use ffprobe to inspect stream rates and timestamps. The helper assumes constant frame rate. For variable-rate video, explicitly conform once and record that derivative, e.g. `ffmpeg -i input.mp4 -map 0:v:0 -an -vf fps=24 -c:v ffv1 source-cfr.mkv`. Choose a rate appropriate to the source; 24 is an example. Do not relabel video FPS to fake a timing fix.

`timing.json` is a sorted, nonoverlapping array in **source seconds**:

```json
[
  {"start": 0.5, "end": 2.8, "speed": 1.35, "ramp": 0.3},
  {"start": 6.0, "end": 8.2, "speed": 1.35, "ramp": 0.3}
]
```

`speed=1` means native timing; `1.35` is faster, `0.8` slower. A raised-cosine ramp eases rate changes. Frames may be temporally sampled to keep GIF durations at least 20ms. Timings are rounded cumulatively to GIF's 10ms units, preventing cumulative drift. Intervals outside phases remain 1×. This is temporal resampling, not synthesis of missing motion.

Outputs: `animation.gif`, optional `animation.png` (APNG), numbered RGBA `frames/`, dark/light `contact.png`, and `manifest.json` with input/output hashes, source-index mapping, durations, key settings and decoded QC. Identical adjacent GIF frames may be coalesced by the encoder; verification checks their timeline coverage rather than requiring artificial duplicates.

Use at modest delivery resolutions first: all RGBA frames remain in memory. Long/high-resolution video should be cut to the intended asset or processed with a streaming implementation; this helper is for short animations. Keep the full-resolution source separately. PNG frame hashes are retained in the manifest, but full input paths can be private; redact portable share copies when needed.

A technically passed export still needs visual checks for alpha correctness, quantization banding, source flicker, edge contamination and motion. GIF has binary transparency and at most 256 palette entries. APNG preserves full-color and soft alpha but may be large or unsupported by a target app. Preserve the original source when testing app-specific playback.

Default framing includes the full character, weapon and complete VFX lifetime. If cropping is needed, derive one common crop from the union of all reviewed foreground/effect extents with margin, not separate per-frame boxes; keep detached particles and late decay. Do not trim the timeline while effects are still disappearing merely to meet a preferred duration. Inspect original and decoded frames for spatial clipping and incomplete decay; see [motion.md](motion.md). A larger output canvas cannot recover content already missing from the generated source.

## Pixel-style video export

For a user-selected video route with pixel-style artwork:

```sh
python3 scripts/gif_pipeline.py ./source.mp4 --out ./pixel-run --key FF00FF \
  --pixel-width 160 --pixel-scale 3 --phases ./timing.json --apng
```

`--pixel-width` overrides `--width`, downsamples only when the input is wider, and preserves aspect ratio. Keying happens on that raster; `--pixel-scale` then enlarges both dimensions by an integer using nearest-neighbor sampling. The manifest records the actual raster size. The example is 160 pixels wide enlarged 3×, not a mandatory size or a claim of hand-authored native pixel art. Video generation can still introduce drifting pixel clusters; inspect the final animation. Do not force nonsquare video into a square or normalize every pose's bounding box. Impact holds use the existing phase interface described in [motion.md](motion.md).

## Matting and spill boundaries

Preserve the user-selected foreground objects as well as the person. Person-only segmentation can remove a requested table, cup or chair, and independent masks can flicker across frames. Inspect interior gaps and fine edges over multiple backgrounds. Prefer separable generation backgrounds when available; complex scenes need temporal matting or reviewed masks.

The bundled keyer does not repair spill. Do not promote a single production's fixed magenta threshold or nearest-color replacement into universal skin/hair cleanup: it may erase intended subject or effect colors. A task-specific cleanup must be explicitly limited to contaminated edges, preserve clean interiors and alpha topology, retain original RGB/masks, and be reviewed across time. Record that cleanup separately from generated effects. Do not copy private production assets into repository examples without user authorization.

## Optional video containers

GIF remains the default. For requested MOV/WebM output from the same RGBA frames and timing, use [video-export.md](video-export.md). The separate video exporter preserves the pipeline's 10ms timing through repeated frames, verifies decoded alpha and does not generate new motion.
