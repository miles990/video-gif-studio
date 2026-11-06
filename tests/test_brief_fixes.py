from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import brief

class FixTests(unittest.TestCase):
    def test_modes_need_edit_context(self):
        for text in ('make 3 faster','fix shot 2','an export product launch','第三鏡往右推 30 度','咖啡新品，也做幾個版本嗎，不急'):
            self.assertEqual(brief.classify(text)[0],'brief',text)
        old={'shots':[{'id':'shot-1'}]}
        self.assertEqual(brief.classify('fix shot 2',previous=old)[0],'delta')
        self.assertEqual(brief.classify('export mp4',previous=old)[0],'housekeeping')
        self.assertEqual(brief.classify('create 4 variations')[0],'batch')
