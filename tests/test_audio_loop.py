import sys,tempfile,unittest,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from audio_loop import check,normalise,encode,decode,export,bar_samples,riff_markers


def control(meter='4/4'):
    n=round(bar_samples(120,meter)*4);t=np.arange(n)/48000;period=round(bar_samples(120,meter))
    # Harmonic pad and smooth percussive attacks; all phases close exactly.
    f=[round(v*period/48000)*48000/period for v in (110,220,261.6256,329.6276)]
    x=sum(.1*np.sin(2*np.pi*v*t+phase) for v,phase in zip(f,(.8,2.1,3.8,5.2)))
    pulse=(np.arange(n)%(12000 if meter=='7/8' else 24000))/48000
    x+=.12*np.sin(2*np.pi*80*pulse)*np.exp(-20*pulse)*np.minimum(pulse/.004,1)
    # Smooth high-frequency percussion gives a realistic highpass noise floor.
    x+=.015*np.sin(2*np.pi*6000*t)*(.65+.35*np.cos(2*np.pi*t*4))
    return normalise(np.repeat(x[:,None],2,axis=1),-16)[0]


class LoopTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.good=control()
    def test_positive_and_negative_controls(self):
        x=self.good;good=check(x,120,measured_bpm=120)
        self.assertEqual(good['status'],'PASS',good)
        cut=check(x[:345600],120,measured_bpm=120);self.assertFalse(cut['checks']['length']['pass_'])
        click=x.copy();click[227520]+=.5;r=check(click,120,measured_bpm=120)
        self.assertFalse(r['checks']['clicks']['pass_']);self.assertTrue(any(abs(t-4740)<=1 for t in r['checks']['clicks']['events_ms']),r)
        click=x.copy();click[-1]+=.25;self.assertFalse(check(click,120,measured_bpm=120)['checks']['clicks']['pass_'])
        fade=x.copy();fade[-12000:]*=np.linspace(1,0,12000)[:,None];fade[:2400]*=np.linspace(0,1,2400)[:,None]
        self.assertEqual(check(fade,120,measured_bpm=120)['status'],'FAIL')
        drift=x*np.linspace(1,10**(.2),len(x))[:,None];self.assertEqual(check(drift,120,measured_bpm=120)['status'],'FAIL')
        self.assertEqual(check(x,120,measured_bpm=120,source_format='mp3')['status'],'FAIL')
        harmony=x.copy();harmony[-48000:]=np.roll(harmony[-48000:],87,axis=0)
        self.assertEqual(check(harmony,120,measured_bpm=120)['status'],'FAIL')
    def test_odd_meter_and_ogg(self):
        x=control('7/8');r=check(x,120,'7/8',measured_bpm=120)
        self.assertEqual(r['status'],'PASS',r)
        self.assertEqual(check(x,120,measured_bpm=120)['status'],'FAIL')
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'x.ogg';encode(p,self.good);decoded=decode(p)
            self.assertEqual(len(decoded),len(self.good));r=check(decoded,120,measured_bpm=120)
            self.assertEqual(r['status'],'PASS',r)
    def test_riff_inclusive_end(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'x.wav';encode(p,self.good);riff_markers(p,len(self.good),[0,96000])
            raw=p.read_bytes();pos=raw.index(b'smpl');size=struct.unpack_from('<I',raw,pos+4)[0]
            self.assertEqual(size,60);self.assertEqual(struct.unpack_from('<I',raw,pos+8+36+12)[0],len(self.good)-1)
            self.assertIn(b'cue ',raw);self.assertIn(b'adtl',raw)


if __name__=='__main__':unittest.main()
