import copy
import contextlib
import hashlib
import io
import json
import os
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
from fx import Context, EFFECTS, TRANSITIONS, evaluate
from fx.core import load_directory, OVERRIDES, validate_envelope
from fx_render import render, validate_plan, main
from compose_timeline import compose
from music_sync import audio_envelopes, analyze
from background_remove import separate


def synthetic(root):
    yy,xx=np.indices((180,320));distance=np.sqrt(((xx-160)/40)**2+((yy-90)/60)**2)
    for name in ('A','B','C'):
        (root/name/'frames').mkdir(parents=True)
        for i in range(50):
            arr=np.empty((180,320,4),np.uint8);arr[:]=[220,40,40,255] if name=='A' else [40,60,220,255]
            if name=='A':arr[:,4*i:4*i+16,:3]=255
            elif name=='B':arr[2*i:2*i+16,:,:3]=0
            else:
                arr[:]=[255,0,255,0] if i%2 else [0,0,0,0]
                mask=distance<1.06;arr[mask,:3]=[200,160,60];arr[:,:,3]=np.rint(np.clip((1.06-distance)/.06,0,1)*255)
            Image.fromarray(arr).save(root/name/'frames'/f'{i:05d}.png')
        (root/name/'manifest.json').write_text(json.dumps({'durations_ms':[40]*50}))
    (root/'beats.json').write_text(json.dumps({'beats_ms':list(range(0,6001,500))}))
    return {'beatmap':'beats.json','segments':[{'type':'animation','manifest':'A/manifest.json','end_beat':4},
             {'type':'animation','manifest':'B/manifest.json','end_beat':8,'transition':{'name':'crossfade','duration_ms':400}},
             {'type':'still','manifest':'C/manifest.json','frame':'first','end_beat':12,'transition':{'name':'hex_shutter','duration_ms':500}}],
            'effects':[{'name':'flash_white','start_beat':1,'end_beat':2,'amount':{'on':'beats','attack_ms':0,'decay_ms':200,'curve':'linear'}},
                       {'name':'cutout_card','start_beat':9,'end_beat':12,'border_px':6}]}


class FxCoreTests(unittest.TestCase):
    def setUp(self):
        self.depth_tmp=tempfile.TemporaryDirectory();self.addCleanup(self.depth_tmp.cleanup)
        self.depth_file=str(Path(self.depth_tmp.name)/'depth.png')
        Image.fromarray(np.tile(np.arange(320,dtype=np.uint8),(180,1))).save(self.depth_file)
        self.ctx=Context(320,180,25,list(range(0,6001,500)))
        self.a=np.full((180,320,4),[220,40,40,255],np.uint8);self.a[:,20:36,:3]=255
        self.b=np.full_like(self.a,[40,60,220,255])

    def test_all_contracts_purity_determinism_dtype(self):
        for dtype in (np.uint8,np.float32):
            a=self.a.astype(dtype)/(255 if dtype==np.float32 else 1);a=a.astype(dtype)
            b=self.b.astype(dtype)/(255 if dtype==np.float32 else 1);b=b.astype(dtype)
            original=a.copy()
            for reg in (EFFECTS,TRANSITIONS):
                for name,spec in reg.items():
                    with self.subTest(name=name,dtype=dtype):
                        args=(a,1100,self.ctx) if reg is EFFECTS else (a,b,.5,self.ctx)
                        kwargs={'depth':self.depth_file} if name=='parallax' else {}
                        x=spec['function'](*args,**kwargs);y=spec['function'](*args,**kwargs)
                        self.assertEqual(x.dtype,dtype);self.assertEqual(x.shape,a.shape)
                        self.assertTrue(np.isfinite(x).all());self.assertTrue(np.array_equal(x,y));self.assertTrue(np.array_equal(a,original))
                        self.assertGreaterEqual(x.min(),0);self.assertLessEqual(x.max(),255 if dtype==np.uint8 else 1)

    def test_transition_endpoints(self):
        for name,spec in TRANSITIONS.items():
            for p,target in ((0,self.a),(1,self.b)):
                self.assertLessEqual(np.abs(spec['function'](self.a,self.b,p,self.ctx).astype(float)-target).max(),1,name)

    def test_color_alpha_and_neutral(self):
        self.a[:,:,3]=np.arange(320,dtype=np.uint16)[None,:]%256
        for name in ('flash_white','grade','halation'):
            np.testing.assert_array_equal(EFFECTS[name]['function'](self.a,0,self.ctx)[:,:,3],self.a[:,:,3])
        for name,param in [('flash_white',{'amount':0}),('grade',{}),('beat_bounce',{'amount':0}),('zoom_punch',{'amount':0})]:
            x=EFFECTS[name]['function'](self.a,0,self.ctx,**param)
            np.testing.assert_array_equal(x[self.a[:,:,3]>0],self.a[self.a[:,:,3]>0])

    def test_envelopes_and_context(self):
        e={'on':'beats','decay_ms':200}
        for t,want in [(999,0),(1000,1),(1100,.5),(1200,0),(1450,0)]:self.assertAlmostEqual(evaluate(e,t,self.ctx),want)
        self.assertAlmostEqual(evaluate(dict(e,attack_ms=100),950,self.ctx),.5)
        self.assertEqual(evaluate(dict(e,indices=[1,3]),1000,self.ctx),0)
        self.assertEqual(evaluate(dict(e,every=2),1000,self.ctx),1)
        self.assertEqual(evaluate(dict(e,every=2),500,self.ctx),0)
        self.assertEqual(evaluate(.7,2,self.ctx),.7)
        for t,v in [(-10,0),(500,.5),(1100,1)]:self.assertEqual(evaluate({'keyframes':[[0,0],[1000,1]]},t,self.ctx),v)
        self.ctx.t_ms=1100;self.assertEqual(self.ctx.since_previous_beat,100);self.assertEqual(self.ctx.until_next_beat,400)
        self.ctx.t_ms=1000;self.assertEqual(self.ctx.since_previous_beat,0)

    def test_flash_grade_crossfade(self):
        f=EFFECTS['flash_white']['function']
        self.assertEqual(f(self.a,0,self.ctx,amount=1)[140,260,0],255)
        self.assertAlmostEqual(float(f(self.a,0,self.ctx,amount=.5)[140,260,1]),147.5,delta=1)
        gray=EFFECTS['grade']['function'](self.a,0,self.ctx,sat=0)
        np.testing.assert_array_equal(gray[:,:,0],gray[:,:,2])
        mid=TRANSITIONS['crossfade']['function'](self.a,self.b,.5,self.ctx)
        np.testing.assert_allclose(mid[140,260,:3],[130,50,130],atol=1)

    def test_halation_locality(self):
        a=np.zeros_like(self.a);a[:,:,3]=255;a[80:100,150:170,:3]=255
        b=EFFECTS['halation']['function'](a,0,self.ctx)
        self.assertGreater(b[80:100,140:150,:3].mean(),8)
        self.assertGreater((b[80:100,140:150,0].astype(float)-b[80:100,140:150,2]).mean(),10)
        self.assertLess(b[:20,:,:3].max(),2)

    def test_hex_monotonic(self):
        fractions=[]
        for p in np.linspace(0,1,21):
            c=TRANSITIONS['hex_shutter']['function'](self.a,self.b,p,self.ctx).astype(float)
            fractions.append(np.mean((np.max(abs(c-self.a),axis=2)>8)&(np.max(abs(c-self.b),axis=2)>8)))
        self.assertGreater(fractions[10],.9)
        self.assertTrue(.15<fractions[5]<.85);self.assertTrue(.15<fractions[15]<.85)
        self.assertTrue(np.all(np.diff(fractions[:11])>=-.02));self.assertTrue(np.all(np.diff(fractions[10:])<=.02))

    def test_directional_blur(self):
        yy,xx=np.indices((180,320))
        for pattern,axis,limit in [((xx//8)%2,1,.5),((yy//8)%2,0,.8)]:
            a=np.repeat((pattern*255).astype(np.uint8)[:,:,None],4,axis=2);a[:,:,3]=255
            b=TRANSITIONS['whip_pan']['function'](a,a,.5,self.ctx)
            ratio=b[:,:,0].std()/a[:,:,0].std()
            if axis==1:self.assertLess(ratio,limit)
            else:self.assertGreater(ratio,limit)

    def test_nearest_palette(self):
        a=np.zeros_like(self.a);a[50:130,110:210]=[240,80,60,255];a[70:100,140:180]=[50,200,160,255]
        original=set(map(tuple,a[a[:,:,3]>0,:3]))
        for name in ('beat_bounce','zoom_punch'):
            out=EFFECTS[name]['function'](a,0,self.ctx,scale=1.25,sampling='nearest')
            self.assertTrue(set(map(tuple,out[out[:,:,3]>0,:3]))<=original)
            self.assertTrue(set(np.unique(out[:,:,3]))<={0,255})

    def test_seed_rng(self):
        a=self.ctx.rng.random(100);b=self.ctx.rng.random(100)
        np.testing.assert_array_equal(a,b);self.ctx.seed=2
        self.assertFalse(np.array_equal(a,self.ctx.rng.random(100)))

    def test_cross_process_hash_seed(self):
        code="import sys,hashlib,numpy as np;sys.path.insert(0,'scripts');from fx import *;a=np.full((20,30,4),128,np.uint8);c=Context(30,20,seed=9);h=hashlib.sha256();[h.update(s['function'](a,0,c,**({'depth':"+repr(self.depth_file)+"} if n=='parallax' else {})).tobytes()) for n,s in EFFECTS.items()];[h.update(s['function'](a,a,.25,c).tobytes()) for s in TRANSITIONS.values()];print(h.hexdigest())"
        outputs=[subprocess.check_output([sys.executable,'-c',code],env=dict(os.environ,PYTHONHASHSEED=str(seed))) for seed in (1,2)]
        self.assertEqual(outputs[0],outputs[1])

    def test_transparent_geometry_area_and_clean_edges(self):
        a=np.full_like(self.a,[255,0,255,0]);a[50:130,100:220]=[80,190,140,255]
        for name in ('beat_bounce','zoom_punch'):
            b=EFFECTS[name]['function'](a,0,self.ctx)
            scale=EFFECTS[name]['params']['scale']['default']
            self.assertLessEqual(abs(float(b[:,:,3].sum())/a[:,:,3].sum()-scale**2),.03)
            np.testing.assert_allclose(b[b[:,:,3]>12,:3],np.tile([80,190,140],(np.count_nonzero(b[:,:,3]>12),1)),atol=1)


class FxPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.base=synthetic(cls.root)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def plan(self,plan=None):
        path=self.root/'plan.json';path.write_text(json.dumps(plan or self.base));return path

    def test_render_boundaries_manifest_deterministic(self):
        for name in ('out1','out2'):render(self.plan(),self.root/name,('png',))
        a=json.loads((self.root/'out1/manifest.json').read_text());b=json.loads((self.root/'out2/manifest.json').read_text())
        self.assertEqual([s['start_ms'] for s in a['segments']],[0,2000,4000]);self.assertEqual(a['effects'][0]['trigger_times_ms'],[500])
        for fa,fb in zip(sorted((self.root/'out1/frames').glob('*.png')),sorted((self.root/'out2/frames').glob('*.png'))):self.assertEqual(fa.read_bytes(),fb.read_bytes())
        index=int(np.searchsorted(np.cumsum([0]+a['durations_ms']),2000))
        mid=np.array(Image.open(self.root/f'out1/frames/{index:05d}.png'));np.testing.assert_allclose(mid[140,260,:3],[130,50,130],atol=1)

    def test_empty_fx_exact(self):
        plan=copy.deepcopy(self.base);plan.pop('effects')
        for s in plan['segments']:s.pop('transition',None)
        compose(self.plan(plan),self.root/'plain',('png',));render(self.plan(plan),self.root/'plain-fx',('png',))
        for a,b in zip(sorted((self.root/'plain/frames').glob('*.png')),sorted((self.root/'plain-fx/frames').glob('*.png'))):self.assertEqual(a.read_bytes(),b.read_bytes())

    def test_validation_errors_locations_and_options(self):
        changes=[(lambda p:p['effects'][0].update(name='flash_whit'),'effects[0].*flash_whit.*flash_white'),
                 (lambda p:p['effects'][0].update(amout=1),r'effects\[0\].*amout.*amount'),
                 (lambda p:p['effects'][1].update(border_px='wide'),r'effects\[1\].border_px.*number'),
                 (lambda p:p['effects'][0]['amount'].update(decya_ms=200),r'effects\[0\].*decya_ms.*decay_ms'),
                 (lambda p:p['effects'][0].update(start_beat=99),'99.*0..12'),
                 (lambda p:p['segments'][2]['transition'].update(name='hexshutter'),r'segments\[2\].*hexshutter.*hex_shutter'),
                 (lambda p:p['segments'][1]['transition'].update(duration_ms=3000),r'segments\[1\].*3000.*2000'),
                 (lambda p:p.update(effcts=[]),'effcts.*effects')]
        changes[0]=(changes[0][0],r'effects\[0\].*flash_whit.*flash_white')
        for change,regex in changes:
            p=copy.deepcopy(self.base);change(p)
            with self.subTest(regex=regex),self.assertRaisesRegex(ValueError,regex):validate_plan(self.plan(p))

    def test_offset_rule(self):
        (self.root/'offset.json').write_text(json.dumps({'beats_ms':[0,1234.4,2468.8,3703.2]}))
        (self.root/'dummy.wav').write_bytes(b'not decoded for constant effect')
        p={'beatmap':'offset.json','music':{'file':'dummy.wav','in_ms':100},'segments':[{'type':'still','image':'A/frames/00000.png','end_beat':1}], 'effects':[{'name':'flash_white','amount':{'on':'beats'}}]}
        _,_,segments,ctx,_,_=validate_plan(self.plan(p),('mp4',))
        self.assertEqual(segments[0]['duration_ms'],1130);self.assertAlmostEqual(ctx.beats_ms[1],1134.4)

    def test_cutout_hidden_rgb(self):
        a=np.array(Image.open(self.root/'C/frames/00001.png'));ctx=Context(320,180)
        b=EFFECTS['cutout_card']['function'](a,0,ctx,border_px=6)
        visible=b[:,:,3]>12;magenta=(abs(b[:,:,:3].astype(int)-[255,0,255])<40).all(axis=2)
        self.assertFalse(np.any(visible&magenta));self.assertEqual(b[0,0,3],0)
        np.testing.assert_array_equal(b[90,160],[200,160,60,255])
        c=EFFECTS['cutout_card']['function'](a,0,ctx,bg='123456');np.testing.assert_array_equal(c[0,0],[18,52,86,255])

    def test_plugin_override_and_auto_library(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'one').mkdir();(p/'two').mkdir()
            code='from fx import effect\n@effect()\ndef my_invert(frame,t_ms,ctx,amount=1.0):\n    frame=frame.copy();frame[...,:3]=1-frame[...,:3];return frame\n'
            (p/'one/fx.py').write_text(code);(p/'two/fx.py').write_text(code)
            load_directory(p/'one');load_directory(p/'two')
            self.assertEqual(OVERRIDES[-1]['name'],'my_invert');self.assertIn('one',OVERRIDES[-1]['previous'])
            plan=copy.deepcopy(self.base);plan['effects']=[{'name':'my_invert'}]
            r=validate_plan(self.plan(plan));self.assertIn('sha256',r[4][0])
            with patch.dict(os.environ,{'VIDEO_GIF_FX_HOME':str(p/'one')}),contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(['--list']),0)
            self.assertIn('my_invert',output.getvalue())
            EFFECTS.pop('my_invert')

    def test_plugin_actually_renders(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);(folder/'invert.py').write_text('from fx import effect\n@effect()\ndef render_invert(frame,t_ms,ctx):\n frame[...,:3]=1-frame[...,:3];return frame\n')
            load_directory(folder)
            p={'segments':[{'type':'still','image':'A/frames/00000.png','duration_ms':200}],'effects':[{'name':'render_invert'}]}
            render(self.plan(p),self.root/'plugin-render',('png',))
            with Image.open(self.root/'plugin-render/frames/00000.png') as im:self.assertEqual(im.getpixel((260,140)),(35,215,215,255))
            EFFECTS.pop('render_invert')

    def test_downbeats_missing_and_present(self):
        p=copy.deepcopy(self.base);p['effects'][0]['amount']['on']='downbeats'
        with self.assertRaisesRegex(ValueError,'engine beat_this'):validate_plan(self.plan(p))
        fixture=json.loads((Path(__file__).parent/'fixtures/beat_this_fake.json').read_text())
        (self.root/'db.json').write_text(json.dumps(fixture));p={'beatmap':'db.json','segments':[{'type':'still','image':'A/frames/00000.png','end_downbeat':1}], 'effects':[{'name':'flash_white','amount':{'on':'downbeats','decay_ms':100}}]}
        _,_,s,c,_,_=validate_plan(self.plan(p));self.assertEqual(s[0]['duration_ms'],2000)
        self.assertEqual(evaluate({'on':'downbeats'},500,c),0);self.assertEqual(evaluate({'on':'downbeats'},2000,c),1)

    def test_existing_output_and_music_gif(self):
        with self.assertRaisesRegex(ValueError,'new output'):render(self.plan(),self.root,('png',))
        p=copy.deepcopy(self.base);p['music']={'file':'beats.json'}
        with self.assertRaisesRegex(ValueError,'Music requires'):render(self.plan(p),self.root/'badgif',('gif',))
        self.assertFalse((self.root/'badgif').exists())

    def test_birefnet_injected_masker(self):
        for model in ('birefnet-general','birefnet-portrait','u2netp'):
            separate(self.root/'A/frames',self.root/'A/manifest.json',self.root/model,model,lambda im:Image.new('L',im.size,128))
            record=json.loads((self.root/model/'manifest.json').read_text());self.assertEqual(record['background_removal']['model'],model)


class FxAudioTests(unittest.TestCase):
    def test_native_no_ffmpeg_energy_onsets(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'audio.wav';rate=48000;t=np.arange(rate*6)/rate
            for ramp in (False,True):
                x=np.sin(2*np.pi*(440 if ramp else 1000)*t)
                if ramp:x*=.02+.78*t/6
                else:
                    local=t%.5;x*=np.where((t//.5).astype(int)%2==0,.8,.2)*np.exp(-local*100)*(local<.03)
                with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes((x*32767).astype('<i2').tobytes())
                with patch('music_sync.executable',side_effect=AssertionError('must be native')):env=audio_envelopes(path)
                if ramp:
                    self.assertGreater(env['energy'][500],3*env['energy'][100]);self.assertTrue(np.all(np.diff(env['energy'][::10])>=-.02))
                else:self.assertGreater(env['onset'][100],.9);self.assertLess(env['onset'][50],.5)

    def test_fake_engine_and_fallback_offline(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'x.wav').write_bytes(b'fake fixture input')
            raw=np.sin(np.arange(8000*3)*.3).astype('<f4').tobytes()
            fixture=json.loads((Path(__file__).parent/'fixtures/beat_this_fake.json').read_text())
            with patch('music_sync.executable',return_value='offline'),patch('music_sync.subprocess.check_output',return_value=raw):
                r=analyze(p/'x.wav',p/'yes',engine='beat_this',engine_fn=lambda source:fixture)
                self.assertEqual(r['engine'],'beat_this');self.assertEqual(r['downbeats_ms'],[0,2000,4000,6000])
                self.assertEqual(r['bpm'],120)
                def missing(source):raise RuntimeError('beat_this unavailable; pip install beat_this')
                r=analyze(p/'x.wav',p/'no',engine='beat_this',engine_fn=missing)
                self.assertEqual(r['engine'],'rms');self.assertNotIn('downbeats_ms',r);self.assertIn('pip install',r['fallback_reason'])

if __name__=='__main__':unittest.main()
