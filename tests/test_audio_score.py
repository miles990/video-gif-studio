import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audio_score import beat_map,crosscheck,extension_request,drop_alignment
from audio_score import score
from audio_loop import encode
from test_audio_loop import control
import numpy as np

class ScoreTest(unittest.TestCase):
    def test_crosscheck_half_and_mismatch(self):
        p=dict(beats=[dict(time_s=i*.5,bar_position=i%4+1) for i in range(32)],duration_s=16,bpm=120)
        local=dict(downbeats_ms=[i*2000+10 for i in range(8)],bpm=240,engine='beat_this')
        r=crosscheck(p,local);self.assertEqual(r['status'],'PASS');self.assertEqual(r['tempo_factor'],.5)
        local['downbeats_ms']=[t+37 for t in local['downbeats_ms']];self.assertEqual(crosscheck(p,local)['status'],'FAIL')
    def test_extension_and_drop(self):
        b=dict(duration_ms=15000,downbeats_ms=list(range(0,15000,2000)),sections=[dict(start_ms=0),dict(start_ms=8000),dict(start_ms=12000)])
        self.assertEqual(extension_request('fake',b,30000)['params']['continue_at'],14)
        r=drop_alignment(b,[8100,10000],120);self.assertTrue(r[0]['pass_']);self.assertFalse(r[1]['pass_']);self.assertEqual(len(r[1]['candidates']),2)
    def test_score_exact_duration_and_independent_loudness(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);encode(p/'music.wav',np.tile(control(),(2,1)))
            b=dict(duration_ms=16000,beats_ms=list(range(0,16000,500)),downbeats_ms=list(range(0,16000,2000)),bpm=120,sections=[])
            r=score(p/'music.wav',b,7500,p/'score')
            self.assertEqual(r['final_duration_ms'],7500);self.assertTrue(r['joins'])
            self.assertEqual(r['status'],'PASS',r)

if __name__=='__main__':unittest.main()
