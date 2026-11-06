# vocabulary

Adapted from blank-page by Blake Shao / Stewdio, MIT. Copyright (c) 2026 Cekura, Inc. Full licence: [THIRD_PARTY](../THIRD_PARTY.md).

This is the complete absorbed authoring method, vocabulary and evidence, not a claim that our deterministic skeleton invents creative text. Calling agents apply it before `brief.py --content`. Original session examples are instructional examples, not our benchmark outcomes. Source script commands describe capabilities ported into `brief_refs.ReferenceFinder`; use the adapter contract in [brief](brief.md), not the original unbounded downloader. No network is implicit. User footage, taste and reference statistics precede these web-search steps. Runtime data belongs in `.scratch/`.

# Vocabulary — 改寫自 blank-page references/vocabulary.md §Vocabulary（MIT）

Words the author already uses, grouped by slot. Prefer these over synonyms so the
expanded prompt reads as theirs. Every entry appears verbatim in the corpus.

## Easing and pace — 改寫自 blank-page references/vocabulary.md §Easing and pace（MIT）

| word | meaning as used |
|---|---|
| snappy / snappier | short duration, steep ease, no overshoot unless asked |
| smooth / smoother | longer ease, no step, no cut after the move |
| steep quadratic ease-out / ease-in | explicit curve family + steepness |
| sharp ease out | fast start, long tail still moving at the end |
| ease-out decel into a constant speed | entrance then linear travel |
| ease in and out as it moves | symmetric |
| constant speed / fast constant speed afterwards | no decel in the travel phase |
| natural / more natural | physically plausible, no uniform timing |
| overshoot / jiggle chain / jiggle only as a result of the impact | secondary motion tied to a cause |
| hold / pause / no hold / pause 1.5s shorter | explicit dwell time |
| tighter / make everything tighter ~5s | shorter overall, less gap between beats |
| 1.25x faster / 3x faster at top speed / 5x stronger / 1.5x more zoomed in | multiplier, with the phase it applies to |
| at 1.2s exactly / at 6s / ends at 3s / start at 17s | timeline anchor |
| one continuous motion from the start / the camera should be moving the whole time | no stop-and-go |
| real acceleration with motion blur | gravity-like fall |

## Direction and orientation — 改寫自 blank-page references/vocabulary.md §Direction and orientation（MIT）

| word | meaning as used |
|---|---|
| clockwise / counter clockwise / 30 counter clock | rotation sense, degrees |
| upright / no rotation / straighten / align | end pose |
| bottom up / top down / from the left end of the screen to right / upper right | growth or travel direction in frame terms |
| inward / outward / radially outward / radial around rather than point up | field direction |
| horizontal / vertical / diagonal / at 45 degree / 20 degrees from the screen | plane or angle |
| mirrored | transform of a reference ("the other way": avoid, say which) |
| random corner and sides / from all sides of the frame | entry points |
| one direction strictly / each movement to one direction | no back-and-forth |

## Camera — 改寫自 blank-page references/vocabulary.md §Camera（MIT）

| word | meaning as used |
|---|---|
| zoom in / zoom out / 1.5x more zoomed in / camera end zoom param | scale of framing |
| pan fast to the right / fast ease-in into top speed, motion blurred | lateral move with easing |
| track it / move with the orb but not turn | follow without rotation |
| push in / rapid push in / steep ease-in zoom into the green light | dolly into a point |
| bird's eye view / pov / from 45 degrees from a top down angle / 20 degrees off the screen | viewpoint |
| camera stays still, no camera movement yet | lock |
| fits each icon and the orb in that frame | framing constraint |
| perspective sways / perspective shift / sway more dynamic and exaggerated | repeated viewpoint changes |
| hold on the zoomed out view longer | dwell |
| hard cut / no fade / glow-in / cut to | transition type |

## Shape, texture, material — 改寫自 blank-page references/vocabulary.md §Shape, texture, material（MIT）

| word | meaning as used |
|---|---|
| glossy / glass like / crystal / transparent glossy texture like the orb / sheen | material family |
| translucent / glow / soft glow / heavy glow in the center / glow-only | emissive treatment |
| white crisp edges / crisp and clear / ultra smooth | edge and surface quality |
| realistic / very realistic / photoreal / real 3d texture and train models | fidelity demand |
| organic / more organic, less circular / irregular / less uniform square | de-regularise |
| congruent / one continuous body / meshed up / connected at all times | topology constraint |
| riso / riso halftone / 3-ink / misregistration / grain | print look |
| embroidery / cross hatch / strictly vertical and horizontal lines / stitch | textile look |
| pixelation / pixel size / 16bit / low res / less low res | retro quantisation |
| mossy stone texture / worn and weathered / grunge / desaturated | aging |
| frutiger aero / klein blue #002FA7 / cyan / lime green / green on black / white on black / navy on blue / blue and orange like the knicks | named colour ways |

## Composition and layout — 改寫自 blank-page references/vocabulary.md §Composition and layout（MIT）

| word | meaning as used |
|---|---|
| taking up much of the real-estate / take up the entire frame almost | scale in frame |
| center properly / add more white space / more compact | spacing |
| 1:1 / 16:9 / 4:3 / square | aspect |
| borderless, filling the entire frame / thin light grey border | edge treatment |
| water line at the top 1/3 / end at the 1/3 of the screen from the right | rule-of-thirds anchors |
| one word per row / tighter cluster / more sparse / 2x denser | distribution |
| arranged neatly in grids / scattered / random rotation | order vs chaos |
| from the beginning / stays after it grows out, don't fade it | persistence |

## Mechanism verbs — 改寫自 blank-page references/vocabulary.md §Mechanism verbs（MIT）

| verb | example |
|---|---|
| inflate / deflate / plump / 70% inflated pop-in then finish inflating | balloon |
| bump / impact / scale up and down fast to indicate impact / slight screen shake | hit |
| bounce / roll / land on a very bouncy pad and bounce out of frame | ball physics |
| unravel / unfold / stack unfolding / morph / in-process morph | transformation |
| grow out / branches growing in / bleed radially outward / spread like a drop of liquid | reveal field |
| flip / turn / spin / jump up and do a spin | rigid motion |
| drag from a corner to reveal / dissolve / pixel melt / mosaic swap / strip split | carousel transitions |
| crawl / swarm / run cycle / stop motion run cycle / hops | character motion |
| glitch out / flicker / boil | surface disturbance |

## Reference role phrases — 改寫自 blank-page references/vocabulary.md §Reference role phrases（MIT）

| phrase | what it asks for |
|---|---|
| it should look like this <img> | overall look |
| with this type of texture <img> | texture only |
| in the color way of the iridescent woman <img> | palette only |
| use this for computer <usdz> / use this for envelope <glb> | the asset itself, as-is |
| use the same camera as the ref picture but mirrored | camera angle, with a transform |
| similar to this <repo url> / reference this if it is helpful | mechanic or technique, loosely, optional |
| recreate this animation, but make it <subject> | motion with the subject swapped |
| only the spiral form factor, and the scroll animation | a scoped take from a motion ref |
| replicate these more loyally / make it much closer to the og | fidelity bump (say it up front instead) |
| make the arrangement and font visually more like this | layout + type |
| the first two patterns in this picture / the one in the middle / as indicated here | scoped to a part |
| match the timing to the beats of this <mp3> from 17:15s to 30s | audio sync, with a range |
| using <are.na channel> as reference | a family for a batch |

## Scope and bookkeeping — 改寫自 blank-page references/vocabulary.md §Scope and bookkeeping（MIT）

| phrase | use |
|---|---|
| for 23, ... / in 17, ... | target one comp by number |
| across the board / for all of them | every comp in the file |
| keep the rest the same / keep the old X tho / keep my new tweaks too | keep-clause |
| unrelated, ... | different comp inside the same list |
| actually ... / revert, doesn't look right | undo last change |
| create a copy that tries another approach | branch |
| expose params for ... / add a param for X, current value as the center | tunables |
| rename everything in the following format (Prefix: [N word description]) | naming |
| no overlap with ... / not 1-to-1 / backward and mirror are not valid variations | batch dedupe |
| check the render properly / one-to-one with the app | verification |
