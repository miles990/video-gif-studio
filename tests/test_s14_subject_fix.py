import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from PIL import Image
from game_demo import isolate_single_subject

class SubjectFixTests(unittest.TestCase):
    def test_live_wolf_turnaround_selects_requested_column(self):
        im=Image.open('tests/fixtures/live-s14/wolf-front.png').convert('RGBA')
        from game_character import prepare_subject
        front,report=prepare_subject(im,'front')
        side,other=prepare_subject(im,'side')
        self.assertEqual(report['subject_count'],4)
        self.assertEqual(report['selected_index'],0)
        self.assertEqual(other['selected_index'],1)
        self.assertNotEqual(front.tobytes(),side.tobytes())
        self.assertEqual(prepare_subject(side,'side')[1]['subject_count'],1)
        self.assertLess(front.getbbox()[2]-front.getbbox()[0],im.width//2)
