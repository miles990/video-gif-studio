from test_game_engines import EngineTests
from test_game_animation import pose,manifest
from image_common import read,write,ImageError
from game_engines import export_engines
from game_animation import motion_qa
from pathlib import Path
from PIL import Image
import unittest

class MotionFixTests(unittest.TestCase):
    def test_reviewer_jumpseam_and_limp(self):
        root=Path('tests/fixtures/live-s14/motion')
        for name in ('WALK-JUMPSEAM','WALK-LIMP'):
            frames=[Image.open(p).convert('RGBA') for p in sorted(root.glob(name+'-*.png'))]
            q=motion_qa(frames,manifest(len(frames),state='walk',loop=True,contacts=[],foot_boxes={'left':[[18,50,14,14]]*len(frames),'right':[[33,50,14,14]]*len(frames)}))
            self.assertEqual(q['status'],'FAIL',name)
            self.assertTrue(any(i['kind']=='stride_asymmetry' for i in q['issues']),q)
        good=[Image.open(p).convert('RGBA') for p in sorted(root.glob('WALK-8-*.png'))]
        q=motion_qa(good,manifest(8,state='walk',loop=True,contacts=[],foot_boxes={'left':[[18,50,14,14]]*8,'right':[[33,50,14,14]]*8}))
        self.assertEqual(q['status'],'PASS',q)
        self.assertEqual([r['frames'] for r in q['contacts']['measured_intervals']],[[0,3],[4,7]])

    def test_generated_registration_common_ground_and_height(self):
        from game_character import register_subject
        a,ra=register_subject(pose(),(64,64),60,41)
        b,rb=register_subject(pose().resize((256,256)),(64,64),60,41)
        self.assertEqual(a.getbbox(),b.getbbox())
        self.assertEqual(a.getbbox()[3]-1,60)

class ExportGateTests(EngineTests):
    def test_qa_fail_blocks_export_and_override_recorded(self):
        m=read(self.manifests[0]);m['qa']={'status':'FAIL','issues':[{'kind':'foot_slide'}]};write(self.manifests[0],m)
        with self.assertRaises(ImageError) as e:export_engines(self.manifests,self.path/'blocked')
        self.assertEqual(e.exception.error['code'],'E_QA_FAIL')
        self.assertFalse((self.path/'blocked').exists())
        result=export_engines(self.manifests,self.path/'override',allow_qa_fail=True)
        self.assertTrue(result['qa_override']['allow_qa_fail'])
