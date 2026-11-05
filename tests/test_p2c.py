"""P2c regressions and positive/negative instrument controls; offline, small arrays."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fx import Context, TRANSITIONS
from fx.core import premultiply
from fx.transitions.gl_ports import PORT_NAMES
from fx.transitions.gl_common import Shader, finish
from fx_gate_kit import edge_streaks, endpoint_checks, distinct_shot, single_frame_flashes
from fx_gate_pairs import resolve_reference, restyle, break_frame, write_pair_files
from threshold_registry import load, validate, value, check, snapshot, default_value
from threshold_runtime import caption_contrast, motion_smoothness, budget
from calibrate import propose, activate
import captions
from delivery import settings


def texture(w=160,h=90,seed=1):
    a=np.random.default_rng(seed).random((h,w,4),dtype=np.float32);a[...,3]=1
    return a


class Defects(unittest.TestCase):
    def test_polka_near_end_all_aspects(self):
        for w,h in ((320,180),(1000,100),(180,320)):
            a=np.zeros((h,w,4),np.float32);a[...,3]=1;b=a.copy();b[...,:3]=1
            out=TRANSITIONS['gl_polka_dots_curtain']['function'](a,b,.99,Context(w,h))
            self.assertLess(float(np.mean(out[...,0]<1)),.001,(w,h))

    def test_all_ports_last_delivered_frame_and_endpoint_limits(self):
        for name in PORT_NAMES:
            for w,h in ((160,90),(300,30),(90,160)):
                a,b=texture(w,h),texture(w,h,2);spec=TRANSITIONS[name]
                # Reproduce the actual generator's frame clock, including B.
                last=spec['function'](a,b,47/(48-1),Context(w,h))
                np.testing.assert_array_equal(last,b,err_msg=name)
                checks=endpoint_checks(spec,a,b,Context(w,h))
                # Delivered-step screening is a heuristic and remains visible;
                # endpoint identity/limits are the hard shader contract here.
                for key in ('first_error','last_error','first_discontinuity','last_discontinuity'):
                    self.assertLessEqual(checks[key],1/255,(name,key,checks[key]))

    def test_displaced_mattes_are_not_source_union_fragments(self):
        a=np.zeros((90,160,4),np.float32);a[25:65,65:95]=[.3,.6,.9,1]
        for name in ('gl_swirl','gl_rotate_scale_fade','gl_cross_warp','gl_dreamy_zoom'):
            out=TRANSITIONS[name]['function'](a,a,.35,Context(160,90))
            self.assertGreater(float(out[a[...,3]==0,3].sum()),1,name)
            self.assertGreater(float(out[...,3].sum()),100,name)
            hidden=a.copy();hidden[hidden[...,3]==0,:3]=[1,0,1]
            np.testing.assert_allclose(premultiply(out),premultiply(TRANSITIONS[name]['function'](hidden,hidden,.35,Context(160,90))),atol=1e-6)

    def test_spin_only_opaque_zoom_fills_and_hex_keeps_matte(self):
        a=np.zeros((90,160,4),np.float32);a[30:60,65:95]=[.3,.6,.9,1]
        out=TRANSITIONS['spin']['function'](a,a,.5,Context(160,90))
        self.assertAlmostEqual(float(out[...,3].sum()),900,delta=4)
        for p in (.25,.5,.75):
            out=TRANSITIONS['hex_shutter']['function'](a,a,p,Context(160,90))
            np.testing.assert_array_equal(out[...,3],a[...,3])

    def test_nonfinite_progress_public_owned_and_keyword(self):
        a=texture(8,6);ctx=Context(8,6)
        for name in PORT_NAMES:
            for p in (float('nan'),float('inf'),-float('inf')):
                for api in ('function','owned'):
                    with self.assertRaisesRegex(ValueError,'p must be finite'):
                        TRANSITIONS[name][api](a,a,p,ctx)
                with self.assertRaisesRegex(ValueError,'p must be finite'):
                    TRANSITIONS[name]['function'](a,b=a,p=p,ctx=ctx)

    def test_opaque_path_skips_association_and_matches_general_finish(self):
        a,b=texture(),texture(seed=2);s=Shader(a,b,Context(160,90))
        self.assertTrue(s.opaque)
        with patch('fx.transitions.gl_common.premultiply',side_effect=AssertionError('slow path')):
            for name in PORT_NAMES:
                out=TRANSITIONS[name]['function'](a,b,.37,Context(160,90))
                self.assertTrue(np.all(out[...,3]==1))
        with patch.object(Shader,'finish',lambda self,pm,displacement=False: finish(pm,self.original_a,self.original_b,displacement)):
            for name in PORT_NAMES:
                expected=TRANSITIONS[name]['function'](a,b,.37,Context(160,90))
                with patch.object(Shader,'finish',lambda self,pm,displacement=False: pm):
                    actual=TRANSITIONS[name]['function'](a,b,.37,Context(160,90))
                np.testing.assert_allclose(actual,expected,atol=1e-6,err_msg=name)

    def test_glitch_has_local_blocks_and_one_sample(self):
        a=texture();calls=[];original=Shader.sample
        def sample(s,*args): calls.append(float(np.ptp(args[1]-s.x)));return original(s,*args)
        with patch.object(Shader,'sample',sample):
            out=TRANSITIONS['gl_glitch_memories']['function'](a,a,.37,Context(160,90))
        self.assertEqual(len(calls),1);self.assertGreater(calls[0],.001)
        self.assertGreater(np.abs(out-a).mean(),.01)

    def test_curved_wipe_shades_only_band_and_preserves_distant_shots(self):
        a=np.zeros((100,160,4),np.float32);a[...,0]=a[...,3]=1
        b=np.zeros_like(a);b[...,2]=b[...,3]=1
        calls=[];exp=np.exp
        def measured_exp(x):calls.append(np.size(x));return exp(x)
        with patch('fx.transitions.gl_curved_wipe.np.exp',measured_exp):
            out=TRANSITIONS['gl_curved_wipe']['function'](a,b,.5,Context(160,100),curvature=0)
        self.assertEqual(len(calls),1);self.assertLess(calls[0],160*100/3)
        np.testing.assert_array_equal(out[10],a[10])
        np.testing.assert_allclose(out[90],b[90],atol=1/65535)
        self.assertLess(float(out[52,:,2].mean()),1)

    def test_caption_minimum_piece_hyphen_span_and_no_overlap(self):
        cfg=settings((270,480),platform='tiktok')
        for length in range(35,66):
            text='W'*length;words=[dict(text=text,start_ms=113,end_ms=414),dict(text='next',start_ms=414,end_ms=700)]
            data=captions.prepare(dict(words=words,style='clean'),Path('.'),True)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore');r=captions.CaptionRenderer(data,cfg['size'],cfg['safe_zone'])
            pieces=[w for line in r.lines for w in line['words'] if w.get('split_word')]
            self.assertTrue(pieces)
            self.assertEqual(''.join(w['source_text'] for w in pieces),text)
            for i,w in enumerate(pieces):
                self.assertGreaterEqual(len(w['source_text']),3)
                self.assertGreaterEqual(w['start_ms'],113);self.assertLessEqual(w['end_ms'],414)
                if i<len(pieces)-1:self.assertTrue(w['text'].endswith('-'))
                for c in w['chars']:
                    self.assertEqual(c['start_ms'],w['start_ms']);self.assertEqual(c['end_ms'],w['end_ms'])
            for a,b in zip(r.lines,r.lines[1:]):self.assertLessEqual(a['end_ms'],b['start_ms'])

    def test_mask_validation_path_and_nearest_warning(self):
        import contextlib,io
        from fx_render import validate_plan
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);Image.new('RGBA',(24,16),(80,120,160,255)).save(root/'a.png')
            plan=dict(experimental=True,sampling='nearest',segments=[dict(type='still',image='a.png',duration_ms=400),
                dict(type='still',image='a.png',duration_ms=400,transition=dict(name='luma_wipe',duration_ms=160,mask='missing-mask.png'))])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'missing-mask.png'):validate_plan(path)
            for name in PORT_NAMES:
                plan['segments'][1]['transition']=dict(name=name,duration_ms=160);path.write_text(json.dumps(plan))
                stream=io.StringIO()
                with contextlib.redirect_stderr(stream):validate_plan(path)
                self.assertIn(name+' blends colours',stream.getvalue())


def instrument(cls='C',direction='max'):
    scores={'best':.2,'benchmark':.5,'known_worse':2.,'positive_control':.4,'negative_control':1.8,'style_control':.8}
    anchors=[dict(id=k,path='held-out/'+k,role=k,expected='fail' if k in ('known_worse','negative_control') else 'tie' if k=='style_control' else 'pass',held_out=True,label_source='fixture') for k in scores]
    e=dict(id='test.boundary',value=1.,**{'class':cls},unit='ratio',measures='synthetic-v1',direction=direction,anchors=anchors,
           history=[],provenance=dict(source_class='ANCHOR',ref='test fixture'),status='active',bounds=[.01,10.],max_step=.1 if cls=='R' else .15,margin=.01)
    data=dict(version=1,round=3,thresholds=[e])
    ev=dict(measurements={k:[v-.001,v,v+.001] for k,v in scores.items()},baseline={k:dict(mean=v,sigma=.01) for k,v in scores.items()},
            candidate_ids=['unseen-candidate'],trigger='anchor_set_grew',previous_count=15,audited_by='independent-auditor')
    return data,ev


class Registry(unittest.TestCase):
    def test_schema_and_runtime_values(self):
        data=load();self.assertEqual(value('audio.loudness.target'),-14)
        self.assertEqual(check('visibility.onset_contrast.min',999)['decision'],'unknown')
        self.assertEqual(check('caption.contrast.min',4)['decision'],'fail')
        self.assertEqual(len(snapshot(data)['sha256']),64)
        schema=json.loads((ROOT/'references/thresholds.schema.json').read_text())
        item=schema['properties']['thresholds']['items']
        for e in data['thresholds']:
            self.assertTrue(set(item['required'])<=set(e))
            self.assertTrue(set(e)<=set(item['properties']))
        validate(data)

    def test_invalid_schema_and_c_controls(self):
        data,_=instrument();data['thresholds'][0]['value']=float('nan')
        with self.assertRaises(ValueError):validate(data)
        data,_=instrument();data['thresholds'][0]['anchors']=[]
        with self.assertRaises(ValueError):validate(data)

    def test_fixed_immutable(self):
        data,ev=instrument('F')
        with self.assertRaisesRegex(ValueError,'immutable'):propose(data,'test.boundary',ev,3,'coordinator')

    def test_c_boundary_margin_growth_audit_and_next_round(self):
        data,ev=instrument();new,report=propose(data,'test.boundary',ev,3,'coordinator')
        self.assertEqual(report['status'],'pending');self.assertAlmostEqual(report['to'],1.15)
        self.assertEqual(value('test.boundary',data=new),1)
        with self.assertRaisesRegex(ValueError,'later round'):activate(new,3)
        self.assertEqual(value('test.boundary',data=activate(new,4)),report['to'])
        self.assertEqual(len(report['anchor_decisions']),6)
        for key in ('from','to','trigger','approved_by','date','anchor_decisions','evidence'):self.assertIn(key,new['audit'][0])
        self.assertNotIn('pending',data)
        ev['previous_count']=18
        with self.assertRaisesRegex(ValueError,'10%'):propose(data,'test.boundary',ev,3,'coordinator')

    def test_candidate_and_unheld_anchors_rejected(self):
        data,ev=instrument();ev['candidate_ids']=['best']
        with self.assertRaisesRegex(ValueError,'candidate'):propose(data,'test.boundary',ev,3,'coordinator')
        data,ev=instrument();data['thresholds'][0]['anchors'][0]['held_out']=False
        with self.assertRaisesRegex(ValueError,'held-out'):propose(data,'test.boundary',ev,3,'coordinator')
        data,ev=instrument();ev['measurements']['candidate']=[1]
        with self.assertRaisesRegex(ValueError,'candidate'):propose(data,'test.boundary',ev,3,'coordinator')

    def test_drift_freezes_and_control_failure_invalidates(self):
        data,ev=instrument();ev['baseline']['best']['mean']=.1
        new,report=propose(data,'test.boundary',ev,3,'coordinator')
        self.assertEqual(report['status'],'frozen');self.assertFalse(new.get('pending'))
        data,ev=instrument();ev['measurements']['positive_control']=[1.2]*3;ev['baseline']['positive_control']['mean']=1.2
        new,report=propose(data,'test.boundary',ev,3,'coordinator')
        self.assertEqual(report['status'],'instrument_invalid');self.assertEqual(value('test.boundary',data=new),1)
        ev['baseline']['positive_control']['mean']=.4
        new,report=propose(data,'test.boundary',ev,3,'coordinator')
        self.assertEqual(report['status'],'instrument_invalid');self.assertIn('positive_control',report['drift_anchors'])

    def test_overlapping_distributions_never_go_live(self):
        data,ev=instrument();ev['measurements']['benchmark']=[.3,2.4];ev['baseline']['benchmark']['mean']=1.35
        new,report=propose(data,'test.boundary',ev,3,'coordinator')
        self.assertEqual(report['status'],'instrument_invalid');self.assertFalse(new.get('pending'))

    def test_flip_requires_confirmation_and_lists_flips(self):
        data,ev=instrument();ev['measurements']['style_control']=[1.1]*3;ev['baseline']['style_control']['mean']=1.1
        new,report=propose(data,'test.boundary',ev,3,'coordinator')
        self.assertEqual(report['status'],'confirmation_required');self.assertEqual(report['flips'][0]['anchor'],'style_control')
        self.assertFalse(new.get('pending'))
        new,report=propose(data,'test.boundary',ev,3,'coordinator',True)
        self.assertEqual(report['status'],'pending')

    def test_r_tightens_ten_percent_three_trials_over_noise(self):
        data,ev=instrument('R');data['thresholds'][0]['margin']=1.3
        ev.update(trigger='new_best',previous_best=dict(mean=.5,sigma=.01))
        new,report=propose(data,'test.boundary',ev,3,'auto')
        self.assertAlmostEqual(report['to'],.9)
        ev['previous_best']['sigma']=.3
        with self.assertRaisesRegex(ValueError,'2 sigma'):propose(data,'test.boundary',ev,3,'auto')
        ev['previous_best']=dict(mean=.5,sigma=.01);ev['measurements']['best']=ev['measurements']['best'][:2]
        with self.assertRaisesRegex(ValueError,'three'):propose(data,'test.boundary',ev,3,'auto')

    def test_r_never_relaxes_in_both_directions(self):
        for direction in ('min','max'):
            data,ev=instrument('R',direction);ev.update(trigger='new_best',previous_best=dict(mean=10,sigma=.01))
            if direction=='min':
                for a in data['thresholds'][0]['anchors']:
                    if a['expected']!='tie': a['expected']='fail' if a['expected']=='pass' else 'pass'
            data['thresholds'][0]['margin']=10
            if direction=='max':
                with self.assertRaisesRegex(ValueError,'only tighten'):propose(data,'test.boundary',ev,3,'auto')
            else:
                with self.assertRaises(ValueError):propose(data,'test.boundary',ev,3,'auto')

    def test_u_step_bounds_small_sample_defaults_and_choices(self):
        data,ev=instrument('U');ev.update(trigger='user_choice',requested=5,choices=[dict(id=str(i),source='user') for i in range(5)])
        new,report=propose(data,'test.boundary',ev,3,'user')
        self.assertAlmostEqual(report['to'],1.15)
        data['thresholds'][0]['bounds']=[.5,1.05]
        self.assertEqual(propose(data,'test.boundary',ev,3,'user')[1]['to'],1.05)
        ev['choices']=ev['choices'][:2]
        new,report=propose(data,'test.boundary',ev,3,'user');new=activate(new,4)
        self.assertEqual(new['defaults']['test.boundary'],1.05);self.assertEqual(value('test.boundary',data=new),1)
        self.assertEqual(default_value('test.boundary',data=new),1.05)
        ev['choices']=[]
        with self.assertRaisesRegex(ValueError,'choices'):propose(data,'test.boundary',ev,3,'user')

    def test_c_min_boundary_and_requires_independent_auditor(self):
        data,ev=instrument(direction='min')
        for key,samples in ev['measurements'].items():
            ev['measurements'][key]=[2.2-v for v in samples]
            ev['baseline'][key]['mean']=2.2-ev['baseline'][key]['mean']
        new,report=propose(data,'test.boundary',ev,3,'coordinator')
        self.assertAlmostEqual(report['to'],1.05)
        ev['audited_by']='coordinator'
        with self.assertRaisesRegex(ValueError,'independent'):propose(data,'test.boundary',ev,3,'coordinator')

    def test_r_min_boundary_tightens_upward(self):
        data,ev=instrument('R','min');data['thresholds'][0]['margin']=.85
        for key,samples in ev['measurements'].items():
            ev['measurements'][key]=[2.2-v for v in samples]
            ev['baseline'][key]['mean']=2.2-ev['baseline'][key]['mean']
        ev.update(trigger='new_best',previous_best=dict(mean=1.5,sigma=.01))
        new,report=propose(data,'test.boundary',ev,3,'auto')
        self.assertAlmostEqual(report['to'],1.1)

    def test_round_pending_and_p3_ceiling_guards(self):
        data,ev=instrument()
        with self.assertRaisesRegex(ValueError,'active round'):propose(data,'test.boundary',ev,4,'coordinator')
        new,_=propose(data,'test.boundary',ev,3,'coordinator')
        with self.assertRaisesRegex(ValueError,'Already pending'):propose(new,'test.boundary',ev,3,'coordinator')
        ev['measurements']['best']=[.5]*3;ev['baseline']['best']['mean']=.5
        new,report=propose(data,'test.boundary',ev,3,'coordinator')
        self.assertEqual(report['status'],'instrument_invalid')
        with self.assertRaisesRegex(ValueError,'independent repair'):propose(new,'test.boundary',ev,3,'coordinator')

    def test_u_negative_step_and_duplicated_choices(self):
        data,ev=instrument('U');ev.update(trigger='user_choice',requested=0,choices=[dict(id=str(i),source='user') for i in range(5)])
        self.assertAlmostEqual(propose(data,'test.boundary',ev,3,'user')[1]['to'],.85)
        ev['choices'][1]['id']='0'
        with self.assertRaisesRegex(ValueError,'Repeated'):propose(data,'test.boundary',ev,3,'user')

    def test_u_context_does_not_change_other_content_or_platform(self):
        data,ev=instrument('U');data['thresholds'][0]['value']={'default':1.,'vlog/reels':1.,'tutorial/youtube':2.}
        ev.update(trigger='user_choice',requested=3,context='vlog/reels',choices=[dict(id=str(i),source='user') for i in range(5)])
        updated,report=propose(data,'test.boundary',ev,3,'user')
        active=activate(updated,4)
        self.assertEqual(value('test.boundary','vlog/reels',active),1.15)
        self.assertEqual(value('test.boundary','tutorial/youtube',active),2.)
        self.assertEqual(value('test.boundary','default',active),1.)

    def test_c_registered_cap_cannot_be_bypassed(self):
        data,ev=instrument();data['thresholds'][0]['max_step']=.01
        with self.assertRaisesRegex(ValueError,'step cap'):propose(data,'test.boundary',ev,3,'coordinator')

    def test_instrument_version_and_margin_after_hard_bounds(self):
        data,ev=instrument();data['thresholds'][0]['instrument']='measurement-v1'
        with self.assertRaisesRegex(ValueError,'instrument/version'):propose(data,'test.boundary',ev,3,'coordinator')
        ev['instrument']='measurement-v1';data['thresholds'][0]['bounds']=[.1,.502]
        new,report=propose(data,'test.boundary',ev,3,'coordinator')
        self.assertEqual(report['status'],'instrument_invalid')

    def test_runtime_contrast_budget_motion_positive_negative_controls(self):
        self.assertAlmostEqual(caption_contrast('FFFFFF','000000'),21)
        self.assertEqual(check('caption.contrast.min',caption_contrast('808080','777777'))['decision'],'fail')
        data=load()
        for e in data['thresholds']:
            if e['id'].startswith(('motion.','budget.')):e['status']='active'
        for fps in (24,30,60):
            u=np.linspace(0,1,2*fps+1);smooth=10*(10*u**3-15*u**4+6*u**5)
            self.assertEqual(motion_smoothness(smooth,fps,data=data)['decision'],'pass')
            step=smooth.copy();step[len(step)//2:]+=10
            self.assertEqual(motion_smoothness(step,fps,data=data)['decision'],'fail')
        self.assertTrue(all(c['decision']=='pass' for c in budget([dict(at_ms=0,perceived=.5)],data=data)))
        self.assertTrue(all(c['decision']=='fail' for c in budget([dict(at_ms=i*100,perceived=.5) for i in range(8)],data=data)))


class GateControls(unittest.TestCase):
    def test_one_frame_flash_control_and_hard_cut_negative(self):
        levels=[.2]*12+[.6]*12
        self.assertEqual(single_frame_flashes(levels),[])
        levels[5]=1
        self.assertEqual(single_frame_flashes(levels),[5])
        levels[5]=0.2;levels[18]=0
        self.assertEqual(single_frame_flashes(levels),[18])
    def test_swapped_and_first_last_discontinuity_controls(self):
        a,b=texture(),texture(seed=2);ctx=Context(160,90)
        good={'function':lambda a,b,p,c:a*(1-p)+b*p}
        self.assertEqual(endpoint_checks(good,a,b,ctx)['level'],'PASS')
        swapped={'function':lambda a,b,p,c:b*(1-p)+a*p}
        self.assertTrue(endpoint_checks(swapped,a,b,ctx)['swapped'])
        for end in ('first','last'):
            bad={'function':lambda a,b,p,c:a if p==0 else b if p==1 else b if end=='first' else a}
            report=endpoint_checks(bad,a,b,ctx)
            self.assertEqual(report['level'],'FAIL');self.assertGreater(report[end+'_discontinuity'],.01)
        # Correct exact/limiting endpoint, but a snap on the last delivered step.
        snap={'function':lambda a,b,p,c:b if p>=.98 else a}
        report=endpoint_checks(snap,a,b,ctx)
        self.assertEqual(report['last_discontinuity'],0)
        self.assertIn('last',report['frame_discontinuities'])

    def test_four_pixel_streak_positive_negative_controls(self):
        a=texture();self.assertEqual(edge_streaks(a),[])
        flat=np.ones_like(a)*.5;self.assertEqual(edge_streaks(flat),[])
        for width in (3,4,8):
            b=a.copy();b[:,:width-1]=b[:,width-1:width]
            found=edge_streaks(b)
            self.assertEqual(bool(found),width>=4)
            if found:self.assertEqual(found[0]['width_px'],width)

    def test_b_shot_is_independent_and_style_preserves_matte(self):
        a=texture();b=distinct_shot((160,90),0,'rgba')
        self.assertGreater(np.abs(a[:,::-1]-b).mean(),.1)
        styled=restyle(b);np.testing.assert_array_equal(styled[...,3],b[...,3])
        self.assertGreater(np.abs(styled-b).mean(),.001)
        broken=break_frame(b,24,24);self.assertTrue(np.all(broken==1))

    def test_reference_mappings_and_judge_input_schema(self):
        for name in PORT_NAMES:self.assertTrue(resolve_reference('transition',name,{}).startswith('transition:'))
        self.assertEqual(resolve_reference('transition','gl_fade_grayscale',{}),'transition:crossfade')
        self.assertEqual(resolve_reference('transition','gl_bow_tie_horizontal',{}),'transition:hex_shutter')
        self.assertEqual(resolve_reference('transition','gl_swirl',{'gl_swirl':'transition:gl_cross_warp'}),'transition:gl_cross_warp')
        with self.assertRaisesRegex(ValueError,'stable'):resolve_reference('transition','gl_swirl',{'gl_swirl':'transition:glitch'})
        with self.assertRaisesRegex(ValueError,'family'):resolve_reference('transition','gl_swirl',{'gl_swirl':'effect:grade'})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);write_pair_files(root,[dict(id='one',a=tmp,b=tmp,context='same brief')],[])
            self.assertIsInstance(json.loads((root/'pairs.json').read_text()),list)
            criteria=json.loads((root/'criteria.json').read_text());self.assertTrue(criteria['tieOverall'])
            self.assertIn('professional editor',criteria['criteria'][0]['text'])


if __name__=='__main__':unittest.main()
