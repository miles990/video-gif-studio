# Experimental image integration

`scripts/imagegen.py` maps to `vgs image` (no unified vgs executable exists in
this checkout). All generation requires `--experimental`. CLI results are one
JSON object; failures use `ok:false,error:{code,location,message,suggestion}` and
exit 2. Use the skill Python. Scratch, cache, attempts, and ledgers default to
`.scratch/image-state/`; retain that state for the whole round.

```text
python scripts/imagegen.py generate --experimental --prompt "Mia at the cafe" --aspect 9:16 --size 1080x1920 --out .scratch/image --json
python scripts/imagegen.py probe --out .scratch/probe --json
python scripts/imagegen.py usage --json
```

The default `codex` route runs noninteractive `codex exec`, verifies ChatGPT login,
strips OPENAI_* and CODEX_API_KEY from its child environment, and forces ChatGPT
authentication. `auto` stops on subscription failure. API-key Codex login is refused;
use the explicit paid adapter instead. Native image model selection/reporting,
GIF, masks/markup, SVG, and quality controls are unavailable on this route.
Sizes/aspects/quality are prompt instructions, not native tool parameters.
The November 6 probe evidence is mapped in `image-capabilities.json`; `probe`
exports this recorded table without implying it ran a new live probe.

Paid PNG requests require a reviewed `--prices` table, `--approve-spend` matching
the exact request/endpoint/price fingerprint, and `--max-usd` (default zero).
The calling agent must obtain explicit conversational consent before supplying
the flag. No price is invented. Table shape:
`{version,date,rows:[{model,quality,size,unit_usd}]}`. `estimate` performs no request.
`draft` maps to flare/low and `final` to sunburst/high on the explicit API route;
these are requested models, never falsely reported models. Paid references and
native GIF/SVG/edit are rejected; this build does not verify those live features.

Cache keys hash NFC/whitespace-normalized prompts (case and punctuation retained),
all generation parameters and ordered reference bytes. OS locks deduplicate across
processes. Failed requests are not cached. PNG bytes are verified before the cache
commit marker is written. `--no-cache` forces a fresh attempt. Quota failures retry
at most twice after 5 and 10 seconds; timeouts never automatically retry. Every
dispatch reserves an image against the round's cap (default 60, can be lowered).
Failures/ambiguous requests consume the conservative reservation, preventing retries
from exceeding the cap. Use a single state directory/round ID across processes.

Protocol references: [noninteractive Codex](https://learn.chatgpt.com/docs/non-interactive-mode),
[image generation](https://developers.openai.com/api/docs/guides/image-generation),
[PNG generation endpoint](https://developers.openai.com/api/reference/resources/images/methods/generate).
Delivery lineage marks AI-generated images. C2PA detection reads PNG caBX/JPEG APP11
containers only; signature validity and SynthID are not locally verified.
