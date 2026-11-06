import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audio_loop import decode,ffmpeg_pcm
from audio_jingle import correct_key,regeneration_request
from audio_measure import measure
FIX=Path(__file__).parent/'fixtures/live-s15'


class JingleKeyTest(unittest.TestCase):
    def test_live_cues_report_mode_conflicts_honestly(self):
        for name,expected in [('level-up-0','PASS'),('victory-1','regenerate_needed'),('confirm-0','regenerate_needed')]:
            y,r=correct_key(decode(FIX/(name+'.wav')))
            self.assertEqual(r['status'],expected,r)
            self.assertEqual(y is None,expected!='PASS')
            self.assertEqual(r['key_source'],'local_estimate')

    def test_two_semitone_repair_and_quality_gate(self):
        x=decode(FIX/'level-up-0.wav')
        # A real cue detuned two semitones is a nontrivial positive repair control.
        shifted=ffmpeg_pcm(x,f'rubberband=tempo=1:pitch={2**(2/12)}')
        self.assertEqual(measure(shifted)['key'],'Bm')
        y,r=correct_key(shifted)
        self.assertEqual(r['status'],'PASS',r)
        self.assertEqual(r['pitch_semitones'],-2)
        self.assertTrue(r['quality']['key_match'])
        self.assertLessEqual(r['quality']['true_peak'],-1)

    def test_missing_cues_have_exact_unsubmitted_requests(self):
        for name in ('failure','pickup'):
            r=regeneration_request(name)
            self.assertFalse(r['submitted']);self.assertEqual(r['tool'],'sounds_create')
            self.assertEqual(r['params']['key'],'Am');self.assertFalse(r['params']['loop'])
            self.assertNotIn('duration',r['params'])
            self.assertEqual(r,regeneration_request(name))


if __name__=='__main__':unittest.main()
