import json
from pathlib import Path
import sys
import tempfile
import unittest
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
