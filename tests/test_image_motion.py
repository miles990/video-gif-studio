import numpy as np
from PIL import Image,ImageDraw,ImageSequence
from image_fixtures import ImageCase
from image_common import ImageError,read
from image_motion import ingest_gif,loop_keyframes,repair_loop,seam_qa,validate_motion


class MotionTests(ImageCase):
    def circle(self,count=48):
        frames=[]
        for i in range(count):
            im=Image.new('RGBA',(96,96));d=ImageDraw.Draw(im)
            x=48+28*np.cos(2*np.pi*i/48);y=48+28*np.sin(2*np.pi*i/48)
            d.ellipse((x-6,y-6,x+6,y+6),fill='red');frames.append(im)
        return frames

    def test_loop_controls_and_repair(self):
        good=self.circle();bad=good[:-6]
        self.assertEqual(seam_qa(good)['status'],'PASS');self.assertEqual(seam_qa(bad)['status'],'FAIL')
        folder=self.path/'bad';folder.mkdir();paths=[]
        for i,f in enumerate(bad):
            p=folder/f'{i:05d}.png';f.save(p);paths.append(p)
        result=repair_loop(paths,[40]*len(paths),self.path/'repaired')
        self.assertEqual(result['loop']['status'],'PASS')

    def test_disposal_and_variable_delays_decode_exactly(self):
        frames=self.circle(12);durations=[20,40,100,2000]*3;file=self.path/'input.gif'
        frames[0].save(file,save_all=True,append_images=frames[1:],duration=durations,disposal=[1,2,3]*4,loop=0)
        result=ingest_gif(file,self.path/'ingest')
        self.assertEqual(result['durations_ms'],durations)
        with Image.open(file) as gif:
            for i,frame in enumerate(ImageSequence.Iterator(gif)):
                with Image.open(self.path/'ingest/frames'/f'{i:05d}.png') as actual:
                    self.assertEqual(actual.tobytes(),frame.convert('RGBA').tobytes())
                    self.assertTrue(set(np.unique(np.array(actual)[...,3]))<={0,255})
        sprite=read(self.path/'ingest/sprites/sprites.json')
        self.assertEqual([f['duration_ms'] for f in sprite['frames']],durations)
        self.assertEqual(sprite['qc']['rgba_mismatches'],0)

    def test_local_keyframe_loop_and_parameters(self):
        result=loop_keyframes([self.fixture],self.path/'loop',size=(96,160),media_qa=False)
        self.assertTrue(result['loop']['moving']);self.assertEqual(result['loop']['status'],'PASS')
        self.assertFalse(result['ai_video_generated']);self.assertEqual(len(self.calls()),0)
        for size,frames,ms in [((91,160),48,40),((96,160),65,40),((96,160),48,15)]:
            with self.assertRaises(ImageError):validate_motion(size,frames,ms)
