# NEON ZEN — Flow into Stillness

**English** | [繁體中文](README.zh-TW.md)

A 30-second music-PV experiment: an original silver robotic koi travels from a neon rain alley into a reflecting courtyard, skims the water and settles. Five sequential Grok generations are joined using each actual decoded endpoint plus a fixed identity image. The user's **Neon Zen** soundtrack stays at its original speed.

![Silent excerpt preview](preview.gif)

[Watch/download the 30-second MP4 with music](final.mp4) · [Identity image](identity.png) · [Editable timeline](timeline.json) · [Beat/event map](beatmap.json) · [Join comparison](joins.jpg)

## Direction and timing

| Output time | Actual visual sequence |
| --- | --- |
| 0–5.55 s | Koi starts gliding and turns from the alley into the courtyard. |
| 5.55–11.73 s | It circles toward the camera, revealing its flank. |
| 11.73–17.60 s | A lateral glide carries it along the reflecting pool. |
| 17.60–24.20 s | It lowers its fins; small ripples spread across the water. |
| 24.20–30.00 s | The camera opens to a wider courtyard and the movement settles. |

The song excerpt is **19.96–49.96 seconds** of the supplied track. Automatic RMS-onset analysis returned an approximately **82 BPM** candidate, with half/double-tempo ambiguity. Editorial boundaries use selected measured onsets, not an assumed fixed beat grid. The requested 30-second endpoint is not labeled a detected beat.

Two inspected visual events test phase-specific timing: shot 1 frame 84 (the readable bank) is placed at **3.50 s**; shot 4 frame 80 (a clearly spreading ripple) is placed at **21.27 s**. The timeline splits the sources at those frames and time-fits each phase, preserving continuous source frames without optical flow, crossfades or redraws. The soundtrack is never time-stretched. These are editorial event choices, not proof of musically correct downbeats.

## Generation and provenance

No user image reference was used. Codex's available image-generation tool created [the initial image](identity.png) from [this prompt](image-prompt.txt); its model version was not exposed. Grok `grok-imagine-video-1.5` generated the five 1280×720, 24-fps sources, each containing 145 frames (about 6.04 seconds decoded). All in-scene motion, wake, droplets and ripples came from Grok.

Each `segment-01` through `segment-05` directory preserves `prompt.txt`, `start.png`, `last.png`, `references.json`, `inspection.json`, `contact.jpg` and `generation/{job.json,source.mp4}`. The generation endpoint was `/videos/generations` with `image` plus `reference_images`; it was **not** a video-extension call. A small example-specific adapter used the repo's client and ledger; it is not a newly bundled general chain runner. Published helper paths are portable adaptations of the production scripts; recorded production adapter hashes refer to the original local script.

The final MP4 is opaque, 960×540, with audio. Its 100-fps encoding timebase represents 10-ms frame exposures by repeats; it does not contain 100 unique generated frames per second. The short GIF is a silent excerpt and is not designed as a seamless loop.

Music was supplied by the user with permission to include it in this example. Embedded track metadata credits **wizardx07** and identifies the title as **Neon Zen**, made with Suno. Only the selected 30-second excerpt is included as `soundtrack.flac`; see [music provenance](music-provenance.json). The repository's MIT code license does not itself grant additional rights to the music.

## Reproduce the local edit

From the repository root, after installation:

```sh
for n in 1 2 3 4 5; do
  .venv/bin/python examples/neon-zen-pv/prepare_segment.py "$n"
done
.venv/bin/python scripts/compose_timeline.py examples/neon-zen-pv/timeline.json \
  --out output/neon-zen-rebuild --formats mp4
```

Prepared frame directories are deliberately omitted from Git and regenerated from the included videos. Run into fresh output directories; the exporters refuse to overwrite existing deliveries. Editing `beatmap.json` / `timeline.json` needs no Grok generation. Generating new segments with `generate_segment.py` does spend provider quota and will not reproduce identical pixels.

## Verification and remaining review

[Delivery QC](delivery-qc.json), [frame/timing manifest](delivery-manifest.json), [chain QC](chain-qc.json) and [event QC](event-qc.json) record the checks. Each supplied continuation image exactly matches the preceding extracted last frame; decoded first-frame RGB error across joins is approximately 3.0–3.8/255 after provider encoding. Source contact sheets and all four endpoint pairs were visually inspected; audio/video duration and event-frame positions are checked from decoded output.

Full-speed listening/playback aesthetic review is **not certified**. Onset detection cannot prove musical phrasing, and matching endpoint images cannot establish velocity continuity. Some middle-shot tail framing is tight, and small generated scale/fin detail changes remain. Treat this as a working chained-video and beat-editing example, not a claim of flawless identity or cadence.
