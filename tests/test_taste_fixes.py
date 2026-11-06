"""Independent-review regressions: intent stays the user's, instruments stay honest."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import taste_report as report
import taste_lint as advice
import taste_target as target
import taste_pick as pick
from taste_common import compare_curve, ROOT, read
from taste_director import treatment
from storyboard import lint, validate
from animatic import source_frame


def board():
    return dict(core='Ambient stillness', style='ambient', design_curve=[[0,.4],[6,.4]],
                shots=[dict(duration=2, why='Hold space for reflection') for _ in range(3)])


class ReviewRegressions(unittest.TestCase):
    def test_flat_match_never_fails_correlation(self):
        t=np.arange(0,6,.1)
        for end in (.4,.401):
            c=compare_curve(t,np.full(len(t),.4),[[0,.4],[6,end]])
            self.assertFalse(c['revise']);self.assertEqual(c['metric'],'rms_deviation')
            self.assertIsNone(c['peak_offset_bars'])

    def test_flat_excess_has_directional_shot_actions(self):
        b=board();b['design_curve']=[[0,.1],[6,.1]];b['shots'][1].update(perceived=1,motion='push',sound=dict(energy=1))
        c=compare_curve(np.arange(0,6,.1),np.ones(60),b['design_curve'])
        self.assertTrue(c['revise']);self.assertIn('Reduce',c['deviations'][0]['suggestion'])
        rows=[r for r in lint(b)['findings'] if r['rule']=='design_curve']
        self.assertTrue(rows);self.assertTrue(all(r['shot']>0 for r in rows))

    def test_ambient_relaxes_cv_and_dip(self):
        b=board();self.assertNotIn('shot_cv',[r['rule'] for r in lint(b)['findings']])
        r=dict(M1=dict(cv=0,lengths=[2,2,2]),M15=dict(times=[0,1,2],values=[.8,.8,1],peaks=[dict(time=2,value=1)]))
        self.assertFalse({'shot_cv','pre_peak_valley'} & {x['rule'] for x in advice.edit_lint(r,b)})

    def test_report_design_alone_relaxes_cv_and_dip(self):
        r=dict(M1=dict(cv=0,lengths=[2,2,2]),comparison=dict(metric='rms_deviation'),
               M4=dict(warning='Already bright before peak',jump=.1,before_interval=[0,1]),
               M15=dict(times=[0,1,2],values=[.8,.8,1],peaks=[dict(time=2,value=1)]))
        self.assertFalse({'shot_cv','pre_peak_valley'} & {x['rule'] for x in advice.edit_lint(r)})

    def test_director_brief_and_music_not_ramp(self):
        b=treatment(['missing.mp4'],6,'Flat ambient stillness',pick.factory())
        self.assertEqual(np.ptp(np.array(b['design_curve'])[:,1]),0)
        music=dict(sections=[dict(start=0,end=3,energy=.8),dict(start=3,end=6,energy=.2)])
        b=treatment(['missing.mp4'],6,'Follow the music',pick.factory(),music=music)
        self.assertGreater(b['design_curve'][0][1],b['design_curve'][-1][1])

    def test_ambient_director_does_not_add_tail_impacts(self):
        b=treatment(['missing.mp4'],12,'Flat ambient stillness',pick.factory())
        self.assertFalse(any(s.get('recipe') for s in b['shots']))
        self.assertNotIn('design_curve',[r['rule'] for r in lint(b)['findings']])

    def test_director_general_preferences(self):
        p=pick.factory();p['item_preferences']={'transition_crossfade_opaque_example':1}
        p['defaults']['transition_family']='energy'
        b=treatment(['missing.png'],6,'Arrival',p)
        self.assertEqual(b['shots'][1]['transition'],'crossfade')

    def test_missing_footage_is_card(self):
        s=dict(id='missing',size='MS',motion='static',duration=1,footage='does-not-exist.mp4')
        self.assertEqual(source_frame(s,ROOT,(160,90)).shape,(90,160,4))
        self.assertEqual(s['asset_fallback']['reason'],'missing footage')

    def test_nested_transition_and_caption_exemptions(self):
        tokens=advice.default_tokens()
        p=dict(shots=[dict(transition=dict(name='gl_cross_warp',rule_break=dict(rule='token_transition',reason='Intentional warp')),
                           captions=[dict(font='alien',rule_break=dict(rule='token_font',reason='Alien language'))])])
        rows=advice.token_lint(p,tokens)
        self.assertEqual(len(rows),2);self.assertTrue(all(r['status']=='annotated' for r in rows))

    def test_global_exemptions_visible_in_summary(self):
        b=board();b['rule_break']=dict(rule='*',reason='Deliberate static installation')
        r=lint(b)
        self.assertTrue(r['exemptions']);self.assertGreaterEqual(r['exemption_count'],1)
        self.assertTrue(all(x['status']=='annotated' for x in r['findings']))

    def test_jump_cut_kind(self):
        b=board();b['shots'][0]['rule_break']=dict(kind='jump_cut',reason='Deliberate discontinuity')
        validate(b)
        from storyboard_lint import main
        from taste_lint import finding
        self.assertEqual(finding('angle_30',1,0,30,'Change angle',b['shots'][0])['status'],'annotated')

    def test_black_not_weakest_without_design(self):
        r=dict(media=dict(duration=6),M15=dict(times=np.arange(0,6,.1).tolist(),values=([-3]*20+[0]*40),components={}),
               content=dict(times=np.arange(0,6,.1).tolist(),labels=['no content']*20+['content']*40))
        self.assertGreaterEqual(advice.weakest(r)['start'],2)

    def test_single_shot_cv_null(self):
        r=self.fake_analysis([np.full((90,160,3),100,np.uint8)]*3)
        self.assertIsNone(r['M1']['cv'])
        self.assertEqual(r['content']['labels'],['content'])

    def fake_analysis(self,frames):
        class Capture:
            def __init__(self):self.index=0
            def read(self):
                x=frames[self.index] if self.index<len(frames) else None;self.index+=1;return x is not None,x
            def set(self,key,value):
                self.index=round(value*30/1000) if key==report.cv2.CAP_PROP_POS_MSEC else round(value)
                return True
            def release(self):pass
        with patch.object(report,'probe',return_value=dict(fps=30,width=160,height=90,duration=len(frames)/30,audio=False)),patch.object(report.cv2,'VideoCapture',return_value=Capture()):
            return report.analyze('mock.mp4')

    def test_noise_motion_floor(self):
        rng=np.random.default_rng(17)
        frames=[np.clip(100+rng.normal(0,3,(90,160,3)),0,255).astype('uint8') for _ in range(40)]
        r=self.fake_analysis(frames)
        self.assertLess(max(r['M6']['pixels_per_frame']),.3)

    def test_salient_centroid_not_background_centroid(self):
        rng=np.random.default_rng(19)
        rgb=np.clip(80+rng.normal(0,3,(180,320,3)),0,255).astype('uint8')
        rgb[25:45,260:280]=240
        _,_,c=report.saliency(rgb)
        self.assertLess(np.linalg.norm(np.array(c)-[270/320,35/180]),.05)

    def test_white_flash_not_two_cuts(self):
        base=np.full((90,160,3),80,np.uint8)
        r=self.fake_analysis([base]*30+[np.full_like(base,255)]+[base]*30)
        self.assertEqual(r['M1']['cut_frames'],[])

    def test_dissolve_is_boundary(self):
        a=np.full((90,160,3),(30,40,200),np.uint8);b=np.full_like(a,(210,80,30))
        frames=[a]*30+[np.uint8(a*(1-u)+b*u) for u in np.linspace(0,1,31)]+[b]*30
        r=self.fake_analysis(frames)
        self.assertEqual(len(r['M1']['cut_frames']),1)
        self.assertAlmostEqual(r['M1']['cut_times'][0],1.5,delta=.2)

    def test_same_palette_cut_survives_motion_accent(self):
        rng=np.random.default_rng(33)
        a=rng.integers(20,200,(90,160,3),dtype=np.uint8)
        b=np.fliplr(a).copy()
        r=self.fake_analysis([a]*30+[b]*30)
        self.assertEqual(r['M1']['cut_frames'],[30])

    def test_same_palette_dissolve(self):
        a=np.full((90,160,3),30,np.uint8);a[20:70,10:60]=220
        b=np.fliplr(a).copy()
        frames=[a]*30+[np.uint8(a*(1-u)+b*u) for u in np.linspace(0,1,31)]+[b]*30
        r=self.fake_analysis(frames)
        self.assertEqual(len(r['M1']['cut_frames']),1)
        self.assertAlmostEqual(r['M1']['cut_times'][0],1.5,delta=.2)

    def test_transition_is_not_cut_on_action_failure(self):
        r=dict(media=dict(fps=30),M1=dict(cut_times=[1],events=[dict(time_ms=1000,type='flash_cut')]),M6=dict(pixels_per_frame=[10]*26+[0]*40))
        self.assertNotIn('cut_on_action',[x['rule'] for x in advice.edit_lint(r)])

    def test_loudness_windows_centered(self):
        loud=dict(times=[3,4,5,6],short_term=[-30,-20,-10,-30])
        self.assertEqual(float(report.centered_loudness(np.array([3.5]),loud)[0]),-10)

    def test_silent_and_short_loudness(self):
        from types import SimpleNamespace
        stderr=b'I: -70.0 LUFS\nLRA: 0.0 LU\nPeak: -inf dBFS'
        with patch.object(report,'run',side_effect=[SimpleNamespace(stderr=stderr),SimpleNamespace(stdout=np.zeros(48000,dtype='<f4').tobytes())]):
            loud,*_=report.audio_metrics('mock.wav',1)
        self.assertIsNone(loud['integrated_lufs']);self.assertIsNone(loud['lra']);self.assertTrue(loud['low_confidence'])

    def test_effective_weights_exported(self):
        r=self.fake_analysis([np.full((90,160,3),100,np.uint8)]*3)
        self.assertEqual(r['M15']['effective_weights'][2],0)
        # Every component of this static, silent, single-shot plate is constant.
        self.assertEqual(r['M15']['effective_weights'],[0.,0.,0.,0.])

    def test_report_actionable_without_design(self):
        r=self.fake_analysis([np.full((90,160,3),100,np.uint8)]*90)
        # A static plate has no clipping evidence; do not pad to three prompts.
        self.assertGreaterEqual(len(r['summary']['suggestions']),2)
        self.assertFalse(any('clipped_fraction' in s['evidence'] for s in r['summary']['suggestions']))
        self.assertTrue(all(s['shot']>0 and 'start' in s for s in r['summary']['suggestions']))

    def test_m4_predrop_lint(self):
        r=dict(M4=dict(warning='Already bright before peak',jump=.1,before_interval=[2,3]),M15={})
        rows=advice.edit_lint(r)
        self.assertTrue(any('already bright before the drop' in r['suggestion'].lower() for r in rows))

    def test_letterbox_crop(self):
        a=np.zeros((90,160,3),np.uint8);a[15:75]=[70,120,180]
        r=self.fake_analysis([a]*30)
        self.assertEqual(r['media']['active_picture'],[0,15,160,75])
        self.assertGreater(r['M13']['p1'][0],50)

    def test_letterbox_after_black_intro(self):
        a=np.zeros((90,160,3),np.uint8);a[15:75]=[70,120,180]
        r=self.fake_analysis([np.zeros_like(a)]*30+[a]*60)
        self.assertEqual(r['media']['active_picture'],[0,15,160,75])

    def test_target_weights_and_mismatch(self):
        r=self.fake_analysis([np.full((90,160,3),100,np.uint8)]*3)
        with patch.object(target,'analyze',return_value=r):cal=target.calibrate(['mock'])
        self.assertIn('weights',cal)
        self.assertTrue(target.compare_target(r,dict(cal,weights=[1,0,0,0]))['warnings'])

    def test_profile_weights_and_seed_default(self):
        self.assertEqual(pick.profile_path(),ROOT/'references/taste-user.json')
        p=pick.load();self.assertEqual(len(p['choices']),8)
        self.assertEqual(p['choices'][2]['options']['A']['transition_family'],advice.transition_family('gl_cross_warp'))
        self.assertEqual(p['choices'][7]['options']['A']['transition_family'],advice.transition_family('gl_swirl'))
        self.assertEqual(len(p['weights']),4)

    def test_last_recipe_windows_clamped(self):
        from animatic import bounded_effects
        p,adjustments=bounded_effects(dict(effects=[dict(recipe='impact',at_ms=29900)]),30000)
        self.assertTrue(adjustments)
        self.assertTrue(p['effects'])
        for e in p['effects']:
            self.assertLess(e['start_ms'],e['end_ms']);self.assertLessEqual(e['end_ms'],30000)
            for v in e.values():
                if isinstance(v,dict) and 'keyframes' in v:self.assertTrue(all(0<=t<=30000 for t,_ in v['keyframes']))

    def test_fast_director_missing_assets_plan_integration(self):
        from animatic import to_plan
        b=treatment(['nonexistent.mp4'],30,'Arrival',pick.factory(),dict(asl=.7,cv=.5))
        written={}
        with patch.object(Path,'mkdir'),patch.object(Image.Image,'save'),patch('animatic.write',side_effect=lambda path,data:written.update({Path(path).name:data})):
            p=to_plan(b,Path('not-written'),size=(80,48))
        self.assertEqual(len(written['asset-fallbacks.json']),len(b['shots']))
        self.assertTrue(written['effect-adjustments.json'])
        self.assertEqual(b['shots'][-1]['end'],30)
        for e in p['effects']:
            self.assertTrue(0<=e['start_ms']<e['end_ms']<=30000)
            for v in e.values():
                if isinstance(v,dict) and 'keyframes' in v:
                    self.assertTrue(all(0<=t<=30000 for t,_ in v['keyframes']))


if __name__=='__main__':unittest.main()
