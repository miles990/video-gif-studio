# One-liner to a director brief

> Status: experimental (merged trunk-based on 2026-11-06; independent review and held-out acceptance pending).

The director's first step is a brief, before the treatment/storyboard. `scripts/brief.py`
is the accepted standalone mapping for `vgs brief`; this checkout has no unified
`vgs` executable. All commands use the skill Python; scratch data stays in `.scratch/`.
No command calls a paid model. Agent-written creative text enters through `--content`.

```text
python scripts/brief.py --draft "我咖啡店新菜單 10 秒直式，溫暖" --offline --out .scratch/brief.json --json
python scripts/brief.py --draft "sports hype 10s" --content .scratch/authored.json --project .scratch/cafe --music .scratch/beats.json --taste references/taste-user.json --out .scratch/brief.json --json
python scripts/brief.py lint .scratch/brief.json --json
python scripts/brief.py to-storyboard .scratch/brief.json --out .scratch/storyboard.json --json
python scripts/brief.py plan .scratch/storyboard.json --out .scratch/plan --json
python scripts/brief.py render .scratch/storyboard.json --out .scratch/v1 --json
python scripts/brief.py apply .scratch/storyboard.json --draft "第二拍慢一點、保留顏色" --out .scratch/storyboard-v2.json --json
python scripts/brief.py render .scratch/storyboard-v2.json --previous .scratch/v1 --out .scratch/v2 --json
python scripts/brief.py schema --json
```

`schema` maps to `vgs schema brief`, `to-storyboard` to `vgs brief to-storyboard`,
`plan` to `vgs plan`, and `brief_render.diff` to the future `vgs diff`. Commands
return one JSON object; errors return `ok:false,error:{code,location,message,suggestion}`
and exit 2. There is no traceback for expected validation errors.

Batch conversion selects an item with `to-storyboard --variant N`; variants change
mechanism/layout/material, never merely mirror a move. Revision `--previous` accepts
a storyboard file or a version directory; `--project DIR --previous v3` resolves
`DIR/v3/storyboard.json`. Image feedback without `--previous` reads
`DIR/storyboard.json` when it exists. With no explicit `--taste`, the established
`taste_pick.load` user-profile path and environment override are used.

## Authoring method — 改寫自 blank-page SKILL.md §Procedure（MIT）

Read [the absorbed method](blank-page-method.md), [reference method](blank-page-finding-references.md),
[vocabulary](blank-page-vocabulary.md), [templates and examples](blank-page-examples.md),
and [author corpus/failure lessons](blank-page-patterns.md). Every source section
retains its attribution. Those files retain the complete worthwhile method rather
than reducing it to keywords. Numerical advice is class C in `thresholds.json`,
not an external standard. The author corpus statistics are not our measurements.

Classification order: attachment → image feedback; export/rename/QA → housekeeping;
variations → batch; targeted modifications → delta; timeline anchor → sequence;
otherwise brief. Edits skip reference acquisition. Housekeeping describes the exact
operation and never invents an aesthetic. The caller executes export/QA separately.

Agent JSON `--content` can supply aesthetic, fence, subject, turn, pace, camera,
duration, fps, forks, assets, structure and fully authored beats. Beats carry
`id,t_start,t_end,text,is_turn,refs,anchor,mechanism`; cite every ref inline.
The deterministic starting treatment is editable, not a claim of a newly researched
look. Missing reference slots and real subjects remain visible placeholders.

## Grounding/provider contract — 改寫自 blank-page finding-references.md §Order of work（MIT）

Project `shot-cards.json` is a list or `{shots:[...]}` of `{id,path,time,description}`;
use real descriptions and explicit `owned`/`licence` if material is third-party.
Role handles a1–a5 map to look, palette, material, composition, detail; m1–m3 to
main mechanic, turn, exit. `origin_handle:uN` identifies user cards. Additional
scoped copy/UI takes may use c/u handles. `use` says which beat takes what;
`cited_by` must agree with inline text. Reference statistics supply timing, not pixels.

Order: eligible user footage → authored taste/refstat reference slots → vetted local
library → optional provider for gaps only. Local library is a JSON list with
`path,source_url,licence,author,aesthetic_tag,moving,vetted`. A provider implements
`search(role,query,moving)->records`. `CassetteProvider` replays role/query keys.
`ReferenceFinder` exposes channel search, combined fence search, umbrellas,
connections, user channels, Sketchfab metadata, capped download and contact sheets.
Transport is injected as `(operation,url)->dict|bytes` and must bound its own
network timeout; no transport is installed or invoked implicitly. First network
failure trips the circuit breaker. `--offline` never touches the provider.

Channel candidates require agent inspection (`vetted:true`); titles never suffice.
Use the combined endpoint for a fence name/domain, decoded-word channels for its
qualities, and at most three channels per role before host web search restricted
to Pinterest. Motion is not constrained by the aesthetic fence. Primary sites give
brand facts, not browser-scale compositions. Do not scrape Pinterest. An absent
reference stays `[? visual ref]`/`[? motion ref]` with attempted queries.

are.na/Pinterest images are commonly licence-unknown: **read them, never embed them**.
Downloads require URL, licence (unknown is honest), retrieval timestamp, hash, role
and use; at most 30 files and 2 MB per file. `contact_sheet` prints actual frame
timestamps and duration, with 9/16/25 tiles. Model routes prefer an explicitly
supplied Objaverse index, then an authenticated supplied URL, else `[? download]`.
No huge mirror index download or credential handling is implicit. Verify articulated
meshes before promising a moving lid/limb. Assets permit CC0, attributed CC-BY,
or explicitly owned files; SA needs separate review and is blocked at compile,
as are NC/ND/unknown. Credits are emitted separately from references.

## Structure and rendering

The brief's aesthetic/pace/structure and taste choose ASL, CV, shot sizes, transition
family, recipes and moves. Explicit reference ASL/CV wins. Music JSON accepts
`beats_ms,downbeats_ms,drop_ms,sections`; PCM music yields labelled unreviewed RMS
periodicity/4-4 candidates. Authoritative beat maps take precedence over estimates.
Turn starts at the declared drop; other beat edges use downbeats. Each beat covers
one or more shots. Turn shots have maximum perceived strength and hard-cut into
their new composition so centered transition overlap cannot anticipate the drop.
No unavailable mechanic is silently implemented: a warning records the closest
stable camera reveal. The 14 stable recipes and storyboard's named moves are reused.
Recipe camera layers own the movement; no second camera is stacked on top.
Stable visual-only conversion omits recipe SFX because the general SFX router is
still experimental; this decision is recorded in `sound-policy.json`. Supplied
music is retained. Recipe windows stop at their owning shot boundary so direct
plans and incremental shot rendering use the same local accent semantics.

`brief_render` validates provenance before building cards/frames, rejects reference
paths as sources, emits credits, compiles through the existing timeline renderer,
and stores immutable per-shot outputs. Global time is excluded from cache keys;
source, recipe, code, resolution and local action changes invalidate them. Both
neighbors invalidate a boundary transition. Final assembly still encodes a new
delivery; unchanged local PNGs reuse identical hashes. `brief_guard.audit` adds a
decoded pHash/ORB check (including scaled/graded references); uniform fields cannot
establish identity and are explicitly unassessable by that fingerprint alone.

## Revision language — 改寫自 blank-page SKILL.md §Delta / Image feedback（MIT）

Each change has target shot/beat/element, magnitude, absolute axis/sense, phase,
and keep clause. Missing speed magnitude defaults to an explicit `[? 0.8x]` or
`[? 1.25x]`; “make it faster” with no target returns one disambiguation question.
“final pan 3x faster at top speed” preserves endpoints and changes peak-phase easing.
“第二拍慢一點、保留顏色” changes only that beat's shots. Without music, the shot
duration expands. With a music grid, total duration/downbeats remain fixed and
the camera travels less; the revision records that tradeoff. No color fields change.
Image feedback requires contact-sheet `.json` metadata and the original rendered
source. Frame numbers resolve to actual timestamps; luma is measured, never guessed.

Canonical `.md` contains the same fenced prompt plus a hidden serialized JSON
record. Lint verifies visible text against JSON to prevent stale/mismatched proposals.
Exemptions use `{rule,why}` with a meaningful reason; licences, provenance, reference
embedding and schema errors cannot be waived.

## Registered before/after evaluation

`wow/fx/brief-benchmark-registration.json` registers the two-axis protocol and topic
file hash. Two evaluator-held prompts and the required preregistration commit are
pending (this builder was explicitly instructed not to commit). No official
before/after result has been run or claimed. `brief_bench.py register` refuses missing
held-out drafts. `prepare` checks same agent/model/effort/assets/music/platform/
renderer receipts, all topics, >=8 moving pairs and hidden positive/negative controls;
it creates a blind HTML review and separate private key. `score` consumes actual
user answers, reports Wilson intervals and panel agreement, and keeps “未證明更好”
unless technical evidence, controls and user evidence all support the claim.
