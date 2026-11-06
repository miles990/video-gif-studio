import numpy as np
from PIL import Image,ImageDraw
from image_fixtures import ImageCase
from image_common import ImageError,digest,read
from image_identity import build,check,compare,controls,load


def mascot(path,negative=False,pose=0):
    im=Image.new('RGBA',(300,400));d=ImageDraw.Draw(im)
    color='#165bd5' if negative else '#c63625'
    if negative:d.rectangle((60,40,240,240),fill=color)
    else:d.ellipse((60,40,240,240),fill=color)
    d.rectangle((80,225,220,280),fill='#a85ae0' if negative else '#f0ce26')
    d.rectangle((80+pose,280,140+pose,360),fill='#25a066')
    # Stable internal pattern creates meaningful ORB features; pose shifts the cup.
    rng=np.random.default_rng(99 if negative else 8)
    for x,y in rng.integers([90,80],[210,215],size=(80,2)):
        d.rectangle((int(x),int(y),int(x+4),int(y+4)),fill='#341c18' if not negative else '#d3e2ff')
    d.polygon([(80,140),(90,130),(100,140),(95,155),(85,155)],fill='blue')
    im.save(path)


class IdentityTests(ImageCase):
    def setUp(self):
        super().setUp();self.a=self.path/'a.png';self.b=self.path/'b.png';self.neg=self.path/'neg.png'
        mascot(self.a);mascot(self.b,pose=8);mascot(self.neg,negative=True)

    def test_controls_and_reference_integrity(self):
        result=controls(self.a,self.b,self.neg);self.assertTrue(result['valid'])
        ref=self.path/'refs.json';build('Mia',[self.a,self.b],ref,negative=[self.neg])
        self.assertEqual(check(self.a,ref)['status'],'pass');self.assertEqual(check(self.neg,ref)['status'],'identity_fail')
        self.assertEqual(len(load(ref)['images']),2)
        mascot(self.a,pose=20)
        with self.assertRaises(ImageError):load(ref)

    def test_mixed_library_and_limit_rejected(self):
        with self.assertRaises(ImageError) as err:build('mixed',[self.a,self.neg],self.path/'bad.json')
        self.assertEqual(err.exception.error['code'],'E_REFSET_MIXED')
        with self.assertRaises(ImageError):build('too many',[self.a]*17,self.path/'bad.json')

    def test_broken_controls_cannot_judge(self):
        self.assertFalse(controls(self.a,self.b,self.b)['valid'])
        self.assertFalse(controls(self.a,self.a,self.neg)['valid'])

    def test_all_keyframes_send_same_refset_and_retry_drift_once(self):
        from dataclasses import replace
        from image_keyframes import keyframes
        from test_image_keyframes import board
        ref=self.path/'refs.json';build('Mia',[self.a,self.b],ref,negative=[self.neg])
        self.configure(image=str(self.neg))
        req=self.request(refs=[self.a,self.b],refset_path=str(ref),refset_sha=digest(ref))
        b=board();b['height']=1440;b['shots']=b['shots'][:1]
        result=keyframes(b,self.adapter,self.path/'kf',req)
        self.assertEqual(len(self.calls()),2);self.assertEqual(result['shots'][0]['keyframe']['status'],'identity_fail')
        for row in self.calls():self.assertIn(str(self.a).replace('\\','\\\\'),row['stdin'])
