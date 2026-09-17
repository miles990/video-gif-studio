# Reusable character animation states

For RTS-like agents, generation builds an asset library; runtime input selects already generated assets. Do not generate on every click. Scope a first draft to a few useful states rather than silently promising an eight-direction library.

Plan a shared contract: character/version, outfit/props, camera orientation/projection, canvas/scale, ground pivot and alpha policy. Record generated identity changes for review; a partial reference photo requires inferred standing/back design. Keep all motion canvases fixed. Do not recenter every frame or cancel intentional travel.

Use entry -> repeatable loop -> exit, with a common neutral pose as a connection hub. Record the actual inspected source intervals, playback durations, safe exit windows and interruptibility. Add bespoke transitions only for frequent pairs. Pose compatibility alone does not guarantee contact/velocity continuity; review repeated playback and cross-clip joins. Transparent sprite crossfades cause double silhouettes and are not the default solution.

For in-place locomotion, engine translation drives world position and playback cadence follows speed. Do not also apply embedded displacement as root motion. Direction changes need compatible facing assets or turning animations; asymmetrical costume/props cannot always be mirrored. Do not claim generated frames contain skeletons, collisions or physically correct root motion.

Suggested states: idle, move, work, await-user, complete. Map them to actual agent events; decorative playback cannot establish task progress. Queue state changes through safe exits unless the requested interaction needs a defined interrupt transition.

Cache key: provider/model/settings, character base hash, ordered reference hashes/roles, exact prompt, camera/action contract, export settings and tooling version. Keep job IDs separate from cache identity. Reuse only verified complete outputs; preserve rejected candidates and don't automatically publish them as examples.

Deliver PNG frames/sheets and metadata for timing, pivot, states/transitions and review status. State runtime/engine integration as untested unless exercised. A browser state preview can be a first proof; it is not a full RTS controller or integration with live agent events.
