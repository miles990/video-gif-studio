import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from game_character import originality
from image_common import ImageError

class OriginalityFixTests(unittest.TestCase):
    def test_local_names_specific_games_and_contextual_alternatives(self):
        suggestions=[]
        for name in ('瑪利歐','马里奥','Mario','林克','Link','寶可夢','Pokémon','皮卡丘','薩爾達','Zelda','Crash Bandicoot','Shovel Knight','in the style of Stardew Valley'):
            with self.assertRaises(ImageError,msg=name) as e:originality('make '+name+' ice sword sprites')
            suggestions.append(e.exception.error['suggestion'])
        self.assertGreater(len(set(suggestions)),3)
        for p in ('16-bit JRPG 風格的原創騎士','像 90 年代 SNES 動作遊戲那種手感的狐狸劍士','電氣屬性的黃色小動物，原創'):
            self.assertEqual(originality(p)['action'],'proceed')
