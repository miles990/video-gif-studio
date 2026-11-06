"""Round-three failures: noisy plates, signed gaps and short editorial blends."""
import sys
import unittest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import taste_report as report
from taste_common import compare_curve
from taste_lint import weakest, finding, edit_lint
from taste_director import treatment
from taste_pick import factory
from storyboard import lint


def analyze_frames(frames, **kwargs):
    class Capture:
        index = 0
        def read(self):
            x = frames[self.index] if self.index < len(frames) else None
            self.index += 1
            return x is not None, x
        def set(self, key, value):
            self.index = round(value * 30 / 1000) if key == report.cv2.CAP_PROP_POS_MSEC else round(value)
            return True
        def release(self): pass
    h, w = frames[0].shape[:2]
    with patch.object(report, 'probe', return_value=dict(fps=30, width=w, height=h, duration=len(frames)/30, audio=False)), patch.object(report.cv2, 'VideoCapture', return_value=Capture()):
        return report.analyze('synthetic.mp4', **kwargs)


class RoundThree(unittest.TestCase):
    def test_flat_noisy_ambient_absolute_scale(self):
        rng = np.random.default_rng(31)
        frames = [np.clip(90+rng.normal(0,3,(48,80,3)),0,255).astype('uint8') for _ in range(180)]
        r = analyze_frames(frames, design=[[0,.4],[6,.4]])
        self.assertFalse(r['comparison']['revise'])
        self.assertEqual(r['comparison']['metric'], 'absolute_dynamics')
        self.assertFalse(any('restore' in s['action'].lower() for s in r['summary']['suggestions']))

    def test_flat_proxy_without_absolute_evidence_cannot_revise(self):
        t=np.arange(0,6,.1)
        self.assertFalse(compare_curve(t,np.sin(t),[[0,.4],[6,.4]],proxy=True)['revise'])

    def test_flat_absolute_units_ignore_zscore_amplitude(self):
        t=np.arange(0,6,.1)
        low=dict(lra=2,short_term_range_lu=1,luminance_range_y=1,motion_range_px=.1)
        for amplitude in (.01,1,10):
            self.assertFalse(compare_curve(t,amplitude*np.sin(t),[[0,.4],[6,.4]],proxy=True,absolute=low)['revise'])
            self.assertTrue(compare_curve(t,amplitude*np.sin(t),[[0,.4],[6,.4]],proxy=True,absolute=dict(low,lra=8))['revise'])

    def test_auto_curve_does_not_demand_revision(self):
        b=dict(shots=[dict(duration=3) for _ in range(4)])
        self.assertFalse(lint(b)['comparison']['revise'])
        self.assertFalse(any(r['rule']=='design_curve' for r in lint(b)['findings']))

    def test_calm_keyword_director(self):
        for word in ('ASMR','meditation','calm','ambient','安靜','放鬆','冥想','療癒'):
            with self.subTest(word=word):
                b=treatment(['missing.png'],6,word,factory())
                self.assertFalse(any(s.get('recipe') for s in b['shots']))

    def test_weak_signed_residual(self):
        t=np.arange(0,30,.1);d=np.ones(len(t));d[(t>=18)&(t<20)]=0
        y=d.copy();y[(t>=9)&(t<11)]=.3;y[(t>=18)&(t<20)]=3
        r=dict(media=dict(duration=30),M15=dict(times=t.tolist(),values=y.tolist(),components={}),comparison=compare_curve(t,y,[[0,1],[17.9,1],[18,0],[19.9,0],[20,1],[30,1]]))
        self.assertEqual([weakest(r)['start'],weakest(r)['end']],[9,11])

    def test_deviation_names_climax_shot(self):
        frames=[np.full((48,80,3),90,np.uint8)]*240
        b=dict(shots=[dict(duration=2) for _ in range(4)])
        r=analyze_frames(frames,design=[[0,.1],[5.9,.1],[6,1],[8,1]],storyboard=b)
        self.assertTrue(any(s['shot']==4 for s in r['summary']['suggestions'] if 'deviation' in s['evidence']))

    def test_short_crossfades_three_second_asl(self):
        rng=np.random.default_rng(42)
        a=rng.integers(25,220,(48,80,3),dtype=np.uint8)
        plates=[np.roll(a,i*20,axis=1) for i in range(4)]
        frames=[]
        for i,p in enumerate(plates):
            if i: frames.extend([np.uint8(plates[i-1]*(1-u)+p*u) for u in np.linspace(0,1,7)[1:]])
            frames.extend([p]*(90-(6 if i else 0)))
        r=analyze_frames(frames)
        self.assertAlmostEqual(r['M1']['asl'],3,delta=.15)

    def test_director_fast_encoded_roundtrip(self):
        from animatic import render
        from taste_common import read
        b=treatment(['nonexistent.mp4'],30,'Arrival',factory(),dict(asl=.7,cv=.5))
        with tempfile.TemporaryDirectory() as td:
            receipt=render(b,Path(td)/'fast',size=(160,90))
            r=read(Path(td)/'fast/taste.json')
            self.assertEqual(len(receipt['cut_times']),42)
            self.assertAlmostEqual(r['M1']['asl'],.70,delta=.05)

    def test_noise_and_exposure_are_not_edits(self):
        rng=np.random.default_rng(18)
        a=rng.integers(40,150,(48,80,3),dtype=np.uint8)
        frames=[a]*30+[np.uint8(a.astype(float)*v) for v in np.linspace(1,1.5,7)]+[np.uint8(a*1.5)]*30
        self.assertEqual(analyze_frames(frames)['M1']['cut_times'],[])

    def test_short_pan_is_not_crossfade(self):
        rng=np.random.default_rng(20)
        a=rng.integers(20,200,(48,80,3),dtype=np.uint8)
        frames=[a]*30+[np.roll(a,k,axis=1) for k in range(1,8)]+[np.roll(a,7,axis=1)]*30
        self.assertEqual(analyze_frames(frames)['M1']['cut_times'],[])

    def test_wipes_or_front_page_provisional(self):
        a=np.full((48,80,3),(30,70,160),np.uint8);b=np.full_like(a,(180,40,20))
        frames=[a]*30
        for x in range(0,81,8):
            f=a.copy();f[:,:x]=b[:,:x];frames.append(f)
        frames += [b]*30
        r=analyze_frames(frames)
        self.assertTrue(r['M1']['cut_times'] or 'provisional' in r['summary']['shot_numbering'])

    def test_automatic_shot_numbers_explicitly_provisional(self):
        r=analyze_frames([np.full((48,80,3),90,np.uint8)]*30)
        self.assertIn('provisional',r['summary']['shot_numbering'])
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'report'
            report.save_report(r,out)
            markdown=out.with_suffix('.md').read_text(encoding='utf-8')
        self.assertIn('Shot numbering: provisional',markdown)
        self.assertIn('Weight source: default',markdown)
        self.assertIn('0.5-second',markdown)

    def test_noisy_black_is_no_content(self):
        rng=np.random.default_rng(4)
        # Decoded RGB near black corresponds to limited-range Y=16, sigma=3.
        frames=[np.clip(rng.normal(0,3,(48,80,3)),0,255).astype('uint8') for _ in range(30)]
        r=analyze_frames(frames)
        self.assertEqual(set(r['content']['labels']),{'no content'})
        self.assertFalse(any(x is not None for x in r['M10']['centroids']))

    def test_noisy_letterbox_and_colorfulness(self):
        rng=np.random.default_rng(6);a=np.zeros((60,80,3),np.uint8);a[10:50]=[40,100,200]
        frames=[np.clip(a.astype(float)+rng.normal(0,3,a.shape),0,255).astype('uint8') for _ in range(30)]
        r=analyze_frames(frames)
        self.assertEqual(r['media']['active_picture'],[0,10,80,50])
        self.assertAlmostEqual(r['M5']['values'][0],report.colorfulness(frames[0][10:50,:,::-1]),delta=.01)

    def test_encoded_y16_noise_intro_and_letterbox(self):
        from taste_common import executable
        rng=np.random.default_rng(103);data=[]
        for i in range(90):
            y=np.full((60,80),16.,float);u=np.full((30,40),128,np.uint8);v=u.copy()
            if i>=30:y[10:50]=100;u[5:25]=90;v[5:25]=170
            y=np.clip(y+rng.normal(0,3,y.shape),0,255).astype('uint8')
            data.append(y.tobytes()+u.tobytes()+v.tobytes())
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'noisy.mp4'
            subprocess.run([executable('ffmpeg'),'-v','error','-f','rawvideo','-pixel_format','yuv420p','-video_size','80x60','-framerate','30','-i','pipe:0','-c:v','libx264','-crf','12',str(path)],input=b''.join(data),check=True,capture_output=True)
            r=report.analyze(path)
        self.assertEqual(r['media']['active_picture'],[0,10,80,50])
        self.assertEqual(r['content']['labels'][:10],['no content']*10)
        self.assertTrue(all(c is None for c in r['M10']['centroids'][:10]))
        self.assertGreater(r['M5']['values'][15],30)

    def test_fade_in_not_main_peak(self):
        frames=[np.full((48,80,3),v,np.uint8) for v in np.linspace(0,180,60)] + [np.full((48,80,3),180,np.uint8)]*180
        r=analyze_frames(frames)
        self.assertFalse(any(p['time']<2 for p in r['M15']['peaks']))

    def test_black_frame_no_eye_trace(self):
        r=dict(media=dict(fps=30),content=dict(times=[0,1,2],labels=['content','no content','content']),M15={},M10=dict(times=[0,1,2],centroids=[[.1,.5],[.9,.5],[.1,.5]]))
        b=dict(shots=[dict(start=0),dict(start=1),dict(start=2)])
        self.assertNotIn('eye_trace',[x['rule'] for x in edit_lint(r,b)])

    def test_single_frame_flash_listed(self):
        a=np.full((48,80,3),80,np.uint8)
        r=analyze_frames([a]*30+[np.full_like(a,255)]+[a]*60)
        self.assertEqual(len(r['M4']['flash_events']),1)
        self.assertAlmostEqual(r['M4']['flash_events'][0]['time_ms'],1000,delta=34)

    def test_weight_source_and_constant_components(self):
        a=np.full((48,80,3),80,np.uint8)
        r=analyze_frames([a]*30)
        self.assertEqual(r['M15']['effective_weights'],[0,0,0,0])
        self.assertEqual(r['summary']['weight_source'],'default')
        self.assertEqual(analyze_frames([a]*30,weights=[1,0,0,0])['summary']['weight_source'],'user')

    def test_annotation_aliases(self):
        for annotation in (dict(rule='30_degree',reason='Deliberate'),dict(transition='jump_cut',reason='Deliberate')):
            self.assertEqual(finding('angle_30',2,0,30,'Change angle',dict(rule_break=annotation))['status'],'annotated')

    def test_designed_flash_no_highlight_suggestion(self):
        a=np.full((48,80,3),80,np.uint8)
        b=dict(shots=[dict(duration=3,effects=[dict(name='flash',start_ms=1000,end_ms=1100,serves_core='Punctuation')])])
        r=analyze_frames([a]*30+[np.full_like(a,255)]+[a]*59,storyboard=b)
        self.assertFalse(any('clipped_fraction' in s['evidence'] for s in r['summary']['suggestions']))

    def test_plan_flash_without_exemption_prose_is_still_designed(self):
        a=np.full((48,80,3),80,np.uint8)
        b=dict(shots=[dict(duration=3,effects=[dict(name='flash',start_ms=1000,end_ms=1100)])])
        r=analyze_frames([a]*30+[np.full_like(a,255)]+[a]*59,storyboard=b)
        self.assertFalse(any('clipped_fraction' in s['evidence'] for s in r['summary']['suggestions']))

    def test_string_transition_flash_is_designed(self):
        a=np.full((48,80,3),80,np.uint8)
        b=dict(shots=[dict(duration=1),dict(duration=2,transition='white_flash')])
        r=analyze_frames([a]*30+[np.full_like(a,255)]+[a]*59,storyboard=b)
        self.assertFalse(any('clipped_fraction' in s['evidence'] for s in r['summary']['suggestions']))


if __name__=='__main__':unittest.main()
