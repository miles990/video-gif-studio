# Afterglow — rhythm study

Rebuild from a fresh checkout with the project Python, FFmpeg, and a system CJK font:

```powershell
python wow/fx/demo2/build.py; python wow/fx/demo2/verify.py
```

Set VIDEO_GIF_FFMPEG and VIDEO_GIF_FFPROBE if FFmpeg is not on PATH. This route needs
no optional inference environment: assets/depth-small.png and rife-midpoint.png are
small derived caches from repository footage. assets/provenance.json records their
source and engine. The plan explicitly uses the retained Small depth PNG; missing
assets are an error and never silently disable parallax. No font or model is included.
Windows uses Microsoft JhengHei; alternatively set VIDEO_GIF_FONT to a CJK font path.

To regenerate caches, run `python wow/fx/demo2/build.py --models` in fx-optdeps with
VIDEO_GIF_MODELS pointing to the read-only weights directory. This performs Small
and RIFE inference sequentially; finish it before rendering or running tests. All
preparation, flow pairs and depth caches stay under work/. NUMBA_DISABLE_JIT=1 should
be set for any optional rematting process; this film does not rematte frames.

Source footage: examples/neon-zen-pv/segment-01, -03, -04 and -05/generation/source.mp4.
Soundtrack: examples/neon-zen-pv/soundtrack.flac. Prepared sources are 480x270 at 25fps.
The Beat This! grid comes from ../demo/beats.json. The slow opening accelerates into
beat 8; downbeat accents at beats 11,19,35,43 are actual entries in downbeats_ms.
The film progresses through a paired/four-panel phrase, a quiet depth freeze, and a
warm grain/light-leak ending. Text reads 慢一拍 / 讓光流動 / 浮光 / 餘韻.
These effects are editorial treatments of existing movement, not invented fish motion.

The MP4 is opaque and contains music. GIF is a silent, reduced-resolution preview
bounded to 3 MB. build-results.json gives exact export time, selected GIF dimensions,
bytes and master location. manifest.json records source clocks, effects and transitions.
interpolation-comparison.jpg shows the same midpoint under none/blend/flow/RIFE;
interpolation-timings.json includes the real RIFE session timing (not a file-read time).

`verify.py` extracts the event neighborhoods listed in verification.json, including
cut +/-3 frames, each heavy beat +/-1, text's first five frames, ramp slow/hit samples,
transition quarter points, depth start/middle/end and the final two seconds. It streams
and decodes the MP4 to measure adjacent-frame difference peaks around each heavy beat.
Tolerance is one 25fps plan frame (40ms), despite 100fps codec timing repeats. QA uses
--timeline semantics: planned transitions/flashes can also be classified as image
cuts by literal --expect-cuts; that is not an editorial-cut count. Numeric QA and still
inspection do not establish listening or playback acceptance; independent review remains.

Measured delivery: **20.540s**, 480x270; pixel rendering 16.938s / 30.58fps. Render, MP4 and bounded GIF export: **45.96s**. GIF: **2,583,957 bytes**, 192px wide, 129 frames (about 6.25fps sampling), exact 20.540s duration. All four heavy-beat difference peaks are **0ms** from their planned downbeats (4020, 6960, 12840, 15760ms). QA: **PASS**, -14.3 LUFS, -2.3 dBTP; no WARN/FAIL. Inspected 101 extracted event samples across five sheets. The source-stage split layout now participates continuously in the circle wipe.

Builder frame review: all five inspection sheets were viewed. The slow ramp retained a single fish silhouette; CJK glyphs are distinct and readable; the circle wipe now reveals the full-size freeze over the outgoing four-panel composition; the depth segment shows modest layer travel without visible black holes in these samples. The warm ending remains restrained. This is still-frame review, not original-speed audiovisual approval.
