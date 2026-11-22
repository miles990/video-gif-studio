# Builder self-check

2026-11-22, local commands with `XAI_API_KEY` and `FAL_KEY` unset, Python `/home/box/.codex/skills/video-gif-studio/.venv/bin/python`. Outputs under `/tmp`, original example masters untouched.

- S-8: default chibi 90 frames / 3.75 s; last motion 3.42 s, 0.29 s guard, encoded loop PASS; source indices contiguous. Robot auto reports FAIL, no blending. Explicit robot `--loop crossfade` passes after six-frame blend and discloses it.
- S-9: chibi border 0, key share 0; interior warning frame 54 share 0.0465 of canvas. `--keep-interior-key`: key share 0.3450 and `vgs qa` FAIL; default `vgs qa` PASS. Unkeyed chibi fails background check. Low-saturation held-out results in held-out.md. Synthetic transparent border plus center magenta is covered by test_vgs.py.
- S-10: pixel GIF 288×288, 90 frames, 0 nonuniform 3×3 blocks, 32 opaque colors, alpha {0,255}; custom 64×5 with 16 colors produced 320×320, 0 nonuniform blocks, 16 colors. MP4 ffprobe: h264, yuv420p, 288×288, 24 fps, 11.25s; sprite schema and crop checks exported. Idle pixel MP4 padding bottom 1 gives 288×430. See x-pixel-media/ASSET-NOTES.md for reproducible command.
- Batch 1 C1/C2/C3: synthetic C1 keyed with interior warning; C2 opaque, non-flat; C3 keyed green. `--no-key` fails delivery check. Invalid flags and occupied outputs checked by tests.
- Test command: `env -u XAI_API_KEY -u FAL_KEY $PY -m unittest tests/test_vgs.py tests/test_pipeline.py tests/test_qa_media.py tests/test_install.py tests/test_sprite.py -v` — 38 tests passed in 14.237 seconds.

Visual motion, effect retention and distribution approval remain for human review. No publishing or external submissions.

The exact documented pixel pack command was rerun after moving the first output; GIF and MP4 SHA-256 hashes matched between runs. The three existing `final.gif` hashes match the acceptance baseline.

Additional controls: `--loop off` retained 93 frames / 3.87 seconds and reported the measured speed mismatch. Explicit seated `--key F3EADB` exited 1 with a three-part foreground-loss error and no output. C1 with `--keep-interior-key` reported preserved islands and key share 0.1667. The six focused tests passed again after the final help/disclosure edit.
