import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from music_sync import analyze
from compose_timeline import compose


def clicks(path):
    rate=8000;x=np.zeros(rate*4,dtype=np.float32)
    for t in np.arange(.1,4,.5):
        start=round(t*rate);n=160;x[start:start+n]=.8*np.sin(2*np.pi*1000*np.arange(n)/rate)
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((x*32767).astype('<i2').tobytes())


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
class MusicTests(unittest.TestCase):
    def test_auto_candidates_and_manual_grid(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);clicks(p/'click.wav')
            auto=analyze(p/'click.wav',p/'auto')
            self.assertAlmostEqual(auto['bpm'],120,delta=2)
            manual=analyze(p/'click.wav',p/'manual',120,100)
            self.assertEqual(manual['beats_ms'][:4],[100,600,1100,1600])
            self.assertTrue((p/'manual/waveform.svg').exists())

    def test_trim_fit_beat_cuts_and_soundtrack_all_formats(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);clicks(p/'click.wav');analyze(p/'click.wav',p/'beats',120,100)
            (p/'a/frames').mkdir(parents=True)
            for i in range(4):Image.new('RGBA',(16,16),(i*60,100,70,200)).save(p/'a/frames'/f'{i:05d}.png')
            (p/'a/manifest.json').write_text(json.dumps({'durations_ms':[100]*4}))
            plan={'beatmap':'beats/beats.json','music':{'file':'click.wav','in_ms':100,'fade_in_ms':0,'fade_out_ms':0},'segments':[
                {'type':'animation','manifest':'a/manifest.json','in_ms':100,'out_ms':300,'end_beat':1},
                {'type':'still','previous':'last','end_beat':2},
                {'type':'loop','manifest':'a/manifest.json','end_beat':3}]}
            (p/'plan.json').write_text(json.dumps(plan))
            compose(p/'plan.json',p/'out',('mp4','mov','webm'))
            m=json.loads((p/'out/manifest.json').read_text())
            self.assertEqual([v['duration_ms'] for v in m['segments']],[500,500,500])
            self.assertEqual(m['durations_ms'][:2],[250,250])
            with Image.open(p/'out/frames/00000.png') as im:self.assertEqual(im.getpixel((0,0)),(60,100,70,200))
            for fmt in ['mp4','mov','webm']:
                report=json.loads((p/f'out/animation.{fmt}.json').read_text())
                self.assertIsInstance(report['audio'],dict)
                self.assertAlmostEqual(report['audio']['decoded_audio_duration_ms'],1500,delta=100)
            # Verify the actual audio offset using lossless MOV PCM (no fades),
            # and ensure video alpha survives soundtrack muxing.
            decoded=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(p/'out/animation.mov'),'-vn','-ac','1','-ar','8000','-f','f32le','pipe:1']),dtype='<f4')
            with wave.open(str(p/'click.wav'),'rb') as wav:
                original=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(float)/32768
            np.testing.assert_allclose(decoded[:12000],original[800:12800],atol=1/32768)
            pixels=subprocess.check_output(['ffmpeg','-v','error','-i',str(p/'out/animation.mov'),'-frames:v','1','-f','rawvideo','-pix_fmt','rgba','pipe:1'])
            self.assertLessEqual(int(np.abs(np.frombuffer(pixels,dtype='uint8').reshape(16,16,4)[:,:,3].astype(int)-200).max()),2)
            with self.assertRaises(ValueError):compose(p/'plan.json',p/'silent',('gif',))
            self.assertFalse((p/'silent').exists())

    def test_silence_does_not_invent_bpm(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with wave.open(str(p/'silence.wav'),'wb') as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(8000);f.writeframes(bytes(48000))
            r=analyze(p/'silence.wav',p/'out');self.assertIsNone(r['bpm']);self.assertEqual(r['beats_ms'],[])
