You are the builder for Batch 2 of video-gif-studio (wow lite delivery). Work in /workspace/src/video-gif-studio.

READ FIRST (do NOT edit spec.md or acceptance.md):
- wow/batch2/spec.md
- wow/batch2/acceptance.md   ← every test in S-8..S-11 and Batch 1 non-regression must pass this
- scripts/vgs.py, scripts/gif_pipeline.py, scripts/qa_media.py (lines 247-350), scripts/sprite_export.py (lines 1-90)
- README.md, README.zh-TW.md, SKILL.md

HARD RULES
- Cost cap $0: NEVER call Grok, fal, or any paid API. Unset XAI_API_KEY and FAL_KEY in all tests.
- Do NOT touch .github/workflows/ or scripts/run_ci_smoke.py. Leave them completely alone.
- Do NOT overwrite examples/*/final.gif, final.apng, source.mp4, manifest.json, verification.json, or sprites.zip. Compressed/new assets must be separate files (e.g. hero.gif, hero-preview.png, pixel-hero.gif).
- Do NOT leave examples/chibi-running-dash/hero.png staged or referenced; ignore it.
- Do NOT commit or push yourself (coordinator handles git commits, browser screenshots, W4 design review, and Fable).
- Do NOT submit Agensi or post to X.
- Python: PY=/home/box/.codex/skills/video-gif-studio/.venv/bin/python

IMPLEMENT S-8, S-9, S-10, plus tests in tests/test_vgs.py, docs updates, and Agensi pack prep (not submitted).

## S-8: Honest auto loop-point detection (`--loop`)

Add `--loop` with choices `['auto', 'crossfade', 'off']`, default `'auto'`:
- First detect trailing still hold (`last` moving frame).
- Under `--loop off`: standard tail trim (keep up to 0.4s guard if hold > 0.7s, else full length).
- Under `--loop auto` (default):
  - Search candidate end frame indices `end` in a truthful forward window:
    - Never earlier than `last + 1` (so recovery motion is kept, and on chibi `end >= 83`, i.e., >= 3.46s).
    - Never leaving > 0.5s of still guard after `last` (so `end <= min(len(frames), last + 1 + int(0.5 * fps))` when there is a still tail; if no still tail, search `[max(2, int(len(frames)*0.7)), len(frames)]`).
  - Evaluate each candidate `end` using `qa_media`'s exact loop rules (seam against frame 0, median active step `med`, `speed_in`, `speed_out`, `ratio = (speed_in + 0.05) / (speed_out + 0.05)`).
  - Account for small GIF palette-quantization shifts by preferring candidates with comfortable margin (`position`: `seam < 0.45 or seam <= 1.8 * med`, `speed`: `0.55 <= ratio <= 1.8` or stationary), choosing the candidate with smallest seam (or best ratio near 1.0 within good seam), and ALWAYS verifying the actual encoded `animation.gif` with `qa_media.qa()`.
  - Output frames MUST strictly be a contiguous slice `frames[:end]` (strictly increasing `source_indices`, NO crossfade, NO reverse, NO interpolation).
  - If no candidate passes both position and speed (e.g. `robot-wave-no-reference/source.mp4`), keep standard tail trim, record `loop_treatment: {mode: 'auto', method: 'not_found', searched_frame_range: [...], reason: ...}` in `manifest.json`, and print `loop FAIL` with reason (`position`/`speed`) honestly.
- Under `--loop crossfade` (explicit opt-in ONLY):
  - Blend the last N frames (e.g., `N = min(6, max(2, len(frames)//8))`) smoothly with the first N frames (or wrap tail into start, dropping overlap) so start/end match, and explicitly record `loop_treatment` (`method: 'crossfade'`, `blend_frames`, `blend_seconds`, `source_interval_affected`) in `manifest.json` AND print in stdout (`loop 量測通過（經 crossfade 處理，混合 ...，未經視覺核准）`). Never say "seamless" or "無縫".

## S-9: Saturation guard, global key + interior-island warning, `vgs qa` key-share check

1. Saturation check for auto-key:
   - Compute `sat = float((key.max() - key.min()) / max(float(key.max()), 1.0))` (`(max-min)/max`, document formula in `--help` and `manifest.json`).
   - When user does NOT pass `--key` and NOT `--no-key`:
     - Only auto-key if `confidence > 0.95` AND `sat >= 0.35`.
     - If `confidence > 0.95` and `sat < 0.35` (low-saturation flat backdrop like `seated` ~0.10 or `idle` ~0.03): do NOT auto-key! Deliver opaque GIF with exit 0, `manifest.json` recording `background_flat: true, background_removed: false, key_saturation: sat, key_saturation_threshold: 0.35, key_saturation_formula: "(max-min)/max"`, and stdout stating clearly: `未去背，原因：邊框雖平坦但為低飽和純底（飽和度 X.XX < 0.35 門檻）... 這是非透明交付。若確定要去背，請加 --key <HEX>` (actual 6-char hex of border median).
2. Explicit `--key <HEX>`:
   - Validate 6-hex RGB (optional leading `#`). Invalid `--key ZZZZZZ` -> S-4 3-part human error, exit 1, no traceback.
   - If explicit `--key` erases the entire foreground (`No visible foreground` or `< 0.5%` visible pixels on every frame), exit 1 with a 3-part human error (what: `--key <HEX>` too close to foreground; impact: no output written; next step: omit `--key`), leaving `--out` absent or empty!
3. Global key by default + interior island detection & `--keep-interior-key`:
   - Remove dead `and False` code!
   - When keying (auto or `--key`), inspect connected components of key-matching pixels `(soft < 1)`:
     - `bg` = components touching the 4 frame edges.
     - `interior` = `(soft < 1) & ~bg`.
     - Measure `max_share` (max over frames of `interior.sum() / interior.size`) and `max_frame`.
     - Record `interior_key_islands: {threshold: 0.001, max_share: ..., frame: ..., action: 'kept' if args.keep_interior_key else 'removed'}` in `manifest.json`.
   - Default (without `--keep-interior-key`): apply global chroma key (removing both `bg` and `interior`, so trapped studio pockets like chibi frame 54 are cleared and `magenta_share_max <= 0.02`, while keeping non-key bright pink/purple sword glow intact!). If `max_share > 0.001`, MUST print prominent stdout warning naming `max_share`, `frame`, and full `--keep-interior-key` flag!
   - With `--keep-interior-key`: key ONLY border-connected `bg`, leaving `interior` opaque. Stdout MUST state `已保留內部鍵色區...` and must NOT claim key-share passed `<= 0.02`.
4. `vgs qa <gif>` (with `--help`):
   - Measure BOTH `border_opaque_max` (4px border) AND `key_share_max` (ratio of chroma-saturated key-like backdrop pixels in opaque area, e.g. bright magenta `(R>180)&(B>180)&(G<90)` or bright green `(G>180)&(R<90)&(B<90)`, with worst frame `key_share_frame`).
   - Print both values clearly!
   - FAIL (exit 1) if `border_opaque_max > 0.01` ("背景未去除，不是透明 GIF") OR `key_share_max > 0.10` ("中央或封閉區殘留大面積鍵色"). WARN (exit 0 or clear WARN) if `0.02 < key_share_max <= 0.10`. PASS (exit 0) if `border_opaque_max <= 0.01` and `key_share_max <= 0.02`. Verify 9a chibi PASSES `vgs qa`, 9b `--keep-interior-key` chibi does NOT PASS, legacy unkeyed GIF FAILS, and a synthetic "transparent border + 40% center #FF00FF" GIF FAILS!
5. Large GIF (> 15 MB) hint (for `gufeng`):
   - If output `animation.gif` > 15 MB, stdout summary MUST prominently display size and suggest a copy-pasteable `--width` or `--pixel` command to shrink it.

## S-10: `--pixel` preset, `--sprite`, `--mp4`, `--loop-count`

Add flags to `vgs make` (all documented in `--help` with defaults):
- `--pixel` (store_true): pixel-art preset (`NEAREST` downscale to raster grid, default `--pixel-width 96`; limited palette `--colors` default `32`, `Image.Dither.NONE`, binary `{0, 255}` alpha; integer `NEAREST` upscale `--pixel-scale`, default `max(1, math.ceil(288 / pixel_width))`, so `96 * 3 = 288`).
- `--pixel-width` (int): grid width in pixels (must be >= 1; implies pixel mode if passed, or combine with `--pixel`).
- `--pixel-scale` (int): integer nearest-neighbor enlargement factor (must be >= 1).
- `--colors` (int): palette size `2..255` (default `32` in pixel mode; reject `< 2`, `> 255`, or non-int with S-4 3-part human error and exit 1, no output dir).
- Ensure **zero nonuniform blocks and exact palette bound**:
  1. Downscale raw frames to `(pw, ph)` with `Image.Resampling.NEAREST`.
  2. Auto-key / explicit key at `(pw, ph)` (threshold alpha strictly `{0, 255}` in pixel mode, i.e., `alpha = 255 if a >= 128 else 0` — also ensure border doesn't get a 1px magenta fringe when downscaled: run a quick clean check on chibi `--pixel`, and if downscale created 1px boundary magenta bleed on opaque edge pixels, either tune or run a mild border-fringe cleanup only on low-alpha/key-adjacent 1px edge so `magenta_share_max <= 0.02` AND `ring_opaque_max <= 0.01`).
  3. Apply loop trim / tail trim.
  4. Quantize all kept frames jointly using `Image.Quantize.MEDIANCUT` with `colors=args.colors` and `Image.Dither.NONE`, storing the exact `<= colors` RGB palette + reserved transparency index 255. Encode the GIF directly from that exact palette (so `opaque_colors <= args.colors` is 100% guaranteed!), and run `gp.verify()`!
  5. Upscale each quantized RGBA frame by integer `scale` using `Image.Resampling.NEAREST` BEFORE encoding GIF/sprite/MP4 (or upscale the quantized palette-indexed image by `NEAREST` — every `s×s` block is identical, `alpha in {0, 255}`, `opaque_colors <= args.colors`)!
  6. Record `pixel_processing` in `manifest.json`: `grid_size: [pw, ph]`, `scale`, `output_size: [pw*scale, ph*scale]`, `colors`, `resample: 'nearest'`, `dither: 'none'`.
- `--sprite`: export into `out / 'sprites'` using `sprite_export.export(staging_frames_dir, staging_manifest, out / 'sprites')`. Frame PNGs have `{0, 255}` alpha, matching output (or grid — document clearly in summary & README which size `frame_size` is; upscaled output size matching GIF is great and avoids confusion). Ensure `sprites.json` has `schema_version: 1`, `engine_validation: "not performed"`, `qc.rgba_mismatches == 0`. Never mention Unity/Godot/TexturePacker as native.
- `--mp4` and `--loop-count`:
  - Composite frames onto solid dark studio background `#141820` (no checkerboard, no magenta).
  - If `w` or `h` is odd (e.g. `idle_cute.mp4` at 96×143 scaled 3× → 288×429), **pad** 1px right/bottom with `#141820` so width and height are even (NEVER non-nearest scaling!), and record `mp4_padding` in `manifest.json` + summary.
  - Determine `loop_count`: if `--loop-count` omitted, choose integer `k >= 1` such that `k * single_loop_seconds` lands in `8..15` seconds (closest in `[8, 15]`, e.g., `max(1, round(10.5 / single_loop_seconds))` clamped so if `single_loop_seconds <= 15` it fits `8..15` when possible). Document default `--loop-count` rule in `--help`.
  - Encode `out / 'animation.mp4'` via ffmpeg (`libx264`, `-pix_fmt yuv420p`, `-movflags +faststart`, CFR/input rate matching `fps`), keeping single-loop playback speed untouched!

## Update heroes, docs, tests, and Agensi pack

1. Update `examples/chibi-running-dash/hero.gif` and `hero-preview.png` from the new loop-PASS default chibi run (do NOT overwrite `final.gif`!). Also generate one crisp pixel-art demo image (e.g. `examples/chibi-running-dash/hero-pixel.gif`, <= 3 MB) so README shows `--pixel` too.
2. Generate the X showcase pack under `/workspace/money-radar-team/2026-11-22/x-pixel-media/`:
   - Use `vgs.py make examples/chibi-running-dash/source.mp4 --pixel --sprite --mp4 --out /tmp/vgs-x-pixel` (or `--pixel-width 96 --pixel-scale 5` so MP4 is 480×480 sharp pixel art, or default 288×288 — check acceptance S-10: let's make sure GIF < 15 MB, MP4 8–15s h264 yuv420p, `pixelcheck.py` passes, `ring_opaque_max <= 0.01`, sprite sheet included, and `ASSET-NOTES.md` in Traditional Chinese / bilingual records exact command, specs, and "未發布，需人看核准", AND test re-running the exact documented command!). Copy `animation.mp4`, `animation.gif`, `sprites/sheet-000.png`, `sprites/sprites.json`, `preview.png` into `x-pixel-media/`.
3. Update `README.md`, `README.zh-TW.md`, `SKILL.md`:
   - Document `--loop auto|crossfade`, `--keep-interior-key`, low-saturation guard + `--key`, `--pixel` / `--pixel-width` / `--pixel-scale` / `--colors` / `--sprite` / `--mp4` / `--loop-count`.
   - Update the "What a run looks like" / "執行後會長這樣" sample in BOTH READMEs to match the ACTUAL new `vgs make examples/chibi-running-dash/source.mp4` stdout (frame count, duration, loop PASS, interior-key warning!).
   - Embed the pixel-art demo GIF (`<= 3 MB`) in READMEs.
4. Update `/workspace/money-radar-team/2026-11-22/agensi-listing-pack.md` and rebuild `video-gif-studio-agensi.zip` (mention `--pixel`, `--loop`, `--keep-interior-key`; same exclusion rules; do not submit).
5. Add `tests/test_vgs.py` covering S-8..S-10 invariants & counterexamples (robot no auto-crossfade, low-sat no auto-key, interior island warning + `--keep-interior-key`, pixel block uniformity & palette bound & binary alpha, invalid flags human errors, `vgs qa` center-magenta fail). Run `$PY -m unittest tests/test_vgs.py tests/test_pipeline.py tests/test_qa_media.py tests/test_install.py tests/test_sprite.py -v`.
6. Run S-8, S-9, S-10, S-11 (robot, seated, idle, gufeng — plain `vgs make` with no flags!), and Batch 1 non-regression (C1–C3, S-2, S-4), saving evidence to `wow/batch2/evidence/build-selfcheck.md` and `wow/batch2/evidence/held-out.md`.

Do NOT commit or push. Leave `.github/workflows/` and `scripts/run_ci_smoke.py` untouched.
