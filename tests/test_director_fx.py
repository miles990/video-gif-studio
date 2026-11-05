"""S6 regression and counterexample tests; no subjective appeal assertions."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fx import EFFECTS,TRANSITIONS,Context
from fx.core import catalog,load_directory
from fx_catalog import INTENTS,write_html
from fx_calibrate import load_table,interpolate,inverse,apply
from fx_director import query,lint
from fx_recipes import load_recipes,expand,apply_recipe
from fx_measure import standard,measures,FlashCounter,onset_contrast,classify
from threshold_registry import registry,validate,value


class Cards(unittest.TestCase):
    def test_complete_stable_cards(self):
        required={'intent','energy','needs','good_for','avoid_for','duration_ms','pairs_with_sfx','conflicts','gate','style_tags','preview','cost_ms_per_frame@720p'}
        seen=[]
        for entries in catalog().values():
            for name,card in entries.items():
                with self.subTest(name=name):
                    self.assertFalse(required-set(card));self.assertGreaterEqual(card['energy'],0);self.assertLessEqual(card['energy'],1)
                    self.assertLess(*card['duration_ms']);self.assertTrue(card['good_for']);self.assertTrue(card['avoid_for'])
                    self.assertFalse(set(card['good_for'])&set(card['avoid_for']));self.assertNotIn(card['good_for'],seen);seen.append(card['good_for'])
                    self.assertIsInstance(card['cost_ms_per_frame@720p'],float);self.assertEqual(card['gate']['axis'],'technical')
                    self.assertIn(card['intent'][0],INTENTS)

    def test_schema(self):
        from fx_schema import validate
        schema=json.loads((ROOT/'references/fx-card.schema.json').read_text())
        for entries in catalog().values():
            for card in entries.values():validate(card,schema)
        with self.assertRaises(ValueError):validate({'energy':2},schema)

    def test_intent_distribution(self):
        from collections import Counter
        cards=[c for entries in catalog().values() for c in entries.values()]
        counts=Counter(c['intent'][0] for c in cards)
        self.assertGreaterEqual(len(counts),4);self.assertLessEqual(max(counts.values())/len(cards),.4)
        self.assertGreaterEqual(np.std([c['energy'] for c in cards]),.15)

    def test_technical_gate_sources_not_appeal(self):
        for c in catalog()['transitions'].values():
            self.assertNotIn('score',c['gate'])
            self.assertTrue((ROOT/c['gate']['record_path']).is_file())

    def test_offline_html_escapes_plugins(self):
        c=dict(next(iter(catalog()['effects'].values())),name='<script>x</script>',kind='effect')
        with tempfile.TemporaryDirectory() as d:
            p=write_html([c],Path(d)/'index.html');text=p.read_text(encoding='utf-8')
            self.assertIn('&lt;script&gt;',text);self.assertIn('autoplay muted loop',text)
            self.assertNotIn('src="https://',text)

    def test_plugin_card_preserves_parameter_types(self):
        before=dict(EFFECTS)
        try:
            with tempfile.TemporaryDirectory() as d:
                Path(d,'dim.py').write_text("from fx.core import effect\n@effect(card={'intent':['breathe'],'energy':.2,'needs':[]})\ndef s6_dim(frame,t,ctx,amount=0.5):\n frame[...,:3]*=1-.5*amount\n return frame\n")
                load_directory(d);c=catalog()['effects']['s6_dim']
                self.assertEqual(c['intent'],['breathe']);self.assertEqual(c['params']['amount']['default'],.5)
        finally:EFFECTS.clear();EFFECTS.update(before)


class Calibration(unittest.TestCase):
    def test_registry(self):
        data=validate(registry())
        self.assertEqual(data['calibration_tables']['fx_perceived'],'references/fx-calibration.json')
        for e in data['thresholds']:
            if e['id'].startswith('wcag.'):self.assertEqual(e['class'],'F');self.assertEqual(e['status'],'active')

    def test_grid_and_monotonic(self):
        for name,e in load_table()['effects'].items():
            with self.subTest(name=name):
                self.assertEqual(len(e['rows']),11)
                self.assertLessEqual(e['rows'][0]['perceived'],.02)
                self.assertTrue(all(b['perceived']>=a['perceived']-.01 for a,b in zip(e['rows'],e['rows'][1:])))

    def test_unreachable_is_error(self):
        with self.assertRaisesRegex(ValueError,'unreachable'):inverse('halation',.7)
        with self.assertRaises(ValueError):inverse('flash_white',float('nan'))

    def test_table_changes_affect_measurement(self):
        table=load_table();before=interpolate('flash_white',.3,table)
        for row in table['effects']['flash_white']['rows']:row['perceived']*=2
        self.assertAlmostEqual(interpolate('flash_white',.3,table),before*2)

    def test_raw_measurement_reproducible(self):
        ref=standard(width=160,height=90);out=apply('zoom_punch',ref,.4)
        self.assertEqual(measures(ref,out),measures(ref,out))

    def test_transparent_garbage_ignored(self):
        a=standard('STD-A',160,90);b=a.copy();b[a[...,3]==0,:3]=0
        self.assertLess(measures(a,b)['dY'],1e-5)

    def test_identity_metrics(self):
        a=standard(width=160,height=90);m=measures(a,a)
        self.assertEqual(m['dY'],0);self.assertLess(abs(m['ssim_loss']),1e-5)


class Visibility(unittest.TestCase):
    def test_onset_relative_to_concurrent_motion(self):
        z=np.zeros((32,32),np.float32);effect=np.ones_like(z)*10
        slow=[z,z+1,z+2];fast=[z,z+20,z+40]
        self.assertGreater(onset_contrast([z],[effect],slow),onset_contrast([z],[effect],fast))

    def test_uncalibrated_never_claims_pass(self):
        m=dict(perceived=.2,ssim_loss=.8,sharp4=.01)
        r=classify(m,.01,consecutive=8)
        self.assertEqual(r['instrument_status']['visibility'],'unknown')
        self.assertEqual(r['instrument_status']['harshness'],'unknown')

    def test_active_anchor_decisions_and_transition_exception(self):
        data=copy.deepcopy(registry())
        for e in data['thresholds']:
            if e['id'] in ('visibility.onset_contrast.min','harshness.sharp4.min','harshness.ssim_loss.max'):e['status']='active'
        m=dict(perceived=.4,ssim_loss=.8,sharp4=.01)
        self.assertEqual(classify(m,.01,consecutive=5,data=data)['status'],'destructive')
        self.assertEqual(classify(m,5,transition=True,consecutive=5,data=data)['status'],'ok')
        self.assertEqual(classify(dict(m,ssim_loss=.01,sharp4=1),.01,data=data)['status'],'invisible')
        self.assertEqual(classify(dict(m,ssim_loss=.01,sharp4=1),.01,intent='texture',data=data)['status'],'ok')

    def flash(self,period,red=False,area=1):
        c=FlashCounter();base=np.full((30,40,3),64,np.uint8)
        for i in range(90):
            f=base.copy()
            if i%period==2:
                f[:,:round(40*area)]=[255,0,0] if red else [255,255,255]
            c.push(f,i/30)
        return c.report()

    def test_general_four_flash_blocks(self):
        self.assertEqual(self.flash(7)['status'],'harsh')

    def test_red_four_flash_blocks(self):
        self.assertEqual(self.flash(7,red=True)['status'],'harsh')

    def test_low_frequency_and_small_area_pass(self):
        self.assertEqual(self.flash(60)['status'],'ok');self.assertEqual(self.flash(30)['status'],'ok')
        self.assertEqual(self.flash(7,area=.05)['status'],'ok')

    def test_spatially_opposing_flashes_do_not_cancel(self):
        c=FlashCounter()
        for i in range(90):
            f=np.zeros((20,20,3),np.uint8)
            f[:,:10]=255 if (i//3)%2 else 0;f[:,10:]=255-f[:,:10]
            c.push(f,i/30)
        self.assertEqual(c.report()['status'],'harsh')

    def test_gradual_flash_accumulation(self):
        c=FlashCounter()
        for i in range(90):
            y=[30,100,160,220,160,100][i%6]
            c.push(np.full((20,20,3),y,np.uint8),i/30)
        self.assertEqual(c.report()['status'],'harsh')


class Recipes(unittest.TestCase):
    def test_count_stable_ingredients_and_schema(self):
        from fx_schema import validate
        recipes=load_recipes(experimental=True);self.assertEqual(len(recipes),14)
        schema=json.loads((ROOT/'references/fx-recipe.schema.json').read_text())
        for r in recipes.values():
            validate(r,schema)
            for l in r['layers']:self.assertEqual(EFFECTS[l['ref']]['status'],'stable')
        self.assertGreaterEqual(sum(len(r['layers'])>=2 and len({l['offset_ms'] for l in r['layers']})>1 for r in recipes.values()),7)

    def test_pending_review_is_not_silently_promoted(self):
        for r in load_recipes().values():self.assertEqual(r['gate']['status'],'stable')
        from unittest.mock import patch
        pending=copy.deepcopy(load_recipes(experimental=True)['impact'])
        pending.update(name='pending_impact',status='experimental');pending['gate']['status']='pending-review'
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,VIDEO_GIF_RECIPE_HOME=folder):
            Path(folder,'pending.json').write_text(json.dumps(pending))
            with self.assertRaisesRegex(ValueError,'experimental'):expand({'effects':[{'recipe':'pending_impact','at_ms':1000}]},[])

    def test_expand_and_render_shapes(self):
        recipes=load_recipes(experimental=True);frame=standard(width=128,height=72);ctx=Context(128,72)
        for name,r in recipes.items():
            with self.subTest(name=name):
                result=expand({'effects':[{'recipe':name,'at_beat':2}]},[0,500,1000],True)
                self.assertEqual(result['recipe_events'][0]['at_ms'],1000)
                out=apply_recipe(r,frame,100,ctx)
                self.assertEqual(out.shape,frame.shape);self.assertTrue(np.isfinite(out).all())

    def test_build_strictly_increases(self):
        r=load_recipes(experimental=True)['build'];a=standard(width=160,height=90);ctx=Context(160,90)
        peaks=[measures(a,apply_recipe(r,a,t,ctx))['perceived'] for t in (0,500,1000,1500)]
        self.assertTrue(all(b>a for a,b in zip(peaks,peaks[1:])),peaks)

    def test_breathe_within_budget(self):
        r=load_recipes(experimental=True)['breathe'];a=standard(width=160,height=90)
        p=measures(a,apply_recipe(r,a,800,Context(160,90)))['perceived']
        self.assertLessEqual(p,value('director.breathe.max'))

    def test_repeated_recipe_instances_have_distinct_audio_anchors(self):
        result=expand({'effects':[{'recipe':'impact','at_ms':0},{'recipe':'impact','at_ms':1000}]},[],True)
        a,b=result['recipe_events']
        self.assertNotEqual(a['event_id'],b['event_id'])
        self.assertEqual({e['recipe_event_id'] for e in result['effects']},{a['event_id'],b['event_id']})


class Director(unittest.TestCase):
    def plan(self,energy=.2,n=8):
        return {'fps':30,'sections':[{'name':'intro','start_ms':0,'end_ms':16000,'energy':energy}],
                'effects':[{'name':'flash_white','start_ms':i*500,'end_ms':i*500+100,'amount':.6} for i in range(n)]}

    def test_dense_quiet_section_errors(self):
        r=lint(self.plan());self.assertGreater(r['errors'],0)
        self.assertIn('every-beat-flash',[i['rule'] for i in r['issues']])

    def test_sparse_and_drop_pass(self):
        self.assertEqual(lint(self.plan(n=1))['errors'],0)
        self.assertEqual(lint(self.plan(energy=.95))['errors'],0)
        self.assertTrue(lint(self.plan(energy=.95,n=32))['issues'])

    def test_conflicts(self):
        for a,b in [('flash_white','flash_cut'),('flash_white','gl_overexposure'),('zoom_punch','beat_bounce')]:
            plan={'effects':[{'name':a,'start_ms':0,'amount':.5}]}
            if b in TRANSITIONS:plan['transitions']=[{'name':b,'at_ms':0}]
            else:plan['effects'].append({'name':b,'start_ms':0,'amount':.5})
            self.assertIn('conflict',[i['rule'] for i in lint(plan)['issues']])

    def test_usage_reads_calibration(self):
        p=self.plan(n=1);base=lint(p);table=load_table()
        for r in table['effects']['flash_white']['rows']:r['perceived']*=2
        self.assertAlmostEqual(lint(p,table=table)['sections'][0]['windows'][0]['used'],base['sections'][0]['windows'][0]['used']*2)

    def test_query_constraints_and_formula(self):
        for intent in ('hit','reveal','breathe','texture','title'):
            for section in ('intro','drop','breathe','outro'):
                for needs in ([],['subject','alpha']):
                    for c in query(intent,needs,30,section):
                        self.assertTrue(set(c['needs'])<=set(needs));self.assertLessEqual(c['cost_ms_per_frame@720p'],30)
                        self.assertNotIn(section,c['avoid_for'])
                        r=c['reason'];score=r['intent_match']*4+r['technical_gate_pass']-r['cost_ms']*.01-r['diversity_penalty']
                        self.assertAlmostEqual(c['score'],score)
                        if section=='breathe':self.assertLessEqual(c['energy'],.25)

    def test_query_diversity(self):
        h=[]
        for _ in range(12):h.append(query('hit',section='drop',history=h)[0]['name'])
        self.assertGreaterEqual(len(set(h)),4)
        for i in range(10):self.assertEqual(len(set(h[i:i+3])),3)

    def test_query_hash_seed_bytes(self):
        command=[sys.executable,'-B',str(ROOT/'scripts/fx_query.py'),'--intent','hit','--section','drop','--json']
        a=subprocess.check_output(command,env=dict(os.environ,PYTHONHASHSEED='0'))
        b=subprocess.check_output(command,env=dict(os.environ,PYTHONHASHSEED='123'))
        self.assertEqual(a,b)

    def test_plan_preflight_flash(self):
        p=self.plan(n=12)
        for i,e in enumerate(p['effects']):e['start_ms']=i*250;e['end_ms']=i*250+30
        self.assertTrue(any(i['rule'].startswith('WCAG') for i in lint(p)['issues']))


if __name__=='__main__':unittest.main()
