"""P2a held-out regressions. All media and model fixtures live in OS temp."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import captions
from delivery import settings
from fx import Context, EFFECTS, TRANSITIONS
from fx.masks import field
from fx.timewarp import interpolate, session
from fx_render import render
from qa_media import analyse_picture, rhythm_cuts


class Captions(unittest.TestCase):
    def test_oversized_words_all_presets(self):
        cfg=settings((270,480),platform='tiktok')
        for text in ('pneumonoultramicroscopicsilicovolcanoconiosis'*3,'https://example.com/'+('longpath/'*20),'超級長的中文字詞'*20):
            for preset in captions.PRESETS:
                data=captions.prepare(dict(words=[dict(text=text,start_ms=0,end_ms=4000)],style=preset),Path('.'),True)
                with warnings.catch_warnings(record=True) as caught:
                    r=captions.CaptionRenderer(data,cfg['size'],cfg['safe_zone'])
                self.assertTrue(any('split' in str(w.message) for w in caught))
                self.assertEqual(''.join(word.get('source_text',word['text']) for line in r.lines for word in line['words']),text)
                self.assertTrue(all(x[-1]>=.58 for x in r.layouts))
                for line in r.lines:
                    image=r.overlay(Image.new('RGBA',cfg['size']),(line['start_ms']+line['end_ms'])/2)
                    self.assertIsNotNone(image.getbbox())
                self.assertEqual(data['words'][0]['text'],text)

    def test_clause_punctuation_numeric_boundaries_and_atomic_tokens(self):
        text='Node.js e.g. 10:30 iPhone15 H264 15 3.14 v2.0, 完成!'
        data=captions.prepare(dict(words=[dict(text=text,start_ms=0,end_ms=1000)],language='zh'),Path('.'),True)
        self.assertEqual(data['words'][0]['text'],'Node.js e.g. 10:30 iPhone15 H264 15 3.14 v2.0， 完成！')
        self.assertEqual(data['keywords'],['15','3.14','v2.0'])
        highlights=''.join(c['char'] for line in data['lines'] for c in line['chars'] if c['highlight'])
        self.assertEqual(highlights,'153.14v2.0')
        for word in ('iPhone15','H264','10:30','Node.js','https://example.com/a'):
            self.assertEqual(captions.tokens(word),[word])
        explicit=captions.prepare(dict(words=[dict(text='iPhone15 3.15 15 10:30.15',start_ms=0,end_ms=1000)],keywords=['15']),Path('.'),True)
        self.assertEqual(''.join(c['char'] for line in explicit['lines'] for c in line['chars'] if c['highlight']),'15')

    def test_emoji_never_begins_a_wrapped_line(self):
        data=captions.prepare(dict(words=[dict(text=t,start_ms=i*300,end_ms=(i+1)*300) for i,t in enumerate(('Hello','world','👍🏽','next'))],style=dict(words_per_line=6)),Path('.'),True)
        cfg=settings((270,480));r=captions.CaptionRenderer(data,cfg['size'],cfg['safe_zone'])
        for lines in (data['lines'],r.lines):
            self.assertTrue(all(not line['text'].startswith('👍') for line in lines))
        for emoji in ('👍','⭐'):
            words=[dict(text=t,start_ms=i*300,end_ms=(i+1)*300) for i,t in enumerate(('one','two',emoji,'next'))]
            data=captions.prepare(dict(words=words,style=dict(words_per_line=7)),Path('.'),True)
            self.assertTrue(all(not line['text'].startswith(emoji) for line in data['lines']))

    def test_typing_caret_and_clean_panel(self):
        cfg=settings((270,480));blank=Image.new('RGBA',cfg['size'])
        data=captions.prepare(dict(words=[dict(text='Typing',start_ms=0,end_ms=1000)],style='typewriter'),Path('.'),True)
        r=captions.CaptionRenderer(data,cfg['size'],cfg['safe_zone'])
        self.assertFalse(np.array_equal(r.overlay(blank,200),r.overlay(blank,400)))
        self.assertEqual(captions.PRESETS['clean']['box'],'111111')


class Effects(unittest.TestCase):
    def setUp(self):
        self.ctx=Context(160,90,beats_ms=[0,500,1000])
        y,x=np.indices((90,160));self.a=np.ones((90,160,4),np.float32)
        self.a[...,:3]=np.stack((x/200+.1,y/120+.1,(x+y)/350+.1),axis=-1)

    def fx(self,name,**params):return EFFECTS[name]['function'](self.a,500,self.ctx,**params)

    def test_leak_visible_and_drifting(self):
        f=EFFECTS['light_leak']['function'];a=f(self.a,0,self.ctx);b=f(self.a,1000,self.ctx)
        self.assertGreater(np.abs(a-self.a).mean(),.02)
        self.assertGreater(np.abs(a-b).mean(),.015)

    def test_radial_default_retains_detail(self):
        self.a[...,:3]=(np.indices((90,160)).sum(axis=0)%8<4)[...,None]
        out=self.fx('radial_blur')
        self.assertLess(np.abs(out-self.a).mean(),.2)
        self.assertGreater(out[...,:3].std(),.25)

    def test_colour_halftone_and_tiny_inputs(self):
        self.a[...,:3]=[.8,.2,.1]
        out=self.fx('halftone')
        self.assertGreater(out[...,0].mean()-out[...,2].mean(),.5)
        for h,w in ((1,1),(2,3)):
            for name in ('halftone','kaleidoscope'):
                a=np.ones((h,w,4),np.float32)*.5
                out=EFFECTS[name]['function'](a,0,Context(w,h))
                self.assertEqual(out.shape,a.shape);self.assertTrue(np.isfinite(out).all())

    def test_posterize_removes_isolated_specks(self):
        self.a[...,:3]=.49;self.a[20,20,:3]=.8
        out=self.fx('posterize')
        np.testing.assert_array_equal(out[20,20],out[20,21])
        self.assertLessEqual(len(np.unique(out[...,:3])),4)

    def test_sparse_dust_and_scratch(self):
        out=self.fx('dust_scratches');changed=np.max(np.abs(out-self.a),axis=2)>.001
        self.assertLess(changed.mean(),.01)
        self.assertGreater(changed.sum(axis=0).max(),10)

    def test_echo_decay_and_static_identity(self):
        self.ctx.history=(self.a.copy(),)*4
        np.testing.assert_allclose(self.fx('echo'),self.a,atol=.02)
        self.a[...,:3]=0;history=[]
        for x in (30,60,90,120):
            old=self.a.copy();old[:,x:x+5,:3]=1;history.append(old)
        self.ctx.history=tuple(history);out=self.fx('echo')
        values=[out[:,x+2,0].mean() for x in (30,60,90,120)]
        self.assertTrue(all(a>b for a,b in zip(values,values[1:])))
        self.assertLess(values[0],.4)
        # Overlapping transparent ghosts retain colour instead of whitening.
        self.a[:]=0;self.a[20:70,50:90]=[.2,.4,.6,1]
        old=np.roll(self.a,12,axis=1);self.ctx.history=(old,old,old,old)
        out=self.fx('echo');visible=out[...,3]>.01
        np.testing.assert_allclose(out[...,:3][visible],np.broadcast_to([.2,.4,.6],out[...,:3][visible].shape),atol=1e-5)

    def test_grain_resolution_relative(self):
        noise=[]
        for h,w in ((90,160),(720,1280)):
            a=np.full((h,w,4),.5,np.float32);a[...,3]=1
            out=EFFECTS['film_grain']['function'](a,500,Context(w,h))
            noise.append((out-a)[...,:3].std())
        self.assertLess(noise[0],noise[1]*.6)

    def test_spin_uses_cover_zoom_without_reflections(self):
        # Horizontal monotone ramp must remain monotone after midpoint's 90° turn.
        out=TRANSITIONS['spin']['function'](self.a,self.a,.5,self.ctx)
        differences=np.diff(out[:,80,0]);self.assertTrue(np.all(differences<=.001) or np.all(differences>=-.001))
        self.assertTrue(np.all(out[...,3]==1))

    def test_circle_is_circular_and_luma_default_soft(self):
        value=field(160,90,'circle');mask=value<=.65
        y,x=np.nonzero(mask);self.assertLessEqual(abs(np.ptp(x)-np.ptp(y)),1)
        a=np.zeros_like(self.a);b=np.ones_like(a);a[...,3]=1
        out=TRANSITIONS['luma_wipe']['function'](a,b,.5,self.ctx)
        self.assertGreater(np.count_nonzero((out[...,0]>.01)&(out[...,0]<.99)),90*10)

    def test_sixteen_bit_mask_and_missing_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'16.png';values=np.array([[0,1000,2000,32768,65535]],np.uint16);Image.fromarray(values).save(p)
            out=field(5,1,str(p));np.testing.assert_allclose(out,values/65535,atol=1e-6)
            with self.assertRaisesRegex(ValueError,'absent.png'):field(5,1,str(Path(tmp)/'absent.png'))

    def test_multi_cutout_warns_opaque(self):
        with self.assertWarnsRegex(UserWarning,'alpha'):out=self.fx('multi_cutout')
        np.testing.assert_array_equal(out,self.a)

    def test_parallax_alpha_sum_hidden_rgb(self):
        self.a[...,3]=0;self.a[20:70,50:110,3]=.6
        b=self.a.copy();b[b[...,3]==0,:3]=[1,0,1]
        out=self.fx('parallax');other=EFFECTS['parallax']['function'](b,500,self.ctx)
        self.assertAlmostEqual(float(out[...,3].sum()),float(self.a[...,3].sum()),places=3)
        np.testing.assert_array_equal(out,other)

    def test_glitch_nearest_preserves_palette(self):
        self.ctx.sampling='nearest';self.a[...,:3]=[.2,.4,.8];self.a[:,80:,:3]=[.9,.1,.1]
        out=TRANSITIONS['glitch']['function'](self.a,self.a,.5,self.ctx)
        self.assertTrue(set(map(tuple,out[...,:3].reshape(-1,3)))<=set(map(tuple,self.a[...,:3].reshape(-1,3))))

    def test_push_fractional_seam_preserves_opaque_coverage(self):
        for direction in ('left','right','up','down'):
            for progress in (.137,.331,24/47):
                out=TRANSITIONS['push']['function'](self.a,self.a,progress,self.ctx,direction=direction)
                np.testing.assert_allclose(out[...,3],1,atol=1/255)

    def test_text_errors_glyphs_and_long_fit(self):
        with self.assertRaisesRegex(ValueError,'empty'):self.fx('text',content=' ')
        from fx.effects.typography import check_glyphs,resolve_font
        with self.assertWarnsRegex(UserWarning,r'U\+E000'):
            self.assertIn(0xE000,check_glyphs(resolve_font(),chr(0xE000)))
        with self.assertWarnsRegex(UserWarning,'reduced'):out=self.fx('text',content='A very long title '*10)
        self.assertEqual(out.shape,self.a.shape)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with self.assertRaisesRegex(ValueError,'too long'):self.fx('text',content='A'*10000)

    def test_rife_empty_missing_lazy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);empty=root/'empty.onnx';empty.touch()
            for path in (empty,root/'missing.onnx'):
                with self.assertRaisesRegex(ValueError,path.name):session(str(path))
            with patch('fx.timewarp.session',side_effect=AssertionError('must not load')):
                interpolate(self.a,self.a,0,'rife',model=str(empty))
                Image.fromarray((self.a*255).astype('uint8')).save(root/'a.png')
                p=root/'plan.json';p.write_text(json.dumps(dict(experimental=True,interpolate='rife',rife_model=str(empty),segments=[dict(type='still',image='a.png',duration_ms=100)])))
                render(p,root/'out',('png',))


class QA(unittest.TestCase):
    def test_spring_main_travel_excluded_but_cut_wins(self):
        timing=dict(effects=[dict(name='camera_move',start_ms=1000,end_ms=2000,params=dict(move='spring_in'))])
        events=[dict(seconds=1.1),dict(seconds=1.2),dict(seconds=1.7)]
        kept,excluded=rhythm_cuts(events,timing,34);self.assertEqual(kept,[events[-1]])
        timing['cuts']=[dict(quantized_ms=1200)]
        self.assertIn(events[1],rhythm_cuts(events,timing,34)[0])

    def test_white_flash_at_camera_start_fails(self):
        n=60;d=np.zeros(n);skip=np.zeros(n);means=[100]*n;contrast=[30]*n
        d[30:32]=100;skip[30]=0;means[30]=255;contrast[30]=0
        stats=dict(d=d,skip=skip,patch=np.zeros(n),mean=means,contrast=contrast,seam=0)
        timing=dict(effects=[dict(name='camera_move',start_ms=1000,end_ms=1500,params=dict(move='spring_in'))])
        checks=analyse_picture(stats,np.arange(n+1)/30,timing=timing)
        self.assertEqual(next(c for c in checks if c['name']=='flashes')['level'],'FAIL')

    def test_real_white_flash_frames_at_camera_start_fail(self):
        from qa_media import qa
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);frames=root/'frames';frames.mkdir()
            y,x=np.indices((60,80));base=np.ones((60,80,4),np.uint8)*255
            base[...,:3]=np.where(((x//6+y//6)%2)[...,None],[180,140,90],[30,60,110])
            ctx=Context(80,60,fps=30,effect_start_ms=200)
            for i in range(18):
                frame=base if i<6 else EFFECTS['camera_move']['function'](base,i*1000/30,ctx,move='spring_in')
                if i==6:frame=np.full_like(base,255)
                Image.fromarray(frame).save(frames/f'{i:05}.png')
            timeline=root/'timeline.json';timeline.write_text(json.dumps(dict(effects=[dict(name='camera_move',start_ms=200,end_ms=600,params=dict(move='spring_in'))])))
            report=qa(frames,root/'qa',fps=30,timeline=timeline)
            check=next(c for c in report['checks'] if c['name']=='flashes')
            self.assertEqual(check['level'],'FAIL');self.assertIn(6,[e['frame'] for e in check['events']])


class GateKit(unittest.TestCase):
    def test_edge_check_detects_seam_and_stretch(self):
        from fx_gate_kit import edge_metrics
        a=np.ones((60,80,4),np.float32)*.4;a[...,3]=1;a[:,:2,:3]=1
        self.assertGreater(edge_metrics(a)[0],6)
        a[...,:3]=.4;a[:,3:12,:3]=(np.arange(9)%2)[None,:,None]
        self.assertGreater(edge_metrics(a)[1],8)

    def test_checker_ignores_hidden_rgb(self):
        from fx_gate_kit import checker
        a=np.zeros((10,10,4),np.uint8);b=a.copy();b[...,:3]=255
        np.testing.assert_array_equal(checker(a),checker(b))

    def test_external_output_and_unknown_items(self):
        from fx_gate_kit import run,ROOT
        with self.assertRaisesRegex(ValueError,'outside'):run(ROOT/'forbidden')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'Unknown'):run(Path(tmp)/'new',['not_an_effect'])

    def test_gate_smoke_default_four_cases(self):
        from fx_gate_kit import run
        with tempfile.TemporaryDirectory() as tmp:
            report=run(Path(tmp)/'gate',['grade'])
            item=report['items'][0];self.assertNotIn('error',item)
            self.assertEqual(len(item['cases']),4)
            self.assertEqual(len(item['benchmark']['samples_ms']),10)
            self.assertTrue(all(c['determinism']['level']=='PASS' for c in item['cases']))
            self.assertTrue((Path(tmp)/'gate/index.html').is_file())
            self.assertLess(report['total_bytes'],300_000_000)


if __name__=='__main__':unittest.main()
