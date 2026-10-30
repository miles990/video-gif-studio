# Builder handoff — measured media QA

Implementation and demonstrations are ready for independent review. **This remains a candidate: S-5's required full-environment regression is unverified.** The requested venv cannot be launched in this sandbox (`WinError 5: Access denied`). No dependencies were installed and no permissions or installed skill files were changed. Tests below used the existing Miniforge Python and imageio FFmpeg 7.1 instead.

## Files changed

- Added [scripts/qa_media.py](../scripts/qa_media.py): GIF/APNG/PNG/video loading, real timestamps, alpha-aware metrics, flash/pop/freeze/cut/loop checks, audio measurements, two reports and three sheets. Existing FFmpeg without ffprobe can supply timing through showinfo.
- Added [tests/test_qa_media.py](../tests/test_qa_media.py): 14 picture/CLI tests plus 3 real FFmpeg audio/video tests.
- Added [references/quality-review.md](../references/quality-review.md) and [THIRD_PARTY.md](../THIRD_PARTY.md); updated [SKILL.md](../SKILL.md), [README.md](../README.md), [README.zh-TW.md](../README.zh-TW.md) and [scripts/doctor.py](../scripts/doctor.py).
- Updated [progress.md](progress.md); added this handoff, [demo/](demo/) reports, images, timing records and verification logs.
- No edits to `wow/acceptance.md`, `examples/`, or `requirements.txt`; no commit, push or publication.

## S-item → evidence

These are builder observations, not independent acceptance scores.

| Item | Implementation / evidence | Status |
|---|---|---|
| S-1 | [qa_media.py](../scripts/qa_media.py); complete outputs for [A](demo/synthetic/A/report.md), [T PNG sequence](demo/synthetic/T/report.md), [GIF](demo/chibi-running-dash/report.md), [APNG](demo/chibi-apng/report.md), [MP4](demo/neon-zen-pv/report.md). Tests assert 360 px phone sheets and hook times <3 s. | Implemented, exercised |
| S-2 | [17 passing tests](demo/tests-qa.txt): B/C/D/A, partial holds, E speed, G patch, H0 black/flat, T hidden RGB/freeze, short hook, repeated encoder frames, F hard cuts, APNG poster/variable delays, timeline holds, M1/M2/M3. Example evidence: [robot](demo/robot-wave/report.md), [seated](demo/seated-leg-switch/report.md), [neon without timeline](demo/neon-no-timeline/report.md). | Builder checks passed; independent review pending |
| S-3 | Both SKILL quality/export sections invoke QA and distinguish measurement from visual/semantic quality; [quality review](../references/quality-review.md) has clean-context, default-reject review and adapted completion checklist. | Implemented |
| S-4 | Source URL, MIT and © 2026 win4r in both READMEs; attribution in both new source/reference file headers; [full MIT license](../THIRD_PARTY.md). | Implemented |
| S-5 | [New tests](demo/tests-qa.txt) all pass; [full alternate-environment run](demo/tests-full-miniforge.txt) and [existing-only comparison](demo/tests-existing-miniforge.json) have identical 16 errors. [Required interpreter launch](demo/verification-times.json) denied. | **Required environment regression blocked; not accepted** |
| S-6 | [doctor output](demo/doctor.json) explicitly reports numpy, PIL, ffmpeg, ffprobe and fallback availability. `git diff main -- requirements.txt` is empty. QA uses stdlib, NumPy, Pillow and existing media_runtime only. | Implemented; doctor correctly exits 1 for missing full runtime in alternate environment |
| S-展示 | [chibi GIF report](demo/chibi-running-dash/report.md) + report.json and three JPGs; [neon MP4 report](demo/neon-zen-pv/report.md) + report.json and three JPGs. Builder viewed chibi contact and neon hook images. | Outputs ready, both <30 s; independent first use pending |

## Results and measured wall times

| Execution | Wall seconds | Outcome |
|---|---:|---|
| Chibi transparent GIF | 2.251 | Exit 0; frame 0, flashes, freeze and loop PASS; localized pop WARNs at f38/1.240 s, f53/1.660 s, f54/1.680 s require visual review |
| Chibi APNG | 2.327 | Exit 0; frame 0 and loop PASS; same advisory pop locations |
| Neon music MP4 + timeline | 10.224 | Exit 0, all PASS; 0 flashes/pops/freezes, −14.1 LUFS, −2.3 dBTP; continuation joins not treated as missing cuts |
| Neon MP4, no timeline | 10.281 | Exit 0, all PASS; no loop check |
| Robot GIF | 2.234 | Exit 1; loop seam FAIL as expected at f144 / 6.040 s |
| Seated GIF | 5.097 | Exit 1; loop seam FAIL as expected at f288 / 9.930 s |
| 17 new tests | 15.994 | All pass, no skips with existing FFmpeg enabled |
| Full alternate-environment discovery | 17.536 | 73 tests, 16 errors, 1 skipped, 0 failures |
| Existing-only comparison | 1.620 | 56 tests, the same 16 errors, 1 skipped, 0 failures |

Measurements use `time.perf_counter()` around subprocess execution, including interpreter startup. Demo records retain exact commands in [run-times.json](demo/run-times.json); test/doctor execution records are in [verification-times.json](demo/verification-times.json). Core picture tests patch the FFmpeg resolver to throw if touched, so B/C/D/A actually run without FFmpeg. Audio tests ran against existing FFmpeg with real AAC MP4 inputs; no mocks substitute for their measurements.

The alternate environment has no OpenCV, so several old test modules cannot import. Its 16 errors cannot be substituted for the answer key's 125-test / 5-error baseline. Existing-only comparison demonstrates no additional failures among tests that could execute here; it does not establish the missing modules pass. Re-run the prescribed command in the authorized venv before acceptance.

## First use

```sh
python scripts/qa_media.py examples/chibi-running-dash/final.gif --out qa/chibi
python scripts/qa_media.py examples/neon-zen-pv/final.mp4 --out qa/neon --timeline examples/neon-zen-pv/timeline.json
python -m unittest discover tests
```

Use new output directories. In this sandbox the successful demo command used `C:\Users\User\miniforge3\python.exe` and `VIDEO_GIF_FFMPEG=C:\Users\User\miniforge3\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`; use the requested venv when access is restored. Numeric PASS does not certify anatomy, natural motion, matting truth, intent or audio/video sync. Full playback/listening and independent review remain with the original review flow.

Acceptance file SHA256 before and after: `21A3F0C43873A83319BB7903166D2508856289B5AC292727A8944A7B93254A1F`.
