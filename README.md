# Video GIF Studio

**English** | [繁體中文](README.zh-TW.md)

A character animation skill with optional image references. Use **Grok to generate motion reference videos**, then **Codex with GPT-Image-2.5** to create transparent-background GIFs with a focus on consistent character appearance.

License: [MIT](LICENSE)

## Installation

Give this request to Codex or another AI assistant with access to your local environment:

> Install the Codex skill from https://github.com/miles990/video-gif-studio. Read references/install.md first, register the skill, install its Python dependencies, and run the doctor check. Preserve any existing installation and data. Report local GIF tool readiness and Grok video generation readiness separately.

See the [AI installation instructions](references/install.md). If the repository is private, you need access to it. After installation, use `$video-gif-studio` on your next Codex turn.

## Requirements

- **Codex + GPT-Image-2.5**: Codex coordinates the workflow, motion timing, background removal, and GIF export. GPT-Image-2.5 is used for character image generation and appearance consistency. Your environment must provide access to this image model; availability depends on your setup.
- **Grok**: A signed-in account with video generation access and available quota. Video submission, polling, and downloading are built into this repository; authentication uses the official Grok CLI. See [Grok usage](references/grok.md).
- **Local tools**: Python 3.11 or later, the packages in `requirements.txt`, and FFmpeg/ffprobe.

Existing videos or transparent PNG frames can be converted locally without another Grok generation request.

## Usage

Workflow: **Grok motion reference video → character production with Codex and GPT-Image-2.5 → continuous frames, transparent backgrounds, and GIF export**. Reuse character specifications and references to maintain appearance consistency, and inspect motion transitions.

With a reference image:

> Use $video-gif-studio to create a transparent GIF with natural, continuous motion based on this character image.

Without a reference image:

> Use $video-gif-studio to design an original small robot waving, generate continuous video, and create a transparent GIF.

With an existing video:

> Use $video-gif-studio to turn this video into a transparent GIF, adjust the motion speed, and verify the output.

See [SKILL.md](SKILL.md) for the full workflow and the [export reference](references/export.md) for tool options.

## Successful Example

**Seated leg switch: Grok video → transparent GIF.** This delivered 9.93-second animation preserves continuous character and chair movement. This existing example uses frames extracted directly from the Grok video; it was not redrawn frame by frame with GPT-Image-2.5.

![Transparent seated leg-switch GIF](examples/seated-leg-switch/final.gif)

[Download GIF](examples/seated-leg-switch/final.gif) · [Reference image](examples/seated-leg-switch/reference.png) · [Prompt](examples/seated-leg-switch/prompt.txt) · [Source video](examples/seated-leg-switch/source.mp4) · [Production record and verification](examples/seated-leg-switch/README.md)

**Without a reference image: original robot wave.** Created from text, with an original generated character and a Grok motion video. The transparent GIF is 6.04 seconds with 145 frames.

![Original robot wave without a reference image](examples/robot-wave-no-reference/final.gif)

[Download GIF](examples/robot-wave-no-reference/final.gif) · [Production, prompts and verification](examples/robot-wave-no-reference/README.md)
