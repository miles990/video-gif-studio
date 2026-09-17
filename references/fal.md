# fal.ai / MiniMax H3 Max

Use when the user selects fal.ai or H3 Max. Grok remains the unselected default. The connection is internal: Python standard library HTTPS, no sibling repository, SDK or Grok CLI required. Set `FAL_KEY` in the process environment, or store only the key in `~/.config/video-gif-studio/fal.key` (permissions `600` on macOS/Linux). Environment takes precedence. The optional user-local file is never copied into the repo. Never print keys, search arbitrary credential stores, copy another app's secrets, or commit credentials. Website login does not authenticate this API client. Doctor reports presence only, not valid credentials, credits or entitlement.

## Select an input contract

Verified against fal endpoint schemas on 2026-09-14; recheck before depending on changed capabilities.

- Text: `minimax/h3-max/text-to-video`, prompt only.
- First/last: `minimax/h3-max/image-to-video`, `--image` and/or `--end-image`. Canvas follows the supplied image. Identical endpoints help close a loop but do not prove matching velocity, cloth, contact or light.
- References: `minimax/h3-max/reference-to-video`, repeat `--reference-image`, `--reference-video`, `--reference-audio`. Up to 12 total files; prompt refers to `Image 1`, `Video 1`, `Audio 1` in each list's order. Motion videos and audio are 2–15 seconds each; each modality's combined duration is at most 15 seconds. The CLI validates duration with ffprobe before submitting. Current API says audio may be supplied alone; older guide prose disagrees, so verify audio-only requests against live service before claiming success.
- Do not combine reference lists with pinned first/last frames: the selected endpoints expose different input contracts. Do not treat style/motion references as guaranteed localized editing.

The CLI accepts local files and sends base64 data URIs using fal's documented file-input mechanism. Keep input packs modest; for large files use a separately verified storage upload route rather than inventing URLs. References leave the local machine when submitted. Current wrapper conservatively supports 5–15 seconds; 480P/768P native, 1080P refined from 768P. `balanced` prompt expansion is the speed default; `quality` may spend about 30 seconds rewriting the prompt. Report provider inference and end-to-end time separately. Billing depends on current endpoint, resolution, duration and reference inputs; inspect live pricing and existing authorization before spending. Do not promise promotional prices or free quota.

## Commands

Run with the installed skill interpreter. Output must be a new production directory outside this repo.

```sh
.venv/bin/python scripts/fal_video.py --dry-run --out /path/to/run \
  --prompt /path/to/prompt.txt --image /path/to/neutral.png \
  --end-image /path/to/neutral.png --duration 5

.venv/bin/python scripts/fal_video.py --submit --out /path/to/run \
  --prompt /path/to/prompt.txt --image /path/to/neutral.png \
  --end-image /path/to/neutral.png --duration 5

.venv/bin/python scripts/fal_video.py --resume --out /path/to/run
```

Dry run validates local files without requiring a key or making requests. Submit makes ONE generation request and records its ID. Resume polls ONCE, downloads `source.mp4` when ready, and verifies a previous download by hash. Wait between polls rather than busy looping. Preserve job.json with ordered input roles/hashes, settings, source hash and backend timings. Media URLs and credentials are not persisted. Expanded prompt is not retained because a provider can echo input URLs.

A submission timeout, malformed response or uncertain HTTP failure marks `submission-unresolved` and blocks resubmission. Reconcile the existing ID/dashboard; do not delete the ledger to retry. A download failure can resume the same job. No automatic paid retries. Queue completion is not creative approval; inspect the downloaded stream and actual duration/ratio before export.

## Transparent and reusable output

No native alpha-output contract is exposed in these endpoints. Generate against a separable uniform background, then follow [transparency](transparency.md). Preserve graded alpha in PNG/APNG/sprites and alpha videos; GIF has binary transparency. Never interpret a pictured checkerboard as alpha.

For [animation states](animation-states.md), use a shared base pose for entry/exit references. Generate continuous joint paths; do not use crossfade or reverse playback to hide missing recovery. Cache accepted outputs; missing/changed assets require a deliberate new generation, not a runtime network call on every state change.

Camera Controls and Director are separate provider offerings, not implemented by this wrapper. Director is experimental. Do not claim this CLI supplies streaming, arbitrary camera paths, 3D skeletons, exact physics or automatic seamless loops.

Sources: [I2V](https://fal.ai/models/minimax/h3-max/image-to-video/api), [references](https://fal.ai/models/minimax/h3-max/reference-to-video/api), [T2V](https://fal.ai/models/minimax/h3-max/text-to-video/api), [queue](https://docs.fal.ai/model-apis/model-endpoints/queue).
