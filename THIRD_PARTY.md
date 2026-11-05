# Third-party attribution

## Robert Penner easing equations (P1)

`scripts/fx/easing.py` adapts normalized easeInExpo, easeOutExpo,
easeInOutCubic, easeOutCubic and easeInOutSine from Robert Penner's easing
equations under the BSD option. Camera names, oscillator spring, tracking,
caption layout and procedural audio are original project code.
Source and license: https://robertpenner.com/easing/ and
https://robertpenner.com/easing_terms_of_use.html (checked 2026-11-05).

Copyright © 2001 Robert Penner

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the author nor the names of contributors may be used to
   endorse or promote products derived from this software without specific prior
   written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

## Kenney CC0 audio (P1, downloaded separately)

Kenney: https://kenney.nl/assets/interface-sounds (100 audio files, CC0),
https://kenney.nl/assets/impact-sounds and https://kenney.nl/assets/digital-audio.
CC0 dedication: https://creativecommons.org/publicdomain/zero/1.0/ .
`scripts/download_kenney_audio.py` downloads only on explicit invocation, verifies
the archive includes a CC0 license, retains original names/license, and records
the archive SHA256 and official pack page in provenance.json. The user supplies
a reviewed `sfx-map.json` mapping the six semantic categories to those filenames.
There are **zero bundled Kenney audio files**. Tests use original synthesized
fingerprint WAVs and a fake archive; these are not represented as Kenney assets.

## Optional faster-whisper (P1)

SYSTRAN / Guillaume Klein, https://github.com/SYSTRAN/faster-whisper, MIT.
`scripts/captions.py` calls the public WhisperModel/transcribe API with
word_timestamps=True and local_files_only=True. No upstream source, model weights,
or recorded model output is redistributed. The checked-in timing fixture is
authored synthetic data, explicitly marked as such. The optional dependency
retains its own MIT license in its installation.

Measurement and independent review in `scripts/qa_media.py` and `references/quality-review.md` are adapted from [win4r/video-director](https://github.com/win4r/video-director), MIT, © 2026 win4r. Local adaptations support alpha, variable delays, designed holds and continuation timelines.

MIT License

Copyright (c) 2026 win4r

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Optional Beat This! engine

[CPJKU/beat_this](https://github.com/CPJKU/beat_this), MIT. The optional adapter in
music_sync.py uses the public File2Beats API; no model weights or PyTorch distribution
are bundled. Checkpoint fetching happens only on explicitly selected live model use.
API and license verified against the upstream inference.py, model/postprocessor.py and
LICENSE. Offline fixtures are authored fake output, not recorded model predictions.

MIT License

Copyright (c) 2024 Institute of Computational Perception, JKU Linz, Austria

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Optional rembg / BiRefNet

[rembg](https://github.com/danielgatis/rembg) and
[BiRefNet](https://github.com/ZhengPeng7/BiRefNet) are optional external matting projects;
their project repositories publish MIT licenses. Model files and upstream dependencies
are not redistributed here. Review the selected weights' own terms and provenance before
redistribution; code licensing alone is not a license to training data or depicted people.
The new model choices are passed to rembg.new_session; u2netp remains the default.

## Reference breakdown provenance

fx_reverse.py is an original clean-room implementation of general image-analysis
heuristics. rea-video supplied only the high-level concept of describing edit structure;
its unlicensed source was not consulted, copied or incorporated.

## Optional RIFE interpolation

[Practical-RIFE](https://github.com/hzwer/Practical-RIFE), MIT; optional v4.25 lite ONNX conversion from [latentdivergence/fixflix-rife-lite](https://huggingface.co/latentdivergence/fixflix-rife-lite). No weights are distributed. Derived demo midpoint is repository-owned source footage.

MIT License

Copyright (c) 2021 hzwer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


## Optional Depth Anything V2 Small

[Depth-Anything-V2](https://github.com/DepthAnything/Depth-Anything-V2), Small weights under Apache-2.0; ONNX conversion: [onnx-community/depth-anything-v2-small](https://huggingface.co/onnx-community/depth-anything-v2-small). [Apache-2.0 license text](https://github.com/DepthAnything/Depth-Anything-V2/blob/main/LICENSE). Base/Large are CC-BY-NC and are not used; the adapter refuses base/large/vitb/vitl filenames before loading. Only a small derived depth PNG is distributed, with source provenance.

System fonts are read locally and never distributed. Windows Microsoft JhengHei, macOS PingFang, and Linux Noto CJK remain subject to their respective font licenses.

## Optional OpenCC Traditional Chinese conversion

[OpenCC](https://github.com/BYVoid/OpenCC) and the optional
[opencc-python-reimplemented](https://github.com/yichen0831/opencc-python)
adapter use Apache-2.0. Install separately with `pip install opencc-python-reimplemented`
to enable captions `--traditional` (`s2twp`). No OpenCC code or dictionaries are
vendored. Conversion preserves word timing; it is not speech recognition.


## gl-transitions CPU ports (P2b, experimental)

Adapted from https://github.com/gl-transitions/gl-transitions, `transitions/*.glsl`.
Exact source file SHA256 and uniform defaults: `wow/fx/p2b-provenance.json`.
All 32 selected shaders are MIT; the two BSD shaders are not included.

- 0gust1: LuminanceMelt.
- Adrian Purser: Bounce.
- Ben Zhang: Overexposure.
- Eke Péter <peterekepeter@gmail.com>: CrossWarp.
- Fernando Kuteken: ClockWipe, RotateScaleFade, MultiplyBlend, Hexagonalize.
- Gunnar Roth: GlitchMemories.
- Mr Speaker: Pinwheel.
- P-Seebauer: ColorDistance.
- Paweł Płóciennik: WaterDrop.
- Rich Harris: PerlinDissolve.
- Sergey Kosarevsky: Swirl.
- Zeh Fernando: DreamyZoom.
- bobylito: PolkaDotsCurtain.
- gre: FadeGrayscale, Pixelize, DitherDissolve, RandomSquares, WindowSlices, Wind, ColorPhase, SquaresWipe, CurvedWipe, ArrowWipe.
- haiyoucuv: ScaleIn.
- huynx: BowTieHorizontal.
- liubailin2020@gmail.com: BurnThrough.
- mikolalysenko: Dreamy.
- pschroen: DirectionalWarp.
- pthrasher: Crosshatch.

Additional source credits retained by these ports: gre (upstream porter),
natewave (GlitchMemories basis), Morgan McGuire @morgan3d (value noise in
BurnThrough and PerlinDissolve), benraziel (Pixelize basis),
Amit Patel / Red Blob Games (hexagonal coordinate math).
LuminanceMelt also incorporates MIT simplex noise by Ian McEwan, Ashima Arts,
maintainer ijm: Copyright (c) 2011 Ashima Arts. All rights reserved.
https://github.com/ashima/webgl-noise; covered by the MIT terms below.

MIT License

Copyright (c) 2017-present gl-transitions contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Note: Individual transitions in the transitions/ directory may have their own
license specified in their file header comments. When no license is specified,
the transition is covered by this MIT license.
