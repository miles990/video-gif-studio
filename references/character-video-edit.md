# Character replacement: source motion, complete audio and review

Use this workflow for “same video/music, different character.” Separate appearance refs (face/hair, exact costume, proportions, details) from the original camera/action/effects reference. Save ordered reference roles and hashes. If replacing a previous candidate, record that lineage explicitly: another generation can accumulate drift.

## Route and shot plan

Reference-to-video is interpretation, not exact camera reconstruction. Direct video editing can preserve more timing, but is not a 1:1 guarantee. White-model/depth footage is a guide, not final appearance or proof of control. The bundled fal Python client remains H3-only; the footwear-shot-director console separately implements Kling O3 editing. Never silently route an edit request into image-to-video.

Build each shot from independent modules: source frame range; camera height/angle/framing/path; action phases (anticipation, travel, contact, recovery); effect event; speed ramp; appearance locks; audio policy; acceptance evidence. Preserve all unedited modules. Do not turn one still prompt into many conflicting simultaneous camera commands.

Prefer shot boundaries for generation. Long multi-cut edits can replace only the opening actor. Use overlapping source ranges when a duration limit requires splitting; inspect both motion phases before choosing the join. Global timeline frames and candidate-local frames are different indexes. First generate one diagnostic shot, then one focused correction; after that reassess route/segmentation rather than blind paid retries.

Queue completion is not media success: fetch and validate the result, which may still be a billing/error response. Persist a reservation before POST and the returned request ID immediately. Resume that request; never resubmit an unknown network outcome. Keep keys, source bytes and signed URLs out of shared provenance.

## Deterministic assembly

`scripts/assemble_edit.py` uses only local FFmpeg/ffprobe; no provider call or generation charge. Requires CFR source video. It assembles a full source-length candidate, rejects missing frames, restores explicitly bounded source regions, then muxes complete original audio independently. MP4 is opaque.

```json
{
  "version": 1,
  "source": "original.mp4",
  "fps": "30/1",
  "frames": 450,
  "allow_fps_conform": false,
  "segments": [
    {"path": "part-a.mp4", "start_frame": 0, "frames": 300, "timeline_start": 0},
    {"path": "part-b.mp4", "start_frame": 30, "frames": 150, "timeline_start": 300}
  ],
  "restore_regions": [
    {"x": 380, "y": 60, "width": 280, "height": 240, "start_frame": 0, "end_frame": 390}
  ]
}
```

Paths resolve relative to the manifest. Region coordinates are examples; inspect the actual original. Region frame bounds are start-inclusive, end-exclusive on the output timeline. Restore only while an inset actually exists; otherwise old character fragments can be pasted over the new actor. Rectangles require even coordinates/sizes for YUV420. No tracking or automatic mask inference is claimed.

```bash
python scripts/assemble_edit.py edit.json candidate.mp4
```

The target must be new. `start_frame` indexes the candidate after explicit FPS conform; differing frame rates are rejected unless `allow_fps_conform` is true. Conforming duplicates/drops frames and is reported; it is not exact motion preservation. No automatic stretch, freeze or padding hides provider underflow. The tool retains source/segment hashes, manifest, frame count, stream-copy audio hashes, and pending semantic/human review in `candidate.verification.json`.

Audio must be muxed **after** finite visual assembly. Do not use `-frames:v`, `-t` or `-shortest` in that final mux: these can drop final audio packets. Audio/container duration may legitimately exceed video duration. Verify each encoded audio stream, not whole-file hashes. Codec/container incompatibility fails; do not silently transcode when exact audio retention was requested.

## Whole-film acceptance

Inspect normal-speed playback plus enlarged frames around cuts, overlaps, impacts and ending. Contact sheets locate defects but do not establish cadence. Review face, hair, costume/apron/accessories, both arms/legs, support/contact/shadows and body scale. Include tiny distant actors, figures inside lightning, punch trails, reflections and ghost afterimages. Check restored inset disappearance, not only its first frame.

Separate technical export checks, identity/wardrobe, choreography/camera/effects, audible sync, and human approval. Never promote a candidate because its request completed, frame count passed, or the player reached the end. State if listening/full-speed review was unavailable. Keep failed versions and selection reasons locally; publish reusable methods/tests without personal images, videos, credentials or signed links.
