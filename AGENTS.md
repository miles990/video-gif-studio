# AGENTS.md — video-gif-studio

## Setup
```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
# optional: .venv/bin/pip install -r requirements-matting.txt
# optional identity: follow references in SKILL.md
```

Runtime Python is 3.11+. Local make/qa also need `ffmpeg` and `ffprobe` (`python scripts/media_runtime.py --install` or a system install).

## Test
```bash
PYTHONPATH=scripts:tests .venv/bin/python -m unittest discover -s tests
python scripts/run_ci_smoke.py          # skips live-FFmpeg cases
node <wow>/tools/wow-eng.mjs all . --run
```

## Structure
This is an existing scripts-layout product (not opened from `wow-eng new`).

- `scripts/vgs.py` — human CLI: `make`, `qa`, `doctor`
- `scripts/doctor.py` — read-only runtime check (also `vgs doctor`)
- `scripts/` — pipeline, QA, FX, taste, identity, media runtime
- `tests/` — unittest modules; fixtures generated under `.scratch`
- `examples/` — checked-in source clips and README heroes
- `docs/index.html` — static local preview; do not deploy unless the owner asks
- `wow.manifest.json` — INTEROP 1.0 entrypoints and skills
- `schemas/` — JSON Schema for CLI `--json` output and RFC 9457 errors

## Conventions
- Result commands accept `--json`. Stdout is then a single JSON object; logs and warnings go to stderr. Errors with `--json` are RFC 9457 problem objects on the last line of stderr.
- `--version` prints `1.0.0`, matching `wow.manifest.json` and `pyproject.toml`.
- `doctor` is read-only: no generation, no login, no network.
- Intermediates stay in `wow/work/` (untracked). Process notes and INDEX live under `wow/`. Finals belong in product paths.
- This product follows wow COMMON 1.0 and INTEROP 1.0 (`conformsTo` in the manifest). `wow/skeleton.json` records that it was not generated from the wow Python skeleton.

## Boundaries
- Do not publish, tag a release, list on Agensi, or deploy the preview page without the owner's explicit approval.
- Do not commit `wow/work/`, `.venv/`, or `.scratch/`.
- Do not rewrite recipe golds to chase instrument noise; widen a live remesure tolerance instead.
- Global chroma key can punch enclosed key-colored art; warn and honour `--keep-interior-key`.
