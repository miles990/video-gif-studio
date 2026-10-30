# Media QA: FAIL

D.gif | 100 frames | 4.000 s

Numeric screening is not proof of natural motion, correct semantics, good matting or audio/video sync. Review playback independently.

## PASS — frame0

Visible composition has exposure and contrast
- f0 / 0.000 s

```json
{
  "mean": 134.769775390625,
  "contrast": 45.25231170654297
}
```

## PASS — flashes

Single-frame flash scan

## PASS — pops

Small transient pop scan; inspect in context

## PASS — freeze

Frozen stretches; mark intended pauses with --holds START-END or timeline still segments

```json
{
  "designed_holds": []
}
```

## PASS — cuts

Detected cut candidates (no hard cuts required)

```json
{
  "detected": [],
  "expected_seconds": []
}
```

## PASS — timeline_joins

Continuation/edit boundaries are not required hard cuts; review continuity

## FAIL — loop

Loop position and speed
- f99 / 4.000 s -> f0

```json
{
  "seam": 12.286580085754395,
  "median_step": 0.6903992891311646,
  "seam_ratio": 17.796339421520095,
  "speed_ratio": 0.6187595115735598,
  "position_pass": false,
  "speed_pass": true,
  "speed_applicable": true
}
```

## PASS — loudness

N/A: no audio track

## PASS — true_peak

N/A: no audio track

## PASS — loudest_100ms

N/A: no audio track

## PASS — silence

N/A: no audio track

![contact_sheet](contact_sheet.jpg)
![phone_sheet](phone_sheet.jpg)
![hook_sheet](hook_sheet.jpg)

Analysis and sheets: 0.369 s.
