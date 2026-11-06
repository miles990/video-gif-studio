"""Round-four regressions: physical noise floors and authored editorial intent."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import taste_report as report
from taste_common import executable, read, compare_curve
from taste_lint import finding
from taste_director import treatment
from taste_pick import factory
from test_taste_round3 import analyze_frames

ROOT = Path(__file__).resolve().parents[1]


class RoundFour(unittest.TestCase):
    def test_static_h264_has_no_peaks(self):
        rng = np.random.default_rng(71)
        plate = rng.integers(30, 210, (90, 160, 3), dtype=np.uint8)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'static.mp4'
            subprocess.run([executable('ffmpeg'), '-v', 'error', '-f', 'rawvideo',
                            '-pixel_format', 'rgb24', '-video_size', '160x90', '-framerate', '30',
                            '-i', 'pipe:0', '-c:v', 'libx264', '-crf', '23', '-pix_fmt', 'yuv420p', str(path)],
                           input=plate.tobytes()*300, check=True, capture_output=True)
            r = report.analyze(path)
        self.assertGreater(np.ptp(r['M4']['luma']), 0, 'Exercise actual codec variation')
        self.assertEqual(r['M15']['peaks'], [])
        self.assertEqual(r['M15']['effective_weights'], [0]*4)

    def test_demo_flash_with_and_without_manifest(self):
        for manifest in (None, read(ROOT/'wow/fx/demo/manifest-a.json')):
            with self.subTest(manifest=bool(manifest)):
                r = report.analyze(ROOT/'wow/fx/demo/demo.mp4', manifest=manifest)
                self.assertTrue(r['M4']['flash_events'] or r['M1']['events'])
                if manifest:self.assertEqual(r['M12']['transitions'], manifest['transitions'])
                summary = r['summary']
                self.assertFalse(any('clipped_fraction' in s['evidence'] and abs(s['start']-2.92)<.1
                                     for s in summary['suggestions']))

    def test_jump_cut_shot_annotation_forms(self):
        for transition in ('jump_cut', dict(name='jump_cut'), dict(type='jump_cut')):
            for rule in ('angle_30', 'eye_trace', 'cut_on_action'):
                with self.subTest(transition=transition, rule=rule):
                    self.assertEqual(finding(rule, 2, 0, 30, 'Change cut', dict(transition=transition))['status'], 'annotated')
        self.assertEqual(finding('angle_30', 2, 0, 30, 'Change cut', dict(transition='crossfade'))['status'], 'advice')

    def test_original_scale_component_floors(self):
        t = np.arange(0, 10, .1)
        p = report.arousal(t, .01*np.sin(t), [], .01*np.sin(t), 90+.01*np.sin(t))
        self.assertEqual(p['effective_weights'], [0]*4)
        self.assertTrue(np.allclose(p['values'], 0))

    def test_local_peak_significance_and_real_motion(self):
        t = np.arange(0, 10, .1)
        motion = np.where((t>=2)&(t<3), 4, .01*np.sin(t))
        p = report.arousal(t, motion, [], np.zeros(len(t)), np.full(len(t),90))
        self.assertEqual(p['effective_weights'], [1,0,0,0])
        self.assertTrue(p['peak_significant'][25])
        self.assertFalse(any(p['peak_significant'][60:]))

    def test_manifest_flash_suppression_is_local(self):
        r = analyze_frames([np.full((48,80,3), 255, np.uint8)]*90,
                           manifest=dict(transitions=[dict(name='flash_cut',start_ms=2000,end_ms=2100)]))
        self.assertTrue(any('clipped_fraction' in s['evidence'] and s['start']==0 for s in r['summary']['suggestions']))

    def test_no_zero_clipping_filler(self):
        r = analyze_frames([np.full((48,80,3), 90, np.uint8)]*30)
        self.assertFalse(any('clipped_fraction' in s['evidence'] for s in r['summary']['suggestions']))

    def test_deviations_rank_original_scale(self):
        t = np.arange(0, 10, .1)
        y = np.where(t<6, .4, .8)
        c = compare_curve(t, y, [[0,.2],[5.9,.2],[6,.9],[10,.9]])
        self.assertGreaterEqual(c['deviations'][0]['start'], 6)
        self.assertAlmostEqual(c['deviations'][0]['deficit'], .1)

    def test_cli_weight_provenance(self):
        with patch.object(report, 'analyze', return_value={}) as analyze, patch.object(report, 'save_report'):
            self.assertEqual(report.main(['unused.mp4', '--out', 'unused', '--weights', '.35,.25,.30,.10']), 0)
        self.assertEqual(analyze.call_args.kwargs['weight_source'], 'cli')

    def test_global_advice_not_first_second(self):
        r = analyze_frames([np.full((48,80,3), 90, np.uint8)]*90)
        r['M1'].update(cv=0, lengths=[1,1,1], cut_times=[1,2])
        suggestion = next(s for s in report.front_page(r)['suggestions'] if s['evidence'].get('rule')=='shot_cv')
        self.assertEqual(suggestion.get('scope'), 'film')
        self.assertIsNone(suggestion['shot'])
        self.assertNotIn('0.00-1.00s', suggestion['action'])

    def test_build_overrides_calm_keyword(self):
        b = treatment(['missing.png'], 6, 'calm opening then build', factory())
        self.assertGreater(b['design_curve'][-1][1], b['design_curve'][0][1])

    def test_explicit_brief_design_intent(self):
        for intent, core in (('build', 'calm ambient'), ('calm', 'build a crescendo')):
            b = treatment(['missing.png'], 6, core, factory(), brief=dict(design_curve_intent=intent))
            delta = b['design_curve'][-1][1]-b['design_curve'][0][1]
            self.assertEqual(delta>0, intent=='build')
            if intent=='calm': self.assertFalse(any(s.get('recipe') for s in b['shots']))

    def test_authored_curve_overrides_intent_and_keywords(self):
        curve = [[0,.6],[3,.2],[6,.6]]
        b = treatment(['missing.png'], 6, 'calm build', factory(),
                      brief=dict(design_curve=curve, design_curve_intent='build'))
        self.assertEqual(b['design_curve'], curve)


if __name__ == '__main__': unittest.main()
