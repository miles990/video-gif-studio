# Held-out local checks (S-11, plain `vgs make` with no custom flags + verified recovery runs)

Date: 2026-11-22 (Asia/Taipei, post-fix commit `3b83806`). Command template:
`env -u XAI_API_KEY -u FAL_KEY /home/box/.codex/skills/video-gif-studio/.venv/bin/python scripts/vgs.py make <source> --out <new-dir>`
No Grok/fal requests. Saturation threshold is the spec constant `0.35` (`(max-min)/max`), not tuned to these clips.
`chibi` (`examples/chibi-running-dash/source.mp4`) was the visible sample; the four clips below are held-out real videos.

## Plain default runs (no flags)

| Clip | Source | Exit | Wall (ms) | Key / Saturation / Confidence | Size & Duration | Loop & QA |
|---|---|---:|---:|---|---|---|
| robot | `examples/robot-wave-no-reference/source.mp4` | 0 | 7311 | Keyed `#FA03F8`, sat `0.988`, conf `1.000`; `ring=0`, `mag_max=0`; interior island warn f33 (`0.0100`) | 320×320, 145f, 6.04s, 3.28 MB | `loop FAIL` (position/speed; no crossfade); `QA FAIL` |
| seated | `examples/stylized-redraw-seated/final.mp4` | 0 | ~10371 | Not keyed: low saturation `#F3EADB` `0.10 < 0.35`, conf `1.000`; opaque (`ring=1.0`); explains why chroma key cuts neutral/skin tones and points to magenta/green backdrop or optional `scripts/background_remove.py` | 320×320, 299f, 9.97s, 8.71 MB | `loop FAIL` (speed mismatch), `freeze WARN`; `QA FAIL` |
| idle | `/workspace/wizardx07-dist/agent-avatar/media/idle_cute.mp4` | 0 | ~7357 | Not keyed: low saturation `#F0EBE8` `0.03 < 0.35`, conf `1.000`; opaque (`ring=1.0`); honest neutral-backdrop guidance (no dead-end `--key`) | 320×478, 124f, 5.17s, 3.13 MB | `loop PASS` (measured); `QA PASS` |
| gufeng | `/workspace/liu/gufeng.mp4` | 0 | 25620 | Not keyed: non-flat (`conf=0.124`); opaque (`ring=1.0`) | 320×569, 361f, 12.03s, **41.16 MB**; printed shrink cmd `--width 160` | `pops WARN`, `loop FAIL` (speed); `QA FAIL` |

## Verified recovery runs (post-fix `3b83806`)

- `gufeng` shrink command printed by `vgs.py` (`--width 160`):
  - Exit `0`; `160×284`, `361` frames, `12.03 s`, **`13.29 MB`** (`< 15 MB`), `border_opaque_max 1.0000`, `key_share_max 0.0000` (honest opaque delivery).
- `seated` / `idle` low-saturation check:
  - Previously `vgs.py` printed `--key F3EADB` / `--key F0EBE8`, which failed with exit `1` (`--key ... 與主體太接近，會挖空主體`) because chroma distance deletes neutral skin/white clothing highlights (visually confirmed via 3D-RGB test as well: cream hair/face/white apron match the backdrop).
  - Fixed in `3b83806`: `vgs.py` now keeps low-sat neutral clips safely opaque without suggesting a dead-end `--key`, and directs users needing transparency to a saturated `#FF00FF`/`#00FF00` backdrop or optional `scripts/background_remove.py` (`--with-matting`). Verified by `test_low_saturation_cli_safe_hint` and re-runs on `seated` and `idle`.

Note on `gufeng` wall time (25.6 s > 15 s): `gufeng` is a 12.03 s vertical 360-frame source (unlike the short ~6 s square chibi baseline); S-1's ≤ 15 s target is for the standard short sample, not a 12 s full-frame non-keyed video.
