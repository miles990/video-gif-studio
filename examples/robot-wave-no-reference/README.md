# Example: Original Robot Wave Without a Reference Image

**English** | [繁體中文](README.zh-TW.md)

![Original robot waving on a transparent background](final.gif)

An original robot greeting, created with **zero user-provided reference images**. The result is a 6.04-second transparent GIF at 512×512, with 145 frames.

## Production

1. Codex authored the character and motion brief. The built-in image generator created [character.png](character.png) from [image-prompt.txt](image-prompt.txt), without input images. The tool did not expose its exact model version, so this example does not label it GPT-Image-2.5.
2. The generated character image became the single starting image for Grok. "No reference" means no external/user-provided visual reference; this is an original-image-to-video workflow, not a claim of direct text-to-video.
3. The repo's bundled `grok_client.py` submitted [motion-prompt.txt](motion-prompt.txt) to `grok-imagine-video-1.5`, resumed the job and downloaded [source.mp4](source.mp4). This is a real generation through the internal client, with no external project adapter.
4. The export tool removed the magenta screen, preserved source timing, and encoded the GIF with a dedicated transparency index and one global palette. No optical-flow interpolation, independent pose regeneration or reversed playback was used.

## Verification

All 145 decoded GIF masks match the thresholded source RGBA masks: **zero additional transparent holes**. The [contact sheet](contact.png) was inspected on light and dark backgrounds for appearance and transition frames. A complete normal-speed playback review was not recorded. The ending orientation differs slightly from the start, so this is not certified as a seamless loop.

[Download GIF](final.gif) · [Generated character](character.png) · [Source video](source.mp4) · [Image prompt](image-prompt.txt) · [Motion prompt](motion-prompt.txt) · [Export/QC](export.json) · [Provenance](manifest.json)

## Reproduce the Export

From the repository root, using a new output directory:

```sh
.venv/bin/python scripts/gif_pipeline.py examples/robot-wave-no-reference/source.mp4 \
  --key FF00FF --tolerance .32 --softness .24 --width 512 \
  --out output/robot-wave --apng
```

The key settings were selected for this robot and background; they are not universal defaults. New AI generations can vary even when prompts are reused.
