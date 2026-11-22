#!/usr/bin/env python3
"""CI smoke: discover unit tests, but skip cases that need a live FFmpeg runtime.

Used by the push/PR job so a missing media runtime is a skip, not an error.
The manual full job installs the runtime and runs `python -m unittest discover`.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISSING = 'Media runtime missing'

# Live FFmpeg/ffprobe integration, encoded-media scenarios, and headless
# Chromium plugin tests. The manual full job covers these.
MEDIA_MODULES = {
    'test_assemble_edit',
    'test_audio_beat_sync',
    'test_audio_loop_make',
    'test_audio_preview',
    'test_delivery_audio_cli',
    'test_delivery_p0',
    'test_js_styles',
    'test_music',
    'test_taste_scenarios',
    'test_video',
}


def _iter_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_tests(item)
        else:
            yield item


def _without_media_modules(suite):
    selected = unittest.TestSuite()
    for test in _iter_tests(suite):
        module = getattr(test, '__module__', '') or test.__class__.__module__
        name = module.rsplit('.', 1)[-1]
        if name not in MEDIA_MODULES:
            selected.addTest(test)
    return selected



def _needs_media(err) -> bool:
    typ, val, _tb = err
    text = str(val) if val is not None else ''
    if MISSING in text:
        return True
    name = getattr(typ, '__name__', '')
    lowered = text.lower()
    if name in {'FileNotFoundError', 'OSError'} and ('ffmpeg' in lowered or 'ffprobe' in lowered):
        return True
    return False


class SmokeResult(unittest.TextTestResult):
    def addError(self, test, err):
        if _needs_media(err):
            self.addSkip(test, 'media runtime absent')
            return
        return super().addError(test, err)

    def addFailure(self, test, err):
        if _needs_media(err):
            self.addSkip(test, 'media runtime absent')
            return
        return super().addFailure(test, err)

    def addSubTest(self, test, subtest, err):
        if err is not None and _needs_media(err):
            self.addSkip(subtest, 'media runtime absent')
            return
        return super().addSubTest(test, subtest, err)


def main() -> int:
    os.chdir(ROOT)
    (ROOT / '.scratch').mkdir(exist_ok=True)
    sys.path.insert(0, str(ROOT / 'scripts'))
    suite = _without_media_modules(unittest.defaultTestLoader.discover('tests', pattern='test_*.py'))
    runner = unittest.TextTestRunner(verbosity=2, resultclass=SmokeResult)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
