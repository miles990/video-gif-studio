import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from delivery import settings, quantize, rate, encode_frames, probe, audio_delivery, run
from media_runtime import locate, executable
from fx_render import render
from intake import intake, timestamps
from phone_fixtures import phone_clip, phone_chart, phone_markers, phone_timestamp_defects


def decode(path, fmt='rgb24', limit=None):
    return subprocess.check_output([executable('ffmpeg'),'-v','error','-i',str(path),
        *(['-frames:v',str(limit)] if limit else []),'-f','rawvideo','-pix_fmt',fmt,'-'])


def wav(path, x):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000)
        f.writeframes((np.clip(x,-1,1)*32767).astype('<i2').tobytes())


class TimingTests(unittest.TestCase):
    def test_quantization_half_up_and_valid_rates(self):
        for fps in (24,25,30,50,60,100):
            for t in range(0,5000,517):
                event=quantize(t,fps)
                self.assertLessEqual(abs(event['error_ms']),500/fps+1e-9)
            self.assertEqual(quantize(500/fps,fps)['frame'],1)
        for fps in (0,-1,29,29.97):
            with self.assertRaises(ValueError):rate(fps)

    def test_proxy_geometry_and_safe_zone(self):
        for platform in ('tiktok','reels','shorts','youtube','square'):
            conf=settings((160,90),60,platform,True)
            self.assertLessEqual(min(conf['size']),540)
            self.assertEqual(conf['fps'],60)
            self.assertGreater(conf['safe_zone']['text_inset_px'],0)


@unittest.skipUnless(locate('ffmpeg') and locate('ffprobe'),'FFmpeg/ffprobe required')
class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def plan(self, effects=(), duration=1000, size=(96,64), **extra):
        Image.new('RGBA',size,(80,100,120,255)).save(self.root/'source.png')
        data=dict(segments=[dict(type='still',image='source.png',duration_ms=duration)],effects=list(effects),**extra)
        path=self.root/'plan.json';path.write_text(json.dumps(data));return path

    def test_cfr_each_rate_and_container(self):
        plan=self.plan()
        for ext,fps in [('mp4',24),('mp4',25),('mp4',30),('mp4',50),('mp4',60),('mov',30),('webm',30)]:
            out=self.root/(ext+str(fps));render(plan,out,(ext,),fps=fps)
            stream=probe(out/('animation.'+ext))['streams'][0]
            self.assertEqual(stream['r_frame_rate'],f'{fps}/1')
            self.assertEqual(stream['avg_frame_rate'],f'{fps}/1')
            ts=timestamps(out/('animation.'+ext));self.assertEqual(len(ts),fps)
            self.assertTrue(np.all(np.abs(np.diff(ts)-1/fps)<.0011))
            self.assertFalse((out/'frames').exists())

    def test_odd_beat_pixels_and_manifest(self):
        beats=list(range(0,5000,517));(self.root/'beats.json').write_text(json.dumps({'beats_ms':beats}))
        p=self.plan([dict(name='flash_white',amount=dict(on='beats',decay_ms=10))],5000,beatmap='beats.json')
        for fps in (24,30,60):
            out=self.root/str(fps);render(p,out,('mp4',),fps=fps)
            y=np.frombuffer(decode(out/'animation.mp4','gray'),np.uint8).reshape(-1,64,96).mean((1,2))
            events=json.loads((out/'manifest.json').read_text())['events']
            found=np.flatnonzero(y>220).tolist()
            self.assertEqual(found,[e['frame'] for e in events])
            print('P0_TIMING '+json.dumps({'fps':fps,'detected_events':len(found),'max_error_ms':max(abs(e['error_ms']) for e in events)}),flush=True)

    def test_stream_abort_reaps_encoder_and_does_not_publish(self):
        children=[]
        popen=subprocess.Popen
        def capture(*args,**kwargs):
            proc=popen(*args,**kwargs);children.append(proc);return proc
        def broken():
            for _ in range(450): yield Image.new('RGBA',(96,64),'red')
            raise ValueError('injected render failure')
        with patch('delivery.subprocess.Popen',side_effect=capture), self.assertRaisesRegex(ValueError,'injected'):
            encode_frames(broken(),self.root/'out.mp4',settings((96,64)))
        self.assertFalse(list(self.root.glob('*.mp4')))
        self.assertTrue(children);self.assertTrue(all(p.poll() is not None for p in children))

    def test_platform_color_alpha_and_metadata(self):
        for platform in ('tiktok','reels','shorts','youtube','square'):
            out=self.root/(platform+'.mp4');conf=settings((32,32),30,platform)
            rgba=Image.new('RGBA',tuple(conf['size']),(191,191,0,128))
            encode_frames((rgba for _ in range(60)),out,conf,background='ffffff')
            stream=probe(out)['streams'][0]
            for field in ('color_primaries','color_transfer','color_space'):self.assertEqual(stream[field],'bt709')
            self.assertEqual(stream['pix_fmt'],'yuv420p');self.assertEqual(stream['color_range'],'tv')
            self.assertEqual([stream['width'],stream['height']],conf['size'])
            self.assertAlmostEqual(int(stream['bit_rate']),float(conf['bitrate'][:-1])*1000000,delta=float(conf['bitrate'][:-1])*250000)
            rgb=np.frombuffer(decode(out,limit=1),np.uint8).reshape(1,conf['size'][1],conf['size'][0],3)
            np.testing.assert_allclose(rgb[0,100,100],[223,223,127],atol=3)
            raw=out.read_bytes();self.assertLess(raw.index(b'moov'),raw.index(b'mdat'))

    def test_bt709_color_bars(self):
        colors=np.uint8([[191,0,0],[0,191,0],[0,0,191],[191,191,0],[0,191,191],[191,0,191],[191,191,191]])
        rgb=np.repeat(np.repeat(colors[None,...],32,axis=0),32,axis=1)
        out=self.root/'bars.mp4'
        encode_frames((Image.fromarray(rgb).convert('RGBA') for _ in range(3)),out,settings((224,32)))
        decoded=np.frombuffer(decode(out,limit=1),np.uint8).reshape(32,224,3)
        np.testing.assert_allclose(decoded[16,16::32],colors,atol=3)
        print('P0_COLOR '+json.dumps({'max_channel_error':int(np.abs(decoded[16,16::32].astype(int)-colors).max())}),flush=True)

    def test_two_pass_audio_ducking_and_gate(self):
        self.check_audio_ducking(1)

    def test_quieter_speech_fixed_ducking(self):
        self.check_audio_ducking(.1)

    def check_audio_ducking(self, speech_gain):
        n=48000*20;t=np.arange(n)/48000
        white=np.random.default_rng(4).normal(0,1,n)
        frequencies=np.fft.rfftfreq(n,1/48000)
        spectrum=np.fft.rfft(white);spectrum[(frequencies<300)|(frequencies>3400)]=0
        band=np.fft.irfft(spectrum,n)
        speech=speech_gain*.3*band*(.6+.4*np.sin(2*np.pi*4*t))*(((t>=4)&(t<8))|((t>=12)&(t<16)))
        music=.25*np.sin(2*np.pi*110*t)+.05*np.sin(2*np.pi*6000*t)
        phase=t % .5
        music+=.15*np.sin(2*np.pi*60*phase)*np.exp(-phase*35)  # 120 BPM kick.
        wav(self.root/'speech.wav',speech);wav(self.root/'music.wav',music)
        movie=self.root/'audio.mp4';encode_frames((Image.new('RGBA',(32,32),'gray') for _ in range(600)),movie,settings((32,32)))
        report=audio_delivery(movie,20000,{'file':str(self.root/'music.wav')},{'file':str(self.root/'speech.wav')},True)
        values={c['name']:c for c in report['checks']}
        self.assertAlmostEqual(values['loudness']['lufs'],-14,delta=1)
        self.assertLessEqual(values['true_peak']['dbtp'],-1)
        self.assertIn('input_i',report['first_pass']);self.assertIn('normalization_type',report['second_pass'])
        pcm=np.frombuffer(subprocess.check_output([executable('ffmpeg'),'-v','error','-i',str(movie),'-vn','-ac','1','-ar','48000','-f','f32le','-']),np.float32)
        def level(a,b):
            x=pcm[int(a*48000):int(b*48000)];tt=np.arange(len(x))/48000
            return 20*np.log10(abs(np.mean(x*np.exp(-2j*np.pi*110*tt))))
        depth=level(1,3)-level(4.5,7.5)
        self.assertAlmostEqual(depth,10,delta=2)
        self.assertEqual(report['second_pass']['normalization_type'],'linear')
        baseline=np.mean([level(a,a+.05) for a in np.arange(1,3,.05)])
        attack=next(a-4 for a in np.arange(4,4.5,.05) if baseline-level(a,a+.05)>=depth*.9)
        release=next(a-8 for a in np.arange(8,9.5,.05) if baseline-level(a,a+.05)<=1)
        deviation=np.std([level(a,a+.05) for a in np.arange(9,11,.05)])
        self.assertLessEqual(attack,.15+.00001)
        self.assertGreaterEqual(release,.2-.00001);self.assertLessEqual(release,1)
        self.assertLessEqual(deviation,1)
        print('P0_AUDIO '+json.dumps(dict(speech_gain=speech_gain,lufs=values['loudness']['lufs'],true_peak_dbtp=values['true_peak']['dbtp'],
            duck_db=depth,attack_ms=attack*1000,release_ms=release*1000,non_speech_std_db=deviation)),flush=True)
        hot=self.root/'hot.mp4'
        run(['-v','error','-i',str(movie),'-af','volume=15dB','-c:v','copy',str(hot)])
        from qa_media import analyse_audio
        checks=analyse_audio(hot,{'audio':True},[0,20])
        self.assertEqual(next(c['level'] for c in checks if c['name']=='true_peak'),'FAIL')

    def test_phone_vfr_rotation_hdr(self):
        for kind in ('vfr','rotation','hdr'):
            source=phone_clip(self.root,kind);out=self.root/(kind+'-in')
            report=intake(source,out);stream=probe(out/'source.mp4')['streams'][0]
            self.assertEqual(stream['r_frame_rate'],'30/1');self.assertEqual(stream['avg_frame_rate'],'30/1')
            self.assertTrue(report['av_sync']['passed']);self.assertEqual(stream['color_transfer'],'bt709')
            if kind=='vfr':self.assertEqual(report['fps_mode'],'vfr')
            if kind=='rotation':
                self.assertEqual((stream['width'],stream['height']),(108,192))
                self.assertEqual(abs(report['rotation']),90)
                self.assertFalse(any(s.get('rotation') for s in stream.get('side_data_list',[])))
            if kind=='hdr':self.assertIn('mobius',' '.join(report['actions']))

    def test_phone_timestamp_offset_gap_duplicate_and_sync(self):
        source=phone_timestamp_defects(self.root)
        original=timestamps(source)
        self.assertAlmostEqual(original[0],.7,places=3)
        self.assertTrue(np.any(np.diff(original)==0))
        self.assertGreater(np.max(np.diff(original)),.4)
        out=self.root/'repaired';report=intake(source,out)
        pts=timestamps(out/'source.mp4')
        self.assertAlmostEqual(pts[0],0)
        self.assertTrue(np.all(np.abs(np.diff(pts)-1/30)<.0011))
        self.assertTrue(report['av_sync']['passed'])
        self.assertEqual(report['duplicate_or_backward_pts'],1)
        rgb=np.frombuffer(decode(out/'source.mp4'),np.uint8).reshape(-1,108,192,3)
        flashes=np.flatnonzero(rgb[:,:75].mean((1,2,3))>220)/30
        pcm=np.frombuffer(subprocess.check_output([executable('ffmpeg'),'-v','error','-i',str(out/'source.mp4'),
            '-vn','-ac','1','-ar','48000','-f','f32le','-']),np.float32)
        skews=[]
        for at in (1,3.4):
            flash=flashes[np.argmin(abs(flashes-at))]
            start=round((at-.05)*48000)
            click=(start+np.flatnonzero(abs(pcm[start:start+4800])>.1)[0])/48000
            skews.append(abs(flash-click)*1000)
        self.assertLessEqual(max(skews),1000/30)
        self.assertEqual(len(pts),162)
        print('P0_TIMESTAMP '+json.dumps(dict(frames=len(pts),max_marker_skew_ms=max(skews),**report['av_sync'])),flush=True)

    def test_true_odd_phone_dimensions_after_rotation(self):
        base=self.root/'odd.mp4';source=self.root/'odd-rotated.mp4'
        run(['-v','error','-filter_threads','1','-f','lavfi','-i','testsrc=size=1917x1077:rate=30:duration=0.4',
             '-c:v','libx264','-threads','2','-pix_fmt','yuv444p',str(base)])
        self.assertEqual([probe(base)['streams'][0][k] for k in ('width','height')],[1917,1077])
        run(['-v','error','-display_rotation:v:0','270','-i',str(base),'-c','copy',str(source)])
        out=self.root/'odd-intake';report=intake(source,out)
        stream=probe(out/'source.mp4')['streams'][0]
        self.assertEqual((stream['width'],stream['height']),(1078,1918))
        self.assertEqual(report['dimensions']['displayed'],[1077,1917])
        self.assertEqual(report['dimensions']['pad_right_px'],1)
        self.assertEqual(report['dimensions']['pad_bottom_px'],1)
        self.assertFalse(any(s.get('rotation') for s in stream.get('side_data_list',[])))
        print('P0_ODD_DIMENSIONS '+json.dumps(report['dimensions']),flush=True)

    def test_intake_failure_is_one_readable_line(self):
        import contextlib
        import io
        import intake as module
        errors=io.StringIO()
        with patch.object(sys,'argv',['intake',str(self.root/'missing.mp4'),'--out',str(self.root/'bad')]), contextlib.redirect_stderr(errors):
            code=module.main()
        self.assertEqual(code,2)
        self.assertEqual(len(errors.getvalue().splitlines()),1)
        self.assertIn('intake:',errors.getvalue())
        self.assertNotIn('Traceback',errors.getvalue())
        self.assertFalse((self.root/'bad').exists())

    def test_proxy_event_identity_and_model_bypass(self):
        p=self.plan([dict(name='flash_white',start_ms=517,end_ms=800)],1000,(960,540),interpolate='rife',experimental=True)
        with patch('fx.timewarp.session',side_effect=AssertionError('no optional model')):
            render(p,self.root/'proxy',('mp4',),proxy=True)
        m=json.loads((self.root/'proxy/manifest.json').read_text())
        self.assertEqual(m['size'],[320,180]);self.assertEqual(m['events'][0]['frame'],16)
        render(p,self.root/'full',('mp4',),interpolate='none')
        full=json.loads((self.root/'full/manifest.json').read_text())
        self.assertEqual(m['events'],full['events']);self.assertEqual(m['cuts'],full['cuts'])

    def test_proxy_depth_bypass_records_the_skipped_event(self):
        p=self.plan([{'name':'parallax','start_ms':517}],experimental=True)
        with patch('fx.timewarp.session',side_effect=AssertionError('optional model loaded')):
            render(p,self.root/'depth-proxy',('mp4',),proxy=True)
        m=json.loads((self.root/'depth-proxy/manifest.json').read_text())
        self.assertIn('effect:parallax',m['delivery']['proxy_skipped'])
        self.assertEqual(m['events'][0]['frame'],16)

    def test_silent_track_is_rejected_and_no_audio_is_valid(self):
        from qa_media import analyse_audio
        wav(self.root/'silence.wav',np.zeros(48000*2))
        p=self.plan(duration=2000,music={'file':'silence.wav'},loudnorm=True)
        with self.assertRaisesRegex(ValueError,'silent'):
            render(p,self.root/'silent-track',('mp4',))
        self.assertFalse((self.root/'silent-track').exists())
        p=self.plan(duration=2000);render(p,self.root/'silent-video',('mp4',))
        self.assertTrue(all(c['level']=='PASS' and not c['applicable'] for c in
            analyse_audio(self.root/'silent-video/animation.mp4',{'audio':False},[0,2])))

    def test_composer_streams_and_exporter_quantizes_boundaries(self):
        from compose_timeline import compose
        from video_export import export
        p=self.plan(duration=1000)
        with patch('compose_timeline.export_timeline',side_effect=AssertionError('whole-film exporter')):
            compose(p,self.root/'composed',('mp4',),fps=60,proxy=True)
        self.assertEqual(probe(self.root/'composed/animation.mp4')['streams'][0]['avg_frame_rate'],'60/1')
        frames=self.root/'frames';frames.mkdir()
        Image.new('RGBA',(32,32),'red').save(frames/'00000.png')
        Image.new('RGBA',(32,32),'blue').save(frames/'00001.png')
        (self.root/'times.json').write_text(json.dumps({'durations_ms':[517,483]}))
        result=export(frames,self.root/'times.json',self.root/'grid.mp4')
        rgb=np.frombuffer(decode(self.root/'grid.mp4'),np.uint8).reshape(-1,32,32,3)
        blue=np.flatnonzero(rgb[:,16,16,2]>200)[0]
        self.assertEqual(blue,16);self.assertEqual(result['events'][1]['frame'],blue)

    def test_legacy_png_gif_above_512_mib(self):
        # 65 portrait exposures occupy 514.16 MiB as decoded RGBA.
        frames=self.root/'input/frames';frames.mkdir(parents=True)
        for i in range(65):
            Image.new('RGBA',(1080,1920),(i*3,90,150,255)).save(frames/f'{i:05d}.png')
        (frames.parent/'manifest.json').write_text(json.dumps({'durations_ms':[40]*65}))
        for effects in ([],[{'name':'grade','sat':.7}]):
            p=self.root/'large.json'
            p.write_text(json.dumps(dict(segments=[dict(type='animation',manifest='input/manifest.json')],effects=effects,fps=25)))
            out=self.root/('large-fx' if effects else 'large-plain')
            render(p,out,('png','gif'))
            self.assertEqual(len(list((out/'frames').glob('*.png'))),65)
            with Image.open(out/'animation.gif') as gif:
                self.assertEqual(gif.size,(1080,1920))
                self.assertEqual(gif.n_frames,65)
        print('P0_RASTER '+json.dumps(dict(frames=65,decoded_mib=65*1080*1920*4/1024**2,paths=2)),flush=True)

    def test_stream_pixels_equal_disk_frame_reference(self):
        (self.root/'beats.json').write_text(json.dumps({'beats_ms':[0,500]}))
        p=self.plan([{'name':'zoom_punch','amount':{'on':'beats'}},{'name':'grade','sat':.7},{'name':'halation','amount':.2}],beatmap='beats.json')
        yy,xx=np.indices((64,96))
        rgb=np.stack(((xx*3)%256,(yy*4)%256,((xx+yy)*2)%256),axis=2).astype(np.uint8)
        Image.fromarray(rgb).save(self.root/'source.png')
        render(p,self.root/'stream',('mp4',))
        frames=self.root/'reference-frames';frames.mkdir()
        def save_reference(images,target,config,background):
            count=0
            for i,image in enumerate(images):image.save(frames/f'{i:05d}.png');count+=1
            return {'container_duration_ms':count*1000/config['fps'],'encoded_frames':count}
        with patch('delivery.encode_frames',side_effect=save_reference):
            render(p,self.root/'reference',('mp4',))
        def files():
            for path in sorted(frames.glob('*.png')):
                with Image.open(path) as image:yield image.convert('RGBA')
        encode_frames(files(),self.root/'reference.mp4',settings((96,64)))
        # The reference encodes saved PNG pixels rather than a live render generator.
        self.assertEqual(decode(self.root/'stream/animation.mp4'),decode(self.root/'reference.mp4'))

    def test_invalid_video_rate_has_clean_cli_error_and_no_output(self):
        import contextlib
        import io
        from fx_render import main
        p=self.plan()
        for fps in (0,-1,29):
            out=self.root/('bad'+str(fps));errors=io.StringIO()
            with contextlib.redirect_stderr(errors):
                code=main([str(p),'--out',str(out),'--formats','mp4','--fps',str(fps),'--no-user-fx'])
            self.assertEqual(code,2);self.assertIn('24, 25, 30, 50, 60',errors.getvalue())
            self.assertNotIn('Traceback',errors.getvalue());self.assertFalse(out.exists())

    def test_alpha_containers_decode_fractional_alpha(self):
        for ext in ('mov','webm'):
            out=self.root/('alpha.'+ext)
            encode_frames((Image.new('RGBA',(32,32),(120,80,40,127)) for _ in range(3)),out,settings((32,32)))
            raw=subprocess.check_output([executable('ffmpeg'),'-v','error',*(['-c:v','libvpx-vp9'] if ext=='webm' else []),
                '-i',str(out),'-f','rawvideo','-pix_fmt','rgba','-'])
            alpha=np.frombuffer(raw,np.uint8).reshape(-1,32,32,4)[...,3]
            self.assertLessEqual(np.abs(alpha.astype(float)-127).max(),2)

    def test_all_rotation_angles_apply_once(self):
        for rotation in (90,180,270):
            source=phone_clip(self.root,'rotation',rotation)
            out=self.root/('rot'+str(rotation));intake(source,out)
            # Independent FFmpeg autorotation is the reference pixel placement.
            source_info=probe(source)['streams'][0]
            self.assertEqual(abs(source_info['side_data_list'][0]['rotation'])%180,rotation%180)
            info=probe(out/'source.mp4')['streams'][0];w,h=info['width'],info['height']
            rgb=np.frombuffer(decode(out/'source.mp4'),np.uint8).reshape(-1,h,w,3)[0]
            expected=np.frombuffer(decode(source),np.uint8).reshape(-1,h,w,3)[0]
            def red_center(x):
                mask=(x[...,0]>150)&(x[...,1]<100)&(x[...,2]<100)
                return np.array(np.nonzero(mask)).mean(axis=1)
            np.testing.assert_allclose(red_center(rgb),red_center(expected),atol=1)
            center=red_center(rgb)
            self.assertLess(center[0],h/2);self.assertLess(center[1],w/2)
            white=(rgb.min(axis=2)>220)
            self.assertLess(np.nonzero(white)[0].min(),h/3)
            self.assertFalse(any(s.get('rotation') for s in info.get('side_data_list',[])))

    def test_hdr_chart_decoded_gray_and_hue(self):
        import cv2
        source=phone_chart(self.root);out=self.root/'hdr-chart';report=intake(source,out)
        rgb=np.frombuffer(decode(out/'source.mp4'),np.uint8).reshape(-1,120,220,3)[0]
        gray=rgb[40,10::20].mean(axis=1)
        self.assertTrue(np.all(np.diff(gray)>0),gray)
        self.assertLessEqual(gray[0],30);self.assertGreaterEqual(gray[-1],200)
        self.assertTrue(90<=gray[5]<=170,gray)
        y=np.frombuffer(decode(out/'source.mp4','yuv444p',limit=1),np.uint8).reshape(3,120,220)[0,40,10::20]
        self.assertTrue(np.all(np.diff(y.astype(int))>0),y)
        self.assertLessEqual(y[0],30);self.assertGreaterEqual(y[-1],200)
        self.assertTrue(90<=y[5]<=170,y)
        expected=np.uint8([[[191,0,0],[0,191,0],[0,0,191],[191,191,0],[224,172,105]]])
        actual=rgb[100,22::44][None,...]
        e=cv2.cvtColor(expected,cv2.COLOR_RGB2HSV).astype(float)[0]
        a=cv2.cvtColor(actual,cv2.COLOR_RGB2HSV).astype(float)[0]
        delta=np.abs(e[:,0]-a[:,0]);self.assertTrue(np.all(np.minimum(delta,180-delta)*2<=12),(e,a))
        self.assertGreaterEqual(a[-1,1],e[-1,1]*.6)
        self.assertEqual(report['color']['color_transfer'],'smpte2084')
        print('P0_HDR '+json.dumps({'gray_rgb_means':gray.tolist(),'gray_y':y.tolist(),'max_hue_error_degrees':float(np.max(np.minimum(delta,180-delta)*2)),
            'skin_saturation_ratio':float(a[-1,1]/e[-1,1])}),flush=True)

    def test_phone_vfr_barcode_and_click_sync(self):
        source=phone_markers(self.root);out=self.root/'markers-in';report=intake(source,out)
        self.assertEqual(report['fps_mode'],'vfr')
        rgb=np.frombuffer(decode(out/'source.mp4'),np.uint8).reshape(-1,108,192,3)
        bits=rgb[:,96,6::12].mean(axis=2)>128
        ids=bits.astype(int)@(2**np.arange(16))
        difference=np.abs(ids/120-np.arange(len(ids))/30)
        self.assertLessEqual(difference.max(),1/30+.001)
        pcm=np.frombuffer(subprocess.check_output([executable('ffmpeg'),'-v','error','-i',str(out/'source.mp4'),
            '-vn','-ac','1','-ar','48000','-f','f32le','-']),np.float32)
        skews=[]
        for second in range(10):
            visual=np.flatnonzero(rgb[second*30:(second+1)*30,:70].mean((1,2,3))>220)[0]/30+second
            audio=np.flatnonzero(np.abs(pcm[second*48000:(second+1)*48000])>.1)[0]/48000+second
            self.assertLessEqual(abs(visual-audio),1/30)
            skews.append(abs(visual-audio)*1000)
        print('P0_PHONE '+json.dumps({'max_source_time_error_ms':float(difference.max()*1000),'max_flash_click_skew_ms':max(skews),'events':len(skews)}),flush=True)

    def test_hot_audio_normalizes_and_cli_gate_rejects_raw_hot(self):
        import qa_media
        t=np.arange(48000*6)/48000
        wav(self.root/'hot.wav',np.clip(1.1*np.sin(2*np.pi*110*t)+.2*np.sin(2*np.pi*6000*t),-1,1))
        p=self.plan(duration=6000,music={'file':'hot.wav'},loudnorm=True)
        render(p,self.root/'normalized',('mp4',))
        checks=qa_media.analyse_audio(self.root/'normalized/animation.mp4',{'audio':True},[0,6])
        self.assertTrue(all(c['level']!='FAIL' for c in checks),checks)
        values={c['name']:c for c in checks}
        print('P0_HOT '+json.dumps({'lufs':values['loudness']['lufs'],'true_peak_dbtp':values['true_peak']['dbtp']}),flush=True)
        plan=json.loads(p.read_text());plan['loudnorm']=False;p.write_text(json.dumps(plan))
        with self.assertRaisesRegex(RuntimeError,'Audio delivery QA failed'):
            render(p,self.root/'failed',('mp4',))
        self.assertFalse((self.root/'failed').exists())
        hot=self.root/'hot.mp4'
        run(['-v','error','-i',str(self.root/'normalized/animation.mp4'),'-af','volume=15dB','-c:v','copy',str(hot)])
        result=subprocess.run([sys.executable,str(Path(qa_media.__file__)),str(hot),'--out',str(self.root/'hot-qa')],capture_output=True)
        self.assertEqual(result.returncode,1)
        q=json.loads((self.root/'hot-qa/report.json').read_text())
        self.assertEqual(next(c['level'] for c in q['checks'] if c['name']=='true_peak'),'FAIL')

    def test_source_audio_retention_and_explicit_off(self):
        t=np.arange(48000*6)/48000
        wav(self.root/'voice.wav',.1*np.sin(2*np.pi*440*t))
        wav(self.root/'bed.wav',.1*np.sin(2*np.pi*110*t))
        p=self.plan(duration=6000,source_audio='voice.wav',music={'file':'bed.wav'},duck=False,loudnorm=True)
        levels=[]
        for keep in (False,True):
            out=self.root/str(keep);render(p,out,('mp4',),keep_audio=keep)
            raw=subprocess.check_output([executable('ffmpeg'),'-v','error','-i',str(out/'animation.mp4'),'-vn','-ac','1','-ar','48000','-f','f32le','-'])
            x=np.frombuffer(raw,np.float32)[48000:5*48000];tt=np.arange(len(x))/48000
            levels.append(20*np.log10(abs(np.mean(x*np.exp(-2j*np.pi*440*tt)))+1e-12))
        self.assertGreater(levels[1]-levels[0],20)
        print('P0_SOURCE_AUDIO '+json.dumps({'retained_440hz_increase_db':levels[1]-levels[0]}),flush=True)

    def test_process_tree_memory_is_bounded_at_small_resolution(self):
        import importlib.util
        path=Path(__file__).resolve().parents[1]/'wow/fx/benchmark_p0.py'
        spec=importlib.util.spec_from_file_location('benchmark_p0',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        results=[]
        for seconds in (2,6):
            base=self.root/str(seconds);plan=module.fixture(base/'input',(192,320),seconds)
            output=base/'output';output.mkdir();results.append(module.measure(plan,output/'render'))
        peaks=[r['peak_bytes'] for r in results]
        self.assertTrue(all(0<p<1610612736 for p in peaks),peaks)
        self.assertLessEqual(abs(peaks[1]-peaks[0]),max(peaks[0]*.15,150*1024**2))


if __name__=='__main__':unittest.main()
