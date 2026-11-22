# Pixel-Art Temporal Flicker Diagnosis & Fix

Date: 2026-11-22 (Asia/Taipei)

## Root-Cause Measurements (Before)
1. **Non-integer `NEAREST` pre-key downscale (`720×720 → 96×96`, stride `7.5px`)**: `vgs.py` downscaled BEFORE keying (`apply_key_connected`), producing alternating `(7, 8)` grid phase drift and `26.92/frame` silhouette `alpha` `A→B→A` toggles.
2. **Unstabilized per-frame quantization**: Independent Voronoi nearest-color mapping flipped pixels near palette boundaries by ±3–15 RGB (`20.75/frame` color `A→B→A` churn; `48.8/frame` small-delta `<=35` transitions).
3. **89 redundant Local Color Tables (`LCT_count = 89`)**: Pillow wrote per-frame LCTs on appended frames.
4. **MP4 `288×288` (`3×3`) `yuv420p` chroma subsampling + H.264 deblock blur**: Odd `3×3` cells split across `2×2` chroma blocks and H.264 loop filter blurred edges (`nonuniform(>2std) = 882.91/frame`, `max = 1393`, `max_block_std = 43.70`).

## Fixes Applied
- Key at full/working resolution BEFORE downscaling, then pool each fixed grid cell (`pixel_pool_and_stabilize_alpha`: solid-core median or alpha-weighted RGB, hysteresis `on >= 0.62` / `off <= 0.38`, 1-frame blink clamp).
- Single global palette with temporal stabilization bounded by retained-color distance (`prev_dist <= 32` so gradual fades are never frozen) + 1-frame `A→B→A` spike clamp, plus GIF LCT stripping (`_gif_tables(..., strip=True)` -> `LCT_count = 0`).
- Pixel-mode MP4 integer upscale `>= 576` (`768×768`, `8×` DCT+chroma aligned), `-sws_flags neighbor`, `no-deblock=1`, X-spec limits check (`yuv420p`, High@4.0, `SAR 1:1`, `+cgop`, `+faststart`).
- Added `flicker_metrics()` to `vgs.py make` (stdout + `manifest.json`) and `vgs.py qa`.

## Before vs After (`chibi` `--pixel --sprite --mp4`)
| Metric | Before | After (v3) | Change |
|---|---:|---:|---:|
| GIF `quiet_flicker_rate` (`5×5` static patch `A→B→A`) | `0.0606` | `0.0157` | **-74.1%** |
| GIF `aba_fg_rate` (foreground `A→B→A`) | `0.0601` | `0.0195` | **-67.6%** |
| GIF `aba_pixels_per_frame` | `41.74` | `12.82` | **-69.3%** |
| GIF `quiet_flicker_pixels_per_frame` | `9.70` | `3.81` | **-60.7%** |
| GIF Local Color Tables (`lct_count`) | `89` | `0` | **Single GCT** |
| GIF file size | `0.29 MB` | `0.20 MB` | **-31%** |
| MP4 resolution & pixel scale | `288×288` (`3×`) | `768×768` (`8×`) | `>=576`, `8×8` DCT+4:2:0 aligned |
| MP4 `nonuniform_blocks (>2 std)` / frame | `882.91` (`max 1393`) | `0.13` (`max 2`) | **-99.99%** |
| MP4 `max_block_std` | `43.70` | `2.60` | **-94.1%** |
| MP4 file size & X spec check | `275.9 KB` | `257.2 KB` (`mp4_x_compatible: true`) | Verified via `ffprobe` |
