"""Fix-round regression evidence; real ASR fixtures, no weights or downloads."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import warnings
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from reframe import plan_path, transform
from fx.effects.camera import camera_move, motion, whip_peak_ms
from fx import Context
from sfx import events_from_plan, render_track, read_audio
import captions
from delivery import settings
from beat_layers import layers,apply_layers
from qa_media import rhythm_cuts
from music_fit import candidates


class ReframeFixTests(unittest.TestCase):
    def test_acceptance_v_walk_circle_coverage_and_rendered_area(self):
        from PIL import ImageDraw
        boxes=[]
        for i in range(100):
            x=40+5.6*i;y=180+30*np.sin(2*np.pi*i/50)
            boxes.append([x-40,y-40,x+40,y+40])
        report=plan_path(boxes,(640,360),(270,480));ratios=[]
        self.assertGreaterEqual(sum(not r['needs_review'] for r in report['path'])/100,.98)
        for b,r in zip(boxes,report['path']):
            source=Image.new('RGBA',(640,360),(60,90,120,255));ImageDraw.Draw(source).ellipse(b,fill=(255,20,20,255))
            output=np.asarray(transform(source,r,(270,480)))
            before=np.asarray(source)
            ratios.append(np.count_nonzero((output[...,0]>200)&(output[...,1]<50))/(np.count_nonzero((before[...,0]>200)&(before[...,1]<50))*(480/360)**2))
            self.assertTrue(np.all(output[...,3]==255))
        self.assertGreaterEqual(min(ratios),.9)

    def test_fast_small_and_large_subjects_inside_source_and_frame(self):
        for bw,bh in ((90,260),(360,850)):
            boxes=[[100+370*k/30,100,100+370*k/30+bw,100+bh] for k in range(110)]
            report=plan_path(boxes,(1920,1080))
            covered=0
            for record in report['path']:
                x,y,w,h=record['crop']
                self.assertTrue(0<=x<=1920-w and 0<=y<=1080-h)
                a,b,c,d=record['subject_bbox']
                covered+=a>=-1e-6 and b>=0 and c<=1080+1e-6 and d<=1920+1e-6
            self.assertGreaterEqual(covered/len(boxes),.98)
            centers=np.array([r['crop'][:2] for r in report['path']])*1920/1080
            self.assertLessEqual(np.linalg.norm(np.diff(centers,n=2,axis=0),axis=1).max(),4+1e-6)
            frame=transform(Image.new('RGBA',(1920,1080),(70,90,120,255)),report['path'][-1],(270,480))
            self.assertTrue(np.all(np.asarray(frame)[...,:3]>0))

    def test_too_wide_subject_reports_without_padding(self):
        r=plan_path([[0,0,1000,1080]],(1920,1080))['path'][0]
        self.assertTrue(r['needs_review'])
        self.assertEqual(r['crop'][1],0)


class WhipFixTests(unittest.TestCase):
    def test_truncated_whip_rejected_before_render(self):
        from fx_render import validate_plan
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);Image.new('RGBA',(90,160),'red').save(root/'a.png')
            plan=dict(experimental=True,segments=[dict(type='still',image='a.png',duration_ms=1000)],effects=[dict(move='whip',start_ms=0,end_ms=80)])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'full duration'): validate_plan(path)

    def test_whip_returns_to_identical_original_frame(self):
        a=np.random.default_rng(1).integers(40,240,(160,90,4),dtype=np.uint8);a[...,3]=255
        for t in (0,160,200):
            np.testing.assert_array_equal(camera_move(a,t,Context(90,160,fps=30),move='whip'),a)
        shifts=[motion('whip',t)[1] for t in np.arange(0,200,1000/30)]
        self.assertGreater(max(abs(np.diff(shifts))),.25)

    def test_whoosh_pcm_peak_matches_max_frame_motion(self):
        e=events_from_plan({},[dict(name='camera_move',params={'move':'whip'},start_ms=500)],[],[],fps=30)
        self.assertAlmostEqual(e[0]['at_ms'],500+whip_peak_ms())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'track.wav';render_track(e,1000,path)
            actual=np.argmax(np.max(abs(read_audio(path)),axis=1))/48
            self.assertAlmostEqual(actual,e[0]['at_ms'],delta=1/48)


class WhisperFixTests(unittest.TestCase):
    def test_real_raw_fixtures_numpy_scalars_and_ffmpeg_array_adapter(self):
        fixtures=Path(__file__).parent/'fixtures/live'
        for language,count in (('en',19),('zh',29)):
            raw=json.loads((fixtures/f'whisper-raw-{language}.json').read_text(encoding='utf-8'))
            words=captions.validate_words(raw['words'])
            self.assertEqual(len(words),count)
            for word in words:
                word['start_ms']=np.float64(word['start_ms']);word['end_ms']=np.float32(word['end_ms'])
            json.dumps(captions.validate_words(words))
            segments=[SimpleNamespace(words=[SimpleNamespace(word=w['word'],start=np.float64(w['start']),end=np.float64(w['end'])) for w in raw['words']])]
            class Model:
                def __init__(self,*a,**kw): pass
                def transcribe(inner,audio,**kw):
                    self.assertIsInstance(audio,np.ndarray);self.assertEqual(audio.dtype,np.float32)
                    self.assertEqual(audio.ndim,1);self.assertGreater(len(audio),16000)
                    self.assertEqual(kw['language'],language)
                    return segments,None
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp)/'model.bin').touch()
                with patch.dict(sys.modules,{'faster_whisper':SimpleNamespace(WhisperModel=Model),'av':None}):
                    output=captions.faster_whisper_engine(fixtures/f'speech-{language}.wav',tmp,language=language)
                self.assertEqual(len(output),count)
                self.assertEqual(output[0]['text'],raw['words'][0]['word'])

    def test_cache_root_model_name_and_snapshot_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp);snap=cache/'models--Systran--faster-whisper-small/snapshots/abc'
            snap.mkdir(parents=True);(snap/'model.bin').touch()
            for model,root in ((str(cache),None),('small',cache),(str(snap),None)):
                self.assertEqual(captions.local_whisper_model(model,root),snap)

    def test_optional_conversion_keeps_word_times(self):
        class Converter:
            def __init__(self,config): self.config=config
            def convert(self,text): return text.replace('画','畫')
        word=dict(text='画面',start_ms=10.,end_ms=400.)
        with patch.dict(sys.modules,{'opencc':SimpleNamespace(OpenCC=Converter)}):
            self.assertEqual(captions.traditional_words([word]),[dict(word,text='畫面')])
        with patch.dict(sys.modules,{'opencc':None}):
            with self.assertRaisesRegex(RuntimeError,'pip install'): captions.traditional_words([word])


class CaptionLookFixTests(unittest.TestCase):
    def test_revealed_box_grows_and_presets_differ(self):
        words=[dict(text='MAKE ',start_ms=0,end_ms=350),dict(text='IT ',start_ms=350,end_ms=700),dict(text='MOVE',start_ms=700,end_ms=1200)]
        cfg=settings((1080,1920),platform='tiktok',proxy=True)
        blank=Image.new('RGBA',cfg['size']);outputs=[]
        for preset in captions.PRESETS:
            p=captions.prepare(dict(words=words,style=dict(preset=preset,words_per_line=16)),Path('.'),True)
            r=captions.CaptionRenderer(p,cfg['size'],cfg['safe_zone'])
            outputs.append(r.overlay(blank,900).tobytes())
            if preset=='bounce':
                early=r.overlay(blank,300).getbbox();late=r.overlay(blank,1100).getbbox()
                self.assertLess(early[2]-early[0],late[2]-late[0])
        self.assertEqual(len(set(outputs)),4)


class CaptionTextFixTests(unittest.TestCase):
    def test_pixel_reflow_does_not_orphan_short_phrase(self):
        words=[dict(text=text,start_ms=i*350,end_ms=(i+1)*350) for i,text in enumerate(('MAKE ','IT ','MOVE!'))]
        cfg=settings((1080,1920),platform='tiktok')
        for preset in captions.PRESETS:
            p=captions.prepare(dict(words=words,style=dict(preset=preset,words_per_line=16)),Path('.'),True)
            renderer=captions.CaptionRenderer(p,cfg['size'],cfg['safe_zone'])
            self.assertTrue(all(len(line['text'].split())>1 for line in renderer.lines),renderer.lines)

    def test_atomic_versions_numbers_and_emoji(self):
        text='Use v2.0 for 1,234 clips 👍🏽 👩🏽‍💻 today'
        lines=captions.break_lines(text,8)
        for token in ('v2.0','1,234','👍🏽','👩🏽‍💻'):
            self.assertTrue(any(token in line for line in lines),(token,lines))
        self.assertEqual(''.join(lines).replace(' ',''),text.replace(' ',''))

    def test_sentence_pause_and_no_width_orphan(self):
        self.assertEqual(captions.break_lines('Hello world. New scene!',40),['Hello world.','New scene!'])
        lines=captions.break_lines('one two three four five',8)
        self.assertTrue(all(len(line.split())>1 for line in lines),lines)
        p=captions.prepare(dict(words=[dict(text='First line',start_ms=0,end_ms=500),dict(text=' Next line',start_ms=650,end_ms=1000)],style=dict(preset='clean',words_per_line=40)),Path('.'),True)
        self.assertEqual([line['text'] for line in p['lines']],['First line','Next line'])

    def test_missing_graphemes_warn_drop_and_render(self):
        with warnings.catch_warnings(record=True) as caught:
            p=captions.prepare(dict(words=[dict(text='Hello \U0010ffff 👩🏽‍💻',start_ms=0,end_ms=900)]),Path('.'),True)
        self.assertTrue(any('U+10FFFF' in str(w.message) for w in caught))
        self.assertIn('U+10FFFF',p['dropped_codepoints'])
        self.assertNotIn('\U0010ffff',''.join(line['text'] for line in p['lines']))
        cfg=settings((540,960));r=captions.CaptionRenderer(p,cfg['size'],cfg['safe_zone'])
        self.assertIsNotNone(r.overlay(Image.new('RGBA',cfg['size']),300).getbbox())


class DensityFixTests(unittest.TestCase):
    def test_accent_and_hit_density_uses_layered_rules(self):
        beatmap=dict(duration_ms=64000,beats_ms=list(range(0,64000,500)),downbeats_ms=list(range(0,64000,2000)))
        counts=[]
        for density in ('low','mid','high'):
            plan,design=apply_layers(dict(cut_density=density,segments=[{}]),beatmap)
            counts.append(len(design['accents_ms']))
            self.assertNotIn('flash_white',[e['name'] for e in plan['effects']])
            effects=[dict(name='zoom_punch',params={},trigger_times_ms=design['accents_ms'],start_ms=0)]
            segments=[dict(start_ms=t) for t in [0]+design['cuts_ms']]
            events=events_from_plan(plan,effects,[],segments)
            self.assertEqual([e['at_ms'] for e in events],design['cuts_ms'])
        self.assertEqual(counts,[8,16,32])

    def test_rhythm_excludes_planned_impulses_but_keeps_real_cuts(self):
        observed=[dict(seconds=t) for t in (1,1.1,2,3)]
        timing=dict(beat_layers={'cuts_ms':[2000]},effects=[dict(name='zoom_punch',params={'scale':{'decay_ms':160}},trigger_times_ms=[1000,2000])])
        kept,excluded=rhythm_cuts(observed,timing,34)
        self.assertEqual([e['seconds'] for e in kept],[2,3])
        self.assertEqual(len(excluded),2)
        kept,excluded=rhythm_cuts([dict(seconds=.5)],dict(captions={'lines':[dict(start_ms=0,chars=[dict(start_ms=500,word_start_ms=500)])]}),34)
        self.assertEqual(len(excluded),1)


class MusicCameraFixTests(unittest.TestCase):
    def test_short_music_actionable_error(self):
        with self.assertRaisesRegex(ValueError,'shorten the target or use --no-music'):
            candidates(dict(duration_ms=2000,beats_ms=[0,500,1000,1500]),30000)

    def test_crash_out_eases_from_original_and_returns(self):
        self.assertEqual(motion('crash_out',0),(1,0))
        self.assertAlmostEqual(motion('crash_out',600)[0],1)
        samples=[motion('crash_out',t)[0] for t in np.linspace(0,600,301)]
        self.assertAlmostEqual(max(samples),1.35)
        self.assertLess(max(abs(np.diff(samples))),.02)


if __name__=='__main__': unittest.main()
