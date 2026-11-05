"""Independent-review regressions: boundaries, isolation, evidence and portability."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import cv2

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fx import EFFECTS,TRANSITIONS,Context
from fx.core import load_directory,catalog
from fx_catalog import coverage,output_root,write_html
from fx_measure import FlashCounter,measures,classify,visibility_residual,onset_contrast,standard
from fx_recipes import load_recipes,apply_recipe
from fx_director import lint,query


class FlashBoundaries(unittest.TestCase):
    def scan(self,period,red=False,legacy=False):
        counter=FlashCounter()
        for index in range(301):
            frame=np.full((12,16,3),64,np.uint8)
            if index%period==2:frame[:]=[255,0,0] if red else [255]*3
            if legacy:counter.push(frame,index/30)
            else:counter.push_frame(frame,index,30)
        return counter.report()

    def test_three_per_second_half_open_passes(self):
        for legacy in (False,True):
            report=self.scan(10,legacy=legacy)
            self.assertEqual(report['max_flashes_per_s'],3);self.assertEqual(report['status'],'ok')

    def test_three_point_three_per_second_fails(self):
        self.assertEqual(self.scan(9)['max_flashes_per_s'],4)
        self.assertEqual(self.scan(9)['status'],'harsh')

    def test_red_boundary(self):
        self.assertEqual(self.scan(10,red=True)['red_max'],3)
        self.assertEqual(self.scan(10,red=True)['status'],'ok')
        self.assertEqual(self.scan(9,red=True)['status'],'harsh')

    def test_red_rule_independent_of_general_luma(self):
        c=FlashCounter()
        # Equal linear luminance, but saturated red versus grey.
        grey=round((1.055*(.2126**(1/2.4))-.055)*255)
        for i in range(90):
            f=np.full((12,16,3),grey,np.uint8)
            if i%9==2:f[:]=[255,0,0]
            c.push_frame(f,i,30)
        self.assertEqual(c.report()['general_max'],0)
        self.assertEqual(c.report()['red_max'],4)

    def test_integer_tick_pts(self):
        from fractions import Fraction
        c=FlashCounter()
        for i in range(301):
            f=np.full((12,16,3),255 if i%10==2 else 64,np.uint8)
            c.push(f,Fraction(i*512,15360))
        self.assertEqual(c.report()['max_flashes_per_s'],3)

    def test_spatially_staggered_single_flash_is_not_four_flashes(self):
        counter=FlashCounter()
        # Each quarter completes one pulse at a different frame: one flash per
        # pixel, not four flashes on the screen area. Models a gradient fade.
        for i in range(30):
            frame=np.full((20,40,3),64,np.uint8)
            for region in range(4):
                if 2+region<=i<8+region:frame[:,region*10:(region+1)*10]=255
            counter.push_frame(frame,i,30)
        self.assertEqual(counter.report()['max_flashes_per_s'],1)
        self.assertEqual(counter.report()['status'],'ok')

    def test_four_repetitions_of_staggered_flash_still_fail(self):
        counter=FlashCounter()
        for i in range(90):
            frame=np.full((20,40,3),64,np.uint8)
            for region in range(4):
                if (i-region)%7 in (2,3):frame[:,region*10:(region+1)*10]=255
            counter.push_frame(frame,i,30)
        self.assertEqual(counter.report()['status'],'harsh')

    def test_decoded_delivery_uses_integer_pts(self):
        from fx_check import check_video
        from qa_media import qa,media_info
        with tempfile.TemporaryDirectory() as d:
            for period,expected in ((10,'ok'),(9,'harsh')):
                path=Path(d,f'p{period}.avi')
                writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),30,(64,48))
                self.assertTrue(writer.isOpened())
                for i in range(150):writer.write(np.full((48,64,3),240 if 2<=i%period<6 else 64,np.uint8))
                writer.release()
                self.assertEqual(check_video(path,fps=30)['wcag']['status'],expected)
                info=media_info(path,30);self.assertIn('frame_ticks',info);self.assertIn('time_base',info)
                report=qa(path,Path(d,f'qa{period}'),fps=30)
                wcag=next(c for c in report['checks'] if c['name']=='WCAG 2.3.1')
                self.assertEqual(wcag['level'],'PASS' if expected=='ok' else 'FAIL')


class Isolation(unittest.TestCase):
    def setUp(self):self.effects=dict(EFFECTS);self.transitions=dict(TRANSITIONS)
    def tearDown(self):
        EFFECTS.clear();EFFECTS.update(self.effects);TRANSITIONS.clear();TRANSITIONS.update(self.transitions)

    def test_recipe_errors_are_per_file_and_actionable(self):
        source=copy.deepcopy(load_recipes(experimental=True)['build'])
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stderr(io.StringIO()) as err:
            a=dict(source,name='bad-ref');a['layers']=copy.deepcopy(source['layers']);a['layers'][0]['ref']='halaton'
            Path(d,'bad.json').write_text(json.dumps(a));Path(d,'broken.json').write_text('{')
            Path(d,'good.json').write_text(json.dumps(dict(source,name='good_recipe')))
            loaded=load_recipes(d,experimental=True)
            self.assertIn('good_recipe',loaded);self.assertIn('build',loaded);self.assertNotIn('bad-ref',loaded)
            for text in ('bad.json','bad-ref','halaton','experimental','did-you-mean','halation','valid intents','broken.json'):self.assertIn(text,err.getvalue())

    def test_experimental_ingredient_excluded(self):
        r=copy.deepcopy(load_recipes(experimental=True)['build']);r['layers'][0]['ref']='shake'
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stderr(io.StringIO()) as err:
            r['name']='bad_shake';Path(d,'shake.json').write_text(json.dumps(r))
            self.assertNotIn('bad_shake',load_recipes(d,True));self.assertIn('experimental',err.getvalue());self.assertIn('shake',err.getvalue())

    def test_invalid_plugin_card_rolls_back_whole_file(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stderr(io.StringIO()) as err:
            Path(d,'a_bad.py').write_text("from fx.core import effect\n@effect()\ndef before_bad(a,t,c):return a\n@effect(status='experimental',card={'intent':['hitt']})\ndef bad_card(a,t,c):return a\n")
            Path(d,'z_good.py').write_text("from fx.core import effect\n@effect()\ndef valid_after(a,t,c):return a\n")
            load_directory(d)
            self.assertNotIn('before_bad',EFFECTS);self.assertNotIn('bad_card',EFFECTS);self.assertIn('valid_after',EFFECTS)
            for text in ('a_bad.py','bad_card','hitt','experimental','did-you-mean:','hit','valid intents'):self.assertIn(text,err.getvalue())
            self.assertTrue(catalog());self.assertTrue(query('hit'))

    def test_missing_card_coverage_query(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'plugin.py').write_text("from fx.core import effect\n@effect()\ndef cardless(a,t,c):return a\n")
            load_directory(d);cat=catalog();report=coverage(cat)
            self.assertEqual(cat['effects']['cardless']['card'],'missing')
            self.assertIn('effect:cardless',[c['id'] for c in report['missing']])
            self.assertEqual(report['complete_stable'],coverage({k:{n:c for n,c in v.items() if n!='cardless'} for k,v in cat.items()})['complete_stable'])
            self.assertNotIn('cardless',[c['name'] for c in query('texture')])

    def test_list_json_survives_bad_plugin(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'bad.py').write_text("from fx.core import effect\n@effect(card={'intent':['wrong']})\ndef broken(a,t,c):return a\n")
            p=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/fx_render.py'),'--list','--json','--no-user-fx','--fx-dir',d],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertIn('effects',json.loads(p.stdout));self.assertIn('bad.py',p.stderr)

    def test_unserializable_plugin_default_is_isolated(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stderr(io.StringIO()) as err:
            Path(d,'bad_default.py').write_text("from fx.core import effect\n@effect()\ndef bad_default(a,t,c,amount=object()):return a\n")
            load_directory(d);self.assertNotIn('bad_default',EFFECTS)
            self.assertIn('bad_default.py',err.getvalue());json.dumps(catalog())

    def test_recipe_missing_card_fields_cannot_break_query(self):
        r=copy.deepcopy(load_recipes(experimental=True)['build']);r['name']='missing_use';r.pop('good_for')
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,VIDEO_GIF_RECIPE_HOME=d),contextlib.redirect_stderr(io.StringIO()) as err:
            Path(d,'bad_metadata.json').write_text(json.dumps(r))
            self.assertNotIn('missing_use',load_recipes(experimental=True))
            query('build',experimental=True)
            self.assertIn('good_for',err.getvalue())


class DirectorFixes(unittest.TestCase):
    def test_lint_flash_window_uses_quantized_half_open_frames(self):
        for period,unsafe in ((10,False),(9,True)):
            plan={'fps':30,'effects':[dict(name='flash_white',start_ms=i*period*1000/30,amount=.5) for i in range(16)]}
            self.assertEqual(any(i['rule'].startswith('WCAG') for i in lint(plan)['issues']),unsafe)
        duplicate={'effects':[dict(name='flash_white',start_ms=0,amount=.5)]*4}
        self.assertFalse(any(i['rule'].startswith('WCAG') for i in lint(duplicate)['issues']))

    def test_lint_cli_resolves_real_media_segments(self):
        from PIL import Image
        from fx_lint import main
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);Image.new('RGBA',(64,48),'gray').save(root/'still.png')
            plan=dict(segments=[dict(type='still',image='still.png',duration_ms=1000),
                                dict(type='still',image='still.png',duration_ms=1000,transition=dict(name='flash_cut',duration_ms=200))],
                      effects=[dict(name='flash_white',start_ms=1000,end_ms=1200,amount=.5)])
            path=root/'plan.json';path.write_text(json.dumps(plan))
            with contextlib.redirect_stdout(io.StringIO()) as out:self.assertEqual(main([str(path)]),1)
            self.assertTrue(any(i['rule']=='conflict' for i in json.loads(out.getvalue())['issues']))

    def test_conflict_rounding_matches_renderer_half_up(self):
        plan={'fps':25,'effects':[{'name':'flash_white','start_ms':20,'amount':.5}],
              'transitions':[{'name':'flash_cut','at_ms':40}]}
        self.assertTrue(any(i['rule']=='conflict' for i in lint(plan)['issues']))

    def test_real_segment_transition_conflict(self):
        plan={'segments':[{'duration_ms':1000},{'duration_ms':1000,'transition':{'name':'flash_cut','duration_ms':200}}],
              'effects':[{'name':'flash_white','start_ms':1000,'amount':.5}]}
        self.assertTrue(any(i['rule']=='conflict' for i in lint(plan)['issues']))

    def test_beat_segment_transition_conflict(self):
        plan={'beats_ms':[0,500,1000],'segments':[{'end_beat':2},{'duration_ms':1000,'transition':{'name':'flash_cut'}}],
              'effects':[{'name':'flash_white','start_ms':1000,'amount':.5}]}
        self.assertTrue(any(i['rule']=='conflict' for i in lint(plan)['issues']))

    def test_empty_reversed_sections_warn_assign_neighbour(self):
        p={'sections':[{'start_ms':0,'end_ms':1000},{'start_ms':1000,'end_ms':1000},
                       {'start_ms':1500,'end_ms':1200},{'start_ms':1600,'end_ms':3000}],
           'effects':[{'name':'flash_white','start_ms':1500,'amount':.3}]}
        r=lint(p)
        self.assertEqual([i['section_index'] for i in r['issues'] if i['rule']=='invalid-section'],[1,2])
        self.assertEqual(r['sections'][1]['events'][0]['at_ms'],1500)

    def test_empty_query_explains_every_constraint(self):
        d={};self.assertEqual(query('hit',max_cost=0,diagnostics=d),[])
        self.assertEqual(sum(d['removed'].values()),d['candidates'])
        self.assertGreater(d['removed']['max_cost'],0)

    def test_invalid_intent_has_suggestion(self):
        with self.assertRaisesRegex(ValueError,'did-you-mean: hit'):query('hitt')


class VisibilityFixes(unittest.TestCase):
    def test_equal_luma_chroma_is_measured(self):
        a=np.full((32,32,3),.4,np.float32);b=a.copy();b[...,0]+=.1;b[...,1]-=.1*.2126/.7152
        m=measures(a,b,flow=False)
        self.assertLess(m['dY'],.001);self.assertGreater(m['chroma_delta'],5)
        residual,scene=visibility_residual(a,b)
        self.assertGreater(onset_contrast([np.zeros_like(residual)],[residual],[scene,scene]),0)

    def test_motion_normalized_for_texture_contrast(self):
        # Identical geometry/displacement at a 6x scene-contrast difference.
        y,x=np.mgrid[:80,:128];luma=.5+.25*np.sin(x/5)*np.sin(y/7)
        scores=[]
        for contrast in (1.,.16):
            f=np.repeat((.5+(luma-.5)*contrast)[...,None],3,axis=2).astype(np.float32)
            residual,scene=visibility_residual(f,np.roll(f,4,axis=1),'motion')
            scores.append(onset_contrast([np.zeros_like(residual)],[residual],[scene,scene]))
        self.assertLess(max(scores)/min(scores),2)

    def test_unknown_status_and_family_cutoffs(self):
        from threshold_registry import entry,value
        e=entry('visibility.onset_contrast.min');self.assertEqual(e['class'],'C');self.assertEqual(e['status'],'calibrate_first')
        self.assertNotEqual(value(e['id'],'motion'),value(e['id'],'tonal'))
        self.assertEqual(classify({'perceived':.3,'sharp4':1,'ssim_loss':0},3)['status'],'unknown')

    def test_2afc_labels_are_separate_from_fixture_expectations(self):
        from fx_anchor_harness import attach_labels
        rows=[{'id':'a','expected':'visible'},{'id':'b','expected':'invisible'}]
        result=attach_labels(rows,[{'id':'a','observer':'independent-1','choice':'reference'}])
        self.assertEqual(result[0]['panel'][0]['choice'],'reference');self.assertEqual(result[1]['label_status'],'pending')
        with self.assertRaises(ValueError):attach_labels(rows,[{'id':'x','observer':'p','choice':'effect'}])


class PortableCards(unittest.TestCase):
    def test_paths_relative_default_not_temp_or_repo(self):
        with patch.dict(os.environ):
            os.environ.pop('VIDEO_GIF_FX_PREVIEWS',None);root=output_root()
        self.assertNotIn(ROOT,root.parents);self.assertNotIn('Temp',root.parts)
        for entries in catalog().values():
            for c in entries.values():
                if 'preview' in c:self.assertFalse(Path(c['preview']['video']).is_absolute())

    def test_moved_catalog_keeps_media_links(self):
        c=dict(catalog()['effects']['grade'],name='grade',kind='effect')
        with tempfile.TemporaryDirectory() as d:
            first=Path(d,'first');first.mkdir();Path(first,c['preview']['video']).write_bytes(b'fixture')
            write_html([c],first/'catalog.html');moved=Path(d,'moved');shutil.move(str(first),moved)
            self.assertIn('src="effect-grade.mp4"',(moved/'catalog.html').read_text(encoding='utf-8'))
            self.assertTrue((moved/c['preview']['video']).is_file())

    def test_cutout_not_perceived_addressable(self):
        from fx_calibrate import inverse
        from fx_recipes import expand
        c=catalog()['effects']['cutout_card'];self.assertFalse(c['calibration']['perceived_addressable'])
        with self.assertRaisesRegex(ValueError,'not addressable'):inverse('cutout_card',.01)
        with self.assertRaisesRegex(ValueError,'not addressable'):expand({'effects':[{'name':'cutout_card','perceived':.01}]},[])

    def test_fixed_transition_record_links(self):
        for n in ('hex_shutter','gl_bounce','gl_multiply_blend','gl_color_phase','gl_dreamy_zoom','gl_glitch_memories'):
            self.assertEqual(catalog()['transitions'][n]['gate']['record_path'],'wow/fx/gate/p2-tech-recheck.md')

    def test_nine_legacy_records_have_four_auto_cases(self):
        record=json.loads((ROOT/'wow/fx/gate/s6-legacy-auto.json').read_text())
        details=json.loads((ROOT/'wow/fx/gate/s6-legacy-auto-details.json').read_text())
        self.assertEqual(len(record['items']),9)
        for item in details['items']:
            r=record['items'][item['id']];self.assertEqual(r['independent_review'],'pending')
            self.assertEqual(len(item['cases']),4)
            failed=any(c.get(k,{}).get('level')=='FAIL' for c in item['cases'] for k in ('alpha','black','flicker','determinism','endpoints','wcag'))
            self.assertEqual(r['status'],'needs-review' if failed else 'stable')

    def test_failed_auto_record_excluded_from_query(self):
        path=ROOT/'wow/fx/gate/s6-legacy-auto.json';read=Path.read_text
        record=json.loads(read(path));record['items']['effect:zoom_punch']['status']='needs-review'
        def altered(p,*a,**kw):return json.dumps(record) if p==path else read(p,*a,**kw)
        with patch.object(Path,'read_text',altered):
            self.assertEqual(catalog()['effects']['zoom_punch']['status'],'needs-review')
            self.assertNotIn('zoom_punch',[c['name'] for c in query('hit')])


class RecipeEvidence(unittest.TestCase):
    def test_default_labels_match_decoded_measurements(self):
        report=json.loads((ROOT/'wow/fx/s6-fix-previews.json').read_text())
        measurements={r['name']:r for r in report['reports'] if r['kind']=='recipe'}
        self.assertEqual(len(measurements),14)
        for name,r in load_recipes(experimental=True).items():
            self.assertEqual(r['perceived_target'],measurements[name]['events'][0]['visibility']['perceived_measured'])
            self.assertEqual(r['status'],'stable')
            self.assertEqual(r['gate']['status'],'stable')
            self.assertTrue((ROOT/r['gate']['record_path']).is_file())

    def test_quiet_recipes_are_explicit_textures(self):
        recipes=load_recipes(experimental=True)
        for name in ('breathe','outro_settle','freeze_card'):
            self.assertEqual(recipes[name]['intent'],'texture');self.assertIn('Texture exemption',recipes[name]['notes'])

    def test_glitch_preview_decoded_flash_limit(self):
        from fx_previews import render_preview
        with tempfile.TemporaryDirectory() as d:
            r=render_preview('gl_glitch_memories','transition',d,width=160,height=90)
            self.assertEqual(r['default_override'],{'context_seed':'6 - floor(24 * progress)'})
            self.assertNotIn('updates',TRANSITIONS['gl_glitch_memories']['params'])
            self.assertLessEqual(r['wcag']['max_flashes_per_s'],3)
            self.assertFalse(Path(r['preview']['video']).is_absolute())

    def test_build_default_remeasures_at_label(self):
        from fx_previews import render_preview
        recipe=load_recipes(experimental=True)['build']
        with tempfile.TemporaryDirectory() as d:
            result=render_preview('build','recipe',d,recipe=recipe,seconds=3,at_ms=500)
            self.assertAlmostEqual(result['events'][0]['visibility']['perceived_measured'],recipe['perceived_target'],places=6)

    def test_gate_triplets_retain_evidence_after_reviewed_promotion(self):
        records=json.loads((ROOT/'wow/fx/gate/s6-recipes.json').read_text())
        self.assertEqual(len(records),14)
        for record in records:
            self.assertEqual(record['status'],'stable')
            self.assertTrue((ROOT/record['promotion_record']).is_file())
            self.assertEqual(record['gate_ready']['pairs'],36)
            self.assertEqual(record['gate_ready']['axis'],'technical')
            self.assertTrue(record['gate_ready']['controls_detectable'])


if __name__=='__main__':unittest.main()
