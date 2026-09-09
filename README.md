# Video GIF Studio

**English** | [繁體中文](README.zh-TW.md)

Create character GIFs with or without reference images. **Grok is used by default** for continuous motion and effects, aiming for more natural motion and stronger continuity, especially for complex actions. **Grok is not required:** if it is unavailable or you choose to skip it, Codex can use available image-generation tools for keyframes or existing media. Codex coordinates creation, timing, background removal and export. Use **GPT-Image-2.5 when available**, or the image tool exposed by your environment. Quality still depends on the source and review.

License: [MIT](LICENSE)

## Installation

Give this request to Codex or another AI assistant with access to your local environment:

> Install the Codex skill from https://github.com/miles990/video-gif-studio. Read references/install.md first, register the skill, install its Python dependencies, and run the doctor check. Preserve any existing installation and data. Report local GIF tool readiness and Grok video generation readiness separately.

See the [AI installation instructions](references/install.md). After installation, use `$video-gif-studio` on your next Codex turn.

## Requirements

- **Codex**: Coordinates generation, motion timing, background removal and export. Character creation or AI repair also needs an available image-generation tool. **GPT-Image-2.5** may be used when your environment exposes it; verify the actual model and alpha output capability. Existing media conversion does not require an image model.
- **Grok (default generation route, optional dependency)**: Only the Grok video route needs a signed-in account with video generation access and available quota. Video submission, polling, and downloading are built into this repository; OAuth authentication uses the official Grok CLI; explicitly selected API-key mode does not require it. See [Grok usage](references/grok.md).
- **Local tools**: Python 3.11 or later, the installer manages the packages in `requirements.txt` and downloads FFmpeg/ffprobe when absent on supported platforms.

See [managed dependencies and local background removal](references/dependencies.md). First installation/model use requires downloads; model services and credentials remain external.

Existing videos or transparent PNG frames can be converted locally without another Grok generation request.

## Usage

Workflow: **Reference or generated character → Grok video by default → background removal when needed → PNG frames, optional APNG and GIF**. If Grok is unavailable or explicitly skipped, new GIFs can still be created from generated keyframes; this is not limited to converting existing files. Existing videos can enter at the background-removal step. Unless specified otherwise, use plausible anatomy, weight transfer and motivated displacement; keep the full character, weapon and effects visible through dissipation. Requested seamless loops require visual boundary review.

**When Grok is available, effects default to Grok.** When effects are requested and no specific design or generation source is specified, let Grok design and generate them in the motion video. Codex directs their timing, physical cause and effect, readability and complete framing, then handles background removal and export. Follow any explicit effect design or source provided by the user.

With a reference image:

> Use $video-gif-studio to create a transparent GIF with natural, continuous motion based on this character image.

Without a reference image:

> Use $video-gif-studio to design an original small robot waving, generate continuous video, and create a transparent GIF.

With an existing video:

> Use $video-gif-studio to turn this video into a transparent GIF, adjust the motion speed, and verify the output.

Choose a transparency workflow, or leave it on **Auto**:

| Mode | What it does |
| --- | --- |
| **Auto — default** | Preserve source frames; use alpha, color keying or suitable available temporal matting. No automatic frame-by-frame redraw. |
| **Preserve artwork** | Prioritize original character pixels and motion; report areas that cannot be cleanly separated. |
| **AI repair/redraw** | Explicitly request image-model repair, accepting possible appearance changes and renewed temporal checks. |

These are workflow choices, not command-line flags. The bundled keyer handles uniform-color backgrounds; an optional local rembg entry point handles foreground masking (`install.py --with-matting`). Its framewise masks require flicker review; it is not a temporal model. Changing the file format cannot recover detail already removed during matting.

For soft edges, hair, smoke and fading effects, retain **RGBA PNG / APNG** masters. **GIF only supports fully transparent or fully opaque pixels** and is a compatibility preview. Pixel art can still use partial alpha; hard pixel edges and transparent glow need different treatment.

**Pixel art is processed on its logical pixel grid by default:** preserve color clusters and stepped contours, use integer nearest-neighbor scaling, and avoid blur or smoothing. Keep partial alpha where effects need it; pixel art does not require binary alpha everywhere. See [pixel-art handling](references/pixel-art.md).

Choose any combination of **GIF**, **APNG**, **RGBA PNG frames**, **Sprite Sheet**, **MOV**, **WebM**, **MP4**, or a **complete asset pack**. These output options are separate from the transparency modes above. **GIF is the default** when no format is specified. MOV (ProRes 4444) and WebM (VP9) are optional video exports with alpha verification; target-player support still needs checking. Long-video requests should use video output, optionally with a short GIF preview. **MP4 (H.264) does not retain transparency in this workflow**: transparent areas are composited over a chosen solid color (black by default). See [video export](references/video-export.md). For game use, prefer PNG frames and sheets with metadata.

The bundled [sprite exporter](references/sprites.md) packs multi-page RGBA sheets with frame rectangles, durations and a fixed pivot. Page size, padding, integer scale reduction and pivot are configurable. Engine importers, gameplay events, hitboxes and root-motion tracks require separate implementation. Character/effect separation is not guaranteed from a composited video.

> Use $video-gif-studio for a Godot character attack. Preserve artwork, retain partial alpha, export PNG frames and an APNG preview, and export a sprite sheet with timing metadata. Report which engine integration steps remain.

See [SKILL.md](SKILL.md), [transparency and delivery choices](references/transparency.md), and the [export reference](references/export.md).

### Music and beat-synced editing

Input music to generate a waveform and editable BPM/beat candidates, then cut prepared animation to selected musical accents. The bundled editor supports **trim, split/reorder, speed or duration fitting, beat-aligned ends, stills and timed loops**. Export a video with one continuous music track; MOV/WebM/MP4 support sound, while GIF/APNG/sprites remain silent.

Automatic BPM is a heuristic, not guaranteed downbeat detection. Override BPM/offset or edit beat timestamps, and review the result by listening. Align actual action events rather than assuming a clip boundary places every attack on beat. The local workflow is informed by lyrica-studio's separation of music analysis and timeline editing; that project is not a dependency. This is not a graphical editor or automatic full-MV generator.

> Use $video-gif-studio with this song and these animations. Analyze the beat candidates, make the main attack land on a suitable accent, trim and arrange the shots, and export an MP4 with the original music. Preserve pixel-art edges and show the timing plan and unresolved sync checks.

See [music input, beat maps and editing](references/music.md).

### Timed still images

Insert a picture for a chosen duration: **animation → last-frame hold for 2 seconds → next animation**, or use a separate image / the next clip's first frame. The bundled [timeline composer](references/timeline.md) joins prepared frames with exact hold durations and exports GIF by default, or APNG, sprites, MOV, WebM and opaque MP4. No Grok generation is needed for a completely static hold.

A still freezes effects as well as the character. Breathing, blinking or particles that keep moving need an animated segment. Shared canvas sizes are required; the tool does not stretch or blur pixel art to fit.

> Use $video-gif-studio to hold this animation's last frame for 2 seconds, then append the next animation. Export GIF and MP4 with a white background.

You can also set **how long a loop plays**, such as “walk loop for 5 seconds → hold for 1 second → attack.” Choose **exact duration** (default; may end mid-cycle) or **finish a complete cycle** (may exceed the requested time; actual duration is reported). This repeats existing animation locally without new generation. The source still needs a valid loop boundary. See [timed loops](references/timeline.md#loop-an-animation-for-a-duration).

### Reference and continuation options

Use an existing video to create an APNG preview and PNG frames, then choose references for the next step:

| Reference mode | Best fit |
| --- | --- |
| **Suitable keyframes — up to 7** | Distinct, readable action states for a new interpretation or sequence; no need to fill all seven slots. |
| **Last frame + consistency references** | Recommended for continuation: use the endpoint as the new first frame and stable character/style images to guide consistency, when supported. |
| **Last frame only** | Simple short continuation, with less context for identity and motion. |

Select by action phase and intended edit, not fixed time intervals. Keep timestamps, frame roles and a contact sheet. APNG is the preview/master; selected references are static PNGs. Reference order does not guarantee motion order, and combined reference/pinned-frame limits must be checked for the actual model.

Choose **reference pack only** or **continue generation**. Editing uses the original video through a supported edit route; generating from references and extending a video are distinct routes. A new clip from the last image is not automatically equivalent to video extension. Check pose, velocity, weight and visual consistency at each join. Repeated continuation needs a target duration, segment count or budget. **One request for a long video means multiple video-gif-studio runs:** Codex generates and reviews segments, then combines accepted segments into a long video. It is not one unlimited Grok request.

> Use $video-gif-studio on this video. Prepare an APNG and choose suitable keyframes for a reference pack only; include timestamps and selection reasons.

> Continue this video for one segment using its last frame plus suitable consistency references. Preserve the character and pixel style, show a recovery followed by a new attack, then export APNG and sprites. Verify the available generation route and the join.

These are **Codex-coordinated workflow options**. The repo bundles video-to-APNG/PNG export and single-image-to-video generation; automatic keyframe selection, a chain runner and multi-reference/edit/extend CLI modes are not yet bundled. See [chain workflow and capability boundaries](references/chain.md).

### Fallback when Grok is unavailable

Use Grok by default for new motion generation unless the user selects another route. Existing-media conversion does not need a new generation call. If it is unavailable or out of quota, Codex can reuse existing footage, generate consistent keyframes with an available image tool, or animate suitable existing layers. Simple blinks and expressions can still become GIFs; complex articulated motion may need a working video provider. The output identifies its actual source and limitations. No automatic repeated submissions or paid-provider/account switching. See [fallback workflow](references/fallback.md).

## Examples

**Seated leg switch: Grok video → transparent GIF.** This delivered 9.93-second animation preserves continuous character and chair movement. This existing example uses frames extracted directly from the Grok video; it was not redrawn frame by frame with GPT-Image-2.5.

![Transparent seated leg-switch GIF](examples/seated-leg-switch/final.gif)

[Download GIF](examples/seated-leg-switch/final.gif) · [Reference image](examples/seated-leg-switch/reference.png) · [Prompt](examples/seated-leg-switch/prompt.txt) · [Source video](examples/seated-leg-switch/source.mp4) · [Production record and verification](examples/seated-leg-switch/README.md)

**Without a reference image: original robot wave.** Created from text, with an original generated character and a Grok motion video. The transparent GIF is 6.04 seconds with 145 frames.

![Original robot wave without a reference image](examples/robot-wave-no-reference/final.gif)

[Download GIF](examples/robot-wave-no-reference/final.gif) · [Production, prompts and verification](examples/robot-wave-no-reference/README.md)

**Chibi running dash attack.** Small running steps, directional sword trails and recovery to guard; 3.23 seconds, 112 frames. GIF and soft-alpha APNG are included. Endpoint frames were inspected; full-speed loop review remains pending. Native-grid edge cleanup reduces purple fringes while preserving alpha.

![Chibi running dash attack](examples/chibi-running-dash/final.gif)

[Download GIF](examples/chibi-running-dash/final.gif) · [Download APNG](examples/chibi-running-dash/final.apng) · [Production, prompt and verification](examples/chibi-running-dash/README.md)

[Sprite pack (PNG + sheets + JSON)](examples/chibi-running-dash/sprites.zip)


**NEON ZEN — 30-second music PV.** Five sequential Grok clips follow an original silver koi through a neon courtyard. The original-speed soundtrack, selected onset boundaries and two inspected visual-event timings exercise the local beat editor. Full-speed musical review remains pending.

![NEON ZEN silent excerpt](examples/neon-zen-pv/preview.gif)

[Watch/download MP4 with music](examples/neon-zen-pv/final.mp4) · [Story, source videos, prompts and timing](examples/neon-zen-pv/README.md)
