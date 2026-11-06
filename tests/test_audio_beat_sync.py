import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audio_beat_sync import allocate,schedule,frame_at,drift_report


def beat_fixture(accelerate=False):
    t=0;beats=[]
    for i in range(132):
        beats.append(dict(time_s=t/1000,bar_position=i%4+1));t+=60000/(120+4*i/131 if accelerate else 120)
    return dict(beats=beats,bpm=240,duration_s=t/1000)

class BeatTest(unittest.TestCase):
    def test_remainder_has_no_drift(self):
        self.assertEqual(sum(allocate([1]*7,997)),997)
        anim=dict(state='idle',frames=[dict(duration_ms=83)]*12)
        r=schedule(anim,beat_fixture(True));self.assertTrue(all(sum(c['duration_ms'])==c['end_ms']-c['start_ms'] for c in r['cycles']))
    def test_32_bars_and_accelerando_and_double_tempo(self):
        anim=dict(state='attack',frames=[dict(duration_ms=80)]*10,events=[dict(name='hit',frame=4)])
        for accelerando in (False,True):
            r=schedule(anim,beat_fixture(accelerando),2);events=[c['event'] for c in r['cycles']]
            self.assertGreaterEqual(len(events),31)
            self.assertEqual(drift_report([e['actual_ms'] for e in events],[e['target_ms'] for e in events])['status'],'PASS')
            for c in r['cycles']:self.assertEqual(frame_at(r,c['event']['actual_ms'])['frame'],4)
        # Fixed 12fps rounded to 83ms: 24 frames/bar lose 8ms per bar.
        self.assertEqual(drift_report([i*24*83 for i in range(32)],[i*2000 for i in range(32)])['status'],'FAIL')
    def test_anticipation_expands_to_two_beats(self):
        a=dict(state='attack',frames=[dict(duration_ms=10)]+[dict(duration_ms=100)]*5,events=[dict(name='hit',frame=1)])
        r=schedule(a,beat_fixture(),1);self.assertTrue(r['anticipation_expanded']);self.assertEqual(r['beats_per_cycle'],2)
        d=r['cycles'][0]['duration_ms'];self.assertGreaterEqual(d[0]+1,.4*sum(d[1:]))

if __name__=='__main__':unittest.main()
