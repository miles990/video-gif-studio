from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import brief

# These fixtures explicitly exercise unfinished previs, not authored proposals.
def skeleton_board(b,**kwargs):return brief.to_storyboard(b,allow_skeleton=True,**kwargs)

class FixTests(unittest.TestCase):
    def test_modes_need_edit_context(self):
        for text in ('make 3 faster','fix shot 2','an export product launch','第三鏡往右推 30 度','咖啡新品，也做幾個版本嗎，不急'):
            self.assertEqual(brief.classify(text)[0],'brief',text)
        old={'shots':[{'id':'shot-1'}]}
        self.assertEqual(brief.classify('fix shot 2',previous=old)[0],'delta')
        self.assertEqual(brief.classify('export mp4',previous=old)[0],'housekeeping')
        self.assertEqual(brief.classify('create 4 variations')[0],'batch')

    def test_no_drop_and_fractional_tempo(self):
        import numpy as np
        import wave,tempfile
        with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as tmp:
            rate=8000;duration=30;t=np.arange(rate*duration)/rate
            audio=np.zeros_like(t)
            for start in np.arange(0,duration,60/123):
                u=t-start;audio+=.2*np.sin(2*np.pi*70*u)*np.exp(-np.maximum(u,0)*45)*(u>=0)*(u<.12)
            p=Path(tmp)/'steady.wav'
            with wave.open(str(p),'wb') as f:
                f.setparams((1,2,rate,0,'NONE',''));f.writeframes((audio*32767).astype('<i2').tobytes())
            grid=brief.music_grid(p)
            self.assertIsNone(grid['drop_ms'])
            self.assertAlmostEqual(grid['beats_ms'][50],50*60000/123,delta=25)
            b=brief.expand('coffee 10s',music=grid)
            self.assertIn('No drop detected; turn anchored to bar',b['prompt'])
            self.assertTrue(all(s['sound']['section']!='drop' for s in skeleton_board(b)['shots']))
        self.assertTrue(all(s['sound']['section']=='silent' for s in skeleton_board(brief.expand('coffee 5s'))['shots']))

    def test_transformations_and_constraints_survive(self):
        from brief_render import compile_plan
        import tempfile
        for draft,verb in [('玉山茶罐碎成粉重新聚成 logo，logo 一定要最後，不要人臉','聚成'),('玉山茶罐黑白變彩色，必須使用玉山茶罐','變彩色'),('Acme kettle dissolves into steam; no faces; logo must appear last','dissolves into')]:
            b=brief.expand(draft)
            turns=[v for v in b['beats'] if v['is_turn']]
            self.assertEqual(len(turns),1);self.assertIn(verb,turns[0]['text'])
            self.assertNotIn('the subject',b['prompt'])
            self.assertNotIn('larger working assembly',b['prompt'])
            board=skeleton_board(b)
            self.assertEqual(board['hard_constraints'],b['hard_constraints'])
            self.assertTrue(all(s['hard_constraints']==b['hard_constraints'] for s in board['shots']))
            with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as tmp:
                plan=compile_plan(board,Path(tmp),size=(64,64))
                self.assertEqual(plan['review']['hard_constraints'],b['hard_constraints'])

    def test_skeleton_guard_and_constraint_lint(self):
        from brief_lint import lint
        b=brief.expand('Acme kettle; must show logo last; no faces',content={'duration':5})
        self.assertEqual(b['status'],'skeleton');self.assertTrue(b['forks'])
        with self.assertRaisesRegex(ValueError,'E_SKELETON'):brief.to_storyboard(b)
        brief.to_storyboard(b,allow_skeleton=True)
        b['hard_constraints']=[]
        self.assertIn('hard_constraint',[f['rule'] for f in lint(b)['findings']])
        authored=brief.expand('Acme kettle',content={'turn':'the lid opens to reveal the brewing chamber'})
        self.assertEqual(authored['status'],'proposal');brief.to_storyboard(authored)
