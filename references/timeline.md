# Local animation and still-image timeline

Use `scripts/compose_timeline.py` to concatenate prepared animation frames and timed still images without another Grok call. A still can be an explicit image, the previous segment's last frame, or the first/last frame of a prepared animation. It freezes every pixel, including particles, light trails, hair and smoke. Breathing, blinking, idle movement or effects that keep dissipating require an actual animation segment, not a still.

Create a JSON plan; relative paths resolve against the plan's directory:

```json
{
  "segments": [
    {"type": "animation", "manifest": "attack/manifest.json"},
    {"type": "still", "previous": "last", "duration_ms": 2000},
    {"type": "still", "manifest": "next/manifest.json", "frame": "first", "duration_ms": 500},
    {"type": "animation", "manifest": "next/manifest.json"},
    {"type": "still", "image": "closing.png", "duration_ms": 1500}
  ]
}
```

Animation manifests must have a sibling `frames/` directory and matching `durations_ms`, as exported by this repo. Stills require exactly one selector (`image`, `manifest`, or `previous`). Manifest selectors accept `frame: first` or `last` (default last). `previous: last` requires an earlier segment. A hold adds the specified time after any existing duration of the selected frame; it does not replace it. Specify durations in milliseconds (2000 = 2 seconds), positive multiples of 10 from 20 through 655350 per frame. Split longer holds deliberately.

```sh
.venv/bin/python scripts/compose_timeline.py timeline.json --out output/composed
.venv/bin/python scripts/compose_timeline.py timeline.json --out output/composed-video \
  --formats apng mov webm mp4 --background 000000
```

GIF is the default. `--formats` accepts one or more of `gif apng png sprite mov webm mp4`. RGBA `frames/`, a timing/segment manifest and QC record are always retained; `png` means only those masters when selected alone. Optional sprite pages use the sprite export defaults; run `sprite_export.py` separately for a custom pivot/page layout. APNG includes a default poster so a single still remains a timed animation; the poster is not part of the playback duration. MOV/WebM preserve alpha through their documented encoders; MP4 is opaque and uses the selected background (default black).

All inputs must use one canvas size. The tool rejects mismatched sizes instead of stretching, recentering, cropping or pixelating them implicitly. Prepare a shared canvas and consistent scale deliberately. It does not remove backgrounds from opaque stills. It retains alpha, image order and timing without transition blends, motion interpolation or audio. Outputs are staged before the new delivery directory is published; existing directories are never overwritten. Source paths in the manifest may be private; make portable copies before sharing.

Review every join, particularly transitions between frozen and moving frames. Use a rested pose for a natural pause when appropriate; freezing a running pose mid-stride is an intentional freeze-frame, not natural idle. Removing duplicated boundary frames must not erase intended hold time. This helper composes prepared local assets; automatic Grok segment generation, video editing/extension and chain orchestration remain separate. Convert video segments to prepared frames first. It currently retains all images in memory, so use it for bounded timelines and use a streaming editing pipeline for long/high-resolution productions.
