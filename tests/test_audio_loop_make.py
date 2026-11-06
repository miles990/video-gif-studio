import sys,unittest,tempfile,json,subprocess,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from audio_grid import grid
from audio_loop_make import candidates,make_loop
from audio_loop import decode,check,normalise,encode,export
from media_runtime import executable

FIX=Path(__file__).parent/'fixtures/live-s15'


class LoopMakerTest(unittest.TestCase):
    def test_live_source_excerpts_and_decoded_exports(self):
        records=json.loads((FIX/'sources.json').read_text())
        for name in ('explore','battle'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as folder:
                self.assertLess((FIX/(name+'.wav')).stat().st_size,1_000_000)
                x=decode(FIX/(name+'.wav'));record=records[name]
                choices=list(candidates(x,120,bars=(2,),measured_grid=record['local_grid']))
                y,cut=next((y,r) for y,r in choices if r['crossfade_samples']==record['crossfade_samples'])
                y,_=normalise(y);source=Path(folder)/(name+'.wav');encode(source,y)
                result=export(source,Path(folder)/'out',120,provenance=dict(source='download',measured_bpm=record['source_grid']['bpm']))
                self.assertEqual(result['qa']['status'],'PASS')
                for fmt in ('wav','ogg'):
                    self.assertEqual(result['formats'][fmt]['qa']['status'],'PASS')
                tags=json.loads(subprocess.check_output([executable('ffprobe'),'-v','error','-show_entries','stream_tags','-of','json',str(Path(folder)/'out'/(name+'.ogg'))]))['streams'][0]['tags']
                self.assertEqual(int(tags['LOOPSTART']),0)
                self.assertEqual(int(tags['LOOPLENGTH']),192000)
                raw=(Path(folder)/'out'/(name+'.wav')).read_bytes();pos=raw.index(b'smpl')
                self.assertEqual(struct.unpack_from('<I',raw,pos+8+36+12)[0],191999)
                self.assertLessEqual(abs(cut['zero_crossing_offset_samples']),48)

    def test_grid_has_no_provider_tempo_dependency(self):
        # Independent synthetic off-tempo rhythm, not a hard-coded 120 BPM grid.
        n=48000*12;t=np.arange(n)/48000;p=t%(60/117)
        x=np.sin(2*np.pi*220*t)*np.exp(-30*p)*np.minimum(p/.005,1)
        g=grid(np.repeat(x[:,None],2,axis=1))
        self.assertLess(abs(g['bpm']-117),.5)
        self.assertEqual(g['downbeat_source'],'local_estimate')
        with self.assertRaises(ValueError):grid(np.zeros((144000,2)))

    def test_reject_impossible_loop(self):
        with self.assertRaises(ValueError):make_loop(np.zeros((48000,2)))


if __name__=='__main__':unittest.main()
