# Builder handoff — measured media QA

Status: review 1 READY and its six fixes verified (review 2). Regression with the skill venv after the fixes: **146 tests, the same 2 pre-existing errors as before the change, 0 regressions**; QA tests 21/21.

## Files changed

- Added [scripts/qa_media.py](../scripts/qa_media.py): GIF/APNG/PNG/video loading, real timestamps, alpha-aware metrics, flash/pop/freeze/cut/loop checks, audio measurements, two reports and three sheets. Existing FFmpeg without ffprobe can supply timing through showinfo.
- Added [tests/test_qa_media.py](../tests/test_qa_media.py): 18 picture/CLI tests plus 3 real FFmpeg audio/video tests, including merged-frame cut tolerance, audio applicability and runtime recovery guidance.
- Added [references/quality-review.md](../references/quality-review.md) and [THIRD_PARTY.md](../THIRD_PARTY.md); updated [SKILL.md](../SKILL.md), [README.md](../README.md), [README.zh-TW.md](../README.zh-TW.md) and [scripts/doctor.py](../scripts/doctor.py).
- Updated [progress.md](progress.md); added this handoff, [demo/](demo/) reports, images, timing records and verification logs.
- No edits to `wow/acceptance.md`, `examples/`, or `requirements.txt`; no commit, push or publication.

## S-item → evidence

These are builder observations, not independent acceptance scores.

| Item | Implementation / evidence | Status |
|---|---|---|
| S-1 | [qa_media.py](../scripts/qa_media.py); complete outputs for [A](demo/synthetic/A/report.md), [T PNG sequence](demo/synthetic/T/report.md), [GIF](demo/chibi-running-dash/report.md), [APNG](demo/chibi-apng/report.md), [MP4](demo/neon-zen-pv/report.md). Tests assert 360 px phone sheets and hook times <3 s. | Implemented, exercised |
| S-2 | [21 passing tests](demo/tests-review1-qa.txt): B/C/D/A, partial holds, E speed, G patch, H0 black/flat, T hidden RGB/freeze, short hook, repeated encoder frames, F hard cuts, APNG poster/variable delays, timeline holds, M1/M2/M3. Example evidence: [robot](demo/robot-wave/report.md), [seated](demo/seated-leg-switch/report.md), [neon without timeline](demo/neon-no-timeline/report.md). | Builder checks passed; independent review pending |
| S-3 | Both SKILL quality/export sections invoke QA and distinguish measurement from visual/semantic quality; [quality review](../references/quality-review.md) has clean-context, default-reject review and adapted completion checklist. | Implemented |
| S-4 | Source URL, MIT and © 2026 win4r in both READMEs; attribution in both new source/reference file headers; [full MIT license](../THIRD_PARTY.md). | Implemented |
| S-5 | 21 QA tests pass; full regression in the skill venv: 146 tests, 2 pre-existing errors, 0 regressions | Pass |
| S-6 | [doctor output](demo/doctor.json) explicitly reports numpy, PIL, ffmpeg, ffprobe and fallback availability. `git diff main -- requirements.txt` is empty. QA uses stdlib, NumPy, Pillow and existing media_runtime only. | Implemented; doctor correctly exits 1 for missing full runtime in alternate environment |
| S-展示 | [chibi GIF report](demo/chibi-running-dash/report.md) + report.json and three JPGs; [neon MP4 report](demo/neon-zen-pv/report.md) + report.json and three JPGs. Builder viewed chibi contact and neon hook images. | Outputs ready, both <30 s; independent first use pending |

## Results and measured wall times

| Execution | Wall seconds | Outcome |
|---|---:|---|
| Chibi transparent GIF | 2.252 | Exit 0; WARN |
| Chibi APNG | 2.402 | Exit 0; WARN |
| Neon music MP4 + timeline | 10.397 | Exit 0; PASS |
| Neon MP4, no timeline | 10.561 | Exit 0; PASS |
| Robot GIF | 2.179 | Exit 1; FAIL |
| Seated GIF | 4.799 | Exit 1; FAIL |
| Review 1 QA tests | See test log | 21 tests pass, no skips |
| Prior skill-venv regression | Recorded in progress.md | 142 tests, 2 unchanged pre-existing errors, 0 regressions |
| Review 1 fallback full discovery | See test log | 77 tests, 16 existing errors, 1 skipped, 0 failures |

Measurements use `time.perf_counter()` around subprocess execution, including interpreter startup. Demo records retain exact commands in [run-times.json](demo/run-times.json); historical test/doctor execution records are in [verification-times.json](demo/verification-times.json). Current test logs are linked above. Demo commands used temporary empty output directories; `artifact_directory` records where their outputs were copied for review. Core picture tests patch the FFmpeg resolver to throw if touched, so B/C/D/A actually run without FFmpeg. Audio tests ran against existing FFmpeg with real AAC MP4 inputs; no mocks substitute for their measurements.

The fallback environment lacks OpenCV and cannot run all test modules. Its 16 errors match the previous Miniforge run; they are distinct from the 2 pre-existing errors in the completed skill-venv regression. Current fallback checks do not constitute a new full-venv run of these fixes.

## First use

```sh
python scripts/qa_media.py examples/chibi-running-dash/final.gif --out qa/chibi
python scripts/qa_media.py examples/neon-zen-pv/final.mp4 --out qa/neon --timeline examples/neon-zen-pv/timeline.json
python -m unittest discover tests
```

Use new output directories. In this sandbox the successful demo command used `C:\Users\User\miniforge3\python.exe` and `VIDEO_GIF_FFMPEG=C:\Users\User\miniforge3\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`; the requested venv was inaccessible for this refresh. Numeric PASS does not certify anatomy, natural motion, matting truth, intent or audio/video sync. Full playback/listening and independent review remain with the original review flow.

Acceptance file SHA256 before and after: `21A3F0C43873A83319BB7903166D2508856289B5AC292727A8944A7B93254A1F`.
