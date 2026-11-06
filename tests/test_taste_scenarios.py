"""Visible acceptance scenarios, exercised together through real encoded media.

Run: python -B -m unittest discover -s tests -p test_taste_scenarios.py -v
Fixtures are deterministic and generated at test time under .scratch only.
Existing demo films are read-only integration inputs, not added binary fixtures.
"""
from pathlib import Path
import json
import sys
import tempfile
import time
import unittest

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from taste_common import compare_curve, read, zscore
from taste_report import analyze, front_page, save_report
from taste_lint import weakest, finding
from taste_director import treatment
from taste_pick import factory
from taste_target import statistics
from animatic import render
from taste_scenario_media import arc_film, ambient_film, noisy_bars, flash_film


class TasteScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.started = time.perf_counter()
        cls.evidence = {}
        cls.threads = cv2.getNumThreads(); cv2.setNumThreads(1)
        scratch = ROOT/'.scratch'; scratch.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='taste-scenarios-', dir=scratch)
        cls.directory = Path(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup(); cv2.setNumThreads(cls.threads)
        print('\nTaste scenario evidence: '+json.dumps(cls.evidence,sort_keys=True),flush=True)
        print(f'\nTaste scenario suite runtime: {time.perf_counter()-cls.started:.3f}s', flush=True)

    def path(self, name):
        return self.directory/(name+'.mp4')

    def test_flat_ambient_four_variants_and_dynamic_controls(self):
        for variant in ('solid', 'texture', 'noise', 'breathing'):
            with self.subTest(variant=variant):
                r = analyze(ambient_film(self.path(variant), variant), design=[[0,.4],[12,.4]])
                self.assertFalse(r['comparison']['revise'])
                self.assertEqual(r['comparison']['metric'], 'absolute_dynamics')
                if variant != 'breathing': self.assertEqual(r['M15']['peaks'], [])
                self.assertFalse(any('Restore the planned' in s['action'] for s in r['summary']['suggestions']))
        for name, points in (('rise', [[0,.05],[12,1]]), ('pulse', [[0,.1],[4,.1],[5,1],[8,1],[9,.1],[12,.1]])):
            with self.subTest(dynamic=name):
                r = analyze(arc_film(self.path(name), 12, points), design=[[0,.4],[12,.4]])
                self.assertTrue(r['comparison']['revise'])
                self.assertTrue(r['M15']['peaks'])

    def test_f_weak_undesigned_freeze_beats_designed_valley(self):
        design = [[0,.9],[17.9,.9],[18,.1],[19.9,.1],[20,.9],[30,.9]]
        r = analyze(arc_film(self.path('f-weak'), 30, design, [(9,11),(18,20)]), design=design)
        w = r['summary']['weakest']
        self.evidence['f-weak'] = dict(start=w['start'],end=w['end'])
        self.assertGreaterEqual(min(w['end'],11)-max(w['start'],9), 1.5)
        self.assertFalse(18 <= w['start'] < 20)

    def test_f_design_match_mismatch_shift(self):
        design = [[0,.1],[22,.9],[24,.9],[28,.3],[32,.3]]
        variants = [('match', design, False), ('mismatch', [[0,.9],[3,.9],[5,.1],[32,.1]], True),
                    ('shift', [[0,.1],[4,.1],*[ [t+4,v] for t,v in design[1:] ]], True)]
        for name, points, revise in variants:
            with self.subTest(variant=name):
                r = analyze(arc_film(self.path('design-'+name),32,points),design=design)
                c = r['comparison']
                self.evidence['f-design-'+name] = {k:c[k] for k in ('correlation','peak_offset_bars','revise')}
                self.assertEqual(c['revise'], revise, self.evidence['f-design-'+name])
                if name == 'match':
                    self.assertGreaterEqual(c['correlation'],.8)
                    self.assertLessEqual(c['peak_offset_bars'],1)
                    self.assertEqual(c['deviations'],[])
                    self.assertFalse(any('Restore' in s['action'] for s in r['summary']['suggestions']))
                    residual=np.maximum(np.array(c['design'])-c['measured'],0)
                    self.evidence['f-design-'+name]['max_deficit']=float(np.convolve(residual,np.ones(20)/20,'valid').max())
                elif name == 'mismatch': self.assertLess(c['correlation'],.6)
                else:
                    # The measured centre is four seconds late relative to the
                    # plateau centre, three seconds beyond its right edge.
                    self.assertAlmostEqual(c['peak_offset_bars'],1.5,delta=.25)
                independent = np.corrcoef(c['design'], r['M15']['values'])[0,1]
                self.assertAlmostEqual(c['correlation'], independent, places=10)

    def test_ramp_clean_and_freeze_volume_drop(self):
        design = [[0,.1],[30,.9]]
        for name, freezes in (('clean', []), ('defect', [(22,24)])):
            with self.subTest(variant=name):
                r = analyze(arc_film(self.path('ramp-'+name),30,design,freezes),design=design)
                c = r['comparison']; w = weakest(r)
                self.evidence['ramp-'+name] = dict(start=w['start'],end=w['end'],revise=c['revise'],correlation=c['correlation'])
                self.assertIsNotNone(c['alignment'])
                if name == 'defect':
                    self.assertAlmostEqual(w['start'],22,delta=.5)
                    self.assertAlmostEqual(w['end'],24,delta=.5)
                else:
                    self.assertFalse(c['revise'])
                    self.assertFalse(any('Restore the planned' in s['action'] for s in r['summary']['suggestions']))

    def test_identical_shape_units_plateau_and_planning_amplitude(self):
        t = np.arange(0,32,.1)
        for design in ([[0,.1],[32,.9]], [[0,.1],[20,.9],[26,.9],[32,.3]]):
            d = np.interp(t, *np.array(design).T)
            c = compare_curve(t, zscore(d), design, proxy=True)
            self.assertAlmostEqual(c['correlation'],1)
            self.assertFalse(c['revise']); self.assertEqual(c['deviations'],[])
            self.assertAlmostEqual(c['peak_offset_bars'],0)
            self.assertIsNone(weakest(dict(M15=dict(times=t,values=zscore(d),components={}),comparison=c))['start'])
        design = [[0,.1],[20,.9],[26,.9],[32,.3]]
        d = np.interp(t, *np.array(design).T)
        noisy = d+1e-4*np.sin(t*13)
        self.assertLess(compare_curve(t,zscore(noisy),design,proxy=True)['peak_offset_bars'],.1)
        c = compare_curve(t,np.where(t<6,.4,.8),[[0,.2],[5.9,.2],[6,.9],[32,.9]])
        self.assertGreaterEqual(c['deviations'][0]['start'],6)
        self.assertAlmostEqual(c['deviations'][0]['deficit'],.1)

    def test_reference_director_encoded_fast_slow(self):
        measured=[]
        for name, asl, cv in (('fast',30/43,.5), ('slow',3.,.3)):
            with self.subTest(variant=name):
                board=treatment(['nonexistent.png'],30,'Arrival',factory(),dict(asl=asl,cv=cv))
                out=self.directory/name
                receipt=render(board,out,size=(160,90))
                r=read(out/'taste.json'); stats=statistics(r); measured.append(stats['asl'])
                self.evidence['director-'+name] = dict(asl=stats['asl'],cv=stats['cv'])
                self.assertAlmostEqual(stats['asl'],asl,delta=.05)
                self.assertAlmostEqual(stats['cv'],cv,delta=.15)
                self.assertEqual(len(receipt['cut_times']),round(30/asl)-1)
                self.assertAlmostEqual(board['shots'][-1]['end'],30)
        self.assertLess(measured[0],measured[1])

    def test_black_intro_and_letterbox_with_noise(self):
        for width,height in ((80,60),(160,90),(90,160)):
            with self.subTest(size=(width,height)):
                r=analyze(noisy_bars(self.path(f'bars-{width}-{height}'),(width,height)))
                self.assertEqual(r['media']['active_picture'],[0,10,width,height-10])
                self.assertEqual(r['content']['labels'][:10],['no content']*10)
                self.assertTrue(all(c is None for c in r['M10']['centroids'][:10]))
                self.assertGreater(r['M5']['values'][15],30)
                self.assertGreaterEqual(r['summary']['weakest']['start'],1)
                self.assertFalse(any(p['time']<1 for p in r['M15']['peaks']))
                self.evidence[f'letterbox-{width}-{height}']=r['media']['active_picture']

    def test_encoded_plateaus_and_mesa(self):
        designs = dict(plateau24=[[0,.1],[24,.9],[30,.9]],
                       plateau18=[[0,.1],[18,.9],[30,.9]],
                       mesa=[[0,.1],[8,.9],[20,.9],[28,.1],[32,.1]])
        for name,design in designs.items():
            for seed,crf,jitter in ((71,18,0.),(71,18,.01),(113,26,.02)):
                label=f'{name}-{seed}-{crf}-{jitter}'
                with self.subTest(film=label):
                    r=analyze(arc_film(self.path(label),design[-1][0],design,
                                      seed=seed,crf=crf,jitter=jitter),design=design)
                    c=r['comparison']
                    residual=np.maximum(np.array(c['design'])-c['measured'],0)
                    maximum=float(np.convolve(residual,np.ones(20)/20,'valid').max())
                    self.evidence[label]=dict(correlation=c['correlation'],offset=c['peak_offset_bars'],
                                             max_deficit=maximum,revise=c['revise'])
                    self.assertFalse(c['revise'],self.evidence[label])
                    self.assertEqual(c['peak_offset_bars'],0)
                    self.assertEqual(c['deviations'],[])
                    self.assertIsNone(r['summary']['weakest']['start'])
                    self.assertFalse(any('Restore' in s['action'] for s in r['summary']['suggestions']))

    def test_encoded_plateau_freeze(self):
        design=[[0,.1],[18,.9],[30,.9]]
        r=analyze(arc_film(self.path('plateau-freeze'),30,design,[(23,25)],
                          seed=113,crf=26,jitter=.02),design=design)
        c=r['comparison'];w=r['summary']['weakest']
        self.evidence['plateau-freeze']=dict(start=w['start'],end=w['end'],
                                            deficit=max(d['deficit'] for d in c['deviations']))
        self.assertGreaterEqual(min(w['end'],25)-max(w['start'],23),1.5)
        self.assertTrue(any(d['kind']=='missing' and d['deficit']>c['residual_tolerance']
                            and min(d['end'],25)-max(d['start'],23)>=1.5 for d in c['deviations']))
        self.assertTrue(any(23<=s['start']<=24 for s in r['summary']['suggestions']))

    def test_amb13_like_subtle_texture_light_and_audio(self):
        # A generated 13-second ambient control; no external amb13 asset needed.
        r=analyze(ambient_film(self.path('amb13-like'),'amb13-like',13),design=[[0,.4],[13,.4]])
        self.assertFalse(r['comparison']['revise'])
        self.assertEqual(r['comparison']['deviations'],[])
        self.assertEqual(r['M15']['peaks'],[])
        self.assertFalse(any('Restore' in s['action'] for s in r['summary']['suggestions']))
        self.evidence['amb13-like']=dict(revise=False,peaks=len(r['M15']['peaks']))

    def test_t_same_and_single_peak_controls(self):
        r=analyze(ambient_film(self.path('t-same'),'solid'))
        self.assertEqual(r['M15']['peaks'],[])
        self.assertIsNone(r['M4']['peak_frame']); self.assertLess(r['M4']['jump'],.01)
        for peak in (4.,8.):
            points=[[0,.1],[peak-1,.1],[peak,.9],[peak+1,.1],[12,.1]]
            r=analyze(arc_film(self.path('single-'+str(peak)),12,points))
            self.assertEqual(len(r['M15']['peaks']),1)
            self.assertAlmostEqual(r['M15']['peaks'][0]['time'],peak,delta=1)

    def test_designed_assumed_flash_and_nondesigned_blowout(self):
        path=flash_film(self.path('flash'))
        for manifest in (None,dict(events=[dict(name='flash',start_ms=1000,end_ms=1100)])):
            r=analyze(path,manifest=manifest)
            self.assertTrue(r['M4']['flash_events'])
            self.assertFalse(any('clipped_fraction' in s['evidence'] for s in r['summary']['suggestions']))
            self.assertEqual(bool(r['summary']['assumed_designed_events']),manifest is None)
            save_report(r,self.directory/('assumed' if manifest is None else 'designed'))
        self.assertIn('assumed designed',(self.directory/'assumed.md').read_text(encoding='utf-8'))
        r=analyze(flash_film(self.path('blowout'),True),manifest=dict(events=[dict(name='flash',start_ms=2500,end_ms=2600)]))
        self.assertTrue(any(s['evidence'].get('clipped_fraction',0)>.9 for s in r['summary']['suggestions']))

    def test_jump_cut_annotations_and_calm_ambience(self):
        for transition in ('jump_cut',dict(name='jump_cut'),dict(type='jump_cut')):
            for rule in ('angle_30','eye_trace','cut_on_action'):
                self.assertEqual(finding(rule,2,0,30,'Review',dict(transition=transition))['status'],'annotated')
        self.assertEqual(finding('eye_trace',2,0,30,'Review',dict(transition='crossfade'))['status'],'advice')
        for core,build in (('build a calm meditation ambience',False),('calm opening then build',True)):
            b=treatment(['missing.png'],6,core,factory())
            self.assertEqual(b['design_curve'][-1][1]>b['design_curve'][0][1],build)
            if not build:self.assertFalse(any(s.get('recipe') for s in b['shots']))

    def test_both_demo_key_assertions(self):
        for name in ('demo','demo2'):
            r=analyze(ROOT/f'wow/fx/{name}/demo.mp4')
            self.assertIn('provisional',r['summary']['shot_numbering'])
            self.assertIsNotNone(r['summary']['weakest']['start'])
            if name=='demo':
                for manifest in (None,read(ROOT/'wow/fx/demo/manifest-a.json')):
                    if manifest:
                        r['M12'].update(transitions=manifest['transitions'],events=manifest.get('events',[]),manifest_supplied=True)
                        r['summary']=front_page(r)
                    self.assertFalse(any('clipped_fraction' in s['evidence'] and abs(s['start']-2.92)<.1 for s in r['summary']['suggestions']))
            else:
                for cut in (2.92,5.86,11.72):self.assertTrue(any(abs(t-cut)<.08 for t in r['M1']['cut_times']))
                self.assertAlmostEqual(r['summary']['weakest']['start'],14.5,delta=.5)
                self.assertTrue(any('music' in s['action'] and 14<=s['start']<=15 for s in r['summary']['suggestions']))


if __name__=='__main__':unittest.main()
