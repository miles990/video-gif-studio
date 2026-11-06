"""S7 synthetic controls. No third-party media, paid clients or repository scratch."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave
import cv2
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from taste_common import write,read,peaks,compare_curve,plot_curve,ROOT
from taste_report import colorfulness,saliency,frame_metrics,arousal,analyze,audio_analysis,save_report
from taste_lint import intent_lint,token_lint,default_tokens,edit_lint,ablation_measure,weakest,default_distance
from storyboard import normalize,validate,lint,prompts,shot_table,fingerprint
from taste_pick import factory,ingest,load,persist,spotcheck,agreement
from shot_match import match,linear,srgb,delta_e,match_plan
from taste_target import calibrate,plan_timing
from media_runtime import locate


def board():
    return dict(core='The traveler arrives',fps=30,design_curve=[[0,.1],[3,.8],[6,.3]],shots=[
        dict(id='wide',duration=1,size='WS',subject='traveler',motion='static',angle=0,why='Establish the destination',reference_id='traveler.png',lighting='soft window light',action='Enter the station'),
        dict(id='mid',duration=2,size='MS',subject='traveler',motion='push',angle=35,why='Reveal the uncertain expression',reference_id='traveler.png',lighting='soft window light',action='Look toward the platform'),
        dict(id='close',duration=3,size='CU',subject='traveler',motion='static',angle=70,why='Resolve the recognition',reference_id='traveler.png',lighting='soft window light',action='Smile')])


def rules(result):return [r['rule'] for r in result['findings']]


class TasteMath(unittest.TestCase):
    def test_colorfulness_independent_known_formula(self):
        rng=np.random.default_rng(12);rgb=rng.integers(0,256,(60,80,3),dtype=np.uint8);a=rgb.astype(float)
        rg=a[:,:,0]-a[:,:,1];yb=.5*(a[:,:,0]+a[:,:,1])-a[:,:,2]
        expected=np.sqrt(np.var(rg)+np.var(yb))+.3*np.sqrt(np.mean(rg)**2+np.mean(yb)**2)
        self.assertAlmostEqual(colorfulness(rgb),expected,places=10)
        self.assertEqual(colorfulness(np.full((30,40,3),128,np.uint8)),0)

    def test_contrast_ramp(self):
        rgb=np.tile(np.arange(256,dtype=np.uint8)[None,:,None],(90,1,3));m=frame_metrics(rgb)
        self.assertAlmostEqual(m['p1'],2.55,delta=1.5);self.assertAlmostEqual(m['p99'],252.45,delta=1.5)

    def test_saliency_centroid_and_dispersion(self):
        a=np.full((180,320,3),25,np.uint8);cv2.circle(a,(224,54),19,(255,0,0),-1)
        b=np.full_like(a,25)
        for i in range(40):cv2.circle(b,(16+(i%8)*40,18+(i//8)*35),3,(255,0,0),-1)
        _,ca,center=saliency(a);_,cb,_=saliency(b)
        self.assertGreaterEqual(ca,cb+.15);self.assertLess(np.linalg.norm(np.asarray(center)-[.7,.3]),.05)

    def test_clutter_controls(self):
        values=[]
        for count in (0,10,40,160,320):
            a=np.full((540,960,3),128,np.uint8);cv2.circle(a,(480,270),45,(255,255,255),-1);rng=np.random.default_rng(13)
            for i in range(count):
                x,y=rng.integers([0,0],[900,500]);cv2.rectangle(a,(int(x),int(y)),(int(x+30),int(y+20)),(0,0,0),1)
            values.append(frame_metrics(a)['clutter'])
        self.assertTrue(np.all(np.diff(values)>0));self.assertGreater(values[-1],values[0]*3)

    def test_arousal_formula_and_weights(self):
        t=np.arange(0,12,.1);m=np.where((t>=8)&(t<8.5),40,0);l=np.where((t>=6)&(t<8),-40,np.where((t>=8)&(t<8.5),-10,-24));y=np.where((t>=6)&(t<8),35,np.where((t>=8)&(t<8.5),220,110))
        p=arousal(t,m,[],l,y);z=np.array(list(p['components'].values()));raw=np.array(p['weights'])@z
        independent=np.convolve(np.pad(raw,(10,9),mode='edge'),np.ones(20)/20,'valid')
        np.testing.assert_allclose(p['values'],independent,atol=1e-10)
        self.assertTrue(7.7<=t[np.argmax(p['values'])]<=9)
        self.assertNotEqual(p['values'],arousal(t,m,[],l,y,[1,0,0,0])['values'])
        with self.assertRaises(ValueError):arousal(t,m,[],l,y,[-1,1,1,1])

    def test_design_match_mismatch_shift(self):
        t=np.arange(0,32,.1);points=[[0,0],[23,1],[28,.5],[32,.3]];d=np.interp(t,*np.array(points).T)
        match=compare_curve(t,d,points);bad=compare_curve(t,1-d,points);shift=compare_curve(t,np.interp(t-4,t,d),points)
        self.assertFalse(match['revise']);self.assertTrue(bad['revise']);self.assertTrue(shift['revise']);self.assertAlmostEqual(shift['peak_offset_bars'],2)
        self.assertEqual(len(bad['deviations']),3)

    def test_weakest_uses_residual_not_designed_valley(self):
        t=np.arange(0,30,.1);d=np.ones(len(t));d[(t>=18)&(t<20)]=0;y=d.copy();y[(t>=9)&(t<11)]=0
        report=dict(M15=dict(times=t.tolist(),values=y.tolist(),components={'motion':y.tolist()}),comparison=compare_curve(t,y,[[0,1],[17.9,1],[18,0],[19.9,0],[20,1],[30,1]]))
        self.assertAlmostEqual(weakest(report)['start'],9,delta=.3)

    def test_ablation_amended_lossless_boundary(self):
        a=np.full((2,20,30,3),100,np.uint8);self.assertTrue(ablation_measure(a,a)['noop'])
        b=a.copy();b[:,::2]+=1;self.assertTrue(ablation_measure(a,b)['noop'])
        b=a+40;self.assertFalse(ablation_measure(a,b)['noop'])
        self.assertFalse(ablation_measure(a,a,2)['noop'])
        json.dumps(ablation_measure(a,a),allow_nan=False)

    def test_default_distance_seed_range(self):
        seeds=[dict(asl=1,cv=.3),dict(asl=1.1,cv=.4),dict(asl=.9,cv=.2)]
        self.assertEqual(default_distance(dict(asl=3,cv=.8),seeds)['distinct_metrics'],2)
        self.assertEqual(default_distance(seeds[1],seeds)['distinct_metrics'],0)

    def test_delta_e_sharma_reference_pairs(self):
        a=np.array([[50,2.6772,-79.7751],[50,3.1571,-77.2803],[50,2.8361,-74.0200]])
        b=np.tile([50,0,-82.7485],(3,1));np.testing.assert_allclose(delta_e(a,b),[2.0425,2.8615,3.4412],atol=.0001)

    def test_shot_match_linear_card_and_strength_zero(self):
        colors=np.array([[x,x,x] for x in np.linspace(10,245,11)]+[[224,172,105],[200,20,20],[20,200,20],[20,20,200]],np.uint8)
        a=np.repeat(colors[None,:,:],30,axis=0);b=srgb(linear(a)*np.array([1.2,1,.8])*.76)
        corrected,r=match(a,b);self.assertLess(r['after']['mean_delta_e2000'],2);self.assertLess(r['after']['max_delta_e2000'],5)
        np.testing.assert_array_equal(match(a,b,0)[0],b)

    def test_matching_precedes_creative_lut(self):
        from shot_match import apply_lut,load_lut,measure
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'look.cube'
            rows=['LUT_3D_SIZE 2']+[f'{r*.9} {g*.8} {b*.7}' for b in (0,1) for g in (0,1) for r in (0,1)]
            path.write_text('\n'.join(rows));lut=load_lut(path)
            reference=np.tile(np.arange(20,220,dtype=np.uint8)[None,:,None],(20,1,3));source=srgb(linear(reference)*[.912,.76,.608])
            matched,_=match(reference,source)
            self.assertLess(measure(apply_lut(reference,lut),apply_lut(matched,lut))['mean_delta_e2000'],3)

    def test_png_amended_color_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'curve.png';t=np.arange(0,10,.1);plot_curve(path,t,np.sin(t),np.cos(t))
            rgb=np.array(Image.open(path))
            for color in ([57,217,239],[255,171,81]):
                mask=np.all(rgb==color,axis=2);self.assertGreater(mask.mean(),.001);self.assertGreater(np.any(mask[:,55:966],axis=0).mean(),.8)


class TasteLint(unittest.TestCase):
    def test_intent_exact_missing_two_and_copy_rejected(self):
        b=board();self.assertEqual(intent_lint(b),[])
        b['shots'][0]['why']='';b['shots'][1]['why']=b['core'];r=intent_lint(b)
        self.assertEqual([x['element_id'] for x in r],['wide','mid'])

    def test_intent_nested_elements(self):
        b=board();b['shots'][0]['effects']=[dict(id='noise',name='halation',serves_core='')]
        self.assertEqual(intent_lint(b)[0]['element_id'],'noise')

    def test_eye_trace_and_annotated_exception(self):
        b=normalize(board());b['shots'][0]['focal']=[.15,.15];b['shots'][1]['focal']=[.85,.85]
        r=dict(media=dict(fps=30,width=1080,height=1920));rows=edit_lint(r,b);self.assertEqual(rows[0]['rule'],'eye_trace')
        self.assertAlmostEqual(rows[0]['measured'],1.428,delta=.02)
        b['shots'][1]['rule_break']=dict(rule='eye_trace',reason='Disorient the audience at the reveal')
        self.assertEqual(edit_lint(r,b)[0]['status'],'annotated')
        b['shots'][1]['focal']=[.20,.18];self.assertEqual(edit_lint(r,b),[])

    def test_cut_on_action_positive_negative(self):
        b=normalize(board());r=dict(M6=dict(pixels_per_frame=[0]*30+[8]*20+[0]*130))
        b['shots'][1]['start']=2;self.assertIn('cut_on_action',[x['rule'] for x in edit_lint(r,b)])
        b['shots'][1]['start']=1.5;self.assertNotIn('cut_on_action',[x['rule'] for x in edit_lint(r,b)])

    def test_mickey_and_cv(self):
        b=board();b['actions']=[dict(sfx=True) for _ in range(12)]
        self.assertIn('mickey_mousing',[x['rule'] for x in edit_lint({},b)])
        b['actions']=[dict(sfx=i in (0,5,11)) for i in range(12)];self.assertEqual(edit_lint({},b),[])
        self.assertEqual(edit_lint(dict(M1=dict(cv=0,lengths=[1,1])),{})[0]['rule'],'shot_cv')
        self.assertEqual(edit_lint(dict(M1=dict(cv=.6,lengths=[.5,2])),{}),[])

    def test_peak_valley_controls(self):
        ts=np.arange(0,4,.1);v=np.ones(40);v[20]=1.1
        r=dict(M15=dict(times=ts.tolist(),values=v.tolist(),peaks=[dict(time=2,value=1.1)]))
        self.assertEqual(edit_lint(r)[0]['rule'],'pre_peak_valley')
        r['M15']['values'][5]=0;self.assertEqual(edit_lint(r),[])

    def test_tokens_all_sources_and_exceptions(self):
        tokens=default_tokens();p=dict(captions=dict(font='third',items=[dict(font='third',start_ms=1000)]),effects=[dict(name='title',font='third')])
        self.assertEqual(len(token_lint(p,tokens)),3)
        p=dict(font='sans',lut=None,motion='push',film_grain=.1,sfx_family='hit',transition='crossfade');self.assertEqual(token_lint(p,tokens),[])
        p.update(font='third',lut='second.cube',motion='crash_in',film_grain=.8,sfx_family='beep',transition='hex_shutter')
        self.assertEqual({x['rule'] for x in token_lint(p,tokens)},{'token_font','token_lut','token_motion','token_texture','token_sfx','token_transition'})
        p['rule_break']={'rule':'token_font','reason':'Guest title is intentionally alien'}
        self.assertEqual(next(x for x in token_lint(p,tokens) if x['rule']=='token_font')['status'],'annotated')

    def test_transition_family_registry_coverage(self):
        from fx.core import catalog
        cards=read(ROOT/'references/fx-cards.json')
        for name in catalog()['transitions']:self.assertIn('family',cards['transition:'+name])

    def test_focal_overlap(self):
        from mastery_lint import inspect_focal
        a=np.full((180,320,3),20,np.uint8);cv2.circle(a,(240,40),12,(255,255,255),-1)
        mask=np.zeros((180,320),np.uint8);mask[:90,160:]=255
        self.assertEqual(inspect_focal(a,mask)['findings'],[])
        cv2.circle(a,(60,130),30,(255,255,255),-1)
        self.assertEqual(inspect_focal(a,mask)['findings'][0]['rule'],'focal_hierarchy')


class StoryboardTests(unittest.TestCase):
    def test_schema_and_legacy_copy(self):
        b=board();before=json.dumps(b);validate(b);self.assertEqual(json.dumps(b),before)
        for key,bad in [('size','XX'),('motion',['push','pan']),('lens','fisheye'),('direction','up')]:
            x=deepcopy(b);x['shots'][0][key]=bad
            with self.assertRaises(ValueError):validate(x)

    def test_same5_positive_negative(self):
        b=board();b['shots']=[dict(duration=1,size='MS',why='Show the next station') for _ in range(5)]
        self.assertEqual(rules(lint(b)).count('shot_size_variation'),3)
        for s,size in zip(b['shots'],['WS','MS','CU','MS','WS']):s['size']=size
        self.assertNotIn('shot_size_variation',rules(lint(b)))

    def test_angle_positive_negative(self):
        b=board();b['shots'][1].update(size='WS',angle=20);self.assertIn('angle_30',rules(lint(b)))
        b['shots'][1]['angle']=35;self.assertNotIn('angle_30',rules(lint(b)))

    def test_axis_positive_negative(self):
        b=board();b['shots'][0]['direction']='left-to-right';b['shots'][1]['direction']='right-to-left'
        self.assertIn('axis_180',rules(lint(b)));b['shots'][1]['visible_axis_crossing']=True;self.assertNotIn('axis_180',rules(lint(b)))
        del b['shots'][1]['visible_axis_crossing'];b['shots'][0]['direction']='neutral';self.assertNotIn('axis_180',rules(lint(b)))

    def test_two_move_positive_negative_recipe(self):
        b=board();b['shots'][1]['motion']=['push','pan'];self.assertIn('one_motion',rules(lint(b)))
        b['shots'][1]['motion']='push';self.assertNotIn('one_motion',rules(lint(b)))
        b['shots'][1]['recipe']=dict(name='impact',perceived=.8);self.assertIn('one_motion',rules(lint(b)))
        b['shots'][1]['motion']='static';self.assertNotIn('one_motion',rules(lint(b)))

    def test_quiet_budget_positive_negative_monotonic(self):
        b=board();b['design_curve']=[[0,0],[6,0]];b['shots'][0]['perceived']=.8
        self.assertIn('effect_budget',rules(lint(b)));b['shots'][0]['perceived']=.05;self.assertNotIn('effect_budget',rules(lint(b)))
        from threshold_registry import value
        e=np.array([.8,.2,.5,.1]);v=value('taste.budget.base')+value('taste.budget.slope')*e
        self.assertEqual(sum((e[i]-e[j])*(v[i]-v[j])<0 for i in range(4) for j in range(i)),0)

    def test_storyboard_cv_intent_tokens(self):
        b=board();b['shots'][0]['why']='';b['shots'][2]['why']=''
        self.assertEqual(rules(lint(b)).count('intent_coverage'),2)
        b['tokens']=default_tokens();b['shots'][1]['transition']='hex_shutter';self.assertIn('token_transition',rules(lint(b)))

    def test_automatic_design_is_explicit(self):
        b=board();del b['design_curve'];r=lint(b)
        self.assertIn('automatic',r['design_origin']);self.assertTrue(r['design_curve'])

    def test_prompts_fields_coverage_reference_and_no_calls(self):
        b=board();p=prompts(b);self.assertEqual(p['provider_calls'],0);self.assertFalse(p['ready_for_authorized_generation'])
        b['shots'][0]['coverage']=True;p=prompts(b,dict(storyboard_sha256=fingerprint(b)))
        self.assertEqual(len(p['prompts']),5);self.assertFalse(p['ready_for_authorized_generation'])
        for s in p['prompts']:self.assertTrue({'size','motion','action','lighting','duration','reference_id'}<=set(s))
        b['shots'][1]['reference_id']='different'
        with self.assertRaises(ValueError):prompts(b)

    def test_table_has_same_rows_and_cinematography(self):
        table=shot_table(board());self.assertEqual(len(table.splitlines()),5)
        for field in ['size','angle','lens','motion','composition','lighting','intent','recipe']:self.assertIn(field,table.splitlines()[0])


class ProfileTests(unittest.TestCase):
    def test_bounded_persisted_five_density_choices(self):
        p=factory();original=deepcopy(p)
        for i in range(5):
            old=p['defaults']['density'];p=ingest(p,[dict(id=str(i),date='2026-11-05',source='test',choice='B',dimension='density',options={'B':{'density':10}})])
            self.assertLessEqual(p['defaults']['density']/old,1.15000001)
        self.assertGreater(p['defaults']['density'],original['defaults']['density']);self.assertFalse(p['gate_updates'])
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'taste.json';persist(path,p);self.assertEqual(load(path),p)
            path.unlink();self.assertEqual(load(path),factory())

    def test_family_two_choices_and_idempotent(self):
        choices=[dict(id=str(i),date='2026-11-05',source='test',choice='B',dimension='transition_family',options={'B':{'transition_family':'energy'}}) for i in range(2)]
        p=ingest(factory(),choices);self.assertEqual(p['defaults']['transition_family'],'energy');self.assertEqual(ingest(p,choices),p)
        scoped=ingest(factory(),choices,'mv/reels');self.assertEqual(scoped['defaults']['transition_family'],'dissolve');self.assertEqual(scoped['contexts']['mv/reels']['defaults']['transition_family'],'energy')
        from taste_pick import prepare_pairs
        with self.assertRaises(ValueError):prepare_pairs([],Path('unused'))

    def test_profile_roundtrip_preserves_weights_and_contexts(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'taste.json'
            for weights in ([.35,.25,.30,.10], [7,5,6,2]):
                with self.subTest(weights=weights):
                    p=factory()
                    p['weights']=weights
                    p['contexts']={'quiet':factory()}
                    before=deepcopy(p)
                    persist(path,p)
                    self.assertEqual(p,before)
                    self.assertEqual(load(path),before)
                    persist(path,load(path))
                    self.assertEqual(load(path),before)

    def test_spotcheck_first_sample_and_wilson(self):
        choices=spotcheck(read(ROOT/'wow/fx/gate/spotcheck-1-answers.json'),read(ROOT/'wow/fx/gate/spotcheck-1-key.json'))
        p=ingest(factory(),choices);self.assertEqual(len(p['choices']),8);self.assertEqual(p['agreement']['status'],'invalid')
        self.assertEqual(p['defaults']['density'],1)
        for name in ('burn_through','luminance_melt'):self.assertTrue(any(name in k and v==1 for k,v in p['item_preferences'].items()))
        self.assertEqual(agreement([dict(choice='A',judge='A')]*7+[dict(choice='B',judge='A')])['status'],'valid')
        self.assertEqual(agreement([dict(choice='A',judge='A')]*4+[dict(choice='B',judge='A')]*4)['status'],'directional')

    def test_corruption_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'taste.json';path.write_text('broken')
            with self.assertWarns(UserWarning):self.assertEqual(load(path),factory())
            with self.assertWarns(UserWarning):persist(path,factory())
            self.assertEqual(path.read_text(),'broken');self.assertEqual(path.with_suffix('.json.bak').read_text(),'broken')

    def test_target_timing_and_director_defaults(self):
        fast=plan_timing(30,dict(asl=.7,cv=.5));slow=plan_timing(30,dict(asl=3,cv=.3))
        self.assertLess(fast['achieved_asl'],slow['achieved_asl']);self.assertAlmostEqual(fast['achieved_cv'],.5,delta=.02)
        from taste_director import treatment
        p=factory();a=treatment(['asset.png'],30,'Arrival',p);p['defaults']['density']=2;b=treatment(['asset.png'],30,'Arrival',p)
        self.assertGreater(sum('recipe' in s for s in b['shots']),sum('recipe' in s for s in a['shots']))


@unittest.skipUnless(locate('ffmpeg') and locate('ffprobe'),'FFmpeg/ffprobe unavailable')
class MediaTasteTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()

    def movie(self,name,durations):
        from delivery import encode_frames,settings
        rng=np.random.default_rng(41);frames=[]
        for i,duration in enumerate(durations):
            rgb=np.array(cv2.cvtColor(np.uint8([[[i*25%180,220,210]]]),cv2.COLOR_HSV2RGB)[0,0],float)
            for _ in range(round(duration*30)):
                a=np.clip(rgb+rng.normal(0,1,(90,160,3)),0,255).astype(np.uint8);frames.append(Image.fromarray(a).convert('RGBA'))
        path=self.root/(name+'.mp4');encode_frames(iter(frames),path,settings((160,90),30));return path

    def test_cut_sequences_cv_known_answers_and_determinism(self):
        for name,durations,cv in [('eq',[1]*10,0),('alt',[.5,2]*4,.6)]:
            path=self.movie(name,durations);r=analyze(path)
            self.assertEqual(r['M1']['cut_frames'],np.cumsum(np.array(durations)*30).astype(int).tolist()[:-1]);self.assertAlmostEqual(r['M1']['cv'],cv,places=5)
            self.assertAlmostEqual(r['M1']['asl'],np.mean(durations));self.assertIsNone(r['M8']['lra'])
            save_report(r,self.root/(name+'-report'));a=(self.root/(name+'-report.png')).read_bytes();save_report(analyze(path),self.root/(name+'-again'))
            self.assertEqual(a,(self.root/(name+'-again.png')).read_bytes());self.assertEqual(r,read(self.root/(name+'-again.json')))

    def test_reference_calibration_stats_only(self):
        a=self.movie('a',[.5,1]*2);b=self.movie('b',[1,2]*2)
        first=calibrate([a,b]);self.assertEqual(first,calibrate([b,a]));raw=json.dumps(first)
        self.assertLess(len(raw),64000);self.assertNotIn(str(a),raw);self.assertNotIn('values',raw)

    def wav(self,name,pcm):
        path=self.root/(name+'.wav')
        with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes((np.asarray(pcm)*32767).astype('<i2').tobytes())
        return path

    def test_audio_spectrum_onset_silence_ebu(self):
        rate=48000;t=np.arange(3*rate)/rate;pcm=np.concatenate([.1*np.sin(2*np.pi*f*t) for f in (50,1000,6000)])
        loud,spectrum,_,_=audio_analysis(self.wav('band',pcm),9);ts=np.asarray(spectrum['times'])
        for i,f in enumerate((50,1000,6000)):
            mask=(ts>i*3+.1)&(ts<(i+1)*3-.1);self.assertAlmostEqual(float(np.mean(np.array(spectrum['centroid_hz'])[mask])),f,delta=f*.05)
            self.assertAlmostEqual(float(np.mean(np.array(spectrum['low_band_ratio'])[mask])),1 if i==0 else 0,delta=.05)
        self.assertIsNotNone(loud['integrated_lufs']);self.assertAlmostEqual(loud['plr'],loud['true_peak_dbtp']-loud['integrated_lufs'])
        x=np.zeros(rate*10)
        for at in np.r_[np.arange(0,5,.5),np.arange(5,10,.125)]:x[round(at*rate):round(at*rate)+100]=.8
        _,_,onsets,_=audio_analysis(self.wav('click',x),10);self.assertAlmostEqual(sum(t<5 for t in onsets)/5,2,delta=.2);self.assertAlmostEqual(sum(t>=5 for t in onsets)/5,8,delta=.8)
        rng=np.random.default_rng(1);x=rng.normal(0,.1,rate*4);x[rate:rate*2]=0
        _,_,_,ratio=audio_analysis(self.wav('silence',x),4);self.assertAlmostEqual(ratio,.25,delta=.01)

    def test_animatic_zero_assets_mixed_prompts_and_report(self):
        from animatic import render,card,moved
        b=board();b['shots'][1]['duration']=1.5;b['shots'][2]['duration']=.5
        result=render(b,self.root/'animatic');self.assertTrue(Path(result['movie']).is_file());self.assertTrue((self.root/'animatic/taste.png').is_file())
        self.assertTrue(prompts(b,result)['ready_for_authorized_generation'])
        from storyboard import generation_gate
        with self.assertRaises(ValueError):generation_gate(b,result,False)
        self.assertEqual(len(generation_gate(b,result,True)),3)
        from mastery_lint import focal_movie
        Image.fromarray(np.full((180,320),255,np.uint8)).save(self.root/'mask.png')
        b['shots'][0]['subject_mask']='mask.png'
        focal=focal_movie(result['movie'],b,self.root);self.assertEqual(focal['findings'],[]);self.assertIsNone(focal['shots'][1]['value'])
        self.assertEqual(result['cut_times'],[1,2.5])
        wide=card(dict(id='A',size='EWS',duration=1,motion='static'));close=card(dict(id='B',size='CU',duration=1,motion='static'))
        self.assertLess(np.mean(np.all(wide[:,:,:3]==[24,35,46],axis=-1)),np.mean(np.all(close[:,:,:3]==[24,35,46],axis=-1))/4)
        push=dict(id='p',size='MS',duration=1,motion='push');frame=card(push)
        self.assertGreater(np.mean(np.all(moved(frame,push,1)[:,:,:3]==[24,35,46],axis=-1)),np.mean(np.all(frame[:,:,:3]==[24,35,46],axis=-1))*1.1)

    def test_invalid_media_no_output(self):
        from taste_report import main
        dest=self.root/'absent'/'report';self.assertNotEqual(main([str(self.root/'nope'),'--out',str(dest)]),0);self.assertFalse(dest.parent.exists())

    def test_actual_category_ablation_two_noops_and_zoom(self):
        from mastery_lint import ablate
        yy,xx=np.indices((90,160));a=np.stack([(xx*7)%256,(yy*11)%256,((xx+yy)*3)%256],axis=-1).astype(np.uint8)
        Image.fromarray(a).save(self.root/'source.png')
        p=dict(experimental=True,segments=[dict(type='still',image='source.png',duration_ms=2000)],effects=[dict(name='vignette',amount=0),dict(name='film_grain',amount=0),dict(name='zoom_punch',scale=1.25)])
        write(self.root/'plan.json',p);r=ablate(self.root/'plan.json',self.root/'ablate');rows={x['category']:x for x in r['categories']}
        self.assertEqual(r['coverage'],1);self.assertTrue(rows['vignette']['noop']);self.assertTrue(rows['film_grain']['noop']);self.assertFalse(rows['zoom_punch']['noop'])
        self.assertTrue(Path(rows['zoom_punch']['pair']['A']).is_file())

    def test_j_l_cut_measured_after_render(self):
        from animatic import render
        from taste_common import run,executable
        t=np.arange(48000*5)/48000
        a=self.wav('a',.15*np.sin(2*np.pi*440*t));b=self.wav('b',.15*np.sin(2*np.pi*880*t))
        for key,expected in [('audio_lead_ms',1.5),('audio_tail_ms',2.5)]:
            sb=dict(core='Dialogue bridges the cut',shots=[dict(id='a',duration=2,size='WS',why='Hear the first speaker',sound={'file':str(a)}),dict(id='b',duration=2,size='CU',why='Hear the reply',sound={'file':str(b)})])
            sb['shots'][1 if key=='audio_lead_ms' else 0]['sound'][key]=500
            r=render(sb,self.root/key)
            pcm=np.frombuffer(run([executable('ffmpeg'),'-v','error','-i',r['movie'],'-ac','1','-ar','48000','-f','f32le','-']).stdout,'<f4')
            centers=np.arange(1,3,.02);scores=[]
            for c in centers:
                x=pcm[round((c-.01)*48000):round((c+.01)*48000)];clock=np.arange(len(x))/48000
                scores.append(abs(x@np.exp(-2j*np.pi*880*clock))-abs(x@np.exp(-2j*np.pi*440*clock)))
            change=float(centers[np.flatnonzero(np.array(scores)>0)[0]])
            self.assertAlmostEqual(change,expected,delta=1/30)

    def test_three_storyboards_prediction_vs_actual(self):
        from animatic import render
        cases=[('arc',[4,3,2,1,1,1,4],[.1,.3,.5,.9,1,.8,.2],['static','pan','push','push','pan','push','static']),
               ('quiet',[4,3,2,1,2,4],[.05,.15,.3,1,.4,.1],['static','static','pan','push','pull','static']),
               ('style',[3,2,1,1,2,3],[.2,.5,.9,1,.5,.2],['static','pan','push','pull','pan','static'])]
        for name,lengths,energies,moves in cases:
            rng=np.random.default_rng(77);audio=np.concatenate([rng.normal(0,10**((-45+e*30)/20),round(d*48000)) for d,e in zip(lengths,energies)])
            music=self.wav(name,audio);b=dict(core='Arrival into a crowded station',shots=[]);cursor=0;points=[]
            for i,(duration,energy,move) in enumerate(zip(lengths,energies,moves)):
                b['shots'].append(dict(id=str(i),duration=duration,size=['WS','MS','CU'][i%3],motion=move,why='Show the next phase of arrival',sound={'energy':energy}))
                points.append([cursor,energy]);cursor+=duration
            b['design_curve']=points+[[cursor,energies[-1]]]
            result=render(b,self.root/name,music=music)
            self.assertGreaterEqual(result['predicted_correlation'],.6,name)
            report=read(self.root/name/'taste.json');pred=read(self.root/name/'lint.json')['predicted']
            measured=np.interp(pred['times'],report['M15']['times'],report['M15']['values'])
            independent=float(np.corrcoef(pred['values'],measured)[0,1]);self.assertAlmostEqual(independent,result['predicted_correlation'],places=10)

    def test_shot_match_plan_reference_hash_unchanged(self):
        a=np.tile(np.arange(160,dtype=np.uint8)[None,:,None],(90,1,3));b=srgb(linear(a)*[.912,.76,.608])
        Image.fromarray(a).save(self.root/'a.png');Image.fromarray(b).save(self.root/'b.png')
        write(self.root/'plan.json',dict(segments=[dict(type='still',image='a.png',duration_ms=1000),dict(type='still',image='b.png',duration_ms=1000)]))
        before=hashlib.sha256((self.root/'a.png').read_bytes()).hexdigest();match_plan(self.root/'plan.json',self.root/'match')
        self.assertEqual(hashlib.sha256(Path(read(self.root/'match/plan.json')['segments'][0]['image']).read_bytes()).hexdigest(),before)

    def test_luminance_peak_and_constant_controls(self):
        from delivery import encode_frames,settings
        for name,levels,expected in [('drop',[110]*60+[35]*20+[220]*5+[120]*35,220/35-1),('lit',[110]*60+[200]*20+[220]*5+[120]*35,.1),('same',[128]*120,0)]:
            levels=np.repeat(levels,3)
            frames=(Image.fromarray(np.full((90,160,3),round((y-16)*255/219),np.uint8)).convert('RGBA') for y in levels)
            path=self.root/(name+'.mp4');encode_frames(frames,path,settings((160,90),30));r=analyze(path)
            if name=='drop':self.assertAlmostEqual(r['M4']['jump'],expected,delta=.08);self.assertEqual(r['M4']['peak_frame'],240)
            elif name=='lit':self.assertAlmostEqual(r['M4']['jump'],expected,delta=.02);self.assertEqual(r['M4']['peak_frame'],240);self.assertIn('Already bright',r['M4']['warning'])
            elif name=='same':self.assertLess(r['M4']['jump'],.01);self.assertIsNone(r['M4']['peak_frame'])
            self.assertEqual(len(r['M13']['p1']),len(levels))

    def test_motion_three_known_speeds(self):
        from delivery import encode_frames,settings
        for speed in (0,4,16):
            frames=[]
            for i in range(60):
                a=np.full((180,320,3),30,np.uint8);cv2.circle(a,(20+(i*speed)%280,90),12,(230,230,230),-1);frames.append(Image.fromarray(a).convert('RGBA'))
            path=self.root/f'motion{speed}.mp4';encode_frames(iter(frames),path,settings((320,180),30));r=analyze(path)
            measured=float(np.median(r['M6']['pixels_per_frame'][1:]));self.assertAlmostEqual(measured,speed,delta=max(.3,speed*.15))

    def test_signed_cut_beat_offsets(self):
        boundaries=np.array([30,61,92,117,150,181,212,237,270]);durations=np.diff(np.r_[0,boundaries])/30
        r=analyze(self.movie('beat',durations),beats=np.arange(0,10,.5).tolist())
        np.testing.assert_allclose([o['offset_seconds']*30 for o in r['M2']['offsets']],[0,1,2,-3,0,1,2,-3],atol=.5)
        self.assertEqual(r['M2']['within_one_frame'],.5)


if __name__=='__main__':unittest.main()
