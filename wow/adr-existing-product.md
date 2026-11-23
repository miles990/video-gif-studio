# ADR: adopt wow COMMON 1.0 / INTEROP 1.0 on an existing product

- Status: accepted
- Date: 2026-11-24

video-gif-studio already existed as a scripts-layout CLI and skill. It was not created with `wow-eng new`, so `wow/skeleton.json` records `"skeleton": "none"` instead of a skeleton id.

Adoption means adding `wow.manifest.json`, `--json` / `--version` / RFC 9457 errors on the CLI, `AGENTS.md`, `pyproject.toml` metadata, and schema files under `schemas/`, without relocating `scripts/` into a `src/` package layout in this pass. Engineering debt (complexity, fan-out) is ratcheted from a baseline rather than treated as a gate-zero rewrite.
