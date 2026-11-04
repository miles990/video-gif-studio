# Third-party attribution

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
