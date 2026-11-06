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
            self.assertTrue(all(s['sound']['section']!='drop' for s in brief.to_storyboard(b)['shots']))
        self.assertTrue(all(s['sound']['section']=='silent' for s in brief.to_storyboard(brief.expand('coffee 5s'))['shots']))
