import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audio_variants import relation,validate_set,stretch,measure
from image_common import ImageError
import numpy as np

class VariantTest(unittest.TestCase):
    def test_key_relations(self):
        self.assertEqual(relation('Am','C'),'relative');self.assertEqual(relation('A minor','E minor'),'dominant')
        self.assertEqual(relation('Am','Bbm'),'conflict');self.assertEqual(relation('Am','A'),'parallel')
    def test_bad_set_identifies_all_three(self):
        good=[dict(name=str(i),measured=dict(bpm=120,key='Am'),downbeat_samples=0) for i in range(4)]
        self.assertEqual(validate_set(good,'Am')['status'],'PASS')
        good[1]['measured']['bpm']=123;good[2]['downbeat_samples']=1776;good[3]['measured']['key']='Bbm'
        r=validate_set(good,'Am');self.assertEqual({e['check'] for e in r['errors']},{'bpm','downbeat','key'})
    def test_stretch_limit_before_processing(self):
        with self.assertRaises(ImageError):stretch(np.zeros((48000,2)),100,120)
    def test_local_tempo_is_measured(self):
        t=np.arange(384000)/48000;p=t%.5
        x=np.sin(2*np.pi*220*t)*np.exp(-20*p)*np.minimum(p/.005,1)
        r=measure(np.repeat(x[:,None],2,axis=1));self.assertLessEqual(abs(r['bpm']-120),.5)

if __name__=='__main__':unittest.main()
