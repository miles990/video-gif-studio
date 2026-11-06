# finding-references

Adapted from blank-page by Blake Shao / Stewdio, MIT. Copyright (c) 2026 Cekura, Inc. Full licence: [THIRD_PARTY](../THIRD_PARTY.md).

This is the complete absorbed authoring method, vocabulary and evidence, not a claim that our deterministic skeleton invents creative text. Calling agents apply it before `brief.py --content`. Original session examples are instructional examples, not our benchmark outcomes. Source script commands describe capabilities ported into `brief_refs.ReferenceFinder`; use the adapter contract in [brief](brief.md), not the original unbounded downloader. No network is implicit. User footage, taste and reference statistics precede these web-search steps. Runtime data belongs in `.scratch/`.

# Finding references and assets — 改寫自 blank-page references/finding-references.md §Finding references and assets（MIT）

The roles a reference may play, where to search, and how to vet. `scripts/brief_refs.py`
does the fetching; run it with no arguments for the command list. Output is one JSON
object per line.

## Roles — 改寫自 blank-page references/finding-references.md §Roles（MIT）

Every reference gets exactly one role, a take (what it supplies) and a fidelity word.
A file good for two roles is listed twice with two scoped takes.

| role | supplies | never supplies | media | default fidelity | house phrasing |
|---|---|---|---|---|---|
| **motion** | mechanic, beat order, timing, easing, camera move, transitions | subject, palette, texture | gif / mp4 / multi-state still | mechanic + timing closely, look not at all | `recreate this animation, but make it <subject>` / `only the <form> and the <move>` |
| **art direction** | palette, texture, material, lighting, era, background | shape, layout, motion | still | the named quality only | `in the color way of <img>` / `background texture in this` |
| **copy** | the specific thing to rebuild: artwork, character, object, product, lettering | how it moves | still, model, footage | closely; one-to-one for a named artwork or product | `recreate <name> <img>, loyal to the og` |
| **ui** | layout, component vocabulary, density, type hierarchy, states; interaction timing if moving | brand, logo, real product copy | still; gif / mp4 for interaction | structure closely, brand not at all | `<ui type> layout + components, brand-neutral, no real company` |
| **detail** | one feature inside a larger frame | anything outside the scoped region | still | the scoped part only | `<feature> as indicated here <img>` |
| **family** | the space a batch is drawn from | a copy of any single item | are.na channel, board | loosely across the set | `using <channel> as reference` |
| **technique** | how to build it | look or motion | repo, article | optional | `reference this if it is helpful` |
| **timing** | beat grid, cut points | anything visual | audio | the stated range | `match the timing to the beats of <mp3> from 17.15s to 30s` |

**Assets are not references.** Models, fonts, footage, logos, placeholder photos and
audio go under `assets:` with `use as-is` or `one-to-one`.

Handles use the role letter: m motion, a art direction, u ui, c copy, d detail,
f family, t technique.

## Order of work — 改寫自 blank-page references/finding-references.md §Order of work（MIT）

References come first, before any beat (SKILL.md steps 2-4): five images from one
aesthetic and three moving references, then, for all eight, the beat each feeds and
what is taken. Five tiles from one channel is normal; two channels of the same
aesthetic is fine; two aesthetics is not. For motion the test is "would he add this to
mo-graph?", not "does it show the right object?": a dull move on the right object
loses to a striking move on a different subject. Before falling back on a camera move
written in words, try `channels "camera move"`, `"zoom"`, `"transitions"`.

### The fence: a named style or an attached reference — 改寫自 blank-page references/finding-references.md §The fence: a named style or an attached reference（MIT）

Blake names niche aesthetics himself; other users name mainstream ones in plain words
(`clean and minimal, lots of white`, `like stripe's style`, `like claymation`). Both
past failures (overriding the word, screenshotting it; see `blank-page-patterns.md`) treated the
fence as a place to copy from, not as a query. So:

1. **Decode the word** in one line: what the user pictures when they say it. `minimal,
   lots of white` = big type, one accent, generous margins; `claymation` = stop-motion
   clay, fingerprints, boil, on twos; `like stripe, dark mode` = navy, blurple, fine
   gradient lines, mono code. That line is the fence; it constrains palette, material,
   type and component vocabulary. It does not constrain layout, scale, camera or the
   mechanic.
2. **The word is the are.na query.** Still are.na, still curated, but the style or
   company name is the constraint. Two kinds of query, both needed:
   - **The name itself**, with `search "<style word>"` / `search "<brand domain>"`
     (the combined endpoint; `channels` only matches titles and `stripe` titles are
     fashion stripes). For a style word it returns the channels named for it plus the
     canon (`claymation` → six channels, Aardman, Bickford, Will Vinton). For a brand
     domain it returns the brand's own artefacts (`stripe.com` → the gradient wave
     plates, the letterbox, the dashboard redesign, the gradient codepen): the a1
     *look* tile and the facts, inside the fence by construction. `connections` from
     brand blocks leads to dump channels; skip it for brands, use it for style words.
   - **The decoded visual words**, with `channels "<word>"`: the fence turned into the
     two or three things a curator would collect. Stripe = `gradient` (gradient-airbrush
     273/316, odd-gradient), `glow`, `iridescent`; minimal white = `big type`
     (big-type-container 1477, big-juicy-type), `white space`, `swiss`; claymation =
     `clay`, `stop motion`. These channels hold what is striking *about* the fence and
     supply a2-a5 (palette, material, composition, detail). A product-UI channel
     (`fintech`, `minimal-ui`, `dashboard`) is a `u` source only, never a1-a5: its
     tiles are screenshots and the build will be one too.
   - **Umbrella channels** stay a source inside the fence: `umbrella <slug> "<word>|<decoded
     word>"` finds his nested channels that carry it.
   Sheet two or three per kind, drop the homonyms by eye (`stripe` fashion, `clay-play`
   = clay.com), pick the tile that stops you. If the name query is all homonyms, the
   decoded-word and umbrella channels carry the fence on their own; a channel named for
   the subject (`menu design` for a menu clip) is not a way round it. Remarkable is judged among tiles that
   pass the fence; a tile outside it loses however striking.
3. **The primary site supplies facts, not frames.** For `like <brand>` take the hex,
   the typeface and one real component from the product surface (homepage, docs, app)
   and write them into a1/a2's take. A docs page, a settings screen or a pricing table
   is never a composition reference; the composition ref is a designed frame (a hero,
   a poster, a product-film still, a campaign still in the product palette). Campaign
   and event work is fine for composition and material when its palette is the
   product's; it was the Sessions palette, not its provenance, that missed.
4. **Motion is never fenced.** m1-m3 still come from mo-graph and its nested channels
   and still pass "would he put this in mo-graph?". UI micro-interaction channels are a
   ui source, not an m source. The look is applied to the move, not the move to the
   look; a flat look with a flat move is a screenshot.
5. **An attached reference fixes the look.** It takes the role its phrasing implies (an
   attached still is a1 unless the draft says otherwise), and the other four images
   come from the same look: `connections <block_id>` if it is an are.na block, else the
   channel or site it came from, else `channels "<its aesthetic>"`. Never switch
   aesthetic because another sheet is stronger.
6. **No fence** (the draft says nothing about look, brand or medium): the open rule
   applies, pick for remarkable.

Then, as the beats need them:

- **copy / assets**: the subject is a specific recognisable thing (the user's own app,
  a named painting, product, train car, mascot, logo). Search the source and the
  assets together; for 3D, Sketchfab whenever the object is hard to model
  convincingly in code, even if the draft never mentions a model. If the thing is the
  user's own and nothing is attached, say so above the prompt and name the stand-in.
- **ui**: a beat shows an interface and there is no screenshot or earlier mock.
- **detail**: one beat needs a feature none of the five images show (a motif, a
  pattern for the turn beat).

If a mandatory slot is still empty after are.na, Pinterest and primary sites, write
`[? motion ref]` / `[? visual ref]` into the prompt beside a words-only description and
name the queries tried in the fill-ins. Never pass an unvetted hit to fill a slot.

Skip in delta, image-feedback and housekeeping modes unless the change brings in a new
look or move. Skip roles the user already attached.

## Search order — 改寫自 blank-page references/finding-references.md §Search order（MIT）

Images and motion: **are.na channels → Pinterest → primary sites**. 3D: **Sketchfab
first**. Go to Pinterest only for a role are.na left without a passing candidate; when
both pass, keep the are.na one. Primary sites when both are empty, and always for the
final file of a copy reference.

### are.na: channels, never block keywords — 改寫自 blank-page references/finding-references.md §are.na: channels, never block keywords（MIT）

Block keyword search matches the text of the channels a block sits in, not what it
shows (`peel gif` returned a blob, a leaf, a banana and a lily). The one exception is a
fence word: `search "<style>"` / `search "<brand domain>"` (the combined endpoint) is
how a named style or company is found, see "The fence". The loop, per role:

1. **Seed** from the author's channels (below). Most are umbrellas: open them with
   `umbrella` and work in the nested channel that fits, never the umbrella's own
   mixed blocks.
2. **Widen.** `channels "<query>"` lists channels whose title matches, ranked by
   followers, 20+ blocks. `connections <block_id> [n]` lists the other channels holding
   a good block (12 biggest by default): curators with the same eye, usually the best
   next stop. A query with no hits prints one `"empty": true` line.
3. **Rank.** Prefer titles naming the exact mechanic / aesthetic / ui type, 50-2,000
   blocks, followers as a quality signal. Skip catch-all dumps however large.
4. **Sheet.** `channel <slug> .scratch/brief-refs/<topic>/arena 48 <moving|still> [regex]`
   writes numbered contact sheets (24 tiles each). Read them. Under a third of the
   tiles fitting: drop the channel. The regex filters title / description / source,
   but most blocks are untitled, so the sheet is the real filter.
5. **Pick tiles by number** and vet (below). Note the channel next to the block in
   `refs:` so the user can browse the neighbours.

Stop after three channels per role, then go to Pinterest.

**Motion seeds**, always sheeted with `moving`:
- `mo-graph-1uxjlkjqqhc` (76 blocks, gifs and mp4s; pass the bare slug, `blake-shao/...` 404s)
- its five nested channels: TYPE ANIMATION REFERENCES (`type-animation-references`,
  474), DESIGN // MOVING (`design-moving-l9-xt3sxtne`, 406), Motion Inspo
  (`motion-inspo-tfrw-gidqfw`, 205), AD | Device / Tech (`ad-device-tech`, 182),
  Product video (`product-video-mf4kzs1zbo0`, 22). Type beats → TYPE ANIMATION;
  device or product beats → AD | Device / Tech and Product video.
- widen with `channels "<mechanic> animation"`, `"motion design"`, `"kinetic type"`,
  `"transitions"`, and `connections` from the best mo-graph block (leads to 2D Motion
  GIF, design/motion, Movimento).

**Art direction: the visual reference is the aesthetic.** Do not pick a look in words
and then search for a picture of it; browse the menu of aesthetics, sheet the two or
three that could carry the subject, and let the tile that stops you decide. With a
fence (above), the two or three sheeted are instances of the decoded line. If the
brief names none and the file gives none, the menu is:
- Menu: the nested-channel titles of his umbrellas (`umbrella <slug>`): `vis-4hvdpzvvua4`
  (73 nested, graphic and visual culture: Neo-gothic, Digital Embroidery, ASCII art,
  y2k playstation 3d stuff, Anime Computing, Baroque User Interface, Printed Matter,
  practical sigil magic...), `flat-ovcn8k0nwa0` (13, poster / type / 2D: @swissposters,
  Japanese Graphic Design, Chinese Typography, Pattern, single-designer channels),
  `form-glcjdzmigiq` (15, objects: Pocket Tech, Handheld, Industrial Design, form
  follows fiction), `mercenary` (3, Visual Systems, Design Systems). Smaller umbrellas:
  `yiwqez8yg-e` (Japanese houses), `translucent-skin`, `root-systems-m5flfkrwpe8`,
  `foundry-p8qvueq4coo`. `embroidery-jt4hrowbvw4` (19 blocks; sheet it, its one nested
  channel is Woven Images), `data-geo`, `smart-shamate`, `b48e9jcrcse`,
  `baseball-hat-alphabet` are flat single collections (families).
- Plus his past named styles (riso, frutiger aero, 16-bit, ukiyo-e, porcelain,
  embroidery, klein blue, PS2 low-poly) and CARI's ~240 named-aesthetic channels
  (`user-channels evan-collins-1522646491`: Y2K, Frutiger Aero, Vectorheart,
  Cassette Futurism, Whimsigothic...). Prefer one from his umbrellas.
- Fit it to the subject and the file; never blend two. On a bare draft avoid the safe
  default (flat vector on white, dark "linear style", brushed metal) unless a sheet
  makes it striking; his own openers never pick the safe default. When the user asked
  for that default by name, it is the fence and the job is the best version of it,
  not an escape from it. Put the chosen aesthetic in
  the prompt's first line (`in neo-gothic`) and give the one-line reason plus the
  runner-up aesthetic in the fill-ins.

Then sheet the channel that *is* that aesthetic, `still`: the nested channel from his
umbrella, then the CARI channel of the same name, then `channels "<aesthetic>"`. Pick
five tiles with five jobs (look, palette, material, composition, detail). If the
channel cannot supply five, sheet a second channel of the same aesthetic before
switching aesthetic.

**UI seeds**, ui-specific channels only, brand-neutral take:
- his own: `umbrella mercenary`, and `umbrella vis-4hvdpzvvua4 "interface|computing|apple|fidelity"`
- layout: `channels "ui design"`, `"interface"`, `"dashboard"`, `"<ui type> ui"`. Strong
  ones: `fictional-interface`, `user-interface-superchannel`, `interface-bxtmor_fc40`,
  `ux-ui-inspiration-ygomnyuw37e`
- interaction timing, `moving`: `channels "ui animation"` / `"micro interactions"`,
  e.g. `ui-animation-x1j9nqqkflg`, `digital-ui-micro-interactions`

**Family**: one whole channel, sheeted in full; batch one-liners cite tile numbers.

### Pinterest — 改寫自 blank-page references/finding-references.md §Pinterest（MIT）

Web search restricted to pinterest.com. In Claude Code that is
`WebSearch(query="<role query>", allowed_domains=["pinterest.com"])`; a plain
`site:pinterest.com` query returns nothing there. In Codex or another host, use its web
search with a domain filter if it has one, else `site:pinterest.com`.

Resolve pins with `pin <url> ...`: original media, `moving`, outbound `source` (often
the Dribbble / Behance / Instagram original), `embed` (only a thumbnail of a YouTube /
Vimeo / reel) and `dead`.

### Primary sites — 改寫自 blank-page references/finding-references.md §Primary sites（MIT）

Follow `source` from the block or pin first. Otherwise web search restricted to the right
home: the studio's site, Behance, Vimeo, a museum's open-access collection or Wikimedia
Commons for artworks, the brand's press kit for logos. For
`like <brand>`, the product surface (homepage, docs, app) is read for hex, type and one
real component; the images themselves come from are.na channels named for the brand
(see "The fence"). Screenshots of docs or settings pages are facts, not references.
Dribbble and Behance block scripted fetches (empty 202): cite the original page, take
the file through the block or pin.

| role | are.na channel query | Pinterest / web query |
|---|---|---|
| motion | `<mechanic> animation`, `motion design`, `kinetic type` | `<mechanic> animation gif` |
| art direction | the aesthetic's name | `<aesthetic> <medium>` |
| ui | `<ui type> ui`, `interface`, `ui animation` | `<ui type> ui design` |
| copy | rarely on are.na; go to the source | the exact name + `high resolution` |
| detail | the motif | the feature + context |
| assets | n/a | the thing + format + `free download` / `cc0` |

Assets outside Sketchfab: Poly Haven (CC0, props and textures), the type foundry or
Google Fonts, the brand's own SVG, Wikimedia Commons, unsplash for placeholders,
GitHub code search (`filename:<thing> extension:glb`, check the licence).

## 3D models (Sketchfab) — 改寫自 blank-page references/finding-references.md §3D models (Sketchfab)（MIT）

Use for anything that looks fake when invented in code: anatomy, animals, characters,
vehicles, products with recognisable detail, mechanical assemblies, sculptures,
interiors. The hand-coded brain was "very bad"; a real GLB fixed it. Keep procedural
geometry for orbs, blobs, primitives, extruded logos, lathe objects, noise fields.

Use `ReferenceFinder.sketchfab(query, max_faces)` from `scripts/brief_refs.py`. Select a vetted record, then use `model_route(uid, mirror_paths, authenticated_url)` with an explicitly supplied mirror index or authenticated URL. Missing downloads remain placeholders. Inspect meshes and animation channels with an available local glTF viewer before promising articulated motion.

- **Search broad.** Sketchfab matches every word: `R46 subway car` → 0, `nyc subway
  car` → 24. Object plus one style or era word, then narrow by eye.
- **Downloadable only** (the script already filters). Prefer CC0 / CC-BY and record
  the author; flag NC licences in the fill-ins.
- **Face count fits the use.** A 93k-tri brain was grey mush at 620 px until simplified
  to ~6k. Check `glb_mb` and `tex_max` against the 2 MiB script budget when embedding.
- **Parts must match the motion.** A lid, arm or door that moves must be its own mesh;
  say which parts move in the take, confirm with `inspect` after download.
- **Whole object, not a scan fragment or fan variant.** Pick from the sheet.
- **Download routes**, tried in order by `ReferenceFinder.model_route`: the Objaverse mirror
  (allenai/objaverse on Hugging Face, 2022 snapshot, ~800k models, no login, rigs
  survive; `free_download: true` marks these, so prefer them when candidates are
  close); the Sketchfab API with `SKETCHFAB_TOKEN`; else it prints the page, which goes
  in `assets:` with `[? download]`.
- **Role.** Normally an **asset**, used as-is with styling on top. A **copy** reference
  only when the comp redraws it in another medium. Say which.

## Vetting, every time — 改寫自 blank-page references/finding-references.md §Vetting, every time（MIT）

Matching titles are not references. Pinterest's top `sticker peel animation` pins were
tutorial thumbnails.

1. Download each candidate to `.scratch/brief-refs/<topic>/` with `ReferenceFinder.download`, named
   `<role-letter><n>.<ext>` (`m1.mp4`, `a1.jpg`). `download` fixes the extension to the
   real type (a png served as `.jpg` is saved as `a1.png`); cite the `saved` path.
2. Look at it. Stills: Read the file. Moving: `sheet <file> <out.png>` makes a 3x3
   contact sheet with timestamps and duration; `sheet <file> <out.png> 16` (or 25)
   when the clip is long and a beat's time range has to be read to ~0.3 s.
3. Keep only if the role's quality is visible: motion, the mechanic happens on screen
   as more than a cut or fade and it is not a tutorial; art direction, the palette or
   texture fills most of a 600px+ frame; copy, the real thing, not a remake or
   recolour; ui, a credible interface at a readable size.
4. Five images and three moving references per brief, plus copy / ui / assets as the
   beats need them. Runners-up go in `.scratch/brief-refs/<topic>/notes.md`, not the prompt.
5. Nothing passes: say so in the fill-ins with the query tried, describe the
   mechanism in words, and leave the `[? motion ref]` / `[? visual ref]` marker in
   the prompt. Never pass on an unvetted hit to fill a slot.
6. Prefer the striking tile over the matching tile. When two candidates pass, keep
   the one whose move or look you would want to see regardless of the draft. Passing
   includes the fence: a tile outside a named style or an attachment's look does not
   pass, however striking.
7. A film frame, not a web page (SKILL.md rules): a composition reference that is a
   screenshot at browser scale is a fact for a1's take, not a4.

## Structuring the brief from the references — 改寫自 blank-page references/finding-references.md §Structuring the brief from the references（MIT）

1. **Beats from the motion references.** Read each contact sheet: what enters, the
   main action, each transition, the exit, with times from `frames_at_s`. Assign
   each clip its beat (together they cover the mechanic, the turn and the camera or
   exit; number them m1-m3 in beat order), swap the subject, scale to the target duration and state the ratio (`m1 is 3.4s, ours ~5s,
   so 1.5x slower`). Name the time range taken (`m1 0.0-1.6s`).
2. **First line and surfaces from the five images.** Name the aesthetic in the first
   line. Then place each image on a beat with the exact quality taken: `a3's wet
   stone is the canvas surface from beat 1`, `a5's bead row is the end state of beat
   2`, `a2's palette for the ink only`. Never "like a1".
3. **Subject from the copy reference and assets**, on the beat where it first appears,
   with its fidelity word.
4. **The turn and the ideas**: SKILL.md steps 4-5. If no motion reference has a turn
   beat, add one and find its clip or detail reference.
5. **Detail references inline** on the one beat they affect, scoped.

The `refs:` / `assets:` block follows the brief template in SKILL.md.
