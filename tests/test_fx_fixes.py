"""Reviewer regressions: offline, no optional inference engines or downloads."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave
import numpy as np
from PIL import Image, ImageSequence
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fx import Context, TRANSITIONS, EFFECTS, evaluate
from fx.core import load_directory, OVERRIDES
from fx_render import render, validate_plan
from gif_pipeline import encode, verify
from fx_reverse import inspect_frames, reverse


class FixTests(unittest.TestCase):
    def test_actual_audio_peak_render_both_offsets(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);Image.new('RGBA',(32,24),(40,40,40,255)).save(p/'frame.png')
            rate=48000;t=np.arange(rate*4)/rate;local=t%.5
            x=np.sin(2*np.pi*1000*t)*np.where((t//.5).astype(int)%2==0,.8,.2)*np.exp(-local*100)*(local<.03)
            with wave.open(str(p/'click.wav'),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes((x*32767).astype('<i2').tobytes())
            for channel,offset in (('onset',0),('onset',20),('energy',0),('energy',20)):
                plan={'fps':25,'music':{'file':'click.wav','in_ms':offset},'segments':[{'type':'still','image':'frame.png','duration_ms':3800}],
                      'effects':[{'name':'flash_white','amount':{'on':channel,'decay_ms':140}}]}
                (p/'p.json').write_text(json.dumps(plan))
                # Pixel rendering is real; this offline test mocks only the exporter.
                captured=[]
                def stream(images,target,config,background):
                    captured.extend(images)
                    return {'container_duration_ms':len(captured)*1000/config['fps'],'encoded_frames':len(captured)}
                # Intercept the streaming encoder, not the old whole-film exporter.
                with patch('delivery.encode_frames',side_effect=stream), patch('music_sync.mux_music',return_value={}):
                    render(p/'p.json',p/f'out{channel}{offset}',('mp4',))
                images=captured;times=[1000/30]*len(images);edges=np.arange(len(images)+1)*1000/30
                if offset==0:self.assertGreaterEqual(np.array(images[0])[:,:,:3].mean(),250)
                peaks=[]
                for beat in range(1,8):
                    at=beat*500-offset
                    # CFR events may round earlier by half a frame.
                    ids=[i for i,t in enumerate(edges[:-1]) if abs(t-at)<=1000/60+1e-6]
                    peaks.append(max(np.array(images[i])[:,:,:3].mean() for i in ids))
                self.assertGreater(min(peaks),80)
                self.assertGreater(min(peaks[1::2])-max(peaks[::2]),30)
                print(f'{channel} offset={offset}ms: quiet={max(peaks[::2]):.2f}, loud={min(peaks[1::2]):.2f}, gap={min(peaks[1::2])-max(peaks[::2]):.2f}',flush=True)
                self.assertGreater(evaluate({'on':'onset','decay_ms':140},1050-offset,Context(1,1,audio={'times_ms':[1000],'onset':[1],'offset_ms':offset})),0)

    def test_whip_two_shots_no_replicated_edges(self):
        w,h=160,48;ctx=Context(w,h);a=np.zeros((h,w,4),np.uint8);b=a.copy()
        a[:]=[230,10,20,255];b[:]=[10,30,220,255]
        # Distinct edge markers must translate out, never stretch across the canvas.
        a[:,0]=[0,255,0,255];b[:,-1]=[255,255,0,255]
        for direction in ('left','right'):
            for p in (.25,.5,.75):
                out=TRANSITIONS['whip_pan']['function'](a,b,p,ctx,blur_px=1,direction=direction)
                self.assertEqual(np.count_nonzero(out[h//2,:,0]>200),round(w*(1-p)))
                self.assertTrue(np.all(out[:,:,3]==255))
                self.assertLessEqual(np.count_nonzero(out[:,:,1]>200),h*2)

    def test_validation_and_warning_regressions(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);Image.new('RGBA',(16,16),'red').save(p/'a.png')
            def check(plan):
                (p/'p.json').write_text(json.dumps(plan));return validate_plan(p/'p.json')
            with self.assertRaisesRegex(ValueError,'multiple of 10'):
                check({'segments':[{'type':'still','image':'a.png','duration_ms':101}]})
            plan={'fps':25,'sampling':'nearest','segments':[{'type':'still','image':'a.png','duration_ms':100}]*2}
            plan['segments'][1]=dict(plan['segments'][1],transition={'name':'crossfade','duration_ms':20})
            with self.assertRaisesRegex(ValueError,'40.0'):check(plan)
            plan['segments'][1]['transition']['duration_ms']=80
            with contextlib.redirect_stderr(io.StringIO()) as log:check(plan)
            self.assertIn('blends colours',log.getvalue())
            (p/'beats.json').write_text(json.dumps({'beats_ms':[0,500,1000],'downbeats_ms':[250]}))
            with self.assertRaisesRegex(ValueError,'not in beats_ms'):check(dict(plan,beatmap='beats.json'))

    def test_bad_library_skipped_and_override_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'bad.py').write_text('def broken(:\n')
            plugin='from fx import effect\n@effect()\ndef fix_probe(frame,t,ctx): return frame\n'
            (p/'good.py').write_text(plugin);(p/'override.py').write_text(plugin)
            with contextlib.redirect_stderr(io.StringIO()) as log:load_directory(p)
            self.assertIn('bad.py:1',log.getvalue());self.assertIn('FX override',log.getvalue())
            self.assertIn('fix_probe',EFFECTS);self.assertEqual(OVERRIDES[-1]['name'],'fix_probe');EFFECTS.pop('fix_probe')

    def test_gif_browser_delay_and_exact_total(self):
        with tempfile.TemporaryDirectory() as d:
            frames=[Image.new('RGBA',(12,12),(i*25,60,100,255)) for i in range(8)]
            times=[10,40,20,40,40,10,40,20];file=Path(d)/'x.gif';encode(frames,times,file)
            verify(file,frames,times)
            with Image.open(file) as gif:decoded=[f.info['duration'] for f in ImageSequence.Iterator(gif)]
            self.assertTrue(all(t>20 for t in decoded));self.assertEqual(sum(decoded),sum(times))

    def test_long_dissolve_one_edit_and_flash_hidden_cut(self):
        a=np.full((90,160,3),[220,40,40],np.uint8);b=np.full_like(a,[40,60,220])
        frames=[Image.fromarray(a)]*25
        frames += [Image.fromarray(np.rint(a*(1-p)+b*p).astype(np.uint8)) for p in np.linspace(0,1,31)]
        frames += [Image.fromarray(b)]*25
        r=inspect_frames(frames,np.arange(len(frames))*40,len(frames)*40)
        self.assertEqual(len(r['cuts']),1,r);self.assertEqual(r['cuts'][0]['type'],'crossfade')
        self.assertAlmostEqual(r['cuts'][0]['time_ms'],1600,delta=40)
        white=Image.new('RGB',(160,90),'white')
        frames=[Image.fromarray(a)]*25+[white]+[Image.fromarray(b)]*25
        r=inspect_frames(frames,np.arange(len(frames))*40,len(frames)*40)
        self.assertEqual(len(r['cuts']),1,r);self.assertAlmostEqual(r['cuts'][0]['time_ms'],1000,delta=40)

    def test_in_shot_freeze_becomes_still_segment(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'frames').mkdir();images=[]
            for i in range(80):
                a=np.full((48,80,3),[80,120,160],np.uint8);x=(i if i<20 else 20 if i<50 else i-30)%55;a[12:30,x:x+12]=255
                Image.fromarray(a).save(p/'frames'/f'{i:05d}.png')
            (p/'manifest.json').write_text(json.dumps({'durations_ms':[40]*80}))
            reverse(p/'frames',p/'rev')
            draft=json.loads((p/'rev/draft-plan.json').read_text())
            self.assertTrue(any(s['type']=='still' and s.get('duration_ms',0)>=1000 for s in draft['segments']),draft)
            validate_plan(p/'rev/draft-plan.json')

    def test_flash_cut_between_same_palette_shots(self):
        rng=np.random.default_rng(17)
        a=rng.integers(30,180,(90,160,3),dtype=np.uint8);b=a[:,::-1].copy()
        frames=[Image.fromarray(a)]*25+[Image.new('RGB',(160,90),'white')]+[Image.fromarray(b)]*25
        r=inspect_frames(frames,np.arange(len(frames))*40,len(frames)*40)
        self.assertEqual(len(r['cuts']),1,r)
        self.assertEqual(r['cuts'][0]['type'],'flash_cut')
        self.assertEqual(r['cuts'][0]['time_ms'],1000)

    def test_held_plate_with_repeated_foreground_accents(self):
        rng=np.random.default_rng(18);base=rng.integers(20,80,(90,160,3),dtype=np.uint8)
        frames=[]
        for i in range(90):
            a=base.copy()
            if 20<=i<75:
                y=30+min((i-20)%9,5)*3;a[y:y+24,50:110]=240
            else:a=np.roll(a,i*3,axis=1)
            frames.append(Image.fromarray(a))
        r=inspect_frames(frames,np.arange(len(frames))*40,len(frames)*40)
        self.assertTrue(any(f.get('kind')=='animated_cutout_on_held_plate' and f['end_ms']-f['start_ms']>=1800 for f in r['freezes']),r)

    def test_flash_during_continuous_camera_pan_is_not_cut(self):
        rng=np.random.default_rng(19)
        a=rng.integers(20,200,(90,160,3),dtype=np.uint8);frames=[]
        for i in range(50):
            image=np.roll(a,i,axis=1).copy()
            if i==25:image[:]=255
            frames.append(Image.fromarray(image))
        r=inspect_frames(frames,np.arange(50)*40,2000)
        self.assertEqual(r['cuts'],[],r)

if __name__=='__main__': unittest.main()
