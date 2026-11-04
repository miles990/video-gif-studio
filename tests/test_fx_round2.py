"""Round two regression fixtures: no optional models or network access."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fx_reverse import inspect_frames, reverse
from fx_render import render, validate_plan
from fx import Context,EFFECTS,TRANSITIONS,evaluate
from fx.timewarp import interpolate,source_clock
from fx.depth import depth_map,check_model
from unittest.mock import patch


class RoundOneRegressions(unittest.TestCase):
    def test_cumulative_freeze_with_quality_step_and_spike(self):
        rng=np.random.default_rng(22);base=rng.integers(20,220,(90,160,3),dtype=np.uint8)
        images=[]
        for t in range(0,7000,40):
            image=np.roll(base,t//40,axis=1) if not 4000<=t<5520 else base.copy()
            if 4720<=t<5520:image=np.clip(image.astype(int)+1,0,255).astype('uint8')
            if t==4960:image=np.clip(image.astype(int)+6,0,255).astype('uint8')
            images.append(Image.fromarray(image))
        holds=inspect_frames(images,list(range(0,7000,40)),7000)['freezes']
        self.assertEqual(len(holds),1,holds)
        self.assertEqual((holds[0]['start_ms'],holds[0]['end_ms']),(4000,5520))

    def test_transition_grid_and_manifest_warning(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);Image.new('RGBA',(24,24),'red').save(p/'a.png')
            plan={'sampling':'nearest','segments':[{'type':'still','image':'a.png','duration_ms':1000},
                  {'type':'still','image':'a.png','duration_ms':1000,'transition':{'name':'crossfade','duration_ms':401}}]}
            (p/'p.json').write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'multiple of 10'):validate_plan(p/'p.json')
            plan['segments'][1]['transition']['duration_ms']=400
            (p/'p.json').write_text(json.dumps(plan));render(p/'p.json',p/'out',('png',))
            self.assertIn('blends colours',json.loads((p/'out/manifest.json').read_text())['warnings'][0])

    def test_full_size_animated_cutout_on_stationary_plate(self):
        rng=np.random.default_rng(81);base=rng.integers(20,80,(90,160,3),dtype=np.uint8);images=[]
        for i in range(90):
            a=base.copy()
            if 20<=i<75:
                y=12+min((i-20)%9,5)*2;a[y:y+40,3:150]=240
            else:a=np.roll(a,i*3,axis=1)
            images.append(Image.fromarray(a))
        report=inspect_frames(images,np.arange(90)*40,3600)
        self.assertTrue(any(f.get('kind')=='animated_cutout_on_held_plate' and f['end_ms']-f['start_ms']>=1800 for f in report['freezes']),report)

    @unittest.skipUnless(os.environ.get('VIDEO_GIF_FFMPEG'),'H.264 regression needs explicit FFmpeg runtime')
    def test_h264_mid_freeze_keyframe(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'frames').mkdir();rng=np.random.default_rng(41)
            base=rng.integers(20,220,(90,160,3),dtype=np.uint8)
            for i in range(175):
                a=base if 100<=i<138 else np.roll(base,i,axis=1)
                Image.fromarray(a).save(p/'frames'/f'{i:05d}.png')
            subprocess.run([os.environ['VIDEO_GIF_FFMPEG'],'-v','error','-framerate','25','-i',str(p/'frames/%05d.png'),
                '-c:v','libx264','-crf','24','-g','120','-pix_fmt','yuv420p',str(p/'test.mp4')],check=True)
            report=reverse(p/'test.mp4',p/'rev')
            holds=report['freezes'];self.assertEqual(len(holds),1,holds)
            self.assertAlmostEqual(holds[0]['start_ms'],4000,delta=40)
            self.assertAlmostEqual(holds[0]['end_ms'],5500,delta=40)


class FrameworkTests(unittest.TestCase):
    def test_speed_integral_and_ramp(self):
        ctx=Context(320,180,beats_ms=[0,500,1000,1500,2000],segment={'start_ms':0})
        self.assertEqual(source_clock({'speed':.5},1000,ctx),500)
        self.assertAlmostEqual(source_clock({'speed':{'keyframes':[[0,1],[1000,.25],[2000,1]]}},1000,ctx),625)
        s={'ramp':{'into_beat':4,'slow':.3,'hit_ms':200}}
        self.assertAlmostEqual(source_clock(s,1500,ctx)/1500,.3)
        self.assertAlmostEqual((source_clock(s,2000,ctx)-source_clock(s,1800,ctx))/200,2)

    def test_flow_single_bar_midpoint_and_alpha(self):
        a=np.zeros((180,320,4),np.uint8);a[...,3]=255;a[:,116:132,:3]=255
        b=np.zeros_like(a);b[...,3]=255;b[:,140:156,:3]=255
        result=interpolate(a,b,.5,'flow');profile=result[...,0].mean(axis=0);ids=np.flatnonzero(profile>=200)
        self.assertTrue(13<=len(ids)<=19);self.assertAlmostEqual(ids.mean(),135.5,delta=2)
        self.assertLessEqual(np.count_nonzero((profile>80)&(profile<180)),4)
        np.testing.assert_array_equal(result,interpolate(a,b,.5,'flow'))
        blend=interpolate(a,b,.5,'blend');self.assertGreaterEqual(np.count_nonzero((blend[0,:,0]>100)&(blend[0,:,0]<155)),24)
        a[:]=[255,0,255,0];a[40:140,110:180]=[200,160,60,255];b=a.copy()
        out=interpolate(a,b,.5,'flow');self.assertFalse(np.any((out[...,0]>240)&(out[...,2]>240)&(out[...,3]>12)))

    def test_rife_tensor_fake_and_missing(self):
        class Fake:
            def run(self,_,inputs):
                tensor=inputs['input'];self.tensor=tensor
                return [(tensor[:,:3]+tensor[:,3:6])*.5]
        fake=Fake();a=np.ones((180,320,4),np.float32)
        out=interpolate(a,a,.5,'rife',engine=fake)
        self.assertEqual(out.shape,a.shape);self.assertEqual(fake.tensor.shape,(1,7,192,320))
        self.assertTrue(np.all(fake.tensor[:,6]==.5))
        with patch.dict(sys.modules,{'onnxruntime':None}):
            from fx.timewarp import session
            session.cache_clear()
            with self.assertRaisesRegex(ValueError,'onnxruntime'):interpolate(a,a,.5,'rife',model='missing.onnx')

    def test_render_source_clock_and_history_reset(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'source/frames').mkdir(parents=True)
            for i in range(50):Image.new('RGBA',(24,16),(i*4,30,50,255)).save(p/'source/frames'/f'{i:05d}.png')
            (p/'source/manifest.json').write_text(json.dumps({'durations_ms':[40]*50}))
            plan={'experimental':True,'interpolate':'none','segments':[{'type':'animation','manifest':'source/manifest.json','duration_ms':1000,'speed':.5},
                  {'type':'animation','manifest':'source/manifest.json','duration_ms':1000,'speed':.5}],'effects':[{'name':'echo'}]}
            (p/'p.json').write_text(json.dumps(plan));render(p/'p.json',p/'out',('png',))
            manifest=json.loads((p/'out/manifest.json').read_text());samples=manifest['source_samples']
            self.assertEqual(samples[10]['source_ms'],200);self.assertEqual(samples[25]['source_ms'],0)
            self.assertEqual(np.array(Image.open(p/'out/frames/00025.png'))[0,0,0],0)

    def test_unity_implicit_trim_does_not_fit_long_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'source/frames').mkdir(parents=True)
            for i in range(150):Image.new('RGBA',(16,12),(i,40,80,255)).save(p/'source/frames'/f'{i:05d}.png')
            (p/'source/manifest.json').write_text(json.dumps({'durations_ms':[40]*150}))
            (p/'beats.json').write_text(json.dumps({'beats_ms':[0,500,1000,1500,2000]}))
            for name,speed in [('implicit',None),('unity',1)]:
                segment={'type':'animation','manifest':'source/manifest.json','end_beat':4}
                if speed is not None:segment['speed']=speed
                (p/'p.json').write_text(json.dumps({'experimental':True,'beatmap':'beats.json','segments':[segment]}));render(p/'p.json',p/name,('png',))
                m=json.loads((p/name/'manifest.json').read_text());self.assertEqual(m['source_samples'][25]['source_ms'],1000)
                self.assertEqual(np.array(Image.open(p/name/'frames/00025.png'))[0,0,0],25)
            self.assertEqual((p/'implicit/frames/00025.png').read_bytes(),(p/'unity/frames/00025.png').read_bytes())

    def test_depth_fake_cache_license_and_parallax(self):
        class Fake:
            calls=0
            def run(self,_,inputs):
                self.calls+=1;t=inputs['pixel_values'];h,w=t.shape[2:]
                assert h%14==0 and w%14==0
                out=np.ones((1,h,w),np.float32)*.2;out[:,h//3:h*2//3,w//3:w*2//3]=1
                return [out]
        with tempfile.TemporaryDirectory() as d:
            a=np.full((182,320,4),[80,110,130,255],np.uint8);a[60:122,106:214,:3]=[240,220,40]
            fake=Fake();depth=depth_map(a,'small.onnx',d,fake);depth_map(a,'small.onnx',d,fake);self.assertEqual(fake.calls,1)
            a[0,0,0]+=1;depth_map(a,'small.onnx',d,fake);self.assertEqual(fake.calls,2)
            file=Path(d)/'fixture.png';Image.fromarray((depth*65535).astype('uint16')).save(file)
            out=EFFECTS['parallax']['function'](a,2000,Context(320,182),depth=str(file))
            self.assertTrue(np.all(out[...,3]==255));self.assertGreater(out[...,:3].min(),10)
            for name in ('Base','large','vitb','ViTL'):
                with self.assertRaisesRegex(ValueError,'CC-BY-NC'):check_model(name+'.onnx')

    def test_new_color_alpha_and_envelopes(self):
        a=np.full((80,120,4),[100,130,160,255],np.uint8);a[:,:,3]=np.arange(120)[None,:]*2
        ctx=Context(120,80,beats_ms=[0,500,1000])
        names=['rgb_split','film_grain','vignette','light_leak','dust_scratches','invert_flash','black_flash','posterize','halftone']
        for name in names:
            out=EFFECTS[name]['function'](a,500,ctx)
            np.testing.assert_array_equal(out[...,3],a[...,3],err_msg=name)
            zero=EFFECTS[name]['function'](a,500,ctx,amount=evaluate({'on':'beats','decay_ms':100},700,ctx))
            np.testing.assert_array_equal(zero,a,err_msg=name)

    def test_all_new_nearest_geometry_keeps_palette(self):
        a=np.zeros((96,128,4),np.uint8);a[10:80,20:110]=[210,40,90,255];a[30:55,40:65]=[30,220,140,255]
        ctx=Context(128,96,beats_ms=[0,500,1000],sampling='nearest');colors=set(map(tuple,a[a[...,3]>0,:3]))
        for name in ('shake','mirror','kaleidoscope','split_screen'):
            out=EFFECTS[name]['function'](a,500,ctx)
            self.assertTrue(set(map(tuple,out[out[...,3]>0,:3]))<=colors,name)
        for name in ('spin','push','slide','zoom_through'):
            out=TRANSITIONS[name]['function'](a,a,.4,ctx)
            self.assertTrue(set(map(tuple,out[out[...,3]>0,:3]))<=colors,name)

    def test_shape_area_and_text_missing_font(self):
        a=np.full((90,160,4),[220,40,40,255],np.uint8);b=np.full_like(a,[40,60,220,255]);ctx=Context(160,90)
        for shape in ('circle','diamond','star','heart'):
            for p in (.1,.5,.9):
                out=TRANSITIONS['shape_wipe']['function'](a,b,p,ctx,shape=shape)
                self.assertAlmostEqual(np.mean(out[...,2]==220),p,delta=.05)
        from fx.effects.typography import resolve_font
        with self.assertRaisesRegex(ValueError,'Noto CJK'):resolve_font('NoSuchFont-XYZ')

    def test_cjk_distinct_glyphs_and_font_manifest(self):
        ctx=Context(200,180);a=np.zeros((180,200,4),np.uint8);masks=[]
        for content in ('永','水','\ue000'):
            out=EFFECTS['text']['function'](a,500,ctx,content=content,size=96,stroke=0,shadow_px=0)
            masks.append(out[...,3]>128)
        def iou(a,b):return np.count_nonzero(a&b)/max(1,np.count_nonzero(a|b))
        self.assertLessEqual(iou(masks[0],masks[1]),.8)
        self.assertLessEqual(iou(masks[0],masks[2]),.5)
        self.assertTrue(.05<np.count_nonzero(masks[0])/(96*96)<.6)

    def test_history_plugin_receives_previous_input_and_unity_identity(self):
        from fx import effect
        @effect(history=2)
        def round2_peek(frame,t,ctx):
            assert all(at<t for at in ctx.history_times_ms)
            return ctx.history[0].copy() if ctx.history else frame
        self.addCleanup(lambda:EFFECTS.pop('round2_peek',None))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'source/frames').mkdir(parents=True)
            for i in range(10):Image.new('RGBA',(20,12),(i*20,50,80,255)).save(p/'source/frames'/f'{i:05d}.png')
            (p/'source/manifest.json').write_text(json.dumps({'durations_ms':[40]*10}))
            plan={'segments':[{'type':'animation','manifest':'source/manifest.json'}]}
            (p/'p.json').write_text(json.dumps(plan));render(p/'p.json',p/'plain',('png',))
            plan['experimental']=True
            plan['segments'][0]['speed']=1;(p/'p.json').write_text(json.dumps(plan));render(p/'p.json',p/'unity',('png',))
            for f in (p/'plain/frames').glob('*.png'):self.assertEqual(f.read_bytes(),(p/'unity/frames'/f.name).read_bytes())
            plan['effects']=[{'name':'round2_peek'}];(p/'p.json').write_text(json.dumps(plan));render(p/'p.json',p/'history',('png',))
            for i in range(1,10):self.assertEqual(np.array(Image.open(p/'history/frames'/f'{i:05d}.png'))[0,0,0],(i-1)*20)

    def test_missing_cv2_and_rembg_no_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'frames').mkdir();Image.new('RGBA',(8,8)).save(p/'frames/0.png')
            (p/'manifest.json').write_text('{"durations_ms":[40]}')
            code="import sys,runpy;sys.modules['cv2']=None;sys.argv=['background_remove.py',"+repr(str(p/'frames'))+",'--manifest',"+repr(str(p/'manifest.json'))+",'--out',"+repr(str(p/'out'))+"];runpy.run_path('scripts/background_remove.py',run_name='__main__')"
            result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
            self.assertEqual(result.returncode,2);self.assertIn('requirements-matting.txt',result.stderr);self.assertNotIn('Traceback',result.stderr)
