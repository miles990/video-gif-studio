"""INTEROP 1.0: --help, --version, --json, RFC 9457 errors, doctor help."""
from pathlib import Path
import json
import os
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
VGS = [sys.executable, str(ROOT / 'scripts/vgs.py')]
DOCTOR = [sys.executable, str(ROOT / 'scripts/doctor.py')]
ENV = {k: v for k, v in os.environ.items() if k not in ('XAI_API_KEY', 'FAL_KEY')}
ENV['PYTHONPATH'] = str(ROOT / 'scripts')


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=ENV)


class InteropTests(unittest.TestCase):
    def test_version_matches_manifest(self):
        man = json.loads((ROOT / 'wow.manifest.json').read_text())
        r = run(VGS + ['--version'])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(man['version'], r.stdout + r.stderr)

    def test_help_exits_zero(self):
        r = run(VGS + ['--help'])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('make', r.stdout)

    def test_unknown_command_stderr_only(self):
        r = run(VGS + ['__wow_no_such_command__'])
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(r.stderr.strip())
        self.assertFalse(r.stdout.strip())

    def test_json_unknown_command_is_rfc9457(self):
        r = run(VGS + ['--json', '__wow_no_such_command__'])
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(r.stdout.strip())
        payload = json.loads(r.stderr.strip().splitlines()[-1])
        self.assertIn('type', payload)
        self.assertIn('title', payload)
        self.assertTrue(payload['type'].startswith('urn:video-gif-studio:problem:'))

    def test_doctor_help_is_readable(self):
        r = run(DOCTOR + ['--help'])
        self.assertEqual(r.returncode, 0, r.stderr)
        text = r.stdout
        self.assertIn('Read-only', text)
        self.assertIn('never generates', text.lower() + text)
        self.assertIn('--json', text)
        self.assertIn('--version', text)

    def test_doctor_json_and_vgs_doctor(self):
        r = run(DOCTOR + ['--json'])
        self.assertIn(r.returncode, (0, 1), r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report['schema_version'], 1)
        self.assertIn('ready', report)
        r2 = run(VGS + ['doctor', '--json'])
        self.assertIn(r2.returncode, (0, 1), r2.stderr)
        self.assertEqual(json.loads(r2.stdout)['schema_version'], 1)

    def test_doctor_version(self):
        man = json.loads((ROOT / 'wow.manifest.json').read_text())
        r = run(DOCTOR + ['--version'])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(man['version'], r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
