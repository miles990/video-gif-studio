**PASS** for the three requested fixes.

- **Gradual fade:** Palette retention now has a distance limit, and the added fade test verifies that a gradual change advances.
- **X compatibility:** The manifest check now includes frame rate, width, height, aspect ratio and duration bounds. It reports compatibility based on those checks; it does not verify an upload to X.
- **FFmpeg flags:** Pixel-specific encoding flags are confined to the pixel branch. The non-pixel branch retains its prior encoding options.

The requested test suite passed: **43 tests, OK**. The FAIL messages in its output came from test cases exercising QA failure detection. The requested GIF QA command also passed, with `quiet_flicker_rate 0.0157`, `aba_fg_rate 0.0195` and zero local color tables.

No workflow or CI smoke files appear in the working-tree changes. The existing changes also include a modified example GIF and untracked review artifacts. I did not edit source files.
