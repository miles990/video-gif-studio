# Suno music route — experimental

Python plans requests and performs local analysis; the agent dispatches MCP calls.
No credentials, private library listing, playlist publication or paid fallback is
part of this route. Use `suno_route.py plan --request request.json --json`, then
`create --experimental` for an agent request specification. Kinds: theme, score,
song, bgm-loop, sfx, jingle, variants. Only sounds supports explicit tempo/key/loop.

`download_guard: "instruction_only"` describes **Codex direct MCP** honestly:
there is no native PreToolUse hook. Downloads are disabled by default, producing
only a pending list. An explicit per-run user instruction can authorize agent
dispatch; the agent must record selection, query fresh usage, run Ledger.guard,
call without confirm, and only confirm a requires_credit response after another
fresh check. This does not claim machine interception of arbitrary Codex calls.
The injected Session transport enforces the same guard at dispatch time for
offline cassettes or a host which routes every tool through it. A production
Claude hook must use Ledger.guard before invoking the real MCP transport.

Default cap: five charged downloads, stop when pre-call balance is <=9. A clip
and format already in the ledger returns its cache entry. Use WAV for final
selection; previews belong only under `.scratch/s15/analysis/`, never in a pack.
Ledger is single-writer; do not run concurrent spending agents against it.
Uncertain submissions must be reconciled using the same idempotency key.

All new features remain experimental until independent acceptance. Offline
tests use synthetic audio and FakeSuno and never contact the service.

## Local operations and command mapping

All audio is analyzed at 48 kHz. `audio_loop.py check FILE --bpm 120
--measured-bpm 120 --meter 4/4 --experimental --json` runs length, onset phase,
4 kHz highpass click windows, derivative, chroma/log-band distance, tail/head
correlation and EBU R128 gates. A missing measured BPM fails closed. The local
estimator is `audio_variants.measure(pcm)`; its heuristic is explicitly distinct
from Beat This!, and cannot establish a downbeat or reliable key on every cue.
Pass `audio_analysis`/Beat This! results separately and preserve disagreements.

`audio_loop.py export FILE --bpm 120 --out DIR --provenance receipt.json
--experimental` writes PCM16 WAV, Vorbis OGG, `.import`, RIFF smpl/cue/adtl and
loop JSON, rechecking both decoded files. Receipt needs `source: download|upload`
and `measured_bpm`. `synthetic_test` is reserved for offline instrument fixtures.
Use `audio_provenance.artifact` and `audit` to validate delivery lineage. The
loop JSON end and Godot end are exclusive; RIFF smpl dwEnd is inclusive L−1.
Godot 4.7.2 import enum **2** means forward (`1` disables looping), while the
runtime AudioStreamWAV.LOOP_FORWARD value is **1**. Do not confuse the enums.
`audio_engine.verify_godot(project, executable)` imports, asserts properties and
plays two cycles. Unity/FMOD/Wwise are metadata-only and always untested.

`audio_loop.repair` trims only measured bar boundaries and uses up to one beat
of equal-power incoming preroll; no silence fade. It returns QA, never an
unconditional seamless claim. Calibration remains experimental: at least ten
live loops and independent listening have not yet been completed.

Fix-round local loop making: `audio_loop.py make SOURCE.wav --bpm 120 --out
.scratch/run/processed.wav --experimental` estimates a 5ms spectral-flux grid,
searches 2/4/8/16-bar cuts and zero crossings within 1ms, and selects a measured
equal-power incoming-preroll crossfade of 5ms to one beat. The existing loop
verifier is unchanged. `audio_grid.grid` reports tempo alternatives and labels
metrical accent phase `local_estimate`; it does not claim independent downbeat
recognition. The older RMS estimate is preserved separately in fix-pack reports.
Both WAV and decoded OGG must pass; OGG now carries LOOPSTART/LOOPLENGTH comments.

`audio_variants.align_to_loop(reference_pcm, source_pcm)` refines each candidate
source bar using measured onset correlation, re-cuts from real source preroll,
and checks both the resulting loop and every declared bidirectional hard/faded
switch. It allows <=4% tempo correction only when needed and targets <=2ms
alignment. It does not merely rotate a finished loop and assume it still passes.

`audio_jingle.correct_key` measures chroma, transposes at most two semitones with
rubberband and rechecks key, duration, loudness, peak, DC and release. Transposition
cannot change major/minor mode; larger/mode conflicts are `regenerate_needed`.
`regeneration_request` returns exact unsubmitted sounds_create parameters and
does not authorize or dispatch spending. Missing cues stay missing.

Analysis-only previews: `audio_preview.py PLAYLIST_OR_FILE --out
.scratch/run/analysis --experimental`. FFmpeg probes the actual container/codec
and decodes HLS playlists directly (AAC MPEG-TS/fMP4), Opus, or other supported
audio. Remote playlists use an HTTP(S) protocol whitelist excluding local files;
local fixtures exclude network protocols. Preview PCM cannot enter a delivery.
The live `encoding: 1.0.0` label does not identify a codec. Supplied evidence had
no playable MP4 header or original payload, so live decoding remains blocked;
offline HLS tests are not proof of decoding that provider-specific transport.

Offline repair-pack rebuild: `audio_fix_pack.py --original UNPACKED_OLD_PACK
--sources FINAL_SOURCES --out NEW_SCRATCH_PACK --godot GODOT_EXE --experimental`.
This consumes existing download receipts, records source/output measurements,
checks encoded transitions, remeasures Godot two-cycle playback and attack sync,
and produces a ZIP. A partial cue inventory or unresolved preview remains an
experimental partial result even when BGM and engine checks pass. No Suno calls.

`sfx.py jingle FILE --out DIR --experimental` delegates to `audio_jingle.py`:
exactly five silence-separated cues or E_SPRITE_COUNT; DC removal, silence trim,
release fade and loudness/peak measurements. The original six synthesized SFX
APIs remain available. `audio_jingle.align_event` uses the perceived onset or
explicit sync point; `godot_event_library` produces an AnimationLibrary method
track calling the consumer's `play_cue(name)`. The sprite JSON has both explicit
start/end cue records and Howler-compatible `[start, duration]` under `sprite`.

Python planning/export APIs (no MCP dispatch):

- `audio_score.score`: exact video duration, existing bar-cut/zero-crossing
  fitting, drop alternatives, extension/full-song request specifications and
  decoded loudness checks. `crosscheck` compares provider and local downbeats,
  including half/double tempo. Beat This! is an optional local dependency.
- `audio_variants.measure`, `stretch`, `validate_set`, `switches`: measured
  estimates, <=4% rubberband correction, key relationships, <=2ms downbeat
  alignment, both directions and hard/equal-power transitions at declared bars.
- `audio_lyrics.captions`: provider seconds to integer-ms P1 word timing;
  unavailable/empty/inferred results are explicit. `whisper_crosscheck` compares
  20 matching tokens without writing their text into reports. Private lyrics
  must remain in ignored private manifests, not repository fixtures.
- `sprite_export.py --engine godot4 --anim-manifest ... --beat-sync analysis.json
  --experimental --out DIR`: retimes exposures, reruns spec-14 motion QA and
  writes an audio-clock scheduler. Variable tempo uses each measured beat;
  bar_position selects downbeats even when BPM is doubled. Runtime timing stays
  untested until measured against the actual audio playback clock.

For input sample rates other than 48k, FFmpeg must include soxr. The supplied
Windows static_ffmpeg lacks it; the exporter reports failure instead of silently
substituting another delivery resampler. The 4x peak limiter uses FFmpeg swr;
independent ebur128 measurement remains the final peak authority.

## Snow-mountain demo

`suno_route.py demo game --scene snow-mountain --sprite-pack PATH --out NEW_DIR
--experimental --inputs selected.json --godot GODOT_EXE` consumes selected final
downloads. The input has `explore`, `battle`, `sheet` entries with `file` and
`provenance`, plus `analysis` (provider beat map), optional `theme_clip_id`.
The raw download receipt retains source SHA, URL-response SHA, credit debit,
timestamp, clip, request and idempotency key. Engine copies share the source
artifact hash; local transformations get new hashes and parent links.

`--offline-rehearsal` replaces `--inputs` only for a synthetic instrument/demo
rehearsal, prominently labeled REHEARSAL_NOT_LIVE. It is not a Suno deliverable
and cannot pass the live provenance gate. The game uses existing original
spec-14 SpriteFrames, an audio clock, a bar switch, a cue and attack events.
If a real audio clock advances but exceeds tolerance, status is failed, not
untested. Windows certificate-store errors are preserved as environmental
diagnostics; audio/resource/script errors block engine acceptance.

No live release is certified by this implementation alone. See the current
[build evidence](../wow/fx/build-notes-s15.md) for actual passed/blocked checks.
