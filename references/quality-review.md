<!-- Adapted from https://github.com/win4r/video-director Quality gates / Definition of done / references/quality.md. MIT; Copyright (c) 2026 win4r. Full license: ../THIRD_PARTY.md. -->
# Quality review for animation deliveries

Run measured screening on the decoded delivery after each export or timing repair:

```sh
python scripts/qa_media.py final.gif --out qa-gif
python scripts/qa_media.py final.apng --out qa-apng --loop
python scripts/qa_media.py frames --fps 25 --out qa-frames --holds 1.0-3.0
python scripts/qa_media.py final.mp4 --out qa-video --timeline timeline.json
```

Use a new output directory for each run. Reports and sheets support independent review; they do not certify artistic quality. Frame numbers are zero-based decoded-frame indices. GIF encoders can coalesce identical frames, so indices may differ from source PNGs; seconds come from accumulated embedded delays. PNG sequences use `--fps`; MP4 uses presentation timestamps and the last frame's container duration.

`report.json` and `report.md` have PASS/WARN/FAIL per check, event frame numbers and seconds, and exclusive end times for ranges. Exit 1 means at least one FAIL; exit 0 includes WARN and requires review; exit 2 is an input/runtime error. PASS confirms only the stated measurement. WARN identifies an inspection point: document its disposition. FAIL blocks delivery until repaired or explicitly identified as an unresolved preview. Numbers cannot prove natural motion, semantic correctness, good matting or audio/video sync.

`contact_sheet.jpg` spans the clip, `phone_sheet.jpg` is exactly 360 px wide with one sample per second, and `hook_sheet.jpg` contains only the first 0–3 seconds (or the shorter clip). Labels give the sampled frame and its actual start time. Check flagged frames and neighbors at full resolution too; sheets alone cannot establish playback cadence.

## Measurement scope and controls

- Frame 0 exposure and contrast use alpha-weighted visible color. Transparent assets must be judged only in the alpha-covered area; hidden RGB is ignored, and transparent canvas is not a black-frame failure. Review edges over several backgrounds.
- Picture differences use premultiplied visible RGB at up to 192 px analysis width. Flashes require an isolated excursion that returns toward the preceding image. Small returning patches can be pop warnings. Very small defects can evade this screen.
- Freezes require at least one second with adjacent difference below 0.25/255. Annotate designed pauses with `--holds 1.0-3.0,5.0-6.2` in seconds, or a `still` segment in a compose_timeline plan/manifest. Only the declared overlap is removed; an undeclared remainder of at least one second still warns. Long-duration GIF/APNG frames are checked too.
- `--expect-cuts 2.0,4.0` declares hard cuts and requires detection within one frame. Ordinary timeline source joins and speed edits are continuation boundaries, not demands for hard cuts. Explicit `transition: "cut"` on a segment, or top-level `expect_cuts` in seconds, opts into a hard-cut requirement. Emitted manifests with `start_ms`/`duration_ms` and input plans with `end_beat`/`beatmap` are supported. Plans can also include `holds: [{"from": 1, "to": 3}]`.
- `--loop` checks endpoint position and adjacent moving speed; infinite-loop GIF/APNG metadata also enables it. Repeated endpoint frames are skipped when measuring adjacent motion; speed uses actual elapsed frame time. Position accepts seam ≤2× the median nonduplicate step or <0.5/255; speed ratio must be 0.5–2. If both boundary steps are below the freeze epsilon (0.25/255), velocity is treated as stationary and its ratio is not actionable. These are image differences, not tracked physical velocities: playback review is essential.
- GIF/APNG/PNG and sprite assets do **not** undergo loudness checks. No-audio MP4 reports N/A, never silent-track failure. Audio-bearing video reports FFmpeg ebur128 integrated LUFS and true peak, loudest 100 ms RMS window (50 ms hop), and quiet spans ≥0.4 s below both −40 dBFS and the 90th-percentile RMS minus 15 dB. Target −14 LUFS ±1; true peak must be ≤−1 dBTP. Integrated values describe the entire reported range, not an exact clipping instant. Listening and sync still need review.
- Only NumPy and Pillow are required for picture-only inputs. Video/audio use the existing media_runtime resolver: `VIDEO_GIF_FFMPEG` and `VIDEO_GIF_FFPROBE`, then installed/managed tools. When ffprobe is absent, recent FFmpeg can supply actual presentation timestamps and durations via showinfo (an extra decode pass); if it cannot, install the paired runtime. Missing tools produce an actionable error (`python scripts/media_runtime.py --install`); QA never downloads anything.

## Independent review

Use an independent reviewer with fresh context and **no construction history**, successful-fix narrative, or builder self-scores. Give the delivered clip, sheets, intended action/brief, and acceptance criteria. Ask the reviewer to **default to reject** until evidence supports each applicable item.

First show only pictures: request a one-sentence restatement of the apparent action/message, without sound or the intended description. Then compare it with the brief. For sprites, identify state, action direction, and recognizable entry/loop/exit phases rather than requiring a marketing hook.

Every defect and acceptance claim must cite frame numbers and seconds, including neighboring transition frames. Review actual playback, anatomy, contacts, weight transfer, limb identity, effects and loop cadence. Inspect alpha edges and the 360 px view. For music-bearing video, listen for distortion and synchronization. Do not require narration, factual labels, typography or a call to action when absent from the brief. If playback/listening is unavailable, state the limitation and keep those items unverified.

## Definition of done

- [ ] The action can be restated from pictures alone and matches the brief.
- [ ] Frame 0 is readable; the opening communicates the intended action at delivery scale.
- [ ] Every flagged flash/pop has been inspected with neighboring frames and resolved or documented.
- [ ] Long frozen intervals are intentional and precisely annotated; partial annotations do not hide remaining stillness.
- [ ] Explicit hard cuts meet the timeline; continuation joins do not acquire invented cut requirements.
- [ ] Loop position, speed and repeated playback are acceptable; nonloops are identified.
- [ ] Transparent edges, opaque interiors, negative spaces, palette and decoded alpha have been checked.
- [ ] Sprite canvases/pivots and entry/loop/exit boundaries fit their use. Engine compatibility is claimed only when tested.
- [ ] Audio-bearing video has loudness, true peak, silence intent and music sync checked; silent assets mark this N/A.
- [ ] Decoded output retains intended timing, dimensions and format; source and provenance remain available.
- [ ] Independent review cites evidence and separates measured, seen, heard and unverified properties. Numeric PASS cannot override visible failure.
