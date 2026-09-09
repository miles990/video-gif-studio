# Grok provider route

The founding production used an existing MV Studio `tools/mv-studio/motiongen.py` adapter to call Grok Imagine Video 1.5 through OAuth REST. The installed `grok` CLI acted as authentication broker, not as a video prompt agent. The actual source was one generated character still; the original photo was not uploaded. Do not describe inherited visual resemblance as actual multi-reference input.

Locate the user's available adapter; do not assume a particular checkout or home directory. This skill's wrapper requires its path explicitly and checks its Python function contract. It neither bundles credentials nor reads browser cookies. If unavailable, use an available first-class provider tool or explain the dependency. Do not install plugins, switch billing routes or unofficial session bridges implicitly.

```sh
python3 scripts/grok_video.py --adapter /path/to/motiongen.py \
  --image ./start.png --prompt ./prompt.txt --duration 10 --resolution 720p \
  --out ./generation-01 --submit
python3 scripts/grok_video.py --adapter /path/to/motiongen.py \
  --out ./generation-01 --resume
```

Submit once, retain job ID immediately, then poll with `--resume` at a measured interval (e.g. 15–30s). Keep user-facing updates during long jobs. Each resume checks once; `downloaded` exits idempotently after checking the output hash. Treat failed/cancelled/moderated/expired jobs as terminal. After a bounded wait (e.g. 15 minutes), retain the job and report pending rather than creating another. Never repeat a `submission-unresolved` request without reconciling provider state.

Check live model, duration, image and resolution support before a new generation; defaults are historical, not a promise of current capability or price. Usage returned by the provider is recorded without interpreting unknown units as dollars. Authentication failures and spending-limit failures are distinct. Do not log bearer tokens or signed delivery URLs. Preview/report privacy before publishing artifacts.

Without a reference, create an original start image with the available image generator, inspect it, then use this I2V route. The wrapper does not implement or claim validated text-to-video or multi-reference video input. Other providers may support those modes; inspect their actual API/tool before using them.

Testing the wrapper with fake adapter responses verifies local request/ledger behavior only. New real generations cost time/quota and are not part of routine skill validation unless requested.
