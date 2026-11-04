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

All paths resolve from the plan. Prepared animations have `manifest.json` and sibling RGBA `frames/` from the existing GIF pipeline. Conform phone footage with `intake.py`, then prepare frames with `gif_pipeline.py`; the visual composer reads prepared frames. To retain embedded sound, explicitly provide the aligned video/audio as `source_audio` and enable `keep_audio` (below).

Editing operations:

- **Trim:** animation/loop `in_ms` inclusive and `out_ms` exclusive select the prepared source timeline, before speed fitting. Values must lie within source duration on a 10ms grid. Source-frame exposure can be shortened at the trim edge but cannot become less than 20ms.
- **Reorder/split:** arrange segments in order; reference different ranges of one manifest to split a clip without changing the original.
- **Speed:** `speed: 1.25` shortens frame exposures uniformly. It changes only visuals, not music pitch or tempo. No optical-flow interpolation or new motion is generated.
- **Fit an animation:** `duration_ms` rescales its exposures to fit that duration; cannot be combined with `speed`. Excessively fast fits yielding sub-20ms frames are rejected rather than silently dropping motion.
- **Beat cut:** `end_beat` is a zero-based index into `beats_ms`, defining the segment's absolute output end. The segment starts where the previous one ended. Original song timestamps are shifted by `music.in_ms` and rounded to the nearest 10ms (at most 5ms quantization). A normal animation is time-fitted, a still is held, or a loop is repeated to reach the cut. Do not combine `end_beat` with `duration_ms`, speed-fitting or complete-cycle loop ending. Select later beat indices so each segment has positive duration.

Use a cut only where editorially appropriate; do not cut on every beat by default. For an attack impact to land on a beat, identify its actual source-frame time and split preparation/impact/recovery at that event; fit those phases to chosen beat boundaries. Aligning the end of a whole clip does not guarantee its internal impact lands on the beat. Preserve anticipation, weight transfer and effect decay. Do not force a damaging time-fit; choose a longer musical interval or regenerate the motion when needed. Pixel art retains its logical raster and gets no smoothing or image warping.

## Music output

A `music` entry requires at least one MOV/WebM/MP4 output; GIF, APNG and sprites cannot carry audio. Additional silent previews can be requested alongside a video. The soundtrack starts at `in_ms` in the source, maps to output time zero, is gain-adjusted and trimmed to the visual duration. Short music is padded with silence, never silently looped or stretched. The configured fades apply only at the overall start/end; continuous music is not cut/faded at every visual edit.

The legacy soundtrack-only mux step stream-copies video, adding PCM in MOV, Opus in WebM or AAC in MP4. It verifies stream presence, total duration (within 100ms codec tolerance), and actual decoded audio duration. Reports record source hash, offset, gain and fades. Platform/source-audio delivery uses the gated two-pass path below. These checks do not replace listening for correct accents or aesthetic timing. MOV/WebM alpha support remains player-dependent; MP4 is opaque.

## Delivery audio

P0 plans accept an optional continuous, timeline-aligned `source_audio` (an audio
file or video with an audio stream), `keep_audio`, `duck` and `loudnorm`:

```json
{
  "segments": [{"type":"still", "image":"frame.png", "duration_ms":20000}],
  "source_audio": {"file":"phone-original.mp4", "in_ms":0, "gain_db":0},
  "keep_audio": true,
  "music": {"file":"music.wav", "in_ms":0, "gain_db":0},
  "duck": true,
  "loudnorm": true
}
```

`fx_render --keep-audio [on|off] --duck on|off --loudnorm on|off` overrides plan
booleans. Source retention defaults off; when source sound is requested, `source_audio`
must name the aligned track. This is not an automatic reconstruction of audio from
trimmed/reordered/retimed PNG manifests. Supply an edited continuous track for those
operations. `in_ms`, `gain_db`, `fade_in_ms`, `fade_out_ms` work on both tracks.

When both tracks are present, ducking defaults on. Presence detection uses 10 ms
RMS windows and the larger of 26 dB below the loudest source window, 8 dB above
the source's 20th-percentile noise floor, and 1e-7. Trailing padded silence is
excluded from the floor estimate. Activity must last at least 40 ms before gaps
up to 150 ms are bridged, rejecting short clicks and steady tone/noise beds.
Detected intervals automate music gain to **-10 dB**
with 50 ms attack and 500 ms release; the depth does not depend on speech level.
NumPy writes a stereo 48 kHz float PCM gain envelope in one-second blocks, applied
with `amultiply`; filter graph size does not grow with the number of intervals.
The source is mixed back unchanged. This is level-based presence detection, not a
speech classifier; varying non-speech sounds can still trigger it. A lone music
track never ducks. `manifest.audio.ducking` records intervals and detector settings.

Ducking does **not engage when speech SNR is below approximately 8 dB** relative
to the estimated floor (threshold = noise-floor RMS × 2.5). This is an energy
heuristic, not a measured clean-speech SNR estimator. A noisy recording may need
manual automation or denoising; the tool does not silently lower the threshold.

Every input is converted to stereo before mixing, preserving distinct music L/R
content when the source is mono. Mixed float PCM is measured with loudnorm, then
a single constant gain targets -14 LUFS. A 192 kHz oversampled lookahead limiter
follows, with a -1.5 dBTP ceiling, 5 ms attack, 50 ms release, makeup gain disabled
and latency compensated; output returns to 48 kHz. This limits transient peaks
without lowering the entire mix to accommodate them. First-pass measurements,
`second_pass.gain_db` and limiter settings are retained in `manifest.audio`.
The extra 0.5 dB margin accommodates encoding; the final encoded measurement
remains authoritative. There is no dynamic loudness normalization that lifts
ducked passages back up. Excessively peak-dense material can still fail the gate.

Encoded audio is independently measured with ebur128. Loudness outside -14 ±1 LUFS
or true peak above -1 dBTP blocks publication; `qa_media.py` also returns nonzero.
No audio track and an entirely silent supplied track are valid silent delivery;
QA marks their loudness checks `applicable: false`, with an `N/A` message. Disabling
loudnorm does not disable the gate. Platform exports always use this gate. Existing
non-platform music-only plans retain their legacy mux unless `loudnorm` is explicitly
selected, preserving old soundtrack behavior; run `qa_media` before delivering them.

AAC stereo 48 kHz / 256 kbps is used for MP4/MOV; WebM uses Opus. Tracks are padded
or trimmed to the actual quantized video duration. QA establishes measured levels,
not intelligibility or perceptual sync; listen to the final mix.

Supported now: one continuous soundtrack, prepared-frame trim/reorder/split/uniform speed and duration fit, beat-aligned cuts, stills/loops and video output. P1 adds experimental captions, event SFX, layered beat editing and bar-based music candidates below. Not bundled: a general multitrack editor, music-conditioned Grok generation or an autonomous multi-generation chain runner.

## P1 event sound design (experimental)

Opt in with top-level `"experimental": true, "sfx": "auto"`, or:

```json
{"sfx":{"mode":"auto","user_folder":"my-sfx","kenney_folder":"kenney","gain_db":-3}}
```

| Visual event | Sound | Alignment |
| --- | --- | --- |
| whip_pan, push, slide, named whip | whoosh | onset |
| flash_white, flash_cut, zoom_punch, punch, crash_in/out | hit | onset |
| caption line, text, sticker, cutout_card | pop | onset |
| ramp | riser | end at ramp's impact beat |
| freeze / held previous frame, shutter | click | onset |
| glitch, rgb_split | glitch | onset |

SFX resolution is user folder → Kenney folder → deterministic NumPy synthesis,
independently per category. Use canonical filenames (`whoosh.wav`, `hit.wav`, etc.)
or `sfx-map.json`, e.g. `{"click":"Audio/click_001.ogg"}`. Nested pack folders are
supported. Explicit folder typos error; an absent category falls through. The
manifest lists category, source, file, SHA256, license, requested time and sample
anchor. Identical category/time events deduplicate; different sounds may overlap.
Alignment is at 48 kHz sample precision to the **delivered visual event frame**
(CFR half-up quantization), not a second 10 ms grid. Riser preroll before time zero
is clipped and recorded; provide sufficient lead-in for the full sound.
The named `whip` move is a peak-aligned exception: the maximum absolute sample
of the selected whoosh asset aligns to its maximum delivered frame displacement,
with `alignment: peak` recorded. This applies to user/Kenney assets and synthesis.

No `sfx` field means no new audio code path, preserving legacy plans. Opt-in SFX
are mixed after speech ducking, through P0 stereo conversion, oversampled limiter,
encoded -14 ±1 LUFS / ≤ -1 dBTP gate. Up to four measured gain corrections compensate
limiter loss on sparse impacts; retries are recorded. Pathological material can
still fail the gate. Automatic per-event music masking/relative-level riding is
not implemented. No paid calls or network access occur while rendering.

```sh
python scripts/download_kenney_audio.py --pack interface-sounds --out /local/kenney
# Or download the official archive manually and keep its license:
python scripts/download_kenney_audio.py --zip kenney_interface-sounds.zip --out /local/kenney
```

Downloader is a live step for the coordinator. No pack or weights are bundled.
See [attribution](../THIRD_PARTY.md).

## P1 layered rhythm and music fit

`cut_density: low|mid|high` in an experimental fx_render plan cycles its supplied
source slots. Low cuts every four bars, mid every two, high every bar; section
boundaries also cut. SONG64's 32 bars yield **8 / 15 / 31 cuts**, respectively,
within the documented acceptance bands **6–9 / 13–17 / 28–40**. Other material's
counts depend on its section boundaries. Accents use non-downbeat beats; successive
sections alternate zoom_punch, rgb_split and beat_bounce (zero automatic white
flashes). One non-downbeat accent is selected every four/two/one bars, producing
8 / 16 / 32 accents on SONG64. Automatic hit SFX follow the selected downbeat
cuts; zoom accents do not add a hit on every kick. `beat_layers.py` can
export the design without rendering. Beat maps need `duration_ms`, `beats_ms`,
optional `downbeats_ms`, and `sections:[{start_ms,end_ms,label}]`. Section boundaries
must be downbeats (10 ms tolerance). Without downbeats, every fourth beat is inferred
and marked. This is not automatic section detection. `music.in_ms` must be zero
with cut_density; fit/remap first. `manifest.beat_layers` records the decisions.
qa_media reports `cut_to_downbeat_median_ms` from **decoded cut candidates**, not
the planner's self-reported zero; null means no cut was detected. Bounded planned
effect/entrance impulses are excluded from rhythm scoring, except at known shot
boundaries; the excluded decoded candidates are listed separately. Continuous
effect spans are not blanket exemptions. Flash QA itself remains unchanged.

```sh
python scripts/music_fit.py song.wav --beats beats.json --target 30 --candidates 3 --out fits
python scripts/music_fit.py delivered.mp4 --beats fits/candidate-1-beats.json --no-music --out silent
```

Music fit gives exactly three distinct prefix + ending candidates, preferring
section boundaries, then duration closeness, then balanced lengths. All endpoints
are bar boundaries; tolerance is one bar. If three candidates do not exist, it
reports an error. Inspect candidates.txt, each preview WAV and candidate beat map.
If music is shorter than the target, the error suggests shortening the target or
using `--no-music`.
Joins use stereo low-amplitude zero crossings within ±10 ms, a 40 ms raised-cosine
blend on the unchanged sample grid and a 500 ms squared tail fade. Candidate
manifests retain both musical boundaries and actual zero-crossing centers.
This is deterministic phrase-aware slicing, not harmonic/key analysis or a promise
that every arbitrary song joins naturally. Music fitting decodes the selected song
into RAM; it is separate from the bounded video render loop.

The no-music route stream-copies only video into `no-music.mp4` (no audio stream),
and writes unchanged beat markers to JSON and CSV, including downbeat flags.
Fit beat maps remap each retained source span, so layered cuts use the edited clock.

## Effects and optional downbeats

For requested transitions/crossfades and beat/onset/energy envelopes, use [fx_render](fx.md). The default RMS engine does not identify downbeats; optional `--engine beat_this` records real model downbeats or a clearly documented RMS fallback. Existing RMS beat/onset timestamps stay unchanged. Model beat/downbeat times are rounded to integer milliseconds; its BPM is derived from mean model beat intervals. Beat This! can report double-time (the neon recording is about 164 BPM versus the RMS estimate of 82); inspect the intended pulse before editing.
