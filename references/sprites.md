# Optional game sprite export

Choose one or more deliverables: GIF, APNG, RGBA PNG frames, Sprite Sheet, or a complete asset pack. A complete pack means frames, sheets, JSON metadata and requested previews; it does not imply an engine importer. Output format and transparency workflow are separate choices. Do not force new generation for a format change.

From the skill root, after `gif_pipeline.py` has produced a delivery directory:

```sh
.venv/bin/python scripts/sprite_export.py output/run/frames \
  --manifest output/run/manifest.json --out output/run-sprites
```

The destination must be new. Defaults: maximum 2048-pixel page dimensions, 2-pixel transparent padding, original frame size, one shared bottom-center pivot. These are export defaults, not automatically a character's foot-contact anchor. Select a reviewed ground/contact pivot when appropriate. `--pivot X Y` is measured in output-frame pixels from the top left, before atlas padding. Every frame shares it.

Optional controls:

- `--max-size 2048`: upper bound on each page dimension; pages are rectangular and not necessarily powers of two.
- `--padding 2`: transparent space around every frame; no edge extrusion is applied.
- `--scale-divisor 3`: nearest-neighbor integer downsampling. Use to undo a known 3× presentation enlargement, not as a universal sprite reduction. Dimensions must divide evenly. Default 1 preserves resolution.
- `--pivot X Y`: fixed pivot, independent of intentional body movement. Default is bottom center of the complete frame canvas.

Outputs: numbered RGBA `frames/`, `sheet-NNN.png` pages and `sprites.json`. Metadata records each frame's page, rectangle `[x,y,width,height]`, duration in milliseconds, source index, original/output canvas sizes, padding and pivot. Frames are never individually cropped or recentered. Straight alpha is retained. The exporter decodes every page and verifies each crop equals the corresponding frame, including fractional alpha and RGB under transparent pixels.

Use the JSON durations rather than assuming uniform FPS. This is a documented repo-specific JSON schema, not a claim of native Unity/Godot/Aseprite metadata compatibility. Import rectangles and durations with the target engine's tools or implement an explicit adapter. Use nearest filtering and usually disable mipmaps for crisp pixel art; configure alpha blending for soft effects. Bilinear/mipmap use needs appropriate extrusion/sampling validation beyond the bundled transparent padding.

Visual displacement stays in the images. Avoid applying the same travel again through gameplay movement; separating root motion requires reviewed tracking. Events, hitboxes, collision timing and root-motion tracks are not inferred. Effects remain composited with the character unless independently supplied. Validate in the target engine before declaring a game-ready integration.

See [the running-dash example](../examples/chibi-running-dash/README.md) for an actual 256×256 sprite export from a 3× presentation animation.
