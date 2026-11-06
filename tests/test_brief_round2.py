"""Review round 2: game assets, authored intent and decoded evidence."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import brief
from brief_lint import lint


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
