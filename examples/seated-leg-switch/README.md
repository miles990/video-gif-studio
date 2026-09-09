# Example: Seated Leg-Switch Video to Transparent GIF

**English** | [繁體中文](README.zh-TW.md)

![Final output](final.gif)

This is the actual delivered animation, included as a verified example of **continuous video-to-GIF conversion and transparency handling**. A reference image, model prompt, or encoding check alone cannot establish anatomical correctness or perceived naturalness. The loop endpoints are not completely seamless.

## Actual Assets and Workflow

1. [reference.png](reference.png): The only reference image uploaded to Grok. The character design drew on an earlier photograph, but that original photograph was not uploaded to Grok.
2. [prompt.txt](prompt.txt): The actual English prompt, including the preserve contract appended by the adapter used at the time. The prompt requested a fixed chair base, but the generated video included rotation. The user found that movement natural, so the delivered animation preserves it.
3. [source.mp4](source.mp4): The 12.04-second Grok video at 960×960 and 24 fps. The video stream was copied without re-encoding, and generated audio was removed.
4. All 289 frames were extracted onto the same canvas. The magenta background was removed to produce transparent RGBA frames. No poses were independently redrawn, no optical-flow frames were synthesized, and no fixed chair base was composited into the final version.
5. [timing.json](timing.json): The actual source-frame indices and durations in milliseconds. Leg-switch phases reach 1.4× speed with gradual transitions; settled phases remain at 1×. The final duration is 9.93 seconds.
6. [final.gif](final.gif): The actual delivered 640×640 GIF with a dedicated transparency index. This original file is preserved rather than replaced with a later export from the generalized tool.
7. [verification.json](verification.json): Across 289 frames, decoded GIF alpha exactly matches the thresholded RGBA masks, with zero additional transparent holes. [manifest.json](manifest.json) records provenance and asset SHA-256 hashes.

## Verification Evidence

![Left: before; right: after](before-after.png)

The black marks on the fingers and thighs on the left came from skin-shadow colors being treated as GIF transparency. The transparent PNG frames did not have those defects. The corrected export uses 255 foreground colors plus one dedicated transparent index, with every decoded GIF frame checked against its source mask. No denoising or added outline was used to conceal the issue.

This example validates one production case. Its 12-second source duration, 1.4× speed, magenta background, and seated leg-switch action are not universal defaults. The generalized script exposes different palette-training, keying, and timing controls, so a new export may differ from this preserved deliverable.
