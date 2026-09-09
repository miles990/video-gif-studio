# Optional MOV, WebM and MP4 output

GIF is the default when no output format is specified. Users may instead choose MOV, WebM, MP4 or multiple formats; retain RGBA master frames. For long-video tasks prefer a video container and optionally a short GIF preview. Export changes do not require AI generation.

```sh
.venv/bin/python scripts/video_export.py output/run/frames \
  --manifest output/run/manifest.json --out output/run/animation.mov
.venv/bin/python scripts/video_export.py output/run/frames \
  --manifest output/run/manifest.json --out output/run/animation.webm
```

Use the selected frames and matching timing manifest produced by `gif_pipeline.py`. The output must not exist. Requires FFmpeg/ffprobe with `prores_ks` for MOV, `libvpx-vp9` for WebM or `libx264` for MP4. Scripts are independent: selecting video does not make the GIF pipeline stop exporting its default GIF derivative.

| Container | Encoding | Intended use |
| --- | --- | --- |
| MOV | ProRes 4444 with alpha | Editing/interchange; potentially large files. |
| MP4 | H.264, opaque | Broad compatibility; no transparency. |
| WebM | VP9 with alpha | Web/game delivery where the actual player supports alpha; smaller-file suitability depends on content. |

These extensions do not themselves guarantee transparency. For MOV/WebM the exporter encodes RGBA through the specified alpha-capable codecs and decodes every frame to validate alpha (maximum allowed error 2/255). VP9 verification explicitly uses libvpx because another VP9 decoder may ignore alpha. Validate the actual browser, editor or engine before promising compatibility. RGB can change through YUV conversion, including WebM 4:2:0 chroma subsampling; “lossless VP9” does not mean original RGBA pixels remain identical. Prefer PNG/APNG sprites for exact pixel-art RGB.

Input durations must be positive multiples of 10ms. The exporter repeats existing images at 100 fps to represent the timeline exactly without motion interpolation. This is a timeline-preservation choice, not 100 unique motion frames per second. It may increase encoding cost/file size; a different delivery rate requires explicit timing resampling and verification. WebM and MP4 require even dimensions; do not silently stretch odd-size artwork. Prepare one shared padded canvas when needed.

Writes the movie and a `.mov.json` or `.webm.json` QC record with dimensions, decoded frame count, timing and alpha error. Output is silent and contains one animation cycle; repetition is controlled by the player. Audio preservation, arbitrary video joining, engine import and an automatic long-video chain runner are not bundled. Failed verification does not publish a completed video. For long sequences keep frames on disk; this exporter streams them rather than retaining all frames in memory, although the preceding GIF pipeline still has its own memory limits.

## MP4 is opaque

This skill's MP4/H.264 output **does not preserve transparency**. Transparent pixels are composited onto black by default; choose a six-digit RGB matte color when needed. This is a property of the selected export workflow, not a claim about every codec that could theoretically be placed in an MP4 container.

```sh
.venv/bin/python scripts/video_export.py output/run/frames \
  --manifest output/run/manifest.json --out output/run/animation.mp4 \
  --background FFFFFF
```

The report records `transparent: false` and the background color. Alpha QC checks that the decoded MP4 is fully opaque rather than comparing against the original transparency. Keep PNG/APNG masters for subsequent transparent reuse.
