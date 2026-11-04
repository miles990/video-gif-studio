import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fx_render import render,validate_plan
from fx_reverse import inspect_frames,reverse
from test_fx import synthetic


def roundtrip_plan():
    return {'beatmap':'beats.json','fps':25,'segments':[
        {'type':'animation','manifest':'A/manifest.json','in_ms':0,'out_ms':1000},
        {'type':'animation','manifest':'B/manifest.json','in_ms':0,'out_ms':1000},
        {'type':'animation','manifest':'A/manifest.json','in_ms':0,'out_ms':1480,'duration_ms':1500,'transition':{'name':'whip_pan','duration_ms':240}},
        {'type':'still','manifest':'B/manifest.json','frame':'first','duration_ms':1000},
        {'type':'animation','manifest':'B/manifest.json','in_ms':0,'out_ms':680,'transition':{'name':'hex_shutter','duration_ms':400}},
        {'type':'animation','manifest':'A/manifest.json','in_ms':0,'out_ms':800,'duration_ms':820}],
        'effects':[{'name':'flash_white','start_ms':1500,'end_ms':1640,'amount':{'keyframes':[[1500,1],[1620,0]]}},
                   {'name':'zoom_punch','start_ms':3000,'end_ms':3320,'scale':1.22,'amount':{'keyframes':[[3000,1],[3320,0]]}}]}


class ReverseTests(unittest.TestCase):
    def test_static_and_slow_pan_have_no_zooms(self):
        rng=np.random.default_rng(19)
        texture=rng.integers(20,220,(90,220,3),dtype=np.uint8)
        stripe=np.full((90,220,3),70,np.uint8);stripe[:,70:82]=230
        for source in (texture,stripe):
            for moving in (False,True):
                images=[Image.fromarray(source[:,i if moving else 0:(i if moving else 0)+160]) for i in range(60)]
                report=inspect_frames(images,np.arange(60)*40,2400)
                self.assertEqual(report['zoom_punches'],[],(moving,report))

    def test_textured_centered_punch_and_translation_dominant_rejection(self):
        import cv2
        from fx import Context,EFFECTS
        rng=np.random.default_rng(28)
        base=rng.integers(25,220,(90,160,4),dtype=np.uint8)
        base=cv2.GaussianBlur(base,(5,5),0);base[:,:,3]=255
        for translation in (0,10):
            images=[]
            for i in range(50):
                amount=max(0,1-(i-20)/8) if i>=20 else 0
                frame=EFFECTS['zoom_punch']['function'](base,i*40,Context(160,90),scale=1.2,amount=amount)
                if i>=20:frame=cv2.warpAffine(frame,np.float32([[1,0,translation],[0,1,0]]),(160,90),borderMode=cv2.BORDER_REFLECT_101)
                images.append(Image.fromarray(frame))
            zooms=inspect_frames(images,np.arange(50)*40,2000)['zoom_punches']
            self.assertEqual(len(zooms),0 if translation else 1,zooms)
            if zooms:self.assertEqual(zooms[0]['time_ms'],800)

    def test_step_zoom_without_decay_is_not_a_punch(self):
        from fx import Context,EFFECTS
        base=np.full((90,160,4),[80,40,100,255],np.uint8);base[:,40:52,:3]=230
        images=[Image.fromarray(EFFECTS['zoom_punch']['function'](base,i*40,Context(160,90),scale=1.2,amount=int(i>=20))) for i in range(50)]
        self.assertEqual(inspect_frames(images,np.arange(50)*40,2000)['zoom_punches'],[])

    def test_partial_flashes_and_all_nested_times_are_integer(self):
        from fx import Context,EFFECTS
        from fx_reverse import integer_times
        base=np.full((90,160,4),[12,30,50,255],np.uint8)
        images=[Image.fromarray(EFFECTS['flash_white']['function'](base,i*40,Context(160,90),amount=max(0,.6*(1-abs(i-20)/3),.65*(1-abs(i-40)/3)))) for i in range(60)]
        report=inspect_frames(images,np.arange(60)*40.01,2400.6)
        self.assertEqual([e['time_ms'] for e in report['flashes']],[800,1600])
        self.assertIs(type(report['beat_alignment']['tolerance_ms']),int)
        nested=integer_times({'suggested_effects':[{'end_ms':120.1,'amount':{'keyframes':[[40.4,.65],[80.2,0]]}}]})
        self.assertEqual(nested['suggested_effects'][0],{'end_ms':120,'amount':{'keyframes':[[40,.65],[80,0]]}})

    def test_sampler_retains_flash_between_nominal_frames(self):
        from fx import Context,EFFECTS
        from fx_reverse import sample_frames
        base=np.full((90,160,4),[12,30,50,255],np.uint8)
        images=[Image.fromarray(EFFECTS['flash_white']['function'](base,t,Context(160,90),
                amount=.65*max(0,1-(t-740)/130)**3 if t>=740 else 0)) for t in range(0,1200,10)]
        with patch('fx_reverse.media_frames',return_value=iter(images)):
            sampled,times,duration=sample_frames(Path('unused'),{'durations':[.01]*120},25)
        report=inspect_frames(sampled,times,duration)
        self.assertEqual([e['time_ms'] for e in report['flashes']],[740])

    def test_known_plan_offline_detection_and_draft(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);synthetic(root);(root/'p.json').write_text(json.dumps(roundtrip_plan()))
            render(root/'p.json',root/'rt',('png',))
            images=[Image.open(f).convert('RGBA') for f in sorted((root/'rt/frames').glob('*.png'))]
            durations=json.loads((root/'rt/manifest.json').read_text())['durations_ms']
            report=inspect_frames(images,np.cumsum([0]+durations).tolist()[:-1],6000,list(range(0,6001,500)))
            for t in (1000,3500,5180):self.assertLessEqual(min(abs(c['time_ms']-t) for c in report['cuts']),40,report)
            self.assertLessEqual(min(abs(c['time_ms']-1500) for c in report['flashes']),40)
            self.assertTrue(any(abs(f['start_ms']-3500)<=40 for f in report['freezes']))
            self.assertTrue(any(c['type']=='hex_shutter' for c in report['cuts']),report)
            self.assertEqual([c['type'] for c in report['cuts']],['cut','whip_pan','cut','hex_shutter','cut'])
            self.assertEqual(report['beat_alignment']['ratio'],.8)
            self.assertTrue(any(abs(z['time_ms']-3000)<=80 and z['scale']>=1.1 for z in report['zoom_punches']))
            reverse(root/'rt/frames',root/'rev',root/'beats.json')
            validate_plan(root/'rev/draft-plan.json')
            draft=json.loads((root/'rev/draft-plan.json').read_text())
            def check_times(value,key=''):
                if isinstance(value,dict):
                    for k,v in value.items():check_times(v,k)
                elif isinstance(value,list):
                    if key=='keyframes':
                        for t,_ in value:self.assertIs(type(t),int)
                    else:
                        for v in value:check_times(v,key)
                elif key.endswith('_ms'):self.assertIs(type(value),int,(key,value))
            check_times(draft);check_times(json.loads((root/'rev/report.json').read_text()))
            for s,name in zip(draft['segments'],['A','B','A','B','B','A']):
                s['manifest']=str(root/name/'manifest.json')
            (root/'rev/replaced.json').write_text(json.dumps(draft))
            render(root/'rev/replaced.json',root/'rt2',('png',))
            m=json.loads((root/'rt2/manifest.json').read_text());ims=[]
            for f in sorted((root/'rt2/frames').glob('*.png')):
                with Image.open(f) as im:ims.append(im.convert('RGBA'))
            again=inspect_frames(ims,np.cumsum([0]+m['durations_ms']).tolist()[:-1],sum(m['durations_ms']),list(range(0,6001,500)))
            for c in report['cuts']:self.assertLessEqual(min(abs(x['time_ms']-c['time_ms']) for x in again['cuts']),40)
            self.assertLessEqual(abs(again['flashes'][0]['time_ms']-report['flashes'][0]['time_ms']),40)

    def test_no_cuts_for_flash_or_zoom_only(self):
        from fx import Context,EFFECTS
        ctx=Context(160,90);a=np.full((90,160,4),[200,40,40,255],np.uint8);a[:,50:60,:3]=255
        frames=[Image.fromarray(EFFECTS['flash_white']['function'](a,i*40,ctx,amount=max(0,1-abs(i-20)/4))) for i in range(50)]
        r=inspect_frames(frames,list(range(0,2000,40)),2000)
        self.assertEqual(r['cuts'],[]);self.assertEqual(len(r['flashes']),1)

if __name__=='__main__':unittest.main()
