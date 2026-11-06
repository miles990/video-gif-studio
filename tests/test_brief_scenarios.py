"""Encoded slice-11 scenarios, one renderer at a time, generated fixtures only."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import cv2
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from brief import expand,to_storyboard as convert_board,write

def to_storyboard(b,**kwargs):return convert_board(b,allow_skeleton=True,**kwargs)
from brief_refs import contact_sheet
from brief_edit import parse,apply_changes
from brief_render import compile_plan,render_version
from brief_guard import audit
from fx_render import render


class BriefScenarios(unittest.TestCase):
    def setUp(self):
        (ROOT/'.scratch').mkdir(exist_ok=True);self.temp=tempfile.TemporaryDirectory(dir=ROOT/'.scratch',prefix='brief-scenario-');self.path=Path(self.temp.name)
        self.threads=cv2.getNumThreads();cv2.setNumThreads(1)
    def tearDown(self):cv2.setNumThreads(self.threads);self.temp.cleanup()

    def video(self,name,seconds=3):
        path=self.path/(name+'.avi');out=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),30,(96,64))
        for i in range(seconds*30):
            frame=np.full((64,96,3),41,np.uint8);cv2.rectangle(frame,(i%70,12),(i%70+12,38),(42,42,42),-1);out.write(frame)
        out.release();return path

    def test_image_feedback_uses_actual_time_and_measured_luma(self):
        source=self.video('feedback');sheet=self.path/'sheet.png';meta=contact_sheet(source,sheet)
        b=to_storyboard(expand('coffee 3s'))
        for s in b['shots']:s['min_text_px']=18;s['captions']=[dict(text='MENU')]
        edit=parse('第 5 格太暗、第 8 格字太小',b,image=sheet)
        self.assertFalse(edit['questions']);self.assertEqual(len(edit['changes']),2)
        self.assertAlmostEqual(edit['changes'][0]['time'],meta['frames_at_s'][4],delta=1/30)
        self.assertAlmostEqual(edit['changes'][0]['quantified']['measured_y'],41,delta=2.05)
        self.assertEqual(edit['changes'][1]['quantified']['current_px_1080'],18)
        after=apply_changes(b,edit);targets={s for c in edit['changes'] for s in c['target']['shots']}
        for old,new in zip(b['shots'],after['shots']):
            if old['id'] not in targets:self.assertEqual(old,new)

    def test_owned_footage_is_sampled_not_frozen(self):
        source=self.video('moving');cap=cv2.VideoCapture(str(source));self.assertTrue(cap.isOpened());cap.release()
        # Stronger motion source for decoded equality.
        out=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'MJPG'),30,(96,64))
        for i in range(90):
            frame=np.full((64,96,3),80,np.uint8);cv2.circle(frame,(10+i%75,30),9,(190,100,20),-1);out.write(frame)
        out.release()
        b=to_storyboard(expand('coffee 3s',project=[dict(id='C1',path=str(source),description='cup')]))
        for s in b['shots']:s.pop('recipe');s['motion']='static'
        compile_plan(b,self.path/'plan',size=(96,64))
        files=sorted((self.path/'plan/shot-1/frames').glob('*.png'))
        with Image.open(files[0]) as a,Image.open(files[-1]) as z:self.assertGreater(np.abs(np.array(a).astype(float)-np.array(z)).mean(),1)

    def test_drop_frame_and_reference_exclusion_encoded(self):
        # User footage is distinct from a read-only high-detail reference.
        rng=np.random.default_rng(81);ref=self.path/'reference.png';Image.fromarray(rng.integers(0,255,(96,96,3),dtype=np.uint8)).save(ref)
        b=to_storyboard(expand('coffee 5s',music=dict(downbeats_ms=[0,2000,4000],beats_ms=list(range(0,5000,500)),drop_ms=2000)))
        for s in b['shots']:
            s.pop('recipe');s['motion']='static';s['transition']='cut';s['background']='#c0a080' if s['start']>=2 else '#504030'
        compile_plan(b,self.path/'drop-plan',size=(96,64));render(self.path/'drop-plan/plan.json',self.path/'drop-render',('mp4',),fps=30)
        movie=next((self.path/'drop-render').glob('*.mp4'));cap=cv2.VideoCapture(str(movie));means=[]
        while True:
            ok,frame=cap.read()
            if not ok:break
            means.append(float(frame.mean()))
        cap.release();jump=np.argmax(np.diff(means))+1;self.assertAlmostEqual(jump/30,2,delta=1/30)
        with self.assertRaisesRegex(ValueError,'E_FINGERPRINT_RESOLUTION'):audit(movie,[ref])

    def test_music_edit_keeps_unaffected_frames_and_colours(self):
        source=self.path/'asset.png';Image.new('RGB',(96,64),(140,100,70)).save(source)
        b=to_storyboard(expand('coffee 5s',project=[dict(id='C1',path=str(source))],music=dict(downbeats_ms=[0,2000,4000],drop_ms=2000)))
        for s in b['shots']:s.pop('recipe');s['motion']='pan';s['transition']='cut'
        v1=render_version(b,self.path/'v1',size=(96,64),formats=('png',))
        changed=apply_changes(b,parse('第二拍慢一點、保留顏色',b));v2=render_version(changed,self.path/'v2',self.path/'v1',size=(96,64),formats=('png',))
        self.assertEqual([s['start'] for s in b['shots']],[s['start'] for s in changed['shots']])
        for old,new in zip(v1['shots'],v2['shots']):
            if old['id'] not in v2['rerendered_shots']:self.assertEqual(old['sha256'],new['sha256'])
            else:
                for p,q in zip(old['frames'][::8],new['frames'][::8]):
                    a=cv2.imread(str(self.path/'v1'/p));z=cv2.imread(str(self.path/'v2'/q));self.assertLessEqual(np.abs(a.astype(float)-z).mean(),1)

    def test_sequence_start_and_batch_mechanics_are_distinct(self):
        b=expand('在 3 秒的地方，菜單翻頁之後跳出價格標，6 秒前結束')
        self.assertEqual(b['duration'],6);self.assertEqual(b['beats'][1]['t_start'],3)
        batch=expand('create 4 variations of the menu reveal')
        boards=[to_storyboard(batch,variant=i) for i in range(1,5)]
        self.assertEqual(len({tuple(s['motion'] for s in b['shots']) for b in boards}),4)


if __name__=='__main__':unittest.main()
