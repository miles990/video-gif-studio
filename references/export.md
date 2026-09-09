# Export interface

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
