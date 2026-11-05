"""Second independent-review regressions; media jobs run serially."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fx import EFFECTS,Context
from fx_measure import FlashCounter,standard,moving,measures,classify
from fx_calibrate import apply,inverse,interpolate,load_table
from fx_recipes import expand,load_recipes


class FlashAreaPairs(unittest.TestCase):
    def test_no_effect_synthetic_pans(self):
        base=standard(width=640,height=360)
        for speed in (3,6,9):
            counter=FlashCounter()
            for i in range(90):counter.push_frame(moving(base,i*speed/2),i,30)
            self.assertEqual(counter.report()['status'],'ok',(speed,counter.report()))

    def test_moving_three_and_three_point_three(self):
        base=standard(width=320,height=180)
        for period,expected in ((10,3),(9,4)):
            counter=FlashCounter()
            for i in range(120):
                frame=moving(base,i)
                if i%period==2:frame[...,:3]=255
                counter.push_frame(frame,i,30)
            self.assertEqual(counter.report()['general_max'],expected)
            self.assertEqual(counter.report()['status'],'ok' if period==10 else 'harsh')

    def test_small_red_area_is_not_combined_across_time(self):
        counter=FlashCounter()
        for i in range(90):
            frame=np.full((40,100,3),127,np.uint8)
            frame[:,(i%10)*10:(i%10+1)*10]=[255,0,0]
            counter.push_frame(frame,i,30)
        self.assertEqual(counter.report()['red_max'],0)


class CalibrationModes(unittest.TestCase):
    def test_tiny_inputs_report_unsupported(self):
        for size in (1,16):
            frame=standard(width=size,height=size)
            for name in ('zoom_punch','beat_bounce','halation'):
                for amount in (0,.1,1):
                    m=measures(frame,apply(name,frame,amount))
                    self.assertIsNone(m['perceived'])
                    self.assertEqual(m['perceived_status'],'unsupported')
                    self.assertEqual(classify(m,1)['status'],'unsupported')
            with self.assertRaisesRegex(ValueError,'unsupported'):
                inverse('zoom_punch',.3,resolution=(size,size))

    def test_context_nearest_overrides_legacy_parameter_default(self):
        rng=np.random.default_rng(8);palette=np.array([[0,0,0,255],[255,100,40,255],[70,200,0,255]],np.uint8)
        frame=palette[rng.integers(0,3,(64,64))]
        for name in ('zoom_punch','beat_bounce'):
            result=EFFECTS[name]['function'](frame,1000,Context(64,64,sampling='nearest'),amount=.3)
            explicit=EFFECTS[name]['function'](frame,1000,Context(64,64,sampling='nearest'),amount=.3,sampling='nearest')
            np.testing.assert_array_equal(result,explicit)
            self.assertTrue(set(map(tuple,result.reshape(-1,4)))<=set(map(tuple,palette)))

    def test_sampling_tables_and_plan_inverse(self):
        table=load_table()
        for name in ('zoom_punch','beat_bounce'):
            values=[]
            for mode in ('linear','nearest'):
                entry=table['effects'][name] if mode=='linear' else table['sampling_modes'][mode]['effects'][name]
                self.assertEqual(entry['sampling'],mode)
                self.assertEqual(len(entry['rows']),11)
                measured=measures(standard(),apply(name,standard(),.1,ctx=Context(1280,720,sampling=mode)))['perceived']
                self.assertAlmostEqual(interpolate(name,.1,sampling=mode),measured,places=6)
                values.append(measured)
                target=entry['rows'][3]['perceived']
                plan=expand({'sampling':mode,'effects':[{'name':name,'perceived':target}]},[])
                self.assertAlmostEqual(plan['effects'][0]['amount'],inverse(name,target,sampling=mode))
            self.assertGreater(abs(values[0]-values[1]),.01)

    def test_missing_nearest_table_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'nearest'):
            inverse('zoom_punch',.3,{'effects':load_table()['effects']},sampling='nearest')

    def test_visibility_is_candidate_only(self):
        from threshold_registry import entry,check
        e=entry('visibility.onset_contrast.min')
        self.assertEqual(e['value']['tonal'],.19)
        self.assertEqual(e['class'],'C');self.assertEqual(e['status'],'calibrate_first')
        self.assertEqual(check(e['id'],.4,context='tonal')['decision'],'unknown')


class SparseRecipeDelivery(unittest.TestCase):
    def test_one_call_click_recipes_and_decoded_onset(self):
        from sfx import read_audio
        from fx_check import decoded
        from qa_media import analyse_audio
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ('hook_snap','freeze_card'):
                for at,loudnorm in ((500,'on'),(1000,'off')):
                    case=root/f'{name}-{at}';case.mkdir()
                    frame=standard('STD-A' if name=='freeze_card' else 'STD-P',160,90)
                    Image.fromarray(frame).save(case/'source.png')
                    plan={'segments':[{'type':'still','image':'source.png','duration_ms':3000}],'effects':[{'recipe':name,'at_ms':at}],'fps':30}
                    (case/'plan.json').write_text(json.dumps(plan))
                    result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/fx_render.py'),str(case/'plan.json'),
                        '--out',str(case/'out'),'--formats','mp4','--no-user-fx','--loudnorm',loudnorm],capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                    movie=case/'out/animation.mp4';audio=read_audio(movie)
                    onset=np.flatnonzero(np.max(np.abs(audio),axis=1)>.01)[0]*1000/48000
                    # Decoded visual onset against preceding untouched frames;
                    # no manifest timestamp is used as measurement evidence.
                    frames=list(decoded(movie));baseline=frames[0].astype(float)
                    differences=[np.mean(np.abs(f.astype(float)-baseline)) for f in frames]
                    visual=next(i for i,d in enumerate(differences) if d>max(differences[:int(at*30/1000)])+1)*1000/30
                    self.assertLessEqual(abs(onset-visual),1000/30)
                    self.assertEqual(visual,at)
                    checks=analyse_audio(movie,{'audio':True},[0,3])
                    self.assertFalse([c for c in checks if c['level']=='FAIL'],checks)

    def test_promotions_have_independent_and_regression_links(self):
        recipes=load_recipes();self.assertEqual(len(recipes),14)
        required={'impact','reveal_subject','build','breathe','drop','title_pop','freeze_card'}
        self.assertTrue(required<=recipes.keys())
        for r in recipes.values():
            self.assertEqual(r['gate']['status'],'stable')
            self.assertTrue((ROOT/r['gate']['record_path']).is_file())


class MemoryIdentity(unittest.TestCase):
    def test_recycled_pid_does_not_adopt_old_orphans(self):
        from process_memory import descendants
        parents={2:1,3:2,4:1,5:4,6:1}
        created={1:100,2:110,3:120,4:50,5:60,6:105}
        self.assertEqual(descendants(1,parents,created),{1,2,3,6})

    def test_exited_unreadable_parent_excludes_descendants(self):
        from process_memory import descendants
        self.assertEqual(descendants(1,{2:1,3:2},{1:100,3:120}),{1})


if __name__=='__main__':unittest.main()
