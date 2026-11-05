"""P1 offline contract tests. Synthetic audio/masks only; no model or network calls."""
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import captions
from fx.easing import EASINGS,spring
from fx.effects.camera import motion,MOVES,camera_move
from fx.effects.typography import resolve_font,check_glyphs
from fx import Context
from delivery import settings,probe
from fx_render import render,validate_plan,main as fx_main
from beat_layers import layers,apply_layers
from music_fit import candidates,join_audio,remap_beats,fit,no_music_export
from sfx import synthesize,resolve,write_wav,read_audio,render_track,events_from_plan,KINDS
from reframe import bbox,plan_path,transform,Reframer
from review_shots import build
from media_runtime import locate,executable


def songmap():
    bounds=[0,8000,24000,40000,48000,60000,64000]
    return dict(duration_ms=64000,beats_ms=list(range(0,64000,500)),downbeats_ms=list(range(0,64000,2000)),
                sections=[dict(start_ms=a,end_ms=b,label=str(i)) for i,(a,b) in enumerate(zip(bounds,bounds[1:]))])


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        env=patch.dict(os.environ,{'VIDEO_GIF_INTERPOLATE':''});env.start();self.addCleanup(env.stop)

    def save(self,name,data):
        file=self.root/name;file.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');return file

    def plan(self,**kwargs):
        Image.new('RGBA',(192,108),(65,90,140,255)).save(self.root/'a.png')
        return self.save('plan.json',dict(segments=[dict(type='still',image='a.png',duration_ms=1000)],**kwargs))


class CaptionTests(TempCase):
    def prepared(self,style='pop',**extra):
        return captions.prepare(dict(words=[dict(text='Make it pop 3.14',start_ms=0,end_ms=1000)],style=style,**extra),self.root,True)

    def test_line_break_rules_all_widths(self):
        samples=['我們今天要去台北市政府參加開放資料活動，真的嗎？好！','他說：「這個『效果』太棒了！」然後……就走了。','Version 2.0 在 2026 年 11 月 4 日上線（共 3.14 GB）','停——等……好！']
        for limit in (8,12,16):
            for sample in samples:
                lines=captions.break_lines(sample,limit)
                self.assertEqual(''.join(lines).replace(' ',''),sample.replace(' ',''))
                for line in lines:
                    self.assertNotIn(line[0],captions.CLOSING);self.assertNotIn(line[-1],captions.OPENING)
                    self.assertLessEqual(captions.width(line),limit)
                for token in ('台北市政府','開放資料','效果','Version','2.0','2026','3.14 GB','……','——'):
                    if token in sample:self.assertTrue(any(token in line for line in lines),token)

    def test_unbreakable_long_token_split_with_warning(self):
        with self.assertWarnsRegex(UserWarning,'split'): lines=captions.break_lines('Extraordinary',3)
        self.assertEqual(''.join(lines),'Extraordinary')
        self.assertTrue(all(captions.width(line)<=3 for line in lines))
        for n in (0,-1,float('nan')):
            with self.assertRaises(ValueError): captions.break_lines('text',n)

    def test_offline_json_srt_and_injected_aligner(self):
        fixture=Path(__file__).parent/'fixtures/p1_words.json'
        words,method=captions.load_words({'words':str(fixture)})
        self.assertEqual(len(words),9);self.assertEqual(method,'user_word_timing')
        captions.export_srt(words,self.root/'words.srt')
        restored,_=captions.load_words({'srt':'words.srt'},self.root)
        self.assertEqual(restored[0]['start_ms'],0);self.assertEqual(restored[-1]['end_ms'],2500)
        actual,method=captions.load_words({'audio':'fake.wav','script':'hello'},self.root,lambda audio,script: [dict(text=script,start_ms=50,end_ms=500)])
        self.assertEqual(actual[0]['start_ms'],50);self.assertEqual(method,'injected_alignment_engine')

    def test_script_fallback_honest_and_engine_missing(self):
        with warnings.catch_warnings(record=True) as caught:
            words,method=captions.load_words({'script':'Hello world','duration_ms':1000})
        self.assertTrue(caught);self.assertIn('approximate',method);self.assertAlmostEqual(words[-1]['end_ms'],1000)
        with patch.dict(sys.modules,{'faster_whisper':None}):
            with self.assertRaisesRegex(RuntimeError,'--srt'): captions.faster_whisper_engine('fake.wav','fake-model')

    def test_no_model_import_for_words(self):
        with patch.dict(sys.modules,{'faster_whisper':None,'torch':None}): self.prepared()

    def test_glyph_list_and_strict_rejection(self):
        font=resolve_font()
        self.assertEqual(check_glyphs(font,'Hello 世界'),[])
        with warnings.catch_warnings(record=True) as caught:
            with self.assertRaisesRegex(ValueError,r'U\+10FFFF'):check_glyphs(font,'\U0010ffff',True)
        self.assertTrue(caught)

    def test_presets_gate_and_keyword_override(self):
        with self.assertRaisesRegex(ValueError,'experimental'):captions.prepare({'words':[]},self.root)
        fixture=Path(__file__).parent/'fixtures/p1_words.json'
        p=captions.prepare(dict(words=str(fixture),keywords=['真的嗎']),self.root,True)
        highlighted=''.join(c['char'] for line in p['lines'] for c in line['chars'] if c['highlight'])
        self.assertEqual(highlighted,'真的嗎')
        for preset in captions.PRESETS:self.assertEqual(self.prepared(preset)['status'],'experimental')

    def test_safe_zones_all_positions_and_presets(self):
        config=settings((1080,1920),platform='tiktok',proxy=True)
        for position in ('top','center','bottom'):
            for preset in captions.PRESETS:
                data=self.prepared(dict(preset=preset,position=position,words_per_line=8))
                renderer=captions.CaptionRenderer(data,config['size'],config['safe_zone'])
                for t in (0,50,90,180,390,500):
                    image=renderer.overlay(Image.new('RGBA',config['size']),t);box=image.getbbox()
                    self.assertIsNotNone(box);left,top,right,bottom=renderer.bounds
                    self.assertGreaterEqual(box[0],left);self.assertGreaterEqual(box[1],top)
                    self.assertLessEqual(box[2],right);self.assertLessEqual(box[3],bottom)

    def test_word_ink_onset_from_pixels(self):
        p=captions.prepare(dict(words=[dict(text='A',start_ms=100,end_ms=500),dict(text='B',start_ms=500,end_ms=900)],
                               style=dict(preset='clean',box=None,shadow=0,words_per_line=1)),self.root,True)
        cfg=settings((540,960));renderer=captions.CaptionRenderer(p,cfg['size'],cfg['safe_zone'])
        blank=Image.new('RGBA',cfg['size'])
        visible=[renderer.overlay(blank,k*1000/30).getbbox() is not None for k in range(30)]
        self.assertEqual(visible.index(True),3)
        self.assertIsNone(renderer.overlay(blank,900).getbbox())

    def test_typewriter_non_decreasing_and_pop_peak(self):
        p=self.prepared(dict(preset='typewriter',box=None,shadow=0,words_per_line=20));cfg=settings((540,960))
        r=captions.CaptionRenderer(p,cfg['size'],cfg['safe_zone']);blank=Image.new('RGBA',cfg['size'])
        counts=[np.count_nonzero(np.asarray(r.overlay(blank,t))[...,3]) for t in range(0,1000,40)]
        self.assertTrue(all(b>=a for a,b in zip(counts,counts[1:])))
        p=self.prepared(dict(preset='pop',words_per_line=20));r=captions.CaptionRenderer(p,cfg['size'],cfg['safe_zone'])
        boxes=[r.overlay(blank,t).getbbox() for t in (0,90,200)]
        widths=[b[2]-b[0] for b in boxes];self.assertGreater(widths[1]/widths[0],1.1);self.assertLess(widths[1]/widths[0],1.35);self.assertEqual(widths[0],widths[2])

    def test_style_fields_change_pixels(self):
        cfg=settings((540,960));blank=Image.new('RGBA',cfg['size'])
        base=dict(preset='clean',words_per_line=20)
        def pixels(style):
            data=captions.prepare(dict(words=[dict(text=t,start_ms=i*150,end_ms=1000) for i,t in enumerate(('Make','it','pop','3.14'))],style=style),self.root,True)
            return np.array(captions.CaptionRenderer(data,cfg['size'],cfg['safe_zone']).overlay(blank,500))
        reference=pixels(base)
        for key,value in [('size',120),('stroke',12),('shadow',12),('box','333333'),('keyword_color','FF9900'),('entrance','pop'),('words_per_line',6),('position','top'),('safe_zone',dict(bottom=.65))]:
            with self.subTest(field=key): self.assertFalse(np.array_equal(reference,pixels(dict(base,**{key:value}))))
        with self.assertRaises(ValueError):self.prepared(dict(font='no-font.ttf'))

    def test_malformed_caption_inputs_fail_before_output(self):
        for words in (None,{},['bad'],[dict(text='x',start_ms=float('nan'),end_ms=5)]):
            with self.assertRaises(ValueError):captions.validate_words(words)
        with self.assertRaises(ValueError):self.prepared(dict(color=None))

    def test_bounce_overshoot_and_settle_pixels(self):
        p=captions.prepare(dict(words=[dict(text='TEST',start_ms=0,end_ms=1000)],style=dict(preset='bounce',box=None)),self.root,True)
        cfg=settings((1080,1920));renderer=captions.CaptionRenderer(p,cfg['size'],cfg['safe_zone']);blank=Image.new('RGBA',cfg['size'])
        y=[renderer.overlay(blank,t).getbbox()[1] for t in (0,150,300,400,500)]
        self.assertGreater(y[0],y[-1]);self.assertLess(y[1],y[-1]);self.assertEqual(y[-2],y[-1])


class CameraTests(unittest.TestCase):
    def test_penner_101_points_independent_references(self):
        refs=dict(easeInExpo=lambda t:0 if t==0 else math.exp(math.log(2)*(10*t-10)),
                  easeOutExpo=lambda t:1 if t==1 else 1-math.exp(-10*t*math.log(2)),
                  easeInOutCubic=lambda t:4*t*t*t if t<.5 else .5*((2*t-2)**3+2),
                  easeOutCubic=lambda t:t*(3+t*(t-3)),easeInOutSine=lambda t:math.sin(t*math.pi/2)**2)
        for name,fn in EASINGS.items():
            self.assertEqual(fn(0),0);self.assertEqual(fn(1),1)
            self.assertLess(max(abs(fn(t)-refs[name](t)) for t in np.linspace(0,1,101)),1e-9)

    def test_named_motion_contract(self):
        self.assertGreaterEqual((motion('crash_in',100)[0]-1)/.35,.9)
        self.assertLessEqual(motion('crash_out',600)[0],1.035)
        samples=np.array([motion('smooth_in',t)[0] for t in np.linspace(0,1000,31)])
        velocity=np.diff(samples);self.assertTrue(np.all(velocity>=0));self.assertIn(int(np.argmax(velocity)),range(12,18))
        self.assertLess(velocity[0],velocity.max()*.15)
        self.assertAlmostEqual(motion('punch',200)[0],1)
        shifts=np.diff([motion('whip',t)[1] for t in np.arange(0,200,1000/30)])
        self.assertGreater(abs(shifts).max(),.25)
        with self.assertRaisesRegex(ValueError,'crash_in'):motion('bad',1)

    def test_spring_analytic_under_critical_over(self):
        k,c,m=180,18,1;zeta=c/(2*math.sqrt(k*m));wn=math.sqrt(k/m)
        peak_time=math.pi/(wn*math.sqrt(1-zeta*zeta))
        overshoot=math.exp(-zeta*math.pi/math.sqrt(1-zeta*zeta))
        self.assertAlmostEqual(spring(peak_time,k,c,m)-1,overshoot,places=10)
        values=[spring(t,100,20,1) for t in np.linspace(0,2,101)]
        self.assertTrue(all(a<=b<=1 for a,b in zip(values,values[1:])))
        self.assertAlmostEqual(spring(0,100,30,1),0);self.assertLess(spring(.1,100,30,1),1)

    def test_rgba_determinism_and_input_preserved(self):
        frame=np.zeros((64,96,4),np.uint8);frame[15:45,30:60]=[220,100,10,255];saved=frame.copy()
        for name in MOVES:
            result=camera_move(frame,80,Context(96,64),move=name)
            self.assertEqual(result.dtype,np.uint8);self.assertEqual(result.shape,frame.shape)
            self.assertTrue(np.array_equal(result,camera_move(frame,80,Context(96,64),move=name)))
        self.assertTrue(np.array_equal(saved,frame))

    def test_subject_anchor_centroid_pixels(self):
        frame=np.zeros((160,240,4),np.uint8);frame[20:70,35:85]=[255,100,10,255]
        out=camera_move(frame,100,Context(240,160),move='crash_in',anchor='subject')
        def center(a):
            ys,xs=np.indices(a.shape[:2]);weight=a[...,3];return np.array([(xs*weight).sum()/weight.sum(),(ys*weight).sum()/weight.sum()])
        self.assertLess(np.linalg.norm(center(out)-center(frame)),2)


class BeatAndFitTests(TempCase):
    def test_density_counts_and_boundary_style_sets(self):
        expected={'low':(6,9),'mid':(13,17),'high':(28,40)};counts=[]
        for density,(low,high) in expected.items():
            design=layers(songmap(),cut_density=density);counts.append(len(design['cuts_ms']))
            self.assertTrue(low<=counts[-1]<=high)
            self.assertTrue(set(design['cuts_ms'])<=set(songmap()['downbeats_ms']))
            self.assertTrue({8000,24000,40000,48000,60000}<=set(design['cuts_ms']))
            self.assertTrue(set(design['accents_ms'])<=set(songmap()['beats_ms']))
            for a,b in zip(design['sections'],design['sections'][1:]):self.assertNotEqual(a['effect'],b['effect'])
        self.assertEqual(counts,sorted(set(counts)))

    def test_inferred_downbeats_and_invalid_density(self):
        self.assertTrue(layers(dict(beats_ms=list(range(0,8000,500))))['downbeats_inferred'])
        with self.assertRaisesRegex(ValueError,r'low\|mid\|high'):layers(songmap(),cut_density='wild')

    def test_layer_plan_cuts_and_accents(self):
        plan,design=apply_layers(dict(segments=[dict(type='still',image='a.png')],cut_density='mid'),songmap())
        self.assertEqual(sum(s['duration_ms'] for s in plan['segments']),64000)
        self.assertEqual(len(plan['segments'])-1,len(design['cuts_ms']));self.assertEqual(len(plan['effects']),6)

    def test_three_distinct_candidates_and_bar_joins(self):
        choices=candidates(songmap(),30000)
        self.assertEqual(len({tuple(c) for c in choices}),3)
        edges=set(songmap()['downbeats_ms'])|{64000}
        for spans in choices:
            self.assertLessEqual(abs(sum(b-a for a,b in spans)-30000),2000)
            self.assertTrue(all(a in edges and b in edges for a,b in spans))

    def test_join_sample_derivative_tail_and_remap(self):
        rate=8000;t=np.arange(64*rate)/rate
        wave=.2*np.sin(2*np.pi*(110*t+.008*t*t))+.04*np.sin(2*np.pi*173*t)
        pcm=np.column_stack((wave,wave*.8));threshold=np.percentile(np.abs(np.diff(pcm,axis=0)),99.9)*1.5
        for spans in candidates(songmap(),30000):
            result,joins=join_audio(pcm,spans,rate)
            for join in joins:
                center=round(join['output_ms']*rate/1000);radius=round(.02*rate)
                self.assertLessEqual(np.max(np.abs(np.diff(result[center-radius:center+radius],axis=0))),threshold)
                self.assertLessEqual(abs(join['out_ms']-join['zero_out_ms']),10)
            self.assertLess(np.sqrt(np.mean(result[-round(.05*rate):]**2)),.01)
            mapped=remap_beats(songmap(),spans)
            self.assertEqual(mapped['duration_ms'],sum(b-a for a,b in spans))
            self.assertTrue(set(layers(mapped)['cuts_ms'])<=set(mapped['downbeats_ms']))

    def test_fit_writes_three_wavs_and_manifests(self):
        rate=48000;t=np.arange(rate*8)/rate;pcm=np.column_stack([.1*np.sin(2*np.pi*110*t)]*2)
        write_wav(self.root/'song.wav',pcm)
        beats=dict(duration_ms=8000,beats_ms=list(range(0,8000,125)),downbeats_ms=list(range(0,8000,500)))
        result=fit(self.root/'song.wav',beats,4000,self.root/'fit')
        self.assertEqual(len(result['candidates']),3);self.assertEqual(len(list((self.root/'fit').glob('*.wav'))),3)

    def test_join_high_frequency_no_spike(self):
        rate=48000;t=np.arange(rate*8)/rate
        x=.2*np.sin(2*np.pi*(110*t+.008*t*t))+.04*np.sin(2*np.pi*173*t)
        pcm=np.column_stack([x,x*.8]);out,joins=join_audio(pcm,[(0,2000),(4000,8000)])
        center=round(joins[0]['output_ms']*48)
        def energy(at):
            block=out[at:at+960,0]*np.hanning(960);spectrum=np.fft.rfft(block)
            return float(np.mean(abs(spectrum[np.fft.rfftfreq(960,1/rate)>8000])**2))
        surrounding=[energy(k) for k in list(range(center-9600,center-960,960))+list(range(center+960,center+9600,960))]
        self.assertLessEqual(10*np.log10(energy(center-480)/np.mean(surrounding)),6)


class SoundTests(TempCase):
    def test_priority_fingerprints_and_provenance(self):
        user=self.root/'user';kenney=self.root/'kenney';user.mkdir();kenney.mkdir()
        t=np.arange(4800)/48000
        for kind in KINDS:
            for root,freq in ((user,3300),(kenney,4700)):write_wav(root/(kind+'.wav'),np.column_stack([.2*np.sin(2*np.pi*freq*t)]*2))
        for kind in KINDS:
            for u,k,source,freq in ((user,kenney,'user',3300),(None,kenney,'kenney',4700),(None,None,'procedural',None)):
                pcm,report=resolve(kind,u,k);self.assertEqual(report['source'],source)
                if freq:self.assertAlmostEqual(np.argmax(abs(np.fft.rfft(pcm[:,0])))*48000/len(pcm),freq,delta=10)
                else:self.assertTrue(np.array_equal(pcm,synthesize(kind)))

    def test_rule_table_and_dedup_riser(self):
        effects=[dict(name=n,params={},start_ms=100,trigger_times_ms=[]) for n in ('flash_white','zoom_punch','text','rgb_split')]
        events=events_from_plan({},effects,[dict(name='whip_pan',cut_ms=200)],[],fps=30)
        self.assertEqual([e['kind'] for e in events].count('hit'),1)
        self.assertEqual(set(e['kind'] for e in events),{'hit','pop','glitch','whoosh'})

    def test_kenney_zip_license_and_path_traversal(self):
        from download_kenney_audio import install_zip
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as f:f.writestr('License.txt','Kenney CC0');f.writestr('Audio/click.ogg',b'fixture')
        record=install_zip(stream.getvalue(),self.root/'pack','official fixture');self.assertEqual(record['license'],'CC0-1.0')
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as f:f.writestr('../escape','bad');f.writestr('License.txt','CC0')
        with self.assertRaisesRegex(ValueError,'Unsafe'):install_zip(stream.getvalue(),self.root/'bad','test')

    @unittest.skipUnless(locate('ffmpeg'),'FFmpeg required for float PCM SFX intermediate')
    def test_sample_alignment_from_pcm(self):
        events=[dict(kind='click',at_ms=517,requested_ms=517,event='shutter'),dict(kind='riser',at_ms=1500,requested_ms=1500,event='ramp')]
        report=render_track(events,2000,self.root/'sfx.wav')
        pcm=read_audio(self.root/'sfx.wav');energy=np.max(abs(pcm),axis=1)
        self.assertLessEqual(abs(np.flatnonzero(energy>.001)[0]/48-517),10)
        active=np.flatnonzero(energy>.001);self.assertLessEqual(abs(active[-1]/48-1500),10)
        self.assertEqual(report[0]['anchor_sample'],24816);self.assertFalse((self.root/'sfx.f32.partial').exists())


class ReframeTests(TempCase):
    def test_mask_bbox_and_missing_fallback(self):
        mask=np.zeros((90,160),np.uint8);mask[20:80,50:80]=255
        self.assertEqual(bbox(mask),[50,20,80,80]);self.assertIsNone(bbox(mask*0))
        report=plan_path([None]*5,(160,90),(90,160));self.assertEqual(report['missing_subject_frames'],list(range(5)))

    def test_smooth_follow_head_and_title_space(self):
        boxes=[[400+i*2,180,560+i*2,750] for i in range(120)]
        report=plan_path(boxes,(1920,1080));scale=1920/report['path'][0]['crop'][3]
        centers=np.array([[p['crop'][0],p['crop'][1]] for p in report['path']])*scale
        self.assertLessEqual(np.linalg.norm(np.diff(centers,axis=0),axis=1).max(),12)
        self.assertLessEqual(np.linalg.norm(np.diff(centers,n=2,axis=0),axis=1).max(),4)
        for p in report['path']:
            x,y,right,bottom=p['subject_bbox'];self.assertGreaterEqual(x,0);self.assertLessEqual(right,1080)
            self.assertGreaterEqual(y,.1*(bottom-y));self.assertLessEqual(bottom,1920*.80)
            self.assertFalse(p['needs_review'])

    def test_transform_pixels_and_mask_adapter(self):
        frames=self.root/'masks/frames';frames.mkdir(parents=True)
        mask=Image.new('RGBA',(160,90));a=np.array(mask);a[20:80,50:80]=[255,0,0,255]
        Image.fromarray(a).save(frames/'00000.png');self.save('masks/manifest.json',dict(durations_ms=[1000]))
        follower=Reframer(self.root/'masks/manifest.json',(160,90),(90,160),1000,30)
        image=follower.apply(Image.fromarray(a),0);self.assertEqual(image.size,(90,160))
        self.assertIsNotNone(image.getbbox())

    def test_standalone_reframe_remains_composable(self):
        from reframe import reframe
        source=self.root/'source';(source/'frames').mkdir(parents=True)
        a=np.zeros((90,160,4),np.uint8);a[20:80,50:80]=[255,0,0,255]
        Image.fromarray(a).save(source/'frames/00000.png');self.save('source/manifest.json',dict(durations_ms=[1000]))
        reframe(source/'frames',source/'manifest.json',source/'manifest.json',self.root/'portrait',size=(90,160))
        manifest=json.loads((self.root/'portrait/manifest.json').read_text())
        self.assertEqual(sum(manifest['durations_ms']),1000)
        self.assertTrue(all(t%10==0 and t>=20 for t in manifest['durations_ms']))
        path=self.save('plan.json',dict(segments=[dict(type='animation',manifest='portrait/manifest.json')]))
        validate_plan(path)


class IntegrationTests(TempCase):
    def test_new_plan_fields_opt_in(self):
        for key,value in [('captions',{}),('sfx','auto'),('cut_density','low'),('reframe',{})]:
            path=self.plan(**{key:value})
            with self.assertRaisesRegex(ValueError,'[Ee]xperimental'):validate_plan(path,('mp4',))

    def test_named_move_cli_validation(self):
        path=self.plan(experimental=True,effects=[dict(move='crash_in')])
        self.assertEqual(validate_plan(path)[4][0]['name'],'camera_move')
        path=self.plan(experimental=True,effects=[dict(move='unknown')])
        with self.assertRaisesRegex(ValueError,'crash_in'):validate_plan(path)

    def test_caption_raster_manifest(self):
        path=self.plan(experimental=True,captions=dict(words=[dict(text='Hi',start_ms=0,end_ms=900)],style='clean'))
        render(path,self.root/'out',('png',))
        manifest=json.loads((self.root/'out/manifest.json').read_text());self.assertEqual(manifest['captions']['status'],'experimental')
        self.assertGreater(len(list((self.root/'out/frames').glob('*.png'))),1)

    def test_review_eight_shots_only_two_rerendered(self):
        segments=[]
        for i in range(8):
            Image.new('RGBA',(192,108),(i*25,70,100,255)).save(self.root/f'{i}.png')
            segments.append(dict(type='still',image=f'{i}.png',duration_ms=400))
        Image.new('RGBA',(192,108),(250,220,20,255)).save(self.root/'replacement.png')
        path=self.save('plan.json',dict(segments=segments))
        first=build(path,self.root/'first');self.assertEqual(first['rerendered_shots'],8)
        decision=self.save('decisions.json',dict(shots={str(i):dict(action='replace',segment=dict(image='replacement.png')) for i in (2,5)}))
        second=build(path,self.root/'second',self.root/'first',decision)
        self.assertEqual(second['rerendered_shots'],2);self.assertEqual(second['reused_shots'],6)
        for i,(a,b) in enumerate(zip(first['shots'],second['shots'])):
            self.assertEqual(a['sha256']==b['sha256'],i not in (2,5))
        page=(self.root/'second/review.html').read_text(encoding='utf-8')
        self.assertEqual(page.count('<img '),len(second['events']));self.assertNotIn('http://',page);self.assertNotIn('https://',page)
        self.assertTrue(all((self.root/'second'/e['thumbnail']).exists() for e in second['events']))

    def test_review_invalid_decision_and_source_hash_invalidation(self):
        path=self.plan();build(path,self.root/'first')
        Image.new('RGBA',(192,108),(1,2,3,255)).save(self.root/'a.png')
        second=build(path,self.root/'second',self.root/'first');self.assertEqual(second['rerendered_shots'],1)
        decisions=self.save('bad.json',dict(shots={'0':dict(action='replace')}))
        with self.assertRaisesRegex(ValueError,'Replace needs'):build(path,self.root/'bad',self.root/'first',decisions)
        self.assertFalse((self.root/'bad').exists())

    def test_layered_plan_render_integration(self):
        beatmap=dict(duration_ms=2000,beats_ms=list(range(0,2000,125)),downbeats_ms=list(range(0,2000,500)))
        self.save('beats.json',beatmap)
        path=self.plan(experimental=True,beatmap='beats.json',cut_density='high')
        render(path,self.root/'layered',('png',))
        record=json.loads((self.root/'layered/manifest.json').read_text())
        self.assertEqual(len(record['segments']),4);self.assertEqual(record['beat_layers']['cuts_ms'],[500,1000,1500])

    def test_reframe_and_captions_raster_safe_band(self):
        masks=self.root/'mask/frames';masks.mkdir(parents=True)
        mask=np.zeros((108,192),np.uint8);mask[20:85,70:100]=255
        Image.fromarray(mask).save(masks/'00000.png');self.save('mask/manifest.json',dict(durations_ms=[1000]))
        path=self.plan(experimental=True,reframe=dict(masks='mask/manifest.json'),captions=dict(words=[dict(text='Hi',start_ms=0,end_ms=900)],style='clean'))
        render(path,self.root/'portrait',('png',))
        record=json.loads((self.root/'portrait/manifest.json').read_text());self.assertIn('reframe',record)
        with Image.open(next((self.root/'portrait/frames').glob('*.png'))) as image:self.assertAlmostEqual(image.width/image.height,9/16,delta=.01)

    def test_review_length_shift_reuses_unchanged_pixels(self):
        Image.new('RGBA',(96,64),(60,90,120,255)).save(self.root/'a.png')
        path=self.save('plan.json',dict(segments=[dict(type='still',image='a.png',duration_ms=400) for _ in range(3)]))
        first=build(path,self.root/'first')
        decision=self.save('decision.json',dict(shots={'0':dict(action='replace',segment=dict(duration_ms=800))}))
        second=build(path,self.root/'second',self.root/'first',decision)
        self.assertEqual(second['rerendered_shots'],1);self.assertEqual(second['shots'][1]['start_ms'],800)
        self.assertEqual(first['shots'][1]['sha256'],second['shots'][1]['sha256'])

    @unittest.skipUnless(locate('ffmpeg') and locate('ffprobe'),'FFmpeg/ffprobe required')
    def test_sfx_through_p0_and_silent_markers_export(self):
        path=self.plan(experimental=True,sfx='auto',effects=[dict(name='flash_white',start_ms=200,end_ms=400)])
        render(path,self.root/'movie',('mp4',))
        manifest=json.loads((self.root/'movie/manifest.json').read_text())
        self.assertEqual(manifest['sfx'][0]['source'],'procedural')
        checks={c['name']:c for c in manifest['audio']['checks']}
        self.assertLessEqual(checks['true_peak']['dbtp'],-1);self.assertAlmostEqual(checks['loudness']['lufs'],-14,delta=1)
        beatmap=dict(beats_ms=[0,517],downbeats_ms=[0])
        no_music_export(self.root/'movie/animation.mp4',beatmap,self.root/'silent')
        self.assertFalse(any(s['codec_type']=='audio' for s in probe(self.root/'silent/no-music.mp4')['streams']))
        self.assertEqual(json.loads((self.root/'silent/beats.json').read_text()),beatmap)


if __name__=='__main__':unittest.main()
