"""Offline end-to-end controls. None of these scenarios spends Suno credits."""
import sys,tempfile,unittest,socket
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from audio_demo import rehearsal_loop,rehearsal_sheet
from audio_loop import encode,decode,export,check,repair
from audio_variants import switches
from audio_jingle import split_sheet
from suno_route import Ledger,Session,TOOLS
from test_suno_route import FakeSuno
from image_common import ImageError


class AudioScenarios(unittest.TestCase):
    def test_network_sentinel_and_fake_replay(self):
        with tempfile.TemporaryDirectory() as d,patch.object(socket,'create_connection',side_effect=AssertionError('SUNO-SENTINEL')):
            fake=FakeSuno();ledger=Ledger(Path(d)/'ledger.json');s=Session(ledger,fake,sleep=lambda _:None)
            req=dict(kind='bgm-loop',bpm=120,key='Am',description='offline snow')
            first=s.create(req,True);second=s.create(req,True)
            self.assertEqual(first['clip_ids'],second['clip_ids']);self.assertEqual(ledger.usage()['create_calls'],1)
            for tool in ('library_list','playlists_create','audio_edit'):
                before=len(fake.calls)
                with self.assertRaises(ImageError):s.call(tool,{})
                self.assertEqual(len(fake.calls),before)
            self.assertEqual(len(TOOLS),35)
    def test_wav_ogg_export_and_five_cue_sprite(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);x=rehearsal_loop();encode(d/'loop.wav',x)
            r=export(d/'loop.wav',d/'engine',120,provenance=dict(source='synthetic_test',measured_bpm=120))
            self.assertTrue(all(f['qa']['status']=='PASS' for f in r['formats'].values()))
            self.assertIn('edit/loop_mode=2',(d/'engine/loop.wav.import').read_text())
            encode(d/'sheet.wav',rehearsal_sheet());s=split_sheet(d/'sheet.wav',['level','win','fail','pickup','confirm'],d/'sfx')
            self.assertEqual(len(s['cues']),5)
            with self.assertRaises(ImageError):export(d/'loop.wav',d/'forbidden',120,provenance=dict(source='stream',preview_only=True))
    def test_bidirectional_switches_and_offset_negative(self):
        a=rehearsal_loop();b=rehearsal_loop(True)
        r=switches(a,b,120,points=[96000]);self.assertEqual(len(r['transitions']),4)
        self.assertEqual(r['status'],'PASS',r)
        bad=np.roll(b,1776,axis=0);r=switches(a,bad,120,points=[96000])
        self.assertEqual(r['status'],'FAIL');self.assertTrue(any(t['phase_error_ms']>5 for t in r['transitions']))
    def test_cutbar_chord_progression_and_bar_repair_constraints(self):
        n=768000;t=np.arange(n)/48000;pad=np.zeros(n)
        for i,chord in enumerate(((220,261.5,329.5),(174.5,220,261.5),(261.5,329.5,392),(196,247,293.5))):
            span=slice(i*192000,(i+1)*192000)
            pad[span]=sum(.08*np.sin(2*np.pi*f*t[span]+.3) for f in chord)
        x=np.repeat(pad[:,None],2,axis=1)
        self.assertEqual(check(x[:384000],120,measured_bpm=120)['status'],'FAIL')
        with self.assertRaises(ValueError):repair(x,120,crossfade_beats=1.1)
        with self.assertRaises(ImageError):repair(x,120,start_bar=0)

if __name__=='__main__':unittest.main()
