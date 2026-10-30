import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
import contextlib
import io
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import qa_media as qa


def base(count=100, angles=None):
    images=[]
    gradient=np.repeat(np.arange(60,220,dtype=np.uint8)[None,:,None],120,axis=0)
    gradient=np.repeat(gradient,3,axis=2)
    for i in range(count):
        im=Image.fromarray(gradient.copy())
        theta=angles[i] if angles is not None else 2*math.pi*i/100
        x,y=80+40*math.cos(theta),60+40*math.sin(theta)
        ImageDraw.Draw(im).ellipse((x-20,y-20,x+20,y+20),fill=(230,60,60))
        images.append(im)
    return images


class MediaQATests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.counter=0
        # All core picture checks MUST work without ever resolving ffmpeg.
        self.no_ffmpeg=patch.object(qa,'executable',side_effect=AssertionError('Picture QA used ffmpeg'))
        self.no_ffmpeg.start()

    def tearDown(self):
        self.no_ffmpeg.stop()
        self.tmp.cleanup()

    def check(self, images, suffix='.gif', **kwargs):
        self.counter+=1
        path=self.root/f'input{self.counter}{suffix}'
        if suffix=='.dir':
            path.mkdir()
            for i,im in enumerate(images): im.save(path/f'{i:04d}.png')
        else:
            images[0].save(path,save_all=True,append_images=images[1:],duration=40,loop=0,disposal=2)
        report=qa.qa(path,self.root/f'out{self.counter}',**kwargs)
        with Image.open(self.root/f'out{self.counter}/phone_sheet.jpg') as sheet:
            self.assertEqual(sheet.width,360)
        self.assertTrue(all(e['seconds']<3 for e in report['sheets']['hook_sheet']))
        self.assertTrue(all(c['level'] in ('PASS','WARN','FAIL') for c in report['checks']))
        return {c['name']:c for c in report['checks']}

    def test_normal_loop(self):
        checks=self.check(base(),loop=True)
        self.assertTrue(all(c['level']=='PASS' for c in checks.values()),checks)
        self.assertTrue(checks['loop']['position_pass'])
        self.assertTrue(checks['loop']['speed_pass'])

    def test_flash_frame_and_time(self):
        images=base();images[50]=Image.new('RGB',(160,120),'white')
        c=self.check(images)['flashes']
        self.assertEqual(c['level'],'FAIL')
        self.assertEqual([e['frame'] for e in c['events']],[50])
        self.assertAlmostEqual(c['events'][0]['seconds'],2)

    def test_freeze_hold_and_partial_hold(self):
        images=base()
        for i in range(25,75):images[i]=images[25].copy()
        c=self.check(images,suffix='.dir')['freeze']
        self.assertEqual(c['level'],'WARN')
        self.assertEqual(c['events'][0]['frame'],25)
        self.assertAlmostEqual(c['events'][0]['seconds'],1)
        self.assertAlmostEqual(c['events'][0]['end_seconds'],3)
        self.assertIn('--holds',c['message'])
        c=self.check(images,suffix='.dir',holds=[(1,3)])['freeze']
        self.assertEqual(c['level'],'PASS');self.assertTrue(c['designed_holds'])
        c=self.check(images,suffix='.dir',holds=[(1,1.8)])['freeze']
        self.assertEqual(c['level'],'WARN')
        self.assertAlmostEqual(c['events'][0]['seconds'],1.8)
        self.assertAlmostEqual(c['events'][0]['end_seconds'],3)
        # GIF merges identical frames: long encoded frame duration is still a hold.
        c=self.check(images)['freeze']
        self.assertEqual(c['level'],'WARN')
        self.assertAlmostEqual(c['events'][0]['seconds'],1)
        self.assertAlmostEqual(c['events'][0]['end_seconds'],3)

    def test_position_seam(self):
        c=self.check(base(angles=[2*math.pi*.75*i/99 for i in range(100)]),loop=True)['loop']
        self.assertEqual(c['level'],'FAIL');self.assertFalse(c['position_pass'])
        self.assertEqual(c['events'][0]['frame'],99)
        self.assertAlmostEqual(c['events'][0]['seconds'],4)
        self.assertEqual(c['events'][0]['to_frame'],0)

    def test_speed_seam(self):
        angles=[math.radians(3.9*i if i<=89 else 3.9*89+.9*(i-89)) for i in range(100)]
        c=self.check(base(angles=angles),loop=True)['loop']
        self.assertEqual(c['level'],'FAIL');self.assertTrue(c['position_pass']);self.assertFalse(c['speed_pass'])
        self.assertIn('speed',c['message'])

    def test_small_patch_pop(self):
        images=base();a=np.array(images[60]);a[:16,:16]+=60;images[60]=Image.fromarray(a)
        c=self.check(images)
        events=c['pops']['events']+c['flashes']['events']
        self.assertTrue(any(e['frame']==60 and abs(e['seconds']-2.4)<.001 for e in events),c)

    def test_black_and_flat_first_frame(self):
        for color in ('black',(128,128,128)):
            images=base();images[0]=Image.new('RGB',(160,120),color)
            c=self.check(images)['frame0']
            self.assertEqual(c['level'],'FAIL');self.assertEqual(c['events'][0]['frame'],0)

    def transparent(self, freeze=False):
        images=[]
        for i in range(50):
            a=np.full((128,128,4),255*(i%2),dtype=np.uint8);a[:,:,3]=0
            x=10+2*(min(i,10) if freeze else i)
            for y in range(32):
                for dx in range(32):
                    if x+dx<128:a[y+48,x+dx]=[*( (200,120,40) if (y//4+dx//4)%2 else (90,60,30)),255]
            images.append(Image.fromarray(a))
        return images

    def test_hidden_rgb_and_visible_exposure(self):
        c=self.check(self.transparent(),suffix='.dir')
        for name in ('frame0','flashes','pops','freeze'):self.assertEqual(c[name]['level'],'PASS',c[name])
        c=self.check(self.transparent(True),suffix='.dir')['freeze']
        self.assertEqual(c['level'],'WARN')
        self.assertAlmostEqual(c['events'][0]['seconds'],.4)
        self.assertAlmostEqual(c['events'][0]['end_seconds'],2)

    def test_short_hook(self):
        self.check(base(30))

    def test_varying_delays_and_apng_poster(self):
        frames=base(12);path=self.root/'variable.png'
        delays=[20,30,40]*4
        frames[0].save(path,save_all=True,default_image=True,append_images=frames,duration=delays,loop=0)
        report=qa.qa(path,self.root/'variable')
        self.assertEqual(report['frames'],12)
        self.assertAlmostEqual(report['duration_seconds'],.36)
        self.assertAlmostEqual(report['frame_times_seconds'][3],.09)

    def test_hard_cuts(self):
        images=base(50)
        for color in ((220,190,30),(60,60,60)):
            frame=Image.new('RGB',(160,120),color)
            ImageDraw.Draw(frame).rectangle((20,20,60,80),fill='blue')
            images.extend([frame.copy() for _ in range(50)])
        c=self.check(images,suffix='.dir',expected=[2,4])['cuts']
        self.assertEqual(c['level'],'PASS')
        self.assertEqual([e['frame'] for e in c['detected']],[50,100])
        c=self.check(images,suffix='.dir',expected=[2,4.4])['cuts']
        self.assertEqual(c['level'],'FAIL')
        self.assertTrue(any(e.get('kind')=='missing planned cut' and e['seconds']==4.4 for e in c['events']))
        self.assertTrue(any(e.get('kind')=='unplanned cut' and e['seconds']==4 for e in c['events']))

    def test_repeated_encoder_frames_are_not_pops(self):
        images=[]
        for im in base(40):images.extend([im.copy() for _ in range(4)])
        c=self.check(images,suffix='.dir',fps=100)
        self.assertEqual(c['flashes']['events'],[]);self.assertEqual(c['pops']['events'],[])
        self.assertEqual(c['freeze']['events'],[])

    def test_timeline_joins_and_still(self):
        plan=self.root/'timeline.json'
        plan.write_text(json.dumps({'segments':[{'type':'animation','duration_ms':1000},{'type':'still','duration_ms':2000},{'type':'animation','duration_ms':1000}]}))
        holds,cuts,joins=qa.plan_settings(plan)
        self.assertEqual(holds,[(1,3)]);self.assertEqual(cuts,[]);self.assertEqual(joins,[1,3])
        images=base()
        for i in range(25,75):images[i]=images[25].copy()
        c=self.check(images,suffix='.dir',timeline=plan)
        self.assertEqual(c['freeze']['level'],'PASS');self.assertEqual(c['cuts']['level'],'PASS')

    def test_cli_codes_and_missing_runtime(self):
        images=base();images[50]=Image.new('RGB',(160,120),'white')
        path=self.root/'flash.gif'
        images[0].save(path,save_all=True,append_images=images[1:],duration=40,loop=0,disposal=2)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(qa.main([str(path),'--out',str(self.root/'cli')]),1)
        (self.root/'video.mp4').write_bytes(b'')
        with patch.object(qa,'locate',return_value=None), patch.object(qa,'executable',side_effect=RuntimeError('Media runtime missing; run scripts/media_runtime.py --install')), contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(qa.main([str(self.root/'video.mp4'),'--out',str(self.root/'missing')]),2)
        self.assertIn('scripts/media_runtime.py --install',errors.getvalue())
        self.assertNotIn('Traceback',errors.getvalue())


class AudioQATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg=qa.locate('ffmpeg')
        if not cls.ffmpeg:
            raise unittest.SkipTest('Existing FFmpeg required for audio integration; picture tests never skip')

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def make_video(self,name,source=None,filter_audio=None):
        path=self.root/(name+'.mp4')
        cmd=[self.ffmpeg,'-v','error','-f','lavfi','-i','testsrc2=size=160x120:rate=25:duration=6']
        if source:
            cmd+=['-f','lavfi','-i',source]
        if filter_audio:
            cmd+=['-af',filter_audio]
        cmd+=['-c:v','libx264','-threads','1','-pix_fmt','yuv420p']
        if source:cmd+=['-c:a','aac','-ar','48000']
        qa.command(cmd+['-t','6',str(path)])
        return path

    def test_loudness_peak_silence_and_loudest_window(self):
        path=self.make_video('music','sine=frequency=440:sample_rate=48000:duration=6',
            "loudnorm=I=-14:TP=-1.5,aresample=48000,asetnsamples=n=480,volume=0:enable='between(t,2,3)',volume=12dB:enable='between(t,4.5,4.6)'")
        report=qa.qa(path,self.root/'qa')
        checks={c['name']:c for c in report['checks']}
        # Independent FFmpeg filter output is the reference measurement.
        import subprocess,re
        result=subprocess.run([self.ffmpeg,'-i',str(path),'-af','ebur128=peak=true','-f','null','-'],capture_output=True)
        summary=result.stderr.decode(errors='replace').split('Summary:')[-1]
        self.assertAlmostEqual(checks['loudness']['lufs'],float(re.search(r'I:\s+(-?[\d.]+) LUFS',summary)[1]),delta=.5)
        self.assertAlmostEqual(checks['true_peak']['dbtp'],float(re.search(r'True peak:\s+Peak:\s+(-?[\d.]+) dBFS',summary)[1]),delta=.5)
        quiet=checks['silence']['events']
        self.assertTrue(any(abs(e['seconds']-2)<=.1 and abs(e['end_seconds']-3)<=.1 for e in quiet),quiet)
        peak=checks['loudest_100ms']['events'][0]
        self.assertAlmostEqual(peak['seconds'],4.5,delta=.1)
        self.assertAlmostEqual(peak['end_seconds'],4.6,delta=.1)

    def test_full_scale_square_peak_fails(self):
        path=self.make_video('square','aevalsrc=sgn(sin(2*PI*440*t)):s=48000:d=6')
        report=qa.qa(path,self.root/'qa')
        checks={c['name']:c for c in report['checks']}
        self.assertEqual(checks['true_peak']['level'],'FAIL')
        self.assertEqual(report['level'],'FAIL')
        self.assertGreater(checks['true_peak']['dbtp'],-1)

    def test_no_audio_is_not_silence(self):
        path=self.make_video('silent')
        report=qa.qa(path,self.root/'qa')
        for c in report['checks']:
            if c['name'] in ('loudness','true_peak','silence'):
                self.assertEqual(c['level'],'PASS');self.assertIn('N/A',c['message'])
                self.assertEqual(c['events'],[])


if __name__=='__main__':unittest.main()
