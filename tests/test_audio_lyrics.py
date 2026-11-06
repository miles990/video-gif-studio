import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audio_lyrics import captions,whisper_crosscheck

class LyricsTest(unittest.TestCase):
    def test_forty_words_three_inferred_and_exact_ms(self):
        source=dict(status='complete',words=[dict(word='token',start_s=i*.25,end_s=i*.25+.2,success=i not in (3,17,29)) for i in range(40)])
        result=captions(source);self.assertEqual(result['report']['inferred_word_indexes'],[3,17,29])
        self.assertEqual(result['words'][39]['start_ms'],9750)
        local=[dict(w,start_ms=w['start_ms']+100) for w in result['words']]
        self.assertEqual(whisper_crosscheck(result['words'],local)['status'],'PASS')
        local=[dict(w,start_ms=w['start_ms']+151) for w in result['words']]
        self.assertEqual(whisper_crosscheck(result['words'],local)['status'],'FAIL')
    def test_empty_unavailable_and_rounding(self):
        self.assertEqual(captions(dict(status='complete',words=[]))['status'],'no_lyrics')
        self.assertEqual(captions(dict(status='unavailable'))['status'],'unavailable')
        r=captions(dict(status='complete',words=[dict(word='x',start_s=.0005,end_s=.1005)]))
        self.assertEqual([r['words'][0][k] for k in ('start_ms','end_ms')],[1,101])

if __name__=='__main__':unittest.main()
