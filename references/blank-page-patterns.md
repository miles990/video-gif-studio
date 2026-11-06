# patterns

Adapted from blank-page by Blake Shao / Stewdio, MIT. Copyright (c) 2026 Cekura, Inc. Full licence: [THIRD_PARTY](../THIRD_PARTY.md).

This is the complete absorbed authoring method, vocabulary and evidence, not a claim that our deterministic skeleton invents creative text. Calling agents apply it before `brief.py --content`. Original session examples are instructional examples, not our benchmark outcomes. Source script commands describe capabilities ported into `brief_refs.ReferenceFinder`; use the adapter contract in [brief](brief.md), not the original unbounded downloader. No network is implicit. User footage, taste and reference statistics precede these web-search steps. Runtime data belongs in `.scratch/`.

All corpus counts and the 17% correction rate below are the author's historical corpus, not measurements of this project. A reduction here remains unproven.

# Corpus evidence — 改寫自 blank-page references/patterns.md §Corpus evidence（MIT）

38 Claude Code sessions, 2026-09-25 to 2026-11-02, 587 prompts after filtering harness
noise. 31% are a pasted screenshot or contact sheet with no text; the 406 text prompts
have a median length of 14 words. The author iterates in many short turns and uses
images as the main feedback channel.

Share of the 406 text prompts: "make <thing> more / less" delta 35%; a direction word
22%; names an element inside the comp 21%; **correction of a misread 17%**; targets a
numbered comp 14%; camera vocabulary 13%; removal or ban 13%; attaches a file 12%;
easing vocabulary 10%; numbered list 9%; named style or era 9%; keep-clause 7%;
multiplier 6%; timeline anchor 5%; asks to expose params 3%.

The 17% correction rate is the cost the skill removes. Nearly every correction maps to
an empty slot in the checklist.

## Opening briefs — 改寫自 blank-page references/patterns.md §Opening briefs（MIT）

The 29 openers (sessions that start with a "create" of 12+ words) are a different
genre from the deltas, and they decide the result:

| in the opener | openers |
|---|---|
| a concrete attached reference (image, mp4, URL, GLB) | 21 / 29 |
| a settled aesthetic or medium named up front (frutiger aero, 16bit dungeon crawler, riso, embroidery, klein blue, three.js) | 16 / 29 |
| a video or gif as motion reference | 7 / 29 |
| a seconds anchor | 6 / 29 |
| a ms / px / hex / degree value | 3 / 29 |
| a realism demand | 3 / 29 |
| expose params | 1 / 29 |
| a "no fade / no shadow" ban | 0 / 29 |

The idea lives in the reference (`recreate this <mp4>`, `dancing like in <youtube>`,
`in the texture of embroidery <img>`) and the beats chain turns: `a big wave splats
across the screen, turning the entire screen into a new texture`, `the camera zooms
out to reveal that the wave washes the new scene into a chinese shanshui painting`,
`the landscape painting unravels into a single thread which eventually becomes a woven
running silhouette`, `the camera zooms out, reveal all ~100 carousels in grids`. An
opener never picks the safe default look.

The first skill version (2026-11-02, before the rewrite) was extracted from the
deltas and produced spec-shaped briefs: ms staggers, px rises, bans, pixelRatio
checks, "linear style" and "flat vector" defaults, references found after the beats
to match them. In the before/after test the results were indistinguishable from an
unassisted agent, because a capable agent already picks sensible easing; what it
does not do on its own is commit to a look, copy a striking move, use a real asset
and add a turn.

Real openers, all the same skeleton (location, style, numbered beats with inline
refs, globals after the list, params, realism demand):

- `in vgs-fx file-b, in the style of a 16bit dungeon crawler game, create the following:` + three numbered beats, each with a reference.
- `in vgs-fx file-c, create the following: a text animation where each letter is an individual silver balloon with this type of texture <img>, and each of them animate in from by inflating from a deflated state, and animate out by reversing that process, the inflation and deflation should be very snappy, ease-in-out` + `expose params to edit the text and the texture and color of the balloon, and the inflation extent and timing` + `it should be very realistic`.
- `in the current project's carousel project, create the following comps` + five one-liners + `for all of them use white bg and 3 place holder images <three files>`.
- `in the stewdio file-b, for the main comp, do the following at 7s:` (sequence mode: the location line carries the time anchor).

## Deltas that landed in one round — 改寫自 blank-page references/patterns.md §Deltas that landed in one round（MIT）

`for 60, zoom in more by 1.5x` / `make the final pan 3x faster at top speed` / `in 17,
make the squares just rotate 30 degree clock wise to straighten/align` / `at 2.5s have
the camera zoom fast into the pupil, steep quadratic ease-in` / `after the orb forms
make the pause 1.5s shorter before the drop` / `make the balloon 70 inflated popin and
finish inflating after the entrance`.

## Deltas that needed follow-ups — 改寫自 blank-page references/patterns.md §Deltas that needed follow-ups（MIT）

| first attempt | follow-ups | empty slot |
|---|---|---|
| `make the orb's entrance velocity 5x faster` | `the orb is slower despite me specifying it to be faster` / `keep the old entrance speed, i am saying it should have a fast constant speed afterwards` / `no like the fastest entrance speed we have had` | which phase, reference point for the magnitude, keep-clause |
| `17, have things rotate the other way` | `make it clockwise plz` | direction with a sense |
| `the folder one is upside down` (three times) | | orientation as which way is up, in frame terms |
| `make 23 more editorial, like a new image with white border with either a side or a corner being draged` | `still incorrect, the drag is not a slide in, rather it is dragging from a corner of the frame to reveal the new thing` | the mechanism: what moves, from where, revealing what |
| `make the horizontal rolodex's angle smaller` | `still looks very off, everything should have an equal angle` | the invariant, not the symptom |
| `create individual overlays ... like the ones in demo, tutorial-1?` | `no like the decorated texts in the very beginning as hook` | which element of the referenced comp |
| `make it faster` | `make the fall 2x taller and faster` / `make the fall 2x more faster` | multiplier + which quantity |
| `btw these are references` (two turns after the images) | | role on every attachment |
| `it doesn't look like the glb i uploaded exactly, why?` | | asset used as-is, not re-interpreted |

## Correction families (71 turns) — 改寫自 blank-page references/patterns.md §Correction families (71 turns)（MIT）

- **Orientation / sense**: upside down, other way, clockwise, mirror. Say axis + sense + what "up" means.
- **Magnitude**: faster, bigger, more zoomed. Multiplier + phase + reference point (`the fastest we have had`, `the original size`).
- **Which target**: wrong file, comp or element. Location prefix and comp number on every change.
- **Medium**: `i meant rebuild the scene in 3d`, `make the eye an illustrator vector animation` then `actually revert back to the real eye`. Photo / footage / 3D rebuild / vector / shader, up front.
- **Lost state**: `you got rid of all of them` (params), `keep my new tweaks too`. Keep-clause on every edit.
- **Over-literal reads**: `they still need to be individual frames rather than a literal tunnel`, `it doesn't have to literally contain a square`. Describe the composition of parts, not the metaphor alone.
- **Pace**: `there is a slight pause after the dip`, `shouldn't be a pause when the uis appear`. State holds, including "no hold".

## Process guidance worth keeping verbatim — 改寫自 blank-page references/patterns.md §Process guidance worth keeping verbatim（MIT）

- `treat each of them as a contraption and animate their special mechanisms` (not a default draw-in)
- `think of the whole thing as an in-process morph, rather than a complete deconstruction and reconstruction`
- `use some form of shape morph rather than the tracing play you are doing`
- `make the shape of the splash more dramatic and irregular` / `more random and natural and crystal-like` (organic over orderly)
- `it is still not fully one to one to the one in app, can you check the render properly`
- `take your time with everything before` (do not compress the earlier beats)
- `create a copy that tries another approach` (branch, do not overwrite)
- `no need to do backward directions, they are not a valid variation` / `mirror are not valid either`

## How the author used references — 改寫自 blank-page references/patterns.md §How the author used references（MIT）

From 271 attachments across the transcripts and the prompts that cite them:

1. **One reference, one job.** Two qualities from outside means two files: `a tunnel
   of this pattern <jpg> in the color way of the iridescent woman <png>`. No single
   file was ever asked for both motion and look.
2. **Moving media for motion, stills for look.** Every mp4 and gif was cited for a
   mechanic or transition; every still for a subject, palette, texture or detail.
3. **Motion references get the subject swapped.** `recreate this animation, but make
   it nyc subway`; what is kept is named (`only the spiral form factor and the scroll
   animation`), the look is not inherited.
4. **References get scoped to a part.** `the first two patterns in this picture`, `the
   outer portion of the first comp`.
5. **References come out of curated channels.** Both of his video motion refs were
   blocks in his are.na `mo-graph` channel. Search by channel, never by block keyword.
6. **Copies get loyal only after a correction.** `replicate these more loyally`, `it
   doesn't look like the glb i uploaded exactly, why?`. Say the fidelity up front, and
   never re-interpret an uploaded asset.

## Fence failures (2026-11-02) — 改寫自 blank-page references/patterns.md §Fence failures (2026-11-02)（MIT）

Blake names niche aesthetics himself; other users name mainstream ones in plain words
(`clean and minimal, lots of white`, `like stripe's style`, `like claymation`). The
"remarkable, not matching" rule was written for the first case and, applied to the
second, overrode what the user asked for (2026-11-02: minimal → a graphic score,
stripe → the Sessions conference sizzle, claymation → clay.com's marble run; all three
read as misses). So:

The second fix (rerun r3, same day) overshot the other way: the agents screenshotted
the fence (the stripe docs page, five product-UI screenshots) and fenced the motion
too (UI micro-interactions as m1). The builds came out as web pages at browser scale
with a small thing moving on them. Both runs missed for the same reason: the fence
was treated as a place to copy from, not as a query. So:
