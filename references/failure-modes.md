# Diagnose from the same frame

| Symptom | Evidence to inspect | Repair |
| --- | --- | --- |
| Black dots inside skin or fingers | RGBA is intact but decoded GIF alpha has holes | Reserve transparency index, quantize visible colors separately, compare every decoded alpha mask |
| Holes already in RGBA | Compare mask with raw frame and key color | Narrow/adapt key, use temporal segmentation; do not blur artwork to hide it |
| Fringe only on outer silhouette | View alpha/RGB over black and white | Edge-aware despill or matte adjustment; optional outline only if desired stylistically |
| Palette flicker | Stable source RGB but frame palette changes | One global palette; source flicker needs separate correction |
| Pose teleports | Missing travel path exists in source video | Regenerate or animate with appropriate rig; no optical-flow claim of reconstruction |
| Apparent static patch | Check motion source and layer timing | Correct causal timing or missing animation; breathing can legitimately be subtle |
| Body jumps after alignment | Bbox changes as leg extends | Preserve source canvas or track an actual stable landmark |
| Prop motion called drift | Compare rotation, contact and user preference | Preserve accepted motion; do not pin every prop |
| End/start jump | Compare pose, velocity, expression and contacts | Find compatible handles or regenerate loop; don't silently reverse |
| Looks slow at 1× | Prompt/generated timing can itself be slow | Adjust moving phases; 1× is a technical ratio, not human normal speed |
| Only a messaging app shows defect | Decode local file; compare returned/downloaded file hashes if available | Investigate target re-encoding after local invariants pass |

The founding defect was reproduced in a decoded local GIF, so it was not merely a chat application's dark background. The RGBA remained intact. A foreground palette with a dedicated transparent index removed all additional alpha holes across 289 frames. Do not infer that every future black mark has this cause.

Denoising may destroy fingers, eyes and fabric detail. An added 1–2 pixel outline can protect an intended exterior style, but neither addresses a transparency-index collision inside a character. Isolate the stage before choosing a repair.
