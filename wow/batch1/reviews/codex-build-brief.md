You are the builder for a wow lite delivery of video-gif-studio (Batch 1). Work in /workspace/src/video-gif-studio.

READ FIRST (do not edit acceptance.md or spec.md):
- wow/batch1/spec.md
- wow/batch1/acceptance.md  ← your tests must satisfy this; if conflict, the stricter rule wins
- scripts/gif_pipeline.py, scripts/qa_media.py, scripts/install.py, scripts/doctor.py
- README.md, README.zh-TW.md, SKILL.md

HARD RULES
- Cost cap $0: never call Grok, fal, or any paid generation API. Never set or use XAI_API_KEY / FAL_KEY for generation.
- Do NOT modify .github/workflows/ at all. Leave the existing uncommitted test.yml change and untracked scripts/run_ci_smoke.py UNTOUCHED — they belong to a separate CI effort. Do not git add them.
- Do not git commit or git push. Leave staging clean except for files you may create; ideally do not `git add` at all.
- Do not overwrite examples/*/final.gif, final.apng, source.mp4, or official production records. Compressed heroes must be NEW files (e.g. examples/.../hero.gif).
- Do not overwrite the user's real ~/.claude/skills/video-gif-studio or ~/.codex/skills/video-gif-studio. Test installers with --skills-dir or a temporary HOME.
- Do not claim Unity/Godot/TexturePacker native format, market savings, seamless loops without QA, or agents other than Codex and Claude Code.
- Reuse gif_pipeline.py and qa_media.py. Do not rewrite the encoder. Wrapper + helpers only.
- Python for tests: PY=/home/box/.codex/skills/video-gif-studio/.venv/bin/python
- Put self-test evidence under wow/batch1/evidence/ (ok to write). Outputs of test runs go under /tmp/vgs-build/ not into examples/.

GOAL: implement S-1..S-7 in acceptance.md.

## S-1  scripts/vgs.py  (new human entry)

`python scripts/vgs.py make <input> --out <new-dir>`

Defaults (do not require --key, --tolerance, or --width on the happy path):
- Default output width 320 (print it in the summary). Must finish the chibi sample in ≤ 15 s wall clock.
- Auto background key:
  - Sample borders/corners over time. Only auto-key when evidence shows a uniform flat background color (confidence in manifest).
  - Estimated key hex, tolerance, softness, confidence must be recorded in manifest + human summary.
  - Source magenta is NOT exact FF00FF (decoded ~RGB 244,20,247). Tune tolerance so the 4px border becomes transparent (ring_opaque_max ≤ 0.01) without wiping the chibi sword glow (magenta_share_max ≤ 0.02 is the allowance for legitimate pink/purple).
  - If the subject contains a closed region of the key color (acceptance control C1), either keep that island (prefer flood/connected-to-border key) OR clearly WARN that foreground contains the key color and may have been punched through. Silent punch-through is forbidden.
  - If the background is busy/not flat (C2 testsrc2): do NOT key, do NOT claim transparent. Summary must say 未去背 and why. Exit 0 only if clearly labeled as a non-transparent delivery. (Background QA in S-2 still applies when the user wanted transparency; for C2, honest non-transparent is OK with exit 0.)
  - If green screen (C3): either key the detected green correctly, or say you only support magenta and did not key. Do not claim transparent if you did not key.
- Trailing freeze (S-3): detect a long still tail. On examples/chibi-running-dash/source.mp4 the hold is frames ~85–144 (about 3.54s–6.04s). Trim or retime it. Remaining end freeze must be ≤ 0.5s or gone. Keep the recovery action itself (last non-still source time ≈ ≥ 3.5s). Record in summary+manifest: original duration, new duration, source interval removed/sped, method (trim/speed/decimate). Do NOT use qa_media --holds to hide a freeze. Do not secretly crossfade, reverse, or interpolate. Prefer trimming after a short guard (≤0.5s) and feeding a PNG sequence or cut video into gif_pipeline (PNG dir requires --fps). Preserve source_indices in the manifest so acceptance can check the last moving frame.
- Then run QA (qa_media) on the GIF.
- Human-readable stdout summary (not JSON-only) including: width×height, frame count, duration seconds, file size MB, whether background was removed plus key color, QA grade PASS/WARN/FAIL and main reasons, output path, and a line that visual approval still needs a human. If loop FAIL, say "loop FAIL" and position/speed reason; never write seamless / 無縫 / loop OK / 視覺通過 in that case. If loop PASS, you may write "loop 量測通過（未經視覺核准）".
- Write into --out: the gif (name it in the summary; animation.gif is fine), manifest.json (key, tolerance, confidence, tail treatment, source_indices, qc alpha_mismatch_pixels), QA report (report.md / report.json), and a checkerboard (light and dark) preview or contact so transparency is visible.
- Exit 0 only for a successful transparent delivery (or an honest non-transparent delivery like C2). If chroma/background should have been removed but was not, exit non-zero (S-2).
- Never call the network.

Implement helpers in scripts/ (e.g. scripts/vgs_detect.py) if that keeps vgs.py readable. Keep them local and dependency-free beyond requirements.txt (numpy, pillow already present).

## S-2  QA must fail when background was not removed

- Flag: `--no-key` (and mention `--keep-background` as an alias in help).
- `vgs.py make source --out DIR --no-key` must FAIL the delivery check because of the background itself (e.g. "border fully opaque and magenta"), not merely because loop failed. Exit code != 0. Summary first screen must say the background was not removed and this is not a transparent GIF.
- The background check must not false-FAIL the successful S-1 transparent chibi (sword glow is legal).
- For a legacy `gif_pipeline.py` unkeyed GIF, at least one user-visible gate (vgs delivery check, a `vgs qa` command, or an added qa_media check) must FAIL and name the background. Prefer implementing the check in a shared helper used by `vgs make`, and optionally `python scripts/vgs.py qa <gif>` so the wrapper is the user-visible gate. Avoid silently breaking existing qa_media default contracts on already-passing official GIFs; if you extend qa_media, make the new check explicit or clearly justified and keep official chibi final.gif from false-failing on sword glow.

## S-4  Human-readable errors

`vgs.py make` must catch these and exit != 0 with no `Traceback (most recent call last)`. Each message has three parts in plain language: what happened (name the path or numbers), impact, next step (a copy-pasteable fix):

1. Missing source file
2. PNG directory without --fps
3. Non-empty --out directory: do not write or delete anything (keep.txt hash unchanged, no new files)
4. Relabeling video FPS (`--fps 30` on a 24fps video): explain "source is 24 fps, you passed 30", that this would change playback speed, and to use `--fps 24` or omit it

If a missing source caused an empty out dir to be created, leave it empty or say so.

Wrap ValueError / argparse errors from gif_pipeline into the same style. Do not let raw tracebacks escape `vgs make`.

Also add `--help` that documents make, --no-key / --keep-background, --fps, --out, and the auto-key behavior.

## S-5  Dual-track README

Update BOTH README.md and README.zh-TW.md consistently:

- First ~40 lines: this is a standalone CLI tool AND a Codex + Claude Code skill. One human command (`python scripts/vgs.py make <video> --out <dir>`, after install / with the venv python) and one agent invocation.
- Document `/video-gif-studio` (Claude Code) and `$video-gif-studio` (Codex).
- Say that if the environment has no built-in image generation, the user must supply a start image or an existing video. Local path needs no account and costs $0.
- How it works diagram (mermaid is fine) that distinguishes the local path ($0, no account: existing video/PNG → key/trim → GIF/APNG/sprite) from generation API paths (Grok / fal).
- I2V options table, prices only as specified, dated 2026-11-22, with "recheck before listing":
  - Local existing media: $0
  - Grok / X plan website: uses the site's weekly shared credit pool (not a $/sec retail price in this table)
  - Grok API (prepaid credits, not the weekly pool): headline 1.5 $0.080/sec, lite $0.020/sec; note that a resolution-tier table may differ; recheck before listing
  - fal MiniMax H3 Max: from 2026-11-16, $0.05 / $0.08 / $0.16 per second at 480p / 768p / 1080p
- Move "Measured delivery QA" / qa_media so it is NOT the first section; it must come after the entry path and How it works.
- First-screen hero images each ≤ 3 MB (target ≤ 2 MB). Current seated final.gif 19.9 MB, robot 7.0 MB, neon preview 10.5 MB must not remain as first-screen embeds. Write compressed copies as new files and embed those. Leave original final.gif as optional links, not huge embeds. Do not overwrite official finals.
- No market-savings claims, no agents besides Codex and Claude Code, no native engine-importer claims, do not describe technical_pass as visual approval.

## S-6  Claude Code installer

Extend scripts/install.py:
- `--skills-dir` still overrides everything.
- `--target claude` → $HOME/.claude/skills
- `--target codex` → $CODEX_HOME/skills or $HOME/.codex/skills
- Default with no flags: if --skills-dir not given, then if CODEX_HOME is set use it; else if $HOME/.codex exists use ~/.codex/skills; else if $HOME/.claude exists use ~/.claude/skills; else ~/.codex/skills. Document this in --help and README.
- Keep "do not overwrite an existing install that is not this source"; re-run must exit != 0 with a human explanation (什麼/影響/下一步). Keep staging-dir copy so a failed install cannot look installed.
- `--skip-deps` remains registration-only and must not claim runtime readiness.
- Optionally mention vgs.py in the post-install help check list (in addition to gif_pipeline / grok_video).
- Update SKILL.md so an agent is told to use `python scripts/vgs.py make` for the local one-command path, and both invocation names.

You do not need to run a live Claude Code session yourself if it would be heavy; leave wow/batch1/evidence/ notes of installer tests. The coordinator will run Claude Code verification.

## S-7  Agensi pack (do not submit, do not contact anyone)

Update (do not invent a submit):
/workspace/money-radar-team/2026-11-22/agensi-listing-pack.md
/workspace/money-radar-team/2026-11-22/video-gif-studio-agensi.zip
Keep or refresh cover/logo already in that folder if the listing still needs them.

The existing pack was written before this batch (Codex-only). It MUST be updated to mention `vgs make`, verified Claude Code + Codex only, How it works, and the S-5 price table with 2026-11-22 / 2026-11-16 dates and the recheck note. English form fields can stay, plus a Traditional Chinese note for Alex. Do not claim the listing was submitted. Do not claim market savings.

ZIP must contain SKILL.md, requirements.txt, scripts/ (at least vgs.py, gif_pipeline.py, install.py, doctor.py) and README. Must NOT contain .git, .venv, .runtime, __pycache__, output/, run-*, .env*, local-settings.json, wow/, or QA scratch. A buyer should be able to run `python scripts/vgs.py make` from the unzipped tree against the repo's examples/chibi-running-dash/source.mp4. List the five largest files in the pack markdown with reasons for keeping them. Prefer a zip well under 25 MB (exclude bulky examples if needed; then say to use GitHub for samples).

## Self-check before you stop

Using PY=/home/box/.codex/skills/video-gif-studio/.venv/bin/python, run the acceptance commands for S-1 (chibi + C1/C2/C3), S-2, S-3, S-4, installer --target claude / --skills-dir with a fake HOME, and record results in wow/batch1/evidence/build-selfcheck.md. Fix failures that are in scope.

Do not start a web service. Do not push. When done, list the files you changed.
