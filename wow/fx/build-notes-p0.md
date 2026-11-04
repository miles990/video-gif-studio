# P0 delivery layer build notes

Date: 2026-11-05. Worktree: `C:\Users\User\src\vgs-fx`, branch `p0-delivery`.
Base: `ea2e790859b2cc98fd732256c44274eb0ee4cdb2`. No commit or push.
No edits to spec/acceptance/process files, examples, or either external skill/repository.
The worktree already contained partial P0 edits, debug files and a progress.md change;
those unrelated pre-existing files were preserved.

## Per-item results

| Item | Status | Measured evidence |
| --- | --- | --- |
| S-50 streaming | Implemented; full-size memory and growth checks passed | Three **stable** effects (`zoom_punch`, `grade`, `halation`): 1080×1920 / 30 s / 900 frames, **499,961,856 bytes** peak; 10 s **499,236,864 bytes**, growth **0.145%**. Acceptance's named workload was also run three times: maximum **506,728,448 bytes**, growth **0.548%**, 48.98–49.20% of final MP4 bytes already written halfway through. All below 1,610,612,736 bytes. |
| S-51 CFR | Implemented; decoded timing and compatibility checked | MP4 at 24/25/30/50/60, MOV/WebM at default 30: r_frame_rate = avg_frame_rate; frame count and PTS spacing checked. Ten odd-beat flashes detected exactly at recorded event frames. Maximum error: **18.667 ms at 24**, **16.333 ms at 30**, **3.000 ms at 60**. Explicit legacy 100 fps decoded pixels identical to base for three synthetic plans. |
| S-52 presets | Implemented; all five MP4 presets checked | 1080×1920 (TikTok/Reels/Shorts), 1920×1080 (YouTube), 1080×1080 (square); default 30 fps; yuv420p; BT.709 primaries/transfer/matrix and limited range; faststart; measured bitrate within 25% of 10/8 Mbps on two-second fixtures. 75% RGB color-bar maximum channel error **3/255**. Straight-alpha matte and safe-zone metadata checked. |
| S-53 audio | Implemented; encoded audio gate checked | Synthetic speech/music: **−14.0 LUFS**, **−5.3 dBTP**, **9.91 dB** ducking, **50 ms** attack, **350 ms** recovery, non-speech 110 Hz level standard deviation **0.0022 dB**. Original 440 Hz retained versus explicit off: **+130.45 dB** in the fixture. HOT input normalizes to **−14.0 LUFS / −12.5 dBTP**; unnormalized hot output produces qa_media exit 1 and render publication is blocked. |
| S-54 intake | Implemented; synthetic decoded-pixel/audio checks passed | VFR 30/24/60 with dropped frames → 30 CFR. Across 10 s, barcode source-time error ≤ **33.333 ms**, flash/click skew ≤ **0.084 ms** at all ten markers. 90/180/270° displayed upright once, rotation removed. HDR10 PQ/BT.2020 → mobius SDR BT.709; decoded limited Y steps **16, 37, 60, 81, 103, 126, 146, 166, 180, 192, 201** are strictly monotone; max hue error **4°**, skin saturation retained **98.5%**. |
| S-55 proxy/performance | Implemented; measured serially | Named acceptance workload: 720×1280 **7.62 fps / 673 MB peak**; 1080×1920 **3.39–3.44 fps / 507 MB maximum**. Proxy 360×640: **14.13 fps / 139 MB**, **63.67 s**, **24.18%** of mean full render time. Event and cut frame indices match. Optional RIFE/depth bypass is tested without models; bounded source and flow caches are reused within each run. |

MB above means decimal MB; raw bytes are retained in the JSON. Stable-effect
1080p throughput is **3.965 fps** including source decoding and encoding; stable
720p is **7.251 fps / 268,083,200 bytes** peak. Stable proxy is **13.565 fps /
137,527,296 bytes**, **66.35 s (29.23% of full render time)**.

## Reproduction and resource method

Use the requested Python:
`C:\Users\User\.codex\skills\video-gif-studio\.venv\Scripts\python.exe`.
FFmpeg/ffprobe are the supplied static runtime, version 8.0.1 essentials, on PATH
or through `VIDEO_GIF_FFMPEG` / `VIDEO_GIF_FFPROBE`. No optional-engine venv,
weights, downloads, network calls, paid APIs or concurrent heavy jobs were used.

```text
python wow/fx/benchmark_p0.py --out wow/fx/benchmark-p0.json
python wow/fx/benchmark_p0.py --stable --out wow/fx/benchmark-p0-stable.json
python wow/fx/regression_p0.py
python -m unittest discover -s tests -v
```

`scripts/process_memory.py` samples the render process and all live descendants,
including FFmpeg, at nominal 50 ms intervals. psutil is absent in this venv; the
Windows fallback uses Toolhelp32Snapshot to build the tree and GetProcessMemoryInfo
for WorkingSetSize and PeakWorkingSetSize. Reported peak is the larger of summed
RSS and summed per-process peak working sets. The latter can be conservative because
process peaks need not coincide. The benchmark parent/fixture generator is excluded;
all render/encoder descendants are included. JSON records every sample, file growth,
machine, Python and FFmpeg versions. Source texture moves every frame and film_grain
adds changing noise; the benchmark is not a static-color encoder shortcut.

The acceptance workload names `rgb_split` and `film_grain`, but both are marked
experimental in this branch. The harness explicitly enables them and does not alter
their quality status. The separate stable workload addresses the user's explicit
three-stable-effects requirement. No kernel math was changed to obtain these numbers.

## Compatibility and tests

[regression-p0.json](regression-p0.json) compares archived base-commit scripts with
the current worktree, without changing Git. **670 PNG frames** across P-plain (50),
P-base (52), P-ramp (50) and demo2 (518) are byte-identical. All four GIFs and APNGs
are byte-identical. The three synthetic explicit 100 fps videos decode identically
(infinite PSNR, recorded as `identical`). Demo2 was compared as a silent visual
derivative, removing the same zero-offset soundtrack in both runs; visual parameters,
source frames, timing and effects were unchanged. **demo3/demo4 are absent here**
and were not manufactured or claimed as verified.

The streaming-versus-PNG-reference test also compares decoded video bytes exactly.
The injected failure after frame 450 verifies that the FFmpeg process has exited,
the partial file is gone and no completed movie is published. Raster output is
guarded before film allocation at **512 MiB decoded RGBA** (64 exposures at
1080×1920); palette/working buffers are additional. This keeps the existing demo2
plan usable while rejecting unbounded GIF/APNG requests.

Final full suite: **234 tests in 83.561 s, zero failures, two baseline errors,
four existing Chromium skips; zero new failures/errors**. All **23 P0 tests pass**.
See [tests-p0-final.log](tests-p0-final.log) and the extracted
[measurements-p0.json](measurements-p0.json). The two errors are the supplied
baseline environment issues: Windows symlink privilege (WinError 1314) in
test_install and an open overlay.png handle (WinError 32) in test_mask_review.
The suite therefore still exits nonzero; this is not reported as a clean all-pass
run. Explicit FFmpeg overrides enabled the existing H.264 regression, which passed.
No new P0 test was skipped. Existing video tests now select explicit 100 fps when
testing legacy behavior, and the audio-accent test observes the streaming sink and
nearest CFR event frame rather than assuming whole-film export/forward-only timing.

The offline phone generators are [tests/phone_fixtures.py](../../tests/phone_fixtures.py):
VFR/drop/barcode/flash/click, upright reference artwork with 90/180/270° metadata,
and HDR10 gray/color/skin charts with mastering/MaxCLL metadata. They use local FFmpeg
lavfi and are generated in temporary test directories; no real phone media is required.

## Scope and limits

- Video-only delivery writes frames directly to FFmpeg; mixed requests render video
  and raster timing domains separately, with raster derivatives under `raster/`.
- Plan `fps` retains legacy raster sampling semantics. Video CLI `--fps` controls
  CFR; half ties round later. Explicit 100 is rejected with platform presets;
  fractional 29.97 is not supported. GIF/APNG keep their 10 ms timing.
- Presets preserve aspect ratio with padding. Their pixel safe-zone rectangles and
  2%-width inset are a contract for later captions, not a P0 caption renderer or
  automatic repositioning of existing free-form text effects.
- Source sound is opt-in via a continuous timeline-aligned `source_audio` and
  `keep_audio`. It does not infer audio edits from PNG manifests. Old non-platform
  music-only muxing remains compatible unless loudnorm is explicitly selected.
- Loudnorm logs both passes and requests linear processing; FFmpeg's reported
  dynamic fallback is retained when peak/LRA constraints prevent linear gain.
  Silent tracks are rejected; no track is a valid silent delivery.
- HDR intake requires zscale/libzimg and fails clearly if unavailable. Timestamp
  skew checks cannot establish lip sync for arbitrary speech. Dynamic Dolby Vision,
  untagged HDR and perceptual review are not claimed.
- Proxy reuses bounded in-run caches and records skipped model operations; persistent
  incremental shot caches and caption/shot-review UI belong to later slices.
- Modern streaming MOV/WebM alpha is covered by decode tests, not a retained
  full-film per-frame alpha reference. Check target players for alpha support.
