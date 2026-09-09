# Video GIF Studio

**English** | [繁體中文](README.zh-TW.md)

A character animation skill with optional image references. **Codex** coordinates character creation, **Grok** motion and effect generation, background removal and transparent animation exports. Use **GPT-Image-2.5 when available**, or the image tool provided by your environment, for character creation or explicitly selected repair. Preserve continuous video frames by default.

License: [MIT](LICENSE)

## Installation

Give this request to Codex or another AI assistant with access to your local environment:

> Install the Codex skill from https://github.com/miles990/video-gif-studio. Read references/install.md first, register the skill, install its Python dependencies, and run the doctor check. Preserve any existing installation and data. Report local GIF tool readiness and Grok video generation readiness separately.

See the [AI installation instructions](references/install.md). If the repository is private, you need access to it. After installation, use `$video-gif-studio` on your next Codex turn.

## Requirements

- **Codex**: Coordinates generation, motion timing, background removal and export. Character creation or AI repair also needs an available image-generation tool. **GPT-Image-2.5** may be used when your environment exposes it; verify the actual model and alpha output capability. Existing media conversion does not require an image model.
- **Grok**: A signed-in account with video generation access and available quota. Video submission, polling, and downloading are built into this repository; authentication uses the official Grok CLI. See [Grok usage](references/grok.md).
- **Local tools**: Python 3.11 or later, the packages in `requirements.txt`, and FFmpeg/ffprobe.

Existing videos or transparent PNG frames can be converted locally without another Grok generation request.

## Usage

Workflow: **Reference or generated character → Grok continuous motion and requested effects → background removal → RGBA PNG frames, optional APNG and GIF preview**. Existing videos can enter at the background-removal step. Unless specified otherwise, use plausible anatomy, weight transfer and motivated displacement; keep the full character, weapon and effects visible through dissipation. Grok designs and generates requested effects. Requested seamless loops require visual boundary review.

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

These are workflow choices, not command-line flags. The bundled keyer handles uniform-color backgrounds; temporal matting requires an additional tool. Changing the file format cannot recover detail already removed during matting.

For soft edges, hair, smoke and fading effects, retain **RGBA PNG / APNG** masters. **GIF only supports fully transparent or fully opaque pixels** and is a compatibility preview. Pixel art can still use partial alpha; hard pixel edges and transparent glow need different treatment.

Choose any combination of **GIF**, **APNG**, **RGBA PNG frames**, **Sprite Sheet**, or a **complete asset pack**. These output options are separate from the transparency modes above. Without a selection, sharing defaults to GIF plus an RGBA/APNG master; game use defaults to PNG frames and sheets with metadata.

The bundled [sprite exporter](references/sprites.md) packs multi-page RGBA sheets with frame rectangles, durations and a fixed pivot. Page size, padding, integer scale reduction and pivot are configurable. Engine importers, gameplay events, hitboxes and root-motion tracks require separate implementation. Character/effect separation is not guaranteed from a composited video.

> Use $video-gif-studio for a Godot character attack. Preserve artwork, retain partial alpha, export PNG frames and an APNG preview, and export a sprite sheet with timing metadata. Report which engine integration steps remain.

See [SKILL.md](SKILL.md), [transparency and delivery choices](references/transparency.md), and the [export reference](references/export.md).

## Examples

**Seated leg switch: Grok video → transparent GIF.** This delivered 9.93-second animation preserves continuous character and chair movement. This existing example uses frames extracted directly from the Grok video; it was not redrawn frame by frame with GPT-Image-2.5.

![Transparent seated leg-switch GIF](examples/seated-leg-switch/final.gif)

[Download GIF](examples/seated-leg-switch/final.gif) · [Reference image](examples/seated-leg-switch/reference.png) · [Prompt](examples/seated-leg-switch/prompt.txt) · [Source video](examples/seated-leg-switch/source.mp4) · [Production record and verification](examples/seated-leg-switch/README.md)

**Without a reference image: original robot wave.** Created from text, with an original generated character and a Grok motion video. The transparent GIF is 6.04 seconds with 145 frames.

![Original robot wave without a reference image](examples/robot-wave-no-reference/final.gif)

[Download GIF](examples/robot-wave-no-reference/final.gif) · [Production, prompts and verification](examples/robot-wave-no-reference/README.md)

**Chibi running dash attack.** Small running steps, directional sword trails and recovery to guard; 3.23 seconds, 112 frames. GIF and soft-alpha APNG are included. Endpoint frames were inspected; full-speed loop review remains pending.

![Chibi running dash attack](examples/chibi-running-dash/final.gif)

[Download GIF](examples/chibi-running-dash/final.gif) · [Download APNG](examples/chibi-running-dash/final.apng) · [Production, prompt and verification](examples/chibi-running-dash/README.md)

[Sprite pack (PNG + sheets + JSON)](examples/chibi-running-dash/sprites.zip)
