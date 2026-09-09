# Built-in Grok connection

This repo includes `scripts/grok_client.py`: it reads the official Grok CLI OAuth session, refreshes it through the CLI when expired, submits I2V requests to xAI, checks job progress and downloads the result. No external project, Python adapter or custom module path is required.

## Website use (no API key or CLI)

Sign in to [Grok Imagine](https://grok.com/imagine), generate the requested video within the account’s available access and limits, and import the downloaded file into the local workflow. This website route does not require the bundled API client. Browser-assisted operation requires an available browser tool and the user’s signed-in session; it is not a bundled browser automation feature. Website login alone does not authenticate the CLI client below. See the [official website availability announcement](https://x.ai/news/grok-imagine-video-1-5).

## Authentication for the bundled client

Install the official Grok CLI through its supported installation method if it is absent. Run `grok login` to complete the interactive sign-in. The bundled client reads OAuth/OIDC records from `~/.grok/auth.json`; it never writes or prints tokens. Expired sessions with refresh information invoke `grok models` once as the official credential refresh broker, with output suppressed. There is no implicit API-key fallback or browser-cookie route.

Run the installed virtual environment's Python:

```sh
.venv/bin/python scripts/doctor.py
.venv/bin/python scripts/grok_video.py --image ./start.png --prompt ./prompt.txt \
  --duration 10 --resolution 720p --out ./generation-01 --submit
.venv/bin/python scripts/grok_video.py --out ./generation-01 --resume
```

`doctor` only checks local OAuth metadata and runtime availability; it does not prove generation entitlement, model availability or remaining quota. Login file structure/model capability may change: diagnose an unsupported format explicitly, never silently substitute credentials. Defaults reflect the proven production model, not guaranteed current limits or prices.

## Job handling

Submit once after authorization; the ledger reserves the attempt before the network request. A returned job ID is persisted immediately. Poll with `--resume` at a measured interval such as 15–30 seconds, with user updates during long waits. Each resume checks once. `downloaded` exits idempotently after verifying the output hash. Failed/cancelled/moderated/rejected/expired jobs are terminal.

If submission has no confirmed response, preserve `submission-unresolved` and reconcile provider state before another generation. HTTP 4xx rejection records its bounded status/code; spending-limit failures never trigger a login loop, route switch or automatic resubmission. After a bounded wait (e.g. 15 minutes), retain the job and report pending rather than submitting another.

A failed download can be resumed using the same job. Download requests never forward the API bearer to the media server. Signed delivery URLs and raw provider error messages are omitted from the job ledger. Usage is stored in provider units without an invented dollar conversion.

## Inputs and validation boundaries

The client implements image-to-video. Without a reference, use the available image generator to create an original start image, inspect it, then animate it. Do not claim this client supports pure text-to-video or multiple uploaded references.

The founding production used the equivalent OAuth REST route; its generated source is preserved in the example. The bundled implementation is tested with mocked authentication, request, status and download responses, and was used for the real [no-reference robot example](../examples/robot-wave-no-reference/README.md). Routine installation/tests do not create a new paid video; live generation remains a separate authorized action.

For optional reference packs and continuation routes, see [chain.md](chain.md). Those workflow options do not add multi-reference/edit/extend support to this CLI.

## Direct API-key mode (no Grok CLI)

Explicitly choose `--auth api-key` to read `XAI_API_KEY` from the environment and call the same bundled REST transport. Do not put the key in command arguments, prompts or job files. An API key uses its associated API account/quota; never silently replace subscription OAuth with API-key billing.

```sh
.venv/bin/python scripts/grok_video.py --auth api-key --image start.png \
  --prompt prompt.txt --duration 6 --resolution 720p --out output/job --submit
.venv/bin/python scripts/grok_video.py --out output/job --resume
```

The job records the authentication mode (never the key). Resume inherits that mode and rejects an explicit mode change. Old ledgers default to OAuth. OAuth login/refresh still uses the official CLI; it is not claimed to be reimplemented. API-key handling is tested with mocked requests, not a new billed live generation.
