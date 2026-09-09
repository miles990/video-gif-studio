# Music-driven timing and editing

Local music input, editable beat candidates, frame-timeline cuts and a continuous soundtrack are bundled. No Grok request is needed to analyze audio or edit existing footage. The design was informed by the separate Pulseframe/lyrica-studio project's separation of waveform/BPM analysis, beat snapping and trim operations. This repo implements its own Python/FFmpeg workflow; it does not depend on or claim feature parity with that editor, and includes none of its application media or proprietary reference assets.

## Analyze music

```sh
.venv/bin/python scripts/music_sync.py song.wav --out output/song-analysis
.venv/bin/python scripts/music_sync.py song.wav --out output/song-manual \
  --bpm 120 --offset-ms 100
```

FFmpeg accepts supported audio inputs such as WAV, MP3, M4A and FLAC. Outputs are `beats.json` and `waveform.svg` with beat markers. The new output directory must not exist. Music is decoded locally to mono 8kHz for analysis; the export uses the original music file. The analyzer reads the decoded audio into memory, so select a bounded excerpt for very long inputs.

Automatic analysis uses 10ms RMS-onset periodicity over 60–200 BPM. It reports candidate scores and an estimated phase, not a calibrated musical-confidence probability. Silence returns no BPM. It does not identify downbeats, meter, lyrics, sections, or a changing tempo map. Sparse, syncopated or variable-tempo music may produce wrong or half/double tempos. Review by listening and inspecting the waveform; manual `--bpm` (20–400) and `--offset-ms` override estimates. `beats_ms` is editable and may contain nonuniform, strictly increasing timestamps for manually reviewed tempo changes. Do not claim a musical review from automated tests or a waveform alone.

## Cut animations to beats

```json
{
  "beatmap": "song-analysis/beats.json",
  "music": {
    "file": "song.wav",
    "in_ms": 100,
    "gain_db": 0,
    "fade_in_ms": 30,
    "fade_out_ms": 30
  },
  "segments": [
    {"type": "animation", "manifest": "shot-a/manifest.json", "in_ms": 200, "out_ms": 1000, "end_beat": 4},
    {"type": "still", "previous": "last", "end_beat": 6},
    {"type": "loop", "manifest": "shot-b/manifest.json", "end_beat": 12},
    {"type": "animation", "manifest": "shot-c/manifest.json", "speed": 1.25}
  ]
}
```

```sh
.venv/bin/python scripts/compose_timeline.py timeline.json --out output/music-cut \
  --formats mp4 --background 000000
```

All paths resolve from the plan. Prepared animations have `manifest.json` and sibling RGBA `frames/` from the existing GIF pipeline. Convert an existing source video with `gif_pipeline.py` first; the composer does not directly ingest arbitrary video files or retain their embedded audio.

Editing operations:

- **Trim:** animation/loop `in_ms` inclusive and `out_ms` exclusive select the prepared source timeline, before speed fitting. Values must lie within source duration on a 10ms grid. Source-frame exposure can be shortened at the trim edge but cannot become less than 20ms.
- **Reorder/split:** arrange segments in order; reference different ranges of one manifest to split a clip without changing the original.
- **Speed:** `speed: 1.25` shortens frame exposures uniformly. It changes only visuals, not music pitch or tempo. No optical-flow interpolation or new motion is generated.
- **Fit an animation:** `duration_ms` rescales its exposures to fit that duration; cannot be combined with `speed`. Excessively fast fits yielding sub-20ms frames are rejected rather than silently dropping motion.
- **Beat cut:** `end_beat` is a zero-based index into `beats_ms`, defining the segment's absolute output end. The segment starts where the previous one ended. Original song timestamps are shifted by `music.in_ms` and rounded to the nearest 10ms (at most 5ms quantization). A normal animation is time-fitted, a still is held, or a loop is repeated to reach the cut. Do not combine `end_beat` with `duration_ms`, speed-fitting or complete-cycle loop ending. Select later beat indices so each segment has positive duration.

Use a cut only where editorially appropriate; do not cut on every beat by default. For an attack impact to land on a beat, identify its actual source-frame time and split preparation/impact/recovery at that event; fit those phases to chosen beat boundaries. Aligning the end of a whole clip does not guarantee its internal impact lands on the beat. Preserve anticipation, weight transfer and effect decay. Do not force a damaging time-fit; choose a longer musical interval or regenerate the motion when needed. Pixel art retains its logical raster and gets no smoothing or image warping.

## Music output

A `music` entry requires at least one MOV/WebM/MP4 output; GIF, APNG and sprites cannot carry audio. Additional silent previews can be requested alongside a video. The soundtrack starts at `in_ms` in the source, maps to output time zero, is gain-adjusted and trimmed to the visual duration. Short music is padded with silence, never silently looped or stretched. The configured fades apply only at the overall start/end; continuous music is not cut/faded at every visual edit.

The mux step stream-copies the verified video, adding PCM in MOV, Opus in WebM or AAC in MP4. It verifies stream presence, total duration (within 100ms codec tolerance), and actual decoded audio duration. Reports record source hash, offset, gain and fades. These checks do not replace listening for clipped gain, correct accents or aesthetic timing. MOV/WebM alpha support remains player-dependent; MP4 is opaque.

Supported now: one continuous soundtrack, prepared-frame trim/reorder/split/uniform speed and duration fit, beat-aligned cuts, stills/loops and video output. Not bundled: multitrack audio mixing, transitions/crossfades, subtitles, a graphical editor, automatic phrase-aware montage, reliable downbeat tracking, music-conditioned Grok generation or an autonomous multi-generation chain runner. Future adapters should preserve explicit source/output clocks and per-event timing.
