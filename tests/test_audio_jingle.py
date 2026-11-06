import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from audio_jingle import regions,cleanup,split_sheet,align_event
from audio_loop import encode
from image_common import ImageError

class JingleTest(unittest.TestCase):
    def test_dc_trim_release(self):
        t=np.arange(48000)/48000;x=.8*np.sin(2*np.pi*440*t)*np.minimum(t/.005,1)*np.exp(-8*t)
        x=np.pad(x,(14400,12000))+.02;y,r=cleanup(np.repeat(x[:,None],2,axis=1))
        self.assertLessEqual(r['onset_ms'],5.1);self.assertLessEqual(r['dc'],.001)
        self.assertLessEqual(np.max(np.abs(y[-480:])),.001);self.assertLessEqual(r['measured']['true_peak'],-1)
    def test_sheet_five_and_reverb(self):
        pieces=[];starts=[];clock=0
        for i in range(5):
            t=np.arange(48000)/48000;v=.3*np.sin(2*np.pi*(220+i*55)*t)*np.minimum(t/.002,1)*np.exp(-7*t)
            starts.append(clock);pieces.extend([v,np.zeros(24000)]);clock+=72000
        x=np.repeat(np.concatenate(pieces)[:,None],2,axis=1);spans=regions(x)
        self.assertEqual(len(spans),5)
        for expected,(first,last) in zip(starts,spans):self.assertLessEqual(abs(first-expected),240);self.assertGreater(last-first,30000)
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'sheet.wav';encode(src,x)
            with self.assertRaises(ImageError):split_sheet(src,['a','b'],Path(d)/'out')
            r=split_sheet(src,list('abcde'),Path(d)/'out');self.assertEqual(len(r['sprite']),5)
    def test_event_uses_onset(self):
        r=align_event(dict(frames=[dict(duration_ms=80)]*8,events=[dict(name='hit',frame=3)]),'hit',4)
        self.assertEqual(r['audio_start_ms'],236);self.assertEqual(r['offset_ms'],0)

if __name__=='__main__':unittest.main()
