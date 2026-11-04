# Freeze / cutout / beat

Final candidates: [demo.mp4](demo.mp4) and [demo-b.mp4](demo-b.mp4), with continuous music.
Silent 480px previews: [demo.gif](demo.gif) and [demo-b.gif](demo-b.gif).
[preview.png](preview.png) shows all six effects and all four transitions at three phases.

From the worktree root, reproduce the primary film in a **new** output directory:

```powershell
& C:/Users/User/.codex/skills/video-gif-studio/.venv/Scripts/python.exe scripts/fx_render.py wow/fx/demo/plan.json --out wow/fx/demo/reproduced-a --formats png gif mp4 --no-user-fx
```

Use plan-b.json and a different --out for the second material. The 17-line plans differ
only in material paths: neon clip manifest, character manifest and background plate image.
All timings, effects, numeric parameters, beatmap and music are identical. Prepared
sources are already retained under work/. `prepare_demo.py` recreates character canvases
from repository RGBA exports; neon sources were prepared with gif_pipeline.py, e.g.:

```powershell
& C:/Users/User/.codex/skills/video-gif-studio/.venv/Scripts/python.exe scripts/gif_pipeline.py examples/neon-zen-pv/segment-01/generation/source.mp4 --out wow/fx/demo/work/neon-a-new --width 640
```

The final full-resolution deliveries are **master-a/** and **master-b/**: RGBA frames,
manifest.json (including resolved effects/provenance and timings), qc.json, GIF and MP4.
Root demo.mp4/demo-b.mp4 are copies of those final MP4s. `inspect_demo.py` creates the
smaller GIF previews, decoded beat measurements and detailed inspection sheets.
Older candidates are preserved under work/archive-*; they are not the delivered version.

## Measured delivery

| Metric | A: chibi + neon segment 01 | B: robot + neon segment 03 |
|---|---:|---:|
| Duration | 8.780 s | 8.780 s |
| Canvas | 640×360 | 640×360 |
| Master exposures | 223 | 223 |
| Nominal render rate | 25 fps plus exact 10ms event boundaries | same |
| Exported video | 100 fps repeated frames, H.264 + AAC | same |
| Full render/export wall time | 44.515 s | 45.021 s |
| Pixel render wall time | 23.395 s | 24.004 s |
| Pixel render speed | 9.53 fps | 9.29 fps |
| 480px GIF preview | 14,632,718 bytes | 13,444,870 bytes |
| GIF alpha mismatch | 0 pixels | 0 pixels |

Wall timings exclude source preparation and the separate smaller-GIF preview export.
See wall-times.json and timings.json for machine-readable evidence. Video output keeps
the existing 10ms exporter clock, rather than generating interpolated physical motion.

Flash peaks in the decoded MP4:

| Material | Music trigger after in_ms | Measured peak | Error | Luminance rise vs 3 encoded frames before |
|---|---:|---:|---:|---:|
| A | 2926.829 ms | 2930 ms | +3.171 ms | 120.51 |
| A | 5853.659 ms | 5860 ms | +6.341 ms | 173.59 |
| B | 2926.829 ms | 2930 ms | +3.171 ms | 97.92 |
| B | 5853.659 ms | 5860 ms | +6.341 ms | 173.40 |

All four meet ±1 encoded frame (10ms) and rise ≥40. Transition midpoints are exactly
2930 and 5850ms. The still is 2930–4390ms; the next character segment resumes motion.
Audio is the original neon soundtrack, in_ms=20, with 100ms fade-in and 500ms fade-out.

## QA and visual inspection

[Primary QA](qa/report.md) and [second-material QA](qa-b/report.md) are **PASS** on the
final decoded MP4s: frame 0, flashes, pops, freeze, cuts, timeline joins, loudness, true
peak and silence. Command:

```powershell
& C:/Users/User/.codex/skills/video-gif-studio/.venv/Scripts/python.exe scripts/qa_media.py wow/fx/demo/demo.mp4 --out wow/fx/demo/qa-reproduced --timeline wow/fx/demo/master-a/manifest.json --holds 2.93-4.39
```

**Strict acceptance gap:** the requested `--expect-cuts 2.93,4.39,5.85` command fails
the existing QA hard-cut detector, because these are a flash transition, a continuous
still-to-motion join and a whip transition. The failed probe is retained in
work/archive-qa-initial/report.md. The passing reports above use the existing documented
editorial-join semantics, not that strict hard-cut invocation. This difference is not
claimed as satisfying the unchanged acceptance line; S-展示 remains a candidate.

The builder inspected [A](inspection-final-a.jpg), [B](inspection-final-b.jpg), the QA
contact sheets and preview.png, including each transition's neighboring frames. The
first version applied borders after whip blur, creating thick white streak silhouettes;
source-stage processing fixed that. Reflected edges initially duplicated the subject;
edge replication removed the duplicate. Final cards retain continuous white contours,
consistent down/right shadows, and readable subjects on a dark blurred plate. A's pink
particle is present in the original RGBA animation, not a newly invented effect.
No real-time audiovisual playback/listening or independent aesthetic sign-off occurred
in this builder session; numeric checks and frame inspection are the evidence available.

## Sources

- examples/chibi-running-dash/final.apng: original RGBA animation, frames 18–47.
- examples/robot-wave-no-reference/final.gif: original transparent animation, frames 25–54.
- examples/neon-zen-pv/segment-01/generation/source.mp4 and segment-03/generation/source.mp4.
- examples/neon-zen-pv/music-analysis/beats.json and soundtrack.flac.

All are existing repository works. Preparation used fixed union crops and a shared
640×360 canvas; no per-frame recentering or new character movement. examples/ was not
modified. Optional Beat This! and BiRefNet were not installed or live-run here.
