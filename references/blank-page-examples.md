# examples

Adapted from blank-page by Blake Shao / Stewdio, MIT. Copyright (c) 2026 Cekura, Inc. Full licence: [THIRD_PARTY](../THIRD_PARTY.md).

This is the complete absorbed authoring method, vocabulary and evidence, not a claim that our deterministic skeleton invents creative text. Calling agents apply it before `brief.py --content`. Original session examples are instructional examples, not our benchmark outcomes. Source script commands describe capabilities ported into `brief_refs.ReferenceFinder`; use the adapter contract in [brief](brief.md), not the original unbounded downloader. No network is implicit. User footage, taste and reference statistics precede these web-search steps. Runtime data belongs in `.scratch/`.

# Before / after — 改寫自 blank-page references/examples.md §Before / after（MIT）

Each "before" is a real prompt from the corpus with the corrections it needed. The
"after" is what the expansion should have produced from the first draft plus the
conversation. One example per lesson; the voice stays the author's.

## 1. Medium unstated (four rounds) — 改寫自 blank-page references/examples.md §1. Medium unstated (four rounds)（MIT）

Before (2026-10-21): `in the current vgs-fx project, file-a, create a realistic eye blinking in front of a klein blue background, everything is in resolgraph texture`

Follow-ups: `make the eye an illustrator vector animation` / `actually revert back to the real eye` / `around the eye, add china porcelain vase's organic yet geometric patterns in white <img>` / `give the pattern a boil effect and have it grow out organically in the beginning` / `have the camera start zoomed out by 1x then a steep quadratic ease-out zoom in that is 2s long`.

After:

```
in the current vgs-fx project, file-a, create the following, everything in riso (3-ink halftone, grain, slight misregistration):

1. a realistic eye (photo/footage based, not vector) centered on a klein blue #002FA7 field, blinking naturally [? 2 blinks over the comp]
2. around the eye, white porcelain-vase patterns <img: shape + motif only, not the colour>; the ring around the iris turns clockwise, the field outside it counter-clockwise; the whole pattern boils slightly and grows out bottom-up from 0s
3. camera starts 1x, steep quadratic ease-out zoom in over the first 2s

1:1, ~5s [?], no fade, no border
expose params for zoom end, pattern growth speed, blink timing
```

## 2. Magnitude without a phase or reference point (four rounds) — 改寫自 blank-page references/examples.md §2. Magnitude without a phase or reference point (four rounds)（MIT）

Before (2026-10-08): `make the orb's entrance velocity 5x faster,`

Follow-ups: `the orb is slower despite me specifying it to be faster` / `have the ball keep a constant speed when rolling and add more bounce, lastly 1s, zoom in onto the orb and track it` / `keep the old entrance speed, i am saying it should have a fast constant speed afterwards, also, the zoom should happen at 1.2s exactly` / `no like the fastest entrance speed we have had`.

After:

```
1. entrance: use the fastest entrance speed we have had so far (the v3 one), keep it
2. after landing: constant roll speed, no decel, 1.5x the current; more bounce height
3. at 1.2s exactly: zoom in onto the orb and track it, camera moves with the orb but does not turn
keep the splash and the structure as they are
```

## 3. Mechanism described by adjective — 改寫自 blank-page references/examples.md §3. Mechanism described by adjective（MIT）

Before (2026-10-05): `make 23 more editorial, like a new image with white border with either a side or a corner being draged to reveal the new stuff`

Follow-ups: `still incorrect, the drag is not a slide in, rather it is dragging from a corner of the frame to reveal the new thing` / `make the border a lot thinner and make them come in from random corner and sides`.

After:

```
for 23: the new image is already underneath, full frame; the current image is peeled away from a random corner or side (varies per transition) like a page being dragged off, revealing the new one beneath. not a slide-in. thin white border on each image, no guiding lines, no scale on the image, no fade
```

## 4. Adding to an existing comp without the style lock — 改寫自 blank-page references/examples.md §4. Adding to an existing comp without the style lock（MIT）

Before (2026-10-21): `in riso-tunnel in file-a, add a series of square decoration frames in the style of the pattern in riso-blink, have them twist and turn within the tunnel`

Follow-ups: `it should be purely white, and its better to reference the outer portion of the first comp, also, have the frames form a proper tunnel it self, the tunnel only twists in rotation` / `they still need to be individual frames rather than a literal tunnel ... it doesn't have to literally contain a square`.

After:

```
in riso-tunnel in file-a, add a series of individual decorative frames in the white porcelain pattern from the outer field of riso-blink (not the ring):
- purely white, still riso
- each frame is its own flat shape, roughly square but it need not contain a literal square
- the frames line up along the tunnel axis so together they read as a tunnel; they only rotate about that axis as the camera passes, no other motion
keep the existing colour tunnel and camera as they are
```

## 5. Two animated quantities (good as written; expansion only adds numbers) — 改寫自 blank-page references/examples.md §5. Two animated quantities (good as written; expansion only adds numbers)（MIT）

Before (2026-10-13): `ok the entrance animation should work as the following, two params are animated: size and fullness / they should have roughly similar easing but fullness finish later`

After:

```
entrance animates two params: size and fullness. both ease-out, similar curve; size lands at ~0.3s, fullness keeps going and lands at ~0.8s [?]. the balloon pops in at ~70% fullness and finishes inflating after. jiggle starts right at the pop-in, only as a result of the impact, no delay
keep my plumpness and texture param edits
```

## 6. Batch without a dedupe rule — 改寫自 blank-page references/examples.md §6. Batch without a dedupe rule（MIT）

Before (2026-10-05): `in the current project's carousel project, create the following 25 variations based on the existing comps / keep the new comps tight, around 5-7s / for all of them use white bg and 3 place holder images @a.jpg @b.jpg @c.jpg`

Follow-ups: `the variations doesn't have to be 1-to-1, just create new ideas based on the existing ones` / `no need to do backward directions, they are not a valid variation` / `mirror are not valid either` / `rename everything in the following format (Carousel: [5 word max description])`.

After:

```
in the current project's carousel project, create 25 new carousel comps as variations of the existing ones:
- not 1-to-1: a valid variation changes the mechanic, orientation, layout or treatment; reversing direction or mirroring is not a variation
- stay within the current sensibilities (flat, white bg, no fade, no drop shadow, no rounded corners, no UI chrome)
- each ~5-7s, white bg, the same 3 placeholder images @a.jpg @b.jpg @c.jpg
- expose expressive params for each
- name them "Carousel: [5 word max description]"
```

## 7. Image feedback (stays short, gains a pointer) — 改寫自 blank-page references/examples.md §7. Image feedback (stays short, gains a pointer)（MIT）

Before: a pasted contact sheet + `make the splash's top brim a lot bigger and the background color in this <img> and background texture in this <img>`

After:

```
frame 3-4 (the splash peak): make the top brim ~2x bigger and more irregular
background: colour from <img a> (palette only), texture from <img b> (texture only)
keep the orb and camera as they are
```

## 8. Sequence beat mid-timeline — 改寫自 blank-page references/examples.md §8. Sequence beat mid-timeline（MIT）

Before (2026-10-26): `in vgs-fx file-b, create the following on main comp / at 3.5s mark, have many small jack-o-latern version of clawd <img> crawl from the bottom of the screen up all over the skeleton covering it, / then, they crawl down and back to exit, leaving one bone dropping on the ground`

Follow-ups: `make clawd still look like clawd except for the pumpkin texture` / `still make the eyes glow`.

After:

```
in vgs-fx file-b, main comp, at 3.5s:
1. many small clawds (the clawd silhouette as-is <img>, pumpkin texture + glowing eyes, same 16bit quantisation as the scene) crawl in from the bottom edge and up over the skeleton until it is covered [? ~1.5s]
2. they crawl back down and exit the bottom edge, leaving one bone that drops to the ground and stays
keep the sigil, skeleton dance and flames as they are; the beat ends by [? 7s] so the inventory scene can start
```

## 9. Bare brief: the first skill version versus the opener shape — 改寫自 blank-page references/examples.md §9. Bare brief: the first skill version versus the opener shape（MIT）

Before (2026-11-02 test set): `in vgs-fx file-d, make a video of our issue tracker app where the tasks show up nicely`

What the first skill version produced: a dark linear-style list, "rows stagger in top-down 60ms apart, each rises 8px with opacity 0→1 over 400ms", a 20° tilt, "no fade, no drop shadow", "check sub-pixel smooth at pixelRatio 0.4–2", fill-ins about duration and loop. The unassisted agent built the same thing. Nothing in it was a decision.

After (references chosen first; the motion ref is a stop-motion paper gif from mo-graph, the visual ref a tile from the Printed Matter channel):

```
the brief says "our issue tracker app" and nothing is attached: attach a screenshot of the real issues list, or it gets rebuilt from u1 below.

in the current vgs-fx project, file-d, create the following, in the look of printed matter (riso-ish ink on uncoated stock, two spot colours, visible grain), the ui rebuilt as paper:

1. an empty issues list on a sheet of paper, camera top-down. each task slides in from the right edge as its own paper slip and lands with a stop-motion snap, one after another like m1, the stack getting thicker as they land
2. at ~2.5s a hand (real footage cutout, c1) reaches in and ticks the top three with a marker; each tick is one stroke, the slip turns from the dark ink to the accent ink as it is done
3. the camera pulls up and out to reveal the sheet is one of dozens pinned on a wall, every sheet filling with slips at its own pace
4. hold on the wall, slips still landing

it should look physically printed, not a flat vector of paper; very snappy, stop-motion timing throughout, no eases
white paper on a [? cork / grey] wall; ~7s
expose params for slip count, tick timing, the two ink colours

refs:
- a1 .scratch/brief-refs/tracker/a1.jpg: look, the whole piece's finish: riso ink on uncoated stock, sets beat 1's frame (are.na/block/<id>, channel printed-matter-<slug>)
- a2 .scratch/brief-refs/tracker/a2.jpg: palette, the two spot inks (dark + accent), used everywhere (same channel)
- a3 .scratch/brief-refs/tracker/a3.jpg: material, the slip paper's grain and torn edge, beats 1-2 (same channel)
- a4 .scratch/brief-refs/tracker/a4.jpg: composition, the pinned wall grid of beat 3 (same channel)
- a5 .scratch/brief-refs/tracker/a5.jpg: detail, the marker tick stroke of beat 2 (same channel)
- m1 .scratch/brief-refs/tracker/m1.gif: motion, beat 1: the slide-in and snap landing, the stack thickening, 0.0-2.0s at 1.2x slower, subject swapped (are.na/block/<id>, channel mo-graph-1uxjlkjqqhc)
- m2 .scratch/brief-refs/tracker/m2.mp4: motion, beat 2: one-stroke tick with the colour flip on completion (are.na/block/<id>, channel motion-inspo-tfrw-gidqfw)
- m3 .scratch/brief-refs/tracker/m3.gif: motion, beat 3 (the turn): the pull-up-and-out to a wall of many, its ease-out and hold (are.na/block/<id>, channel design-moving-l9-xt3sxtne)
- u1 [? screenshot of the real issues list]: ui, layout and the row anatomy one-to-one
- c1 .scratch/brief-refs/tracker/c1.mp4: copy, the hand and marker, footage cutout (pexels.com/<id>)
assets: none beyond c1
```

Fill-ins: printed matter was chosen over the safe dark-UI look because it makes "tasks show up" physical; runner-up was the Baroque User Interface channel. The pull-out wall reveal is the turn; drop it if the piece must stay a single screen. The hand is footage, not drawn, so it reads as real.

## 10. Missing motion + art direction + asset (found, vetted, structured) — 改寫自 blank-page references/examples.md §10. Missing motion + art direction + asset (found, vetted, structured)（MIT）

Before (2026-10-26): `in the stewdio file-b, for the main comp, do the following at 7s: / have a inventory/equipment interface move in like stone blocks <img> / the inventory interface is that for a macbook, the controller keep adding stickers onto the laptop, the stickers eventually overflow the inventory screen and the computer is completely covered in stickers / also, be sure to include this memey artifact as part of the overwhelming equiping <makerworld url> / the whole sequence should be around 3-4s`

Eight follow-ups, every one about how stickers land and how dense the cover gets (`the cursor adding the stickers way too quickly`, `don't make it the spiral, make it more randomized`, `upon adding a sticker can you give an impact ... slight screen shake, on the first few`, `cover the laptop's keyboards with more stickers too`). That is what a motion ref and an art-direction ref supply.

Search (run 2026-11-02): are.na `sticker bomb` / `stickers stop motion`, Pinterest `laptop covered in stickers sticker bomb macbook` / `stickers slapping on animation stop motion gif`. Kept one photo of a real sticker-bombed MacBook. Rejected a printed laptop skin, a "sticker" gif that was vinyl records, a dead pin, an unrelated cartoon gif. No moving reference passed. The stone-block image is a still, so it is art direction, not motion. The laptop is a product with a lid that must close, so it is a Sketchfab asset, not procedural geometry.

After:

```
in vgs-fx file-b, main comp, at 7s, ~3.5s total:

1. an inventory/equipment interface slides in as stone blocks (a1), ~0.5s
2. the inventory is for a macbook: laptop open by default, then closes; a highlighted cursor adds stickers to the lid one at a time, each landing exactly under the cursor with a hit impact (slight screen shake on the first ~4)
3. the cursor accelerates until it is a blur with light trails; stickers land at random positions and rotations, overlapping like a2 (no spiral, no pattern), spilling past the laptop and the inventory frame until the whole screen is covered, lid, keyboard and all
4. the claude hold lid stopper (c1) lands among them, closely modelled

stickers: ai startups, y combinator, a16z [? exact list]
same 16bit quantisation and palette as the rest of the comp
keep everything before 7s as is

refs:
- a1 .context/attachments/<id>/image.png: art direction, stone-block material + chunky entrance only
- a2 .scratch/brief-refs/stickerbomb/a2.jpg: art direction, density, random overlap and white die-cut borders only, not the brands or the pink laptop (pinterest.com/pin/749990144179145089)
- c1 makerworld.com/en/models/2924138: copy, the lid stopper object, closely
assets:
- sketchfab.com/3d-models/efab224280fd4c3993c808107f7c0b38 (Macbook Pro 13 2020, timblewee, CC-BY, 77k faces, rotating hinge animation): the laptop, one-to-one, lid hinge drives the open → close, quantised to 16bit on top [? download]
- [? startup logos as svg from each brand's own site]
```

Fill-ins: the sticker list; the logo assets and the model download; no motion ref passed vetting, so the slap is described in words. Drop a sticker-slap clip in if you have one.
