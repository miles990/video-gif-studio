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

## Fix round — 2026-11-07

**EXPERIMENTAL / partial S-178**, built only from the five existing licensed
downloads. No Suno calls, song credits or download credits this round. Branch
`s15-fix` started at `6fb6dbe37a684844a232bc1f8f390af13c160ae4` (`origin/main`).
No specification, acceptance, process or threshold file changed. Six short
regression WAVs are in `tests/fixtures/live-s15/`; each is <=960,078 bytes, with
source/excerpt SHA-256 and sample offsets in the adjacent JSON files.

### Loop making and measured transitions

The provider loop flag is not trusted. A separate local 5ms log-spectral-flux
autocorrelation estimator finds tempo and estimates bar accent phase; searches
consider 2/4/8/16 whole bars when source length permits. Candidate scoring uses
waveform correlation/jump, spectral continuity and head/tail RMS, followed by the
unchanged verifier's actual EBU R128, click, spectrum and phase gates. Cuts use
nearby zero crossings and real incoming preroll, with equal-power crossfades
from 5ms to one beat. There is no fade to silence, padded/repeated substitute or
relaxed verifier threshold. The existing three positive and seven negative
instrument controls remain green. Independent listening remains pending.

Both selected loops are now **two bars / 4.000 seconds / 192,000 samples**,
instead of the old four-bar 8-second cuts. Exploration uses source samples
365,578–557,578 and a 250ms crossfade. Aligned battle uses 408,945–600,945 and a
40ms crossfade; all sample ends here are exclusive. Both cuts fall on zero
crossings within 1ms of their selected/refined bar lines. WAV smpl end=191,999;
JSON/Godot exclusive end=192,000; OGG LOOPSTART=0 / LOOPLENGTH=192,000. Godot
WAV import mode=2; OGG loop=true / loop_offset=0.

| Loop / format | Before xcorr ms | After xcorr ms | Before seam drop LU | After seam drop LU | Head/tail LU | LUFS / dBTP | Result |
|---|---:|---:|---:|---:|---:|---|---|
| explore/wav | 13.604 | 0.625 | 3.60 | 2.25 | 0.00 | -16.0 / -6.1 | PASS |
| explore/ogg | 13.604 | 0.625 | 3.60 | 2.25 | 0.00 | -16.0 / -5.9 | PASS |
| battle/wav | -11.646 | 0.479 | -1.15 | -1.00 | 0.30 | -16.0 / -3.9 | PASS |
| battle/ogg | -11.646 | 0.479 | -1.15 | -1.00 | 0.30 | -16.1 / -3.7 | PASS |

All decoded loop phase errors are 0ms. The before columns are the old delivered
WAV measurements (the historical OGG values differ slightly in loudness; see
the supplied live README). Both formats are independently verified after repair.

| Measurement | Before | After |
|---|---|---|
| Exploration spectral-flux BPM | raw 120.061 | processed 120.011 |
| Battle spectral-flux BPM | raw 120.193 | processed 120.162 |
| Older RMS estimator | old cuts 149.963 / 99.994 | new cuts 76.633 / 118.862; disagreement retained |
| Variant phase error | 36–55ms, 12/12 old tests failed | 1ms; 4/4 tests PASS per encoded format |
| First aligned onset-grid difference | unaligned | 1ms (<=2ms) |
| Switch points | nominal unverified bars | 2,000ms in each repeating 4,000ms cycle |

The measured raw tempos already differ by <0.5 BPM, so these live fixes need no
stretch. The <=±4% stretch guard remains; it is not bypassed. Variant alignment
refines the spectral accent estimate with onset correlation, searches near the
refined grid and re-cuts real source audio. Both directions pass hard cut and
one-beat equal-power transition checks at every declared point in WAV and OGG.
A 37ms shifted negative control fails. The 1ms correlation result is a local
onset-grid estimate, not independent confirmation of musical downbeat labels.

The declared switch phase is 2,000ms in each 4,000ms cycle (one allowed point
every two bars), not every bar. Additional cycle-boundary hard-cut controls fail
the click gate, so wrap switching is explicitly **not verified or enabled**.
The demo now derives its absolute switch from these declared phases: 6 seconds,
not the old hard-coded 8-second wrap. A regression test checks this scheduling
constraint. No verifier threshold was changed to accept the failed wrap control.

### All five cue statuses

| Cue | Locally measured key | Fix-round status | Action |
|---|---|---|---|
| level-up | Am | PASS | Cleanup; no pitch shift needed |
| victory | A major | regenerate_needed | Parallel mode is musically related, but exact requested Am is unmet; pitch shifting cannot change mode |
| confirm | E major | regenerate_needed | Mode conflict; transposition alone cannot make Am |
| failure | unavailable | regenerate_needed | Never delivered; no local audio to measure |
| pickup | unavailable | regenerate_needed | Never delivered; no local audio to measure |

One of five meets the exact requested key. Three audio cues exist; victory and
confirm remain explicitly inspection-only. The sprite contains exactly those
three, reports `INCOMPLETE` / required_count=5, and never fabricates the two missing
cues. Chroma is an estimate and retains confidence margins; the historical
independent victory estimate also disagreed on its root. No unverified key is
reported as measured for missing audio.

Local correction permits at most two semitones with rubberband, preserves mode,
and rechecks the key, duration, loudness, true peak, DC and release. A real
level-up cue detuned +2 semitones to Bm is repaired to Am in the positive control.
All four `regenerate_needed` entries include exact, **unsubmitted** sounds_create
requests in `audio/sfx/cue-status.json` and `s15-fix-evidence.json`. They contain
valid key/tempo/loop/description/title/idempotency_key fields; no unsupported
duration parameter and no paid retry was sent.

### Preview transport and Godot pack

The supplied `preview-fetch-report.json` says encoding `1.0.0`, HTTP 200 and
"moov atom not found; payload has no MP4 header"; anonymous API stream was 401
and legacy URL 403. It includes neither original stream bytes nor a codec or
container identification. Therefore it cannot establish HLS, AAC, fMP4 or Opus.
Live preview decoding stays **BLOCKED_LIVE**, rather than inventing an encoding.
The new analysis fetcher probes real containers and decodes playlists directly
through FFmpeg. Offline generated HLS MPEG-TS/AAC, HLS fMP4/AAC and Opus pass;
unknown provider bytes fail explicitly. Remote protocol whitelists exclude
local files; local fixture whitelists exclude networking. All decoded preview
PCM is analysis-only and cannot enter the provenance-checked delivery pack.

The final pack is `.scratch/s15-fix/pack-verified.zip`; persistent compact evidence
is [s15-fix-evidence.json](s15-fix-evidence.json). Godot 4.7.2 headless import,
loop property/duration assertions and two-cycle playback PASS. The final
30-second scene switches at 6 seconds on a verified bar phase, triggers confirm (still
inspection-only) and records two attack offsets of 6.340 ms, 4.487 ms, both <=16.7ms.
There are zero audio/resource/script errors or warnings. The Windows root
certificate-store diagnostic is retained separately. Provenance is **16/16**
delivered audio files with source SHA/parent lineage. Unity/FMOD/Wwise remain
untested. Source motion, shared motif and independent listening are not newly
certified by this repair round.

Reproduce from an unpacked original pack and its existing downloads:

```text
python scripts/audio_fix_pack.py --original .scratch/s15-fix/original --sources C:\Users\User\src\vgs-fx-private\suno-live\final-sources --out .scratch/s15-fix/new-pack --godot C:\Users\User\src\vgs-fx-private\tools\godot4\Godot_v4.7.2-stable_win64_console.exe --experimental
```

### Validation and patch delivery

- `focused-final`: 42 tests, 0 failures, 0 errors, 0 skips.
- `scenarios`: 30 tests, 0 failures, 0 errors, 0 skips.
- `final-full`: 1061 tests, 0 failures, 2 errors, 6 skips.

Measured baseline: **1,052 tests, 0 failures, 2 existing environment errors,
6 skips** (1,094.691 seconds). The two errors are Windows symlink privilege
(`test_install.InstallTests.test_same_source_symlink_is_preserved`) and the
pre-existing mask-review PNG cleanup lock
(`test_mask_review.Review.test_review_exports_overlay_contact_sheet_and_stability_report`).
All five fix patches passed their cumulative audio tests when applied to a clean
HEAD archive. Replay matched all 22 implementation/fixture files byte-for-byte
after normalizing the fixture JSON line endings to LF.
The final full run was already underway when the additional switch-schedule
regression was added. The final 42-test focused run covers that late integration
fix; the full-run count does not pretend to include the extra test. There are
**zero new failures or errors** relative to the baseline.

Full logs/JSON, generated local HLS test evidence, per-item tests and cumulative
patch replay logs are under `.scratch/s15-fix/`. Each numbered fix patch has a
matching commit-message `.txt` in `.scratch/commits/`. Git history/index was not
modified. Apply in order: 01 loop-maker, 02 variant-alignment, 03 jingle-key,
04 preview-decoder, 05 godot-pack, 06 fix-evidence.
