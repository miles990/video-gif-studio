import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from game_character import identity_report

class IdentityFixTests(unittest.TestCase):
    def test_reviewer_single_front_relative_palette_ranks_side_above_recolour(self):
        from game_character import prepare_subject
        from PIL import Image
        import tempfile
        p=Path('tests/fixtures/live-s14')
        with tempfile.TemporaryDirectory(dir='.scratch') as folder:
            with Image.open(p/'wolf-side.png') as im:side,_=prepare_subject(im.convert('RGBA'),'side')
            side_path=Path(folder)/'side.png';side.save(side_path)
            result=identity_report({'front':p/'wolf-front-single.png','side':side_path},[p/'wolf-negative.png'],p/'wolf-near.png')
            self.assertLess(result['views']['side']['view_palette_distance'],result['near_control']['view_palette_distance'])
            self.assertTrue(result['view_palette_controls']['valid'])
            self.assertEqual(result['status'],'unassessed') # ORB overlaps: palette alone is not identity.

    def test_live_near_lookalike_ranks_below_isolated_side(self):
        from game_character import prepare_subject
        from image_identity import compare
        from PIL import Image
        import tempfile
        with tempfile.TemporaryDirectory(dir='.scratch') as folder:
            paths={}
            for view in ('front','side'):
                with Image.open(Path('tests/fixtures/live-s14')/('wolf-'+view+'.png')) as im:subject,_=prepare_subject(im.convert('RGBA'),view)
                paths[view]=Path(folder)/(view+'.png');subject.save(paths[view])
            side=compare(paths['front'],paths['side'])
            near=compare(paths['front'],'tests/fixtures/live-s14/wolf-near.png')
            # two-axis instrument (spec-13 round 3): the recoloured lookalike keeps structure but loses colour
            self.assertGreater(side['colour'],near['colour'])
            from identity_engine import verdict
            self.assertEqual(verdict(side),'pass')
            self.assertNotEqual(verdict(near),'pass')

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
