# Spatial previs and deterministic review

Use footwear-shot-director's `/motion-lab` to author spatial controls with live lens preview, camera-path dragging, keyframe timeline, separate performance/atmosphere, undo and project interchange. Its Agent CLI and UI use the same bounded command reducer. See the companion project's `docs/motion-lab.md` for command schemas.

## Tools

```sh
.venv/bin/python scripts/motion_pack.py motion-control.zip
.venv/bin/python scripts/motion_pack.py motion-control.zip --output control.mp4
.venv/bin/python scripts/review_pair.py source.mp4 candidate.mp4 --samples 12 --offset 0 --output new-review
```

Motion-pack verification checks member bounds, duplicates, sequence, timestamps, image dimensions and SHA-256 before any encoding. It never executes commands from a pack. Encoding preserves the authored frame count, pads odd dimensions and emits a silent guide plus verification JSON. Existing outputs are refused. The audio silence is deliberate for *control media*, not a final-delivery default. Preserve original music through `assemble_edit.py` when requested.

`review_pair.py` writes `comparison.jpg` (A left, B right per timestamp) and `review.json`. Positive offset means candidate time = source time + offset. Samples cover the overlap, excluding the exact container endpoint. Timestamp seeking does not guarantee exact source-frame correspondence for VFR media. The ledger starts unreviewed; no face-recognition, action-equivalence or audio-equivalence claim is made. Examine extra frames at cuts, occlusions, energy silhouettes, inset boundaries and endings, then play at normal speed.

## Reference roles

Choose camera-only guide ownership when the white model is a blocking sketch: framing, scale, paths and occlusion are its job. Keep acting in text and appearance in character images. Use camera-body ownership only for intentionally authored body timing. Do not copy guide dots, grids, grey surfaces or flat lighting into final footage. Provider reference support is not a guarantee of exact motion or identity.

## Evidence, retrieved 2026-10-04

- [Magncsans white-model example](https://x.com/Magncsans/status/2103371202643501337): reported speed and success rates are author anecdotes, not benchmarks.
- [Explanation of spatial control](https://x.com/magncsans/status/2104381577476067796): make positions and camera paths observable; preserve freedom for acting/material/light. Explicitly not 100% control.
- [Agent-assisted trailer report](https://x.com/Magncsans/status/2104750005097779692): a motivation for local manifests, not proof our tools autonomously edit trailers.

Local production lessons: character edits can change action; effects may retain old-person silhouettes; insets may appear too early; expression prompts can still over-smile. Keep original and candidate media, job provenance, exact replacement ranges and independent audio verification. A technically valid file remains a creative candidate until reviewed.

## Generic white-model studio interchange

The companion `/white-model` page exports `laceframe.white-model.frame-pack.v1` ZIPs. The same `motion_pack.py` command now verifies and encodes them directly, without manual extraction. Verification checks scene SHA-256, each frame's SHA-256 and byte count, zero-based order, finite timestamps, declared dimensions and exact frame-count duration. Packs containing both manifest formats are rejected rather than guessed.

```sh
python3 scripts/motion_pack.py white-model-clay.zip
python3 scripts/motion_pack.py white-model-clay.zip --output new-control-preview.mp4
```

The report preserves source schema and clay/depth pass. The MP4 is a **lossy preview**, including when the input is depth: retain original depth PNGs for quantitative depth use. For lossless FFV1 use the companion project's `web/scripts/encode-white-model-pack.py --lossless` workflow. Neither encoding nor a valid checksum approves motion/identity fidelity. The current generic rig supports FK, procedural walk/punch/wave, fingers and basic expressions; IK, contact/grasp and collision solving are not present yet.
