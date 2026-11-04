# Video delivery

Use MP4/MOV/WebM for long timelines. `fx_render.py` and `compose_timeline.py` send
each rendered RGBA frame directly to an FFmpeg pipe. Only a three-image source
cache, one optical-flow pair and each effect's declared history remain resident.
Frame timing/provenance records grow with duration; decoded image buffers do not.
No intermediate PNG film is written for video-only output. A failed render kills
and waits for FFmpeg, removes its partial movie and never publishes the output directory.

```sh
python scripts/fx_render.py plan.json --out run --formats mp4 --platform tiktok
python scripts/compose_timeline.py plan.json --out preview --formats mp4 --proxy
python scripts/video_export.py frames --manifest manifest.json --out movie.mp4 --fps 30
```

Outputs must be new. Resolve FFmpeg/ffprobe from PATH, the managed runtime, or
`VIDEO_GIF_FFMPEG` / `VIDEO_GIF_FFPROBE` (full executable paths). No render downloads
dependencies. Tests use local synthetic media and no inference models.

## Timing and transparency

Video defaults to **CFR 30 fps**, selectable **24, 25, 30, 50, 60**. Explicit
`--fps 100` selects the legacy 10 ms exposure/repeated-frame route. Fractional
rates including 29.97 are currently rejected. Platform presets reject 100 fps.
The plan's existing `fps` remains the legacy raster sampling rate (default 25,
range 1–50); the CLI video rate controls the delivered video grid independently.

Events and cuts round to the nearest video frame, with exact half ties toward the
later frame. `manifest.json` records `requested_ms`, `frame`, `quantized_ms`,
`error_ms` for effects (`events`) and segment boundaries (`cuts`). Error is at most
half a frame; total duration rounds to the same grid. Same-frame events run together
in effect order; beat envelopes take their maximum. `--validate` warns about beat
collisions. Prepared-frame exports record source exposure boundaries in the movie
sidecar. Sampling holds existing images; it does not invent motion.

| Output | Without a platform | With a platform |
| --- | --- | --- |
| MP4 | H.264, opaque, CRF 18 | H.264 CBR preset, opaque |
| MOV | ProRes 4444, alpha | H.264 CBR preset, opaque |
| WebM | lossless VP9, alpha | VP9 opaque (MP4 is the platform delivery container) |

Modern exports perform RGB-full → BT.709-limited matrix conversion and tag
primaries/transfer/matrix BT.709, range `tv`. RGBA artwork is treated as display
RGB in BT.709 primaries; this is not an ICC-managed conversion. Use intake for
PQ/BT.2020 footage. MP4 and all platform exports composite straight alpha onto
**black**, or `--background FFFFFF` (six hex RGB digits). MP4 cannot retain alpha.
Do not premultiply PNG RGB before supplying it. MOV/WebM without a platform retain
alpha; check the actual player. Explicit legacy 100 fps preserves the previous
RGB→YUV conversion for decoded-frame compatibility instead of relabeling its colors.

Standalone legacy export verifies every decoded alpha frame within 2/255. Modern
streaming alpha is covered by offline decode tests; it does not retain a second
whole-film reference for per-frame alpha comparison. YUV chroma subsampling can
change RGB even with lossless VP9; use PNG/APNG for exact artwork pixels.

## Platform presets

These are project delivery choices, defined in `scripts/delivery.py` from
[S-52 requirements](../wow/fx/acceptance-5.md), checked 2026-11-05. They do not
claim to enumerate a platform's changing upload limits. `--fps` explicitly
overrides the default 30 for all five presets (24/25/30/50/60).

| Preset | Dimensions | Video bitrate | Safe margins L / T / R / B |
| --- | --- | --- | --- |
| tiktok | 1080×1920 | 10 Mbps | 5% / 10% / 10% / 20% |
| reels | 1080×1920 | 10 Mbps | 5% / 10% / 10% / 20% |
| shorts | 1080×1920 | 10 Mbps | 5% / 10% / 10% / 20% |
| youtube | 1920×1080 | 10 Mbps | 5% / 5% / 5% / 5% |
| square | 1080×1080 | 8 Mbps | 5% / 10% / 5% / 10% |

MP4 presets use yuv420p, H.264 CBR filler and faststart; audio, when supplied, is
AAC stereo 48 kHz / 256 kbps. Very short clips have bitrate startup overhead.
Source aspect ratio is fitted with transparent padding, then composited on the
chosen matte; this does not automatically track/crop a subject. `delivery.safe_zone`
contains pixel `x`, `y`, `right`, `bottom` and `text_inset_px` (another 2% of width).
Later caption layout must keep glyphs inside that inset rectangle; P0 does not
reposition existing free-form `text` effects or implement captions.

## Audio and phone intake

See [music](music.md#delivery-audio) for source retention, sidechain ducking,
two-pass loudness and the delivery gate. Source audio is opt-in. Supply a continuous,
timeline-aligned `source_audio` file; automatic audio reconstruction from edited
PNG manifests is not possible. Silent exports omit audio entirely.

```sh
python scripts/intake.py phone.mov --out prepared --fps 30
```

Intake writes `source.mp4` plus `intake.json`: detected CFR/VFR, original display
rotation and color tags, applied transformations, measured stream start/end skew.
FFmpeg applies display rotation once (90/180/270), stores upright pixels and clears
the matrix. Timestamp-based nearest drop/duplicate produces CFR without retiming
audio. The last visual frame is extended to the rounded container duration when
necessary; AAC audio is resampled to 48 kHz stereo with timestamp synchronization.
The timestamp check rejects skew beyond one frame plus 2 ms. It is not a lip-sync
detector; tests independently check synthetic flash/click alignment and source IDs.

HDR10 PQ/BT.2020 (and tagged HLG) is linearized using zscale at 100-nit reference,
converted to BT.709 primaries, tone-mapped using **mobius, transition 0.3**, then
encoded as 8-bit BT.709-limited yuv420p. If libzimg/zscale is unavailable, intake
fails explicitly before publishing; it never silently tags PQ as SDR. Dolby Vision
dynamic metadata and untagged HDR are outside this intake contract.

## Proxy, raster limits and evidence

`--proxy` divides delivery dimensions by three (rounded to even pixels, short side
at most 540). The video clock, cuts and event indices are unchanged. RIFE and
model-backed parallax are skipped; prepared depth maps remain usable. Source-frame
and optical-flow caches are bounded and reused within a render, not persisted
between runs. This is a preview, not a platform-sized deliverable.

GIF/APNG/PNG/sprite rendering retains the old 10 ms behavior and is capped at
**512 MiB of decoded RGBA output frames** before film allocation. For example,
1080×1920 permits at most 64 stored exposures. Working buffers and GIF palette
processing require additional memory. Split or reduce raster previews beyond that
limit. Mixed video/raster requests run separately; raster files live under `raster/`.

Reproduce whole-process-tree measurements with
`python wow/fx/benchmark_p0.py --out wow/fx/benchmark-p0.json` (serial, several minutes).
It samples parent + recursive FFmpeg children every 50 ms, and on Windows takes
the larger of summed RSS and summed peak working sets. Without psutil, Windows
uses Toolhelp32Snapshot/GetProcessMemoryInfo; other OSes need psutil. The JSON
includes machine/runtime versions, file growth and every sample. See
[P0 build notes](../wow/fx/build-notes-p0.md) for measured results and remaining limits.
