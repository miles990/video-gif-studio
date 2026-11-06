import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from game_character import identity_report

class IdentityFixTests(unittest.TestCase):
    def test_cross_view_uncertainty_and_override(self):
        paths={n:Path('tests/fixtures/live-s14')/('wolf-'+n+'.png') for n in ('front','side','back')}
        result=identity_report(paths)
        self.assertEqual(result['status'],'unassessed')
        self.assertEqual(result['views']['back']['expectation'],'hidden face; costume and silhouette')
        self.assertNotIn('same_hist_max',result['method'])
        with patch('game_character.compare',side_effect=AssertionError('override is explicit')):
            result=identity_report(paths,identity_override='same')
        self.assertEqual(result['status'],'pass')
        self.assertEqual(result['identity_override']['decision'],'same')

    def test_overlap_is_unassessed_not_failed_or_calibrated(self):
        p=Path('tests/fixtures/live-s14')
        result=identity_report({n:p/('wolf-'+n+'.png') for n in ('front','side','back')},[p/'wolf-negative.png'],p/'wolf-near.png')
        self.assertIn('controls',result)
        if not result['controls_valid']:self.assertEqual(result['status'],'unassessed')
