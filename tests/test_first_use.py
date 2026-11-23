"""Isolated first-use (clean HOME / venv) and an off-demo input probe."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENV_BASE = {k: v for k, v in os.environ.items() if k not in ('XAI_API_KEY', 'FAL_KEY')}


class FirstUseTests(unittest.TestCase):
    def test_isolated_home_and_venv_doctor(self):
        with tempfile.TemporaryDirectory(prefix='vgs-first-use-', dir=ROOT / '.scratch') as tmp:
            home = Path(tmp) / 'home'
            venv = Path(tmp) / 'venv'
            home.mkdir()
            subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True, capture_output=True)
            pip = venv / 'bin' / 'pip'
            py = venv / 'bin' / 'python'
            env = {**ENV_BASE, 'HOME': str(home), 'PYTHONPATH': str(ROOT / 'scripts'), 'XDG_CACHE_HOME': str(Path(tmp) / 'cache')}
            env.pop('VIRTUAL_ENV', None)
            subprocess.run([str(pip), 'install', '-q', '-r', str(ROOT / 'requirements.txt')], check=True, env=env, capture_output=True, text=True)
            r = subprocess.run([str(py), str(ROOT / 'scripts/vgs.py'), '--version'], cwd=str(home), env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('1.0.0', r.stdout + r.stderr)
            d = subprocess.run([str(py), str(ROOT / 'scripts/doctor.py'), '--json'], cwd=str(home), env=env, capture_output=True, text=True)
            self.assertIn(d.returncode, (0, 1), d.stderr)
            report = json.loads(d.stdout)
            self.assertTrue(report['local_gif_runtime_ready'], report)

    def test_off_demo_input_make(self):
        from media_runtime import locate
        if not (locate('ffmpeg') and locate('ffprobe')):
            self.skipTest('FFmpeg/ffprobe required')
        sys.path.insert(0, str(ROOT / 'scripts'))
        with tempfile.TemporaryDirectory(prefix='vgs-off-demo-', dir=ROOT / '.scratch') as tmp:
            src = Path(tmp) / 'probe.mp4'
            # A synthetic clip that is not one of the repo examples.
            subprocess.run([
                locate('ffmpeg'), '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'color=c=0xFC01F9:s=160x160:d=1:r=12',
                '-f', 'lavfi', '-i', 'color=c=0x2244AA:s=40x40:d=1:r=12',
                '-filter_complex', 'overlay=20:20', '-pix_fmt', 'yuv420p', str(src)
            ], check=True, capture_output=True)
            out = Path(tmp) / 'out'
            env = {**ENV_BASE, 'PYTHONPATH': str(ROOT / 'scripts')}
            r = subprocess.run(
                [sys.executable, str(ROOT / 'scripts/vgs.py'), 'make', str(src), '--out', str(out)],
                capture_output=True, text=True, env=env, cwd=ROOT)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue((out / 'animation.gif').is_file())
            self.assertIn('已去背', r.stdout)


if __name__ == '__main__':
    unittest.main()
