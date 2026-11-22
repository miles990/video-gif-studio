# Held-out local checks (S-11, plain `vgs make` with no custom flags)

Date: 2026-11-22 (Asia/Taipei). Command template:
`env -u XAI_API_KEY -u FAL_KEY /home/box/.codex/skills/video-gif-studio/.venv/bin/python scripts/vgs.py make <source> --out <new-dir>`
No Grok/fal requests. Saturation threshold is the spec constant `0.35` (`(max-min)/max`), not tuned to these clips.
`chibi` (`examples/chibi-running-dash/source.mp4`) was the visible sample; the four clips below are held-out real videos.

| Clip | Source | Exit | Wall (ms) | Key / Saturation / Confidence | Size & Duration | Loop & QA |
|---|---|---:|---:|---|---|---|
| robot | `examples/robot-wave-no-reference/source.mp4` | 0 | 7311 | Keyed `#FA03F8`, sat `0.988`, conf `1.000`; `ring=0`, `mag_max=0`; interior island warn f33 (`0.0100`) | 320×320, 145f, 6.04s, 3.28 MB | `loop FAIL` (position/speed; no crossfade); `QA FAIL` |
| seated | `examples/stylized-redraw-seated/final.mp4` | 0 | 10371 | Not keyed: low saturation `0.10 < 0.35`, conf `1.000`; opaque (`ring=1.0`); suggested `--key F3EADB` | 320×320, 299f, 9.97s, 8.71 MB | `loop FAIL` (speed mismatch), `freeze WARN`; `QA FAIL` |
| idle | `/workspace/wizardx07-dist/agent-avatar/media/idle_cute.mp4` | 0 | 7357 | Not keyed: low saturation `0.03 < 0.35`, conf `1.000`; opaque (`ring=1.0`); suggested `--key F0EBE8` | 320×478, 124f, 5.17s, 3.13 MB | `loop PASS` (measured); `QA PASS` |
| gufeng | `/workspace/liu/gufeng.mp4` | 0 | 25620 | Not keyed: non-flat (`conf=0.124`); opaque (`ring=1.0`) | 320×569, 361f, 12.03s, **41.16 MB**; printed shrink cmd `--width 160` | `pops WARN`, `loop FAIL` (speed); `QA FAIL` |

Note on `gufeng` wall time (25.6 s > 15 s): `gufeng` is a 12.03 s vertical 360-frame source (unlike the short ~6 s square chibi baseline); S-1's ≤ 15 s target is for the standard short sample, not a 12 s full-frame non-keyed video.
