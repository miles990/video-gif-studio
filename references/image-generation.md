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

Storyboard and identity commands:

```text
python scripts/imagegen.py refset build --name mia --images pose1.png pose2.png --negative other.png --out .scratch/mia.json --json
python scripts/storyboard.py keyframes storyboard.json --refs .scratch/mia.json --experimental --out .scratch/kf --json
python scripts/animatic.py storyboard.json --keyframes .scratch/kf --out .scratch/animatic
python scripts/imagegen.py refset check --refs .scratch/mia.json --image keyframe.png --json
python scripts/imagegen.py refset review --refs .scratch/mia.json --same yes --comment "user response" --json
```

Every shot prompt includes shot size, composition, light, colour swatch and aesthetic.
`--shots 2 4` upgrades only those shots. Keyframes retain original timing, failed
shots retain labelled cards, and `brief_render` fingerprints the generated pixels.
Aspect fitting uses uniform contain/padding, never stretching or silently cropping
heads. Final short edge is at least 1080; draft at least 720. Palette ΔE2000 and
subject-mask framing metrics are recorded. Opaque images without a supplied subject
mask are framing-unassessed, not automatically declared correct. Human framing,
composition and aesthetic review remain required.

The identity library records up to 16 actual ordered paths/hashes/roles/sources.
The local CLIP cache contains tokenizer/config files, not usable model weights, and
the skill runtime has no torch/transformers. No embedding model is downloaded.
The fallback uses masked HSV Bhattacharyya distance plus ORB Lowe-ratio matches.
Every verdict reruns distinct-pose positive and different-identity negative controls;
failed controls stop assessment. Mixed libraries are refused. A library without
controls can still supply references but cannot claim measured identity consistency.
Failed keyframe identity gets one corrective generation, then a visible
`identity_fail` label. Human review is recorded separately and never auto-approved.
