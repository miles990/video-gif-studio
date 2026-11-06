import sys,json,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from audio_loop import decode,normalise,check
from audio_loop_make import candidates
from audio_variants import switches,phase_lag
FIX=Path(__file__).parent/'fixtures/live-s15'


class VariantAlignTest(unittest.TestCase):
    def test_real_aligned_cuts_and_negative_phase_control(self):
        ainfo=json.loads((FIX/'sources.json').read_text())['explore']
        binfo=json.loads((FIX/'battle-transition.json').read_text())
        loops=[]
        for name,info in [('explore',ainfo),('battle-transition',binfo)]:
            x=decode(FIX/(name+'.wav'))
            y,_=next((y,r) for y,r in candidates(x,120,bars=(2,),measured_grid=info['local_grid'])
                     if r['crossfade_samples']==info['crossfade_samples'])
            y,_=normalise(y);loops.append(y)
            self.assertEqual(check(y,120,measured_bpm=info['local_grid']['bpm'])['status'],'PASS')
        a,b=loops
        self.assertLessEqual(abs(phase_lag(a,b)),2)
        result=switches(a,b,120)
        self.assertEqual(result['status'],'PASS',result)
        self.assertEqual(len(result['transitions']),4)
        self.assertEqual(result['switch_points_ms'],[2000])
        damaged=np.roll(b,37*48,axis=0)
        self.assertEqual(switches(a,damaged,120)['status'],'FAIL')
        self.assertGreater(abs(phase_lag(a,damaged)),30)


if __name__=='__main__':unittest.main()
