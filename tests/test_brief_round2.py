"""Review round 2: game assets, authored intent and decoded evidence."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import brief
from brief_lint import lint
from brief_edit import parse, apply_changes


class TransformationTests(unittest.TestCase):
    def test_authored_turn_is_never_replaced(self):
        draft = '5 秒，火焰精靈碎成星屑再聚成鳳凰'
        text = '火焰精靈先碎成明亮星屑，沿螺旋聚成鳳凰，翅膀展開'
        b = brief.expand(draft, content={'turn': text})
        turn = next(v for v in b['beats'] if v['is_turn'])
        self.assertTrue(turn['text'].startswith(text))
        authored = deepcopy(b['beats'])
        authored[-1]['shot_durations'] = [.1, .2, .7]
        b = brief.expand(draft, content={'beats': authored})
        self.assertEqual(b['beats'], authored)
        board = brief.to_storyboard(b)
        self.assertEqual(len([s for s in board['shots'] if s['beat'] == turn['id']]), 1)

    def test_result_complements_and_timing(self):
        for draft in ('5 秒，符文排成龍形', '5s slime melts into a crystal',
                      'runes weave into a dragon', '星屑旋成法陣'):
            with self.subTest(draft=draft):
                b = brief.expand(draft)
                turn = next(v for v in b['beats'] if v['is_turn'])
                self.assertIsNotNone(brief.transformation(draft))
                self.assertNotRegex(turn['text'], r'5\s*(?:秒|s)')
                bad = deepcopy(b)
                next(v for v in bad['beats'] if v['is_turn'])['text'] = 'camera pulls out to reveal a sword'
                self.assertIn('transformation_preserved', [f['rule'] for f in lint(bad)['findings']])
        self.assertIsNone(brief.transformation('walk into the dungeon'))
        b=brief.expand('5 秒，火焰精靈展示')
        self.assertNotRegex(next(v for v in b['beats'] if v['is_turn'])['text'],r'5\s*秒')


class DeltaTests(unittest.TestCase):
    def board(self):
        return brief.to_storyboard(brief.expand('game hero reveal 5s'), allow_skeleton=True)

    def test_previous_directional_quantities(self):
        b = self.board()
        b['shots'][0].update(direction='left-to-right', rotation_degrees=30)
        edit = parse('shot 1 other way', b)
        self.assertEqual(len(edit['questions']), 1)
        self.assertIn('right-to-left', edit['questions'][0])
        self.assertIn('counter-clockwise', edit['questions'][0])
        b['shots'][0].pop('rotation_degrees')
        edit = parse('shot 1 other way', b)
        self.assertFalse(edit['questions'])
        self.assertEqual(apply_changes(b, edit)['shots'][0]['direction'], 'right-to-left')
        b['shots'][0].update(direction='neutral',action='knight turns 30 degrees clockwise; animation speed 2x')
        edit=parse('shot 1 other way',b)
        self.assertEqual(len(edit['questions']),1)
        self.assertIn('counter-clockwise',edit['questions'][0])
        self.assertIn('0.5',edit['questions'][0])

    def test_speed_grammar_and_explicit_pan(self):
        b = self.board()
        for words, speed in [('一半', .5), ('half', .5), ('half speed', .5),
                             ('twice', 2), ('兩倍', 2), ('快兩倍', 2), ('2x slower', .5)]:
            edit = parse('shot 1 '+words, b)
            self.assertFalse(edit['questions'], edit)
            self.assertEqual(edit['changes'][0]['magnitude'], speed)
            self.assertEqual(edit['changes'][0]['direction']['sense'], 'slower' if speed < 1 else 'faster')
        self.assertEqual(len(parse('shot 1 more magical', b)['questions']), 1)
        self.assertEqual(len(parse('shot 1 rotate some degrees', b)['questions']),1)
        edit = parse('shot 1 pan 改由右到左', b)
        self.assertFalse(edit['questions'])
        self.assertEqual(apply_changes(b, edit)['shots'][0]['direction'], 'right-to-left')

    def test_dark_sheet_without_frame_number(self):
        import tempfile, cv2
        import numpy as np
        from brief_refs import contact_sheet
        with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as tmp:
            source=Path(tmp)/'sprite.avi'
            out=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'MJPG'),10,(96,64))
            for i in range(50):out.write(np.full((64,96,3),20 if i<10 else 180,np.uint8))
            out.release()
            sheet=Path(tmp)/'sheet.png';contact_sheet(source,sheet)
            b=self.board()
            edit=parse('太暗',b,image=sheet)
            self.assertFalse(edit['questions'],edit)
            self.assertTrue(edit['changes'])
            self.assertTrue(all(c['change']=='brightness' and c['quantified']['measured_y']<80 for c in edit['changes']))
            self.assertEqual({s for c in edit['changes'] for s in c['target']['shots']}, {b['shots'][0]['id']})
