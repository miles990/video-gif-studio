# Motion direction

Use a single coherent motion objective. For each beat record start state, movement, contact/support change, end state, approximate source time, and what should remain invariant. Duration follows the action and medium; neither eight nor twelve seconds is a universal default.

## Prompt structure

Author the actual prompt yourself; replace these fields with photographable facts:

- Subject, appearance and identity role of each actual input.
- One shot or justified shot sequence, framing and perspective.
- Ordered actions with visible travel paths and clear support transitions.
- Ordinary real-time performance if requested. Avoid conflicting combinations such as "normal speed" plus repeated "slow, languid, softly drift".
- Secondary motion caused by the primary action, with plausible follow-through.
- Constant light/background if intended for keying; keep full required silhouette inside a safe margin.
- Intended final state and loop boundary. A requested matching pose is an intention until verified.

Timing ranges are direction, not frame-accurate provider guarantees. Inspect what was actually generated before editing. In the founding example, 12 seconds plus repeated relaxed/soft settling language produced a slow leg switch; this is case evidence, not a normal-human timing standard.

## Articulation and perspective

For human subjects, inspect stable skeletal proportions and plausible joint axes/ranges across transitions, not just attractive endpoint poses. Muscle and soft-tissue tension/compression should follow flexion, extension, load and contact; clothing may hide those changes but must not replace them with arbitrary swelling. Maintain perspective, foreshortening, near/far limb identity and occlusion across the shot. Apply the same structural reasoning to stylized/pixel humans unless the user explicitly asks for departures from it. This is visual plausibility review, not a claim of biomechanical simulation.

Follow proximal-to-distal joint chains and account for occluded limbs. Feet, hands and limbs must travel continuously, clear obstacles and make contact before accepting load. Soft tissue and cloth follow joint movement and contact rather than arbitrary shape morphing. Static frame correctness alone does not prove continuity.

Camera height/pitch, lens impression and perspective should achieve the composition. Do not stretch legs independently to simulate flattering photography. Separate actual camera translation from body sway or swivel rotation. Keep a naturally rotating chair when it matches the intended action; fix a planted base only when requested or clearly necessary, and validate occlusion if compositing.

## Retiming

First identify where the user feels the speed is wrong. Adjust motion phases for slow motion, pauses for long holds, or regenerate incomplete paths. Use a smooth transition back to 1×. Preserve every source index in lineage even when temporal sampling must drop frames for GIF centisecond constraints. Speeding 24 fps motion excessively reduces motion sampling; review at delivery size and speed.

Do not assume that faster means more human. The pass condition is observed readable movement with convincing contact and pacing, judged against the brief and user feedback.

## Effects and causal review

When the user requests effects without specifying their design/source, Grok owns both effect design and generation in the video. Prompt the action and cause, not an unsolicited fixed palette or stock crescent/star pattern. Limit effect colors only as needed for key separation. Preserve user-specified spectacle or style while checking that the effect follows the actual movement, releases at a justified event and dissipates during recovery. A free-standing swing has no invisible target to justify a target-hit reaction; distinguish an intentional stylized energy release from physical contact.

Inspect anticipation → physical movement → release/contact → follow-through → recovery in order. For an overhead chop, the hand and rigid blade must actually descend into a low follow-through; a descending light trail around a stationary raised sword fails. Check grip continuity, weight support, secondary-motion delay and weapon visibility. Retiming cannot repair missing paths or mismatched causes.

Use impact holds only when justified by contact or the requested stylized combat feel. Select the actual event frame after reviewing the video, not the prompt's nominal timestamp. The existing phase interface can lengthen one source-frame interval: at 24 fps, `{ "start": 1.0, "end": 1.0416666667, "speed": 0.5, "ramp": 0 }` makes that interval approximately 80 ms after GIF rounding. Confirm the selected source frame and output duration in the manifest; do not apply a universal hold length.

## Seamless-loop acceptance

Plan recovery and effect dissipation before generation. At the chosen boundary compare feet/support, root location, body proportions, joint pose, weapon angle/grip, face, hair, cloth silhouette, perspective, light/palette, remaining particles and motion direction/speed. Watch multiple repeats at delivery speed; also inspect the last several and first several decoded frames together on light/dark backgrounds. Identical first/last images alone cannot establish velocity continuity.

Do not close a missing recovery with reversed attacks, ping-pong playback, a cut, crossfade, forced limb warping or a duplicated endpoint. A prompt requesting a loop and GIF `loop=0` prove no visual closure. Keep encoding integrity, anatomy/causality review and loop acceptance separate. State `not assessed` if playback review was unavailable. If a requested seamless loop still visibly jumps after the bounded correction, deliver only an explicitly unfinished preview and identify the residual mismatch; do not mark the requested work complete.
