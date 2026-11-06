from copy import deepcopy
import numpy as np
from PIL import Image
from image_fixtures import ImageCase
from image_common import digest,read
from image_keyframes import keyframes,fit_image,frame_qa,keyframe_prompt
from animatic import source_frame,to_plan
from storyboard import lint,normalize


def board():
    return dict(core='Mia opens a cafe',aesthetic='warm painted cinema',width=1080,height=1920,
                shots=[dict(id=f's{i}',duration=.2,size=size,motion='static',subject='Mia',action='holds cup',
                            lighting='window',color_script='#3A5A80',why='reveal',serves_core='show cafe')
                       for i,size in enumerate(['EWS','WS','MS','CU','ECU','MS'],1)])


class KeyframeTests(ImageCase):
    def test_six_shots_incremental_and_aspect(self):
        before=board();b=keyframes(before,self.adapter,self.path/'kf',self.request())
        self.assertEqual(len(self.calls()),6)
        self.assertEqual(lint(before)['errors'],lint(b)['errors'])
        for s in b['shots']:
            with Image.open(s['keyframe']['path']) as im:self.assertEqual(im.size,(1080,1920))
            self.assertIn(s['size'],keyframe_prompt(b,s));self.assertIn('#3A5A80',keyframe_prompt(b,s))
            self.assertTrue(s['keyframe']['colour_pass'])
        changed=deepcopy(before);changed['shots'][3]['size']='MS'
        after=keyframes(changed,self.adapter,self.path/'kf2',self.request())
        self.assertEqual(len(self.calls()),7)
        self.assertEqual(b['shots'][0]['keyframe']['sha256'],after['shots'][0]['keyframe']['sha256'])
        # Only frame contents change; existing clock and shot metadata stay identical.
        self.assertEqual([(s['start'],s['end']) for s in b['shots']],[(s['start'],s['end']) for s in after['shots']])

    def test_contain_never_stretches(self):
        im=Image.new('RGB',(1040,1800),'red');fitted,report=fit_image(im,(1080,1920))
        self.assertEqual(fitted.size,(1080,1920));self.assertLessEqual(report['padding_fraction'],.05)
        self.assertFalse(report['stretched'])

    def test_missing_frame_falls_back_and_generation_failure_keeps_board(self):
        self.configure(error='unavailable')
        b=keyframes(board(),self.adapter,self.path/'fail',self.request())
        self.assertEqual(len(b['shots']),6)
        for s in b['shots']:
            self.assertIn('keyframe_failure',s)
            frame=source_frame(s,self.path,(90,160));self.assertEqual(frame.shape,(160,90,4))
            self.assertEqual(s['asset_fallback']['reason'],'no keyframe')

    def test_animatic_reads_generated_keyframe(self):
        b=keyframes(board(),self.adapter,self.path/'kf',self.request())
        shot=b['shots'][0];actual=source_frame(shot,self.path,(90,160))
        with Image.open(shot['keyframe']['path']) as im:expected=np.array(fit_image(im,(90,160))[0])
        # QA annotations occupy only the label band; remaining pixels are the keyframe.
        self.assertTrue(np.array_equal(actual[25:],expected[25:]))
        to_plan(b,self.path/'plan',size=(90,160))
        self.assertEqual(read(self.path/'plan/shot-1/manifest.json')['durations_ms'],[40]*5)

    def test_size_and_colour_negative_controls(self):
        mask=np.zeros((160,90),np.uint8);mask[20:140,30:60]=255
        report=frame_qa(self.fixture,dict(size='EWS'),'#FFFFFF',mask)
        self.assertEqual(report['size_status'],'size_mismatch');self.assertFalse(report['colour_pass'])
