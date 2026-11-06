# spec-15 builder evidence — experimental, 2026-11-06

The implementation is experimental. **S-178 live acceptance is blocked, not
passed.** No private library was read, no playlist was created/published, and no
download tool was called. All work and evidence stayed in this worktree.

## Slice inventory

| Slice | Implemented | Remaining acceptance limits |
|---|---|---|
| S-170 | Agent request planning, normalized SHA cache, stable retry keys, durable ledger, selection/balance/cap checks, fake transport with all 35 captured input schemas, pending Codex download CLI | Codex guard is explicitly instruction_only; no actual PreToolUse interception. The fake has scriptable responses; it does not emulate every provider model behavior. |
| S-171 | Sample-length/meter, onset phase, highpass click timing, derivative, spectral/chroma distance, tail/head correlation, EBU R128, decoded WAV/OGG gates; bar/preroll repair; RIFF smpl/cue/adtl; real Godot assertions | Ten-live-loop/listening calibration not performed. Missing soxr prevents non-48k delivery conversion on this FFmpeg build. |
| S-172 | Silence sprite split with exact count refusal, DC/trim/fade/normalization, local key estimates/relations, onset event alignment and AnimationLibrary method track; existing six procedural SFX retained | Both live sheet candidates failed provider listening (one phrase / two cues, not five); no local live bytes or jingle-group certification. |
| S-173 | Timing-map adapter, half/double-tempo crosscheck, extension/full-song plans, existing bar fitting with exact video length and drop alternatives | Beat This! absent; no live score/video crosscheck. |
| S-174 | Local BPM/chroma-key estimation, <=4% rubberband guard and remeasurement, explicit key relations, downbeat checks, both-direction hard/equal-power switch tests | Live theme is D minor/108.9 BPM; generated loops are A minor/about 120 BPM. Shared motif not established. |
| S-175 | Exact millisecond word conversion, inferred indexes, empty/unavailable handling, 20-token local timestamp comparison | Live instrumental alignment unavailable; local Whisper absent. No lyrics committed. |
| S-176 | Per-beat integer exposure allocation, accelerando/32-bar/double-time controls, hit anchors, spec-14 motion recheck, SpriteFrames audio-clock driver | Runtime result belongs to the synthetic rehearsal, not live Suno audio. Idle motion QA passed; the reused attack's semantic foot-contact annotation remains unassessed. |
| S-177 | SHA/parent lineage audit, preview/private refusal, download receipt requirements, deferred-settlement account summary | No downloaded live artifacts exist, so live delivery coverage is not established. |
| S-178 | Original Rime snow-mountain scenario, existing original spec-14 sprites, synthetic rehearsal, Godot load/play/30s event evidence, live candidates and ledger | Live pack, independent audio reviewer, >=10-loop calibration and user taste review remain incomplete. |

## Credits and actual provider work

- Initial account read: **8,500 song credits / 67 download credits**.
- Final observed account read: **8,484 / 67**.
- **16 song credits, 0 download credits, 0 download calls**.
- Four successful creation calls returned eight original clips: two exploration,
  two battle, two sound-sheet and two theme candidates.
- One additional sounds request was rejected for description length >500
  characters before generation. Total create submissions: **5**, including that
  rejection. No retry used a different key for an uncertain successful request.
- Suno sound debits settled after the immediate response. The first/last account
  snapshots, rather than overlapping call deltas, determine the honest total.
- Every actual MCP call, parameters, response, clip IDs and observed account
  snapshots are in `.scratch/s15/live/suno-ledger.json` and the live manifest.
  Free reads without a provider timestamp retain sequence order; no invented
  wall-clock timestamp is claimed.

The selected theme candidate measured 29.92s, 108.9 BPM, D minor. Exploration
candidates measured 14.16s/119.9 BPM and 19.16s/120 BPM, both A minor. Battle
candidates measured 17.92s/120.4 BPM and 20.76s/120.2 BPM, both A minor. Raw loop
durations are not integer bars. These are provider measurements, not local QA.
All eight original stream links are in `.scratch/s15/live/README.md`.

Local HTTP access was denied by the execution sandbox (WinError 10013). The
attempt to install optional soxr under scratch failed for that reason. No
alternate path bypassed the network restriction. No paid download was requested
when there was no verified means to retrieve and locally inspect it. The default
Codex downloader remains disabled; the supplied standing authorization does not
magically create a runtime MCP interceptor.

## Instrument and engine evidence

The offline tests cover periodic 4/4 and 7/8 positive controls, OGG decode sample
count, non-bar truncation, chord/phase discontinuity at a bar, seam and internal
clicks (internal event localized within 1ms), fake fades, gain drift and MP3
rejection. Additional scenarios cover bidirectional hard/equal-power switching,
37ms offsets, five-cue slicing with decay, guard boundaries and no-network fake
replay. These are implemented controls, not a claim of independent holdout pass.

Real Godot 4.7.2 imported PCM16 WAV and Vorbis OGG, asserted duration within 1ms,
loop start/end/BPM/bar-beats/beat-count, and played two cycles. The actual import
enum is `edit/loop_mode=2` for forward; runtime LOOP_FORWARD is 1. PCM24 emitted
by this FFmpeg uses an extensible header this Godot importer rejected, so the
delivery encoder uses the accepted PCM16 option. RIFF `smpl.dwEnd` is L−1;
JSON/Godot loop end is L. Independent tests read the RIFF values back.

The Godot sandbox emits a Windows root-certificate-store error. This exact
environment diagnostic is retained and excluded from **audio-related** failure
counting. All script, resource, playback and other warning/error diagnostics
remain failures. An initial scene leaked Vorbis playback references on immediate
quit; cleanup now waits for the audio mixing thread before releasing resources.

## Local evidence paths

- `.scratch/s15/live/`: full actual-call ledger, generation manifest and stream
  candidates. Status **BLOCKED_LIVE_ACCEPTANCE**; no delivered audio.
- `.scratch/s15/rehearsal-final/snow-fox-audio/`: final offline rehearsal, explicitly
  **REHEARSAL_NOT_LIVE**, using synthetic test audio. Contains loop formats,
  five cue files, a SpriteFrames Godot scene and timing evidence.
- `.scratch/s15/godot/engine-check.json`: real two-cycle audio load evidence.
- `.scratch/s15/baseline.json`, `final-full.json`, `focused-final.json`,
  `scenarios.json`, `scenarios-audio.json`: regression summaries.
- `.scratch/s15/doctor.json`: ready local GIF/media runtime; optional audio
  dependencies separately documented above.
- `.scratch/s15/patch-replay.json`: cumulative per-slice replay test evidence.
- `.scratch/commits/01-s15.patch` through `09-s15.patch`, each with matching
  `.txt` commit message. No Git index/branch/commit/push mutation was attempted.

Baseline was 993 tests, zero failures and three errors:
the existing process-memory file-stat race, Windows symlink privilege, and an
existing mask-review PNG cleanup lock. The last is additional to the two
environment errors expected by the task; it was observed before the new audio
implementation was discovered by that baseline run.

The completed first full regression ran **1,017 tests, 0 failures, 2 existing
errors, 4 skips**. The process-memory race did not recur; the remaining errors
were symlink privilege and the pre-existing mask-review PNG cleanup lock.
Scenario regression: **26 tests, 0 failures/errors**. The final targeted suite
includes new scenario and score tests added after that full run; an additional
full run against the final code is retained separately as `final-code-full.json`.

Final rehearsal: Godot 4.7.2 import/load/two-loop checks passed. The 30.0007s
scene switched at a bar, triggered the confirm cue, and recorded two attack
hits **2.045ms and 4.329ms** after their target downbeats (both <=16.7ms).
Scene exit 0, **zero audio/resource/script errors or warnings** after the mixer
retirement fix. The Windows certificate diagnostic remains disclosed. Cached
rerun returned `cache: hit` with unchanged recorded output hashes and no tool
calls. A 20s MP4 preview is labeled synthetic rehearsal on every frame.
The encoded preview independently measured **−14.1 LUFS / −1.5 dBTP**.
The tool-schema fixture contains 35 declarations and no account or library
data; the fake's private-library sentinel is generated at runtime.

Final focused regression: **40 tests, zero failures/errors**, covering every
audio module plus existing music, sprite and engine tests. Nine cumulative
patch-replay stages each passed their slice tests. The route tests also reserve
download authorizations before delayed provider debits settle; five delayed
authorizations block a sixth even while the observed account delta is zero.
No live download was needed to test any budget boundary.

Final full regression (`final-code-full.json`): **1,022 tests in 977.6s, zero
failures, two existing errors, four skips**. Errors: Windows symlink privilege
and the already-observed mask-review PNG cleanup lock. There were **zero new
failures or errors relative to the measured baseline**. Three late fake/ledger
checks and the corresponding ledger settlement fix are additionally covered by
the final 40-test focused run and the final per-slice patch replay. No protected
specification, acceptance, process or threshold file changed.
