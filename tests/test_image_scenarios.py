"""S13 encoded end-to-end scenarios, fake provider only, all files in .scratch."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
from image_fixtures import ImageCase,ROOT
from image_common import digest,read,write
from image_keyframes import keyframes
from image_edit import apply_delta
from image_alpha import transparent_asset
from image_vector import trace
from image_motion import loop_keyframes
from image_variants import variants,pick
from brief_render import render_version


class ImageScenarios(ImageCase):
    def test_board_render_edit_incremental_loop_and_vector(self):
        rng=np.random.default_rng(71)
        a=rng.integers(25,170,(160,96,3),dtype='uint8')
        im=Image.fromarray(a);ImageDraw.Draw(im).rectangle((28,95,60,135),fill='#208040');im.save(self.fixture)
        board=dict(core='cafe continuity',width=1080,height=1920,fps=25,
                   shots=[dict(id=f's{i}',size=size,duration=.24,motion='static',subject='Mia',action='holds cup',why='show cafe',serves_core='cafe continuity')
                          for i,size in enumerate(['EWS','WS','MS','CU','ECU','MS'],1)])
        generated=keyframes(board,self.adapter,self.path/'keyframes',self.request())
        self.assertEqual(len(self.calls()),6)
        before=render_version(generated,self.path/'v1',size=(90,160),formats=('png','mp4'))
        shot=generated['shots'][1];source=Path(shot['keyframe']['path'])
        with Image.open(source) as original:
            edited=original.copy();ImageDraw.Draw(edited).rectangle((340,1150,700,1630),fill='#e9c7a2');edited.save(self.fixture)
        generated['shots'][1]['image_regions']={'杯子':[338,1148,365,485]}
        revised=apply_delta(generated,'第二鏡的杯子改成拿鐵',self.adapter,self.request(),self.path/'edit')
        after=render_version(revised,self.path/'v2',previous=self.path/'v1',size=(90,160),formats=('png','mp4'))
        self.assertEqual(after['rerendered_shots'],['s2']);self.assertEqual(len(after['reused_shots']),5)
        self.assertEqual(before['duration'],after['duration'])
        for old,new in zip(before['shots'],after['shots']):
            if old['id']!='s2':self.assertEqual(old['sha256'],new['sha256'])
        loop=loop_keyframes([source],self.path/'loop',frames=24,frame_ms=80,size=(96,160))
        self.assertEqual(loop['loop']['status'],'PASS');self.assertEqual(read(self.path/'loop/sprites/sprites.json')['qc']['rgba_mismatches'],0)
        self.assertEqual(loop['media_qa_loop']['level'],'PASS')
        svg=trace(source,self.path/'graphic.svg',colors=3)
        self.assertEqual(svg['safety']['status'],'PASS')

    def test_failed_alpha_does_not_reuse_bad_cache(self):
        # Opaque checkerboard cannot become a transparent asset by renaming mode.
        yy,xx=np.indices((160,160));rgb=np.repeat(np.where((xx//16+yy//16)%2,204,255).astype('uint8')[...,None],3,axis=2)
        Image.fromarray(rgb).save(self.fixture)
        for i in range(2):
            with self.assertRaises(ValueError):transparent_asset(self.adapter,self.request(),self.path/f'bad{i}')
        self.assertEqual(len(self.calls()),4)
        self.assertFalse(list((self.path/'state/cache').glob('*/record.json')))

    def test_cli_local_fallback_validates_before_provider(self):
        base=[sys.executable,str(ROOT/'scripts/imagegen.py'),'generate','--experimental','--format','gif','--prompt','loop',
              '--codex',str(self.fake),'--state',str(self.path/'state'),'--json']
        bad=subprocess.run([*base,'--size','95x160','--out',str(self.path/'bad')],capture_output=True,text=True)
        self.assertEqual(bad.returncode,2);self.assertEqual(self.calls(),[])
        good=subprocess.run([*base,'--size','96x160','--frames','8','--start-image',str(self.fixture),'--out',str(self.path/'good')],capture_output=True,text=True)
        self.assertEqual(good.returncode,0,good.stdout+good.stderr);self.assertEqual(self.calls(),[])
        self.assertTrue((self.path/'good/motion/preview.gif').is_file())
