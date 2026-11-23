# Proposed CI workflow

This copy of `.github/workflows/test.yml` also installs `ffmpeg` on the push/PR **smoke** job, so tests that only need FFmpeg (for example `test_pixel_mp4_crisp`) run instead of being skipped. Skip logic in `scripts/run_ci_smoke.py` stays in place for anything that still lacks a fuller runtime.

The GitHub token used to land the Phase A test fixes may lack the `workflow` scope, so this file is committed here instead of (or until it can be) applied under `.github/workflows/`. To adopt it, copy `docs/ci/test.yml` over `.github/workflows/test.yml` with a token that can update workflows.

The smoke job at commit `992006f` already went green without this change: <https://github.com/miles990/video-gif-studio/actions/runs/45218132982>.
