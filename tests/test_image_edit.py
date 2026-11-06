from copy import deepcopy
import numpy as np
from PIL import Image,ImageDraw
from image_fixtures import ImageCase
from image_common import ImageError,digest
from image_edit import composite,edit,apply_delta,region_mask
from brief_edit import parse


class EditTests(ImageCase):
    def setUp(self):
        super().setUp();rng=np.random.default_rng(42)
        a=rng.integers(30,150,(240,160,3),dtype='uint8');self.base=Image.fromarray(a).convert('RGBA')
        d=ImageDraw.Draw(self.base);d.rectangle((55,130,100,190),fill='#208040')
        self.original=self.path/'original.png';self.base.save(self.original)
        self.candidate=self.base.copy();d=ImageDraw.Draw(self.candidate);d.rectangle((55,130,100,190),fill='#dec69d')
        a=np.array(self.candidate);a[...,:3]=np.minimum(a[...,:3].astype(int)+5,255).astype('uint8');self.candidate=Image.fromarray(a)
        self.candidate.save(self.fixture)

    def test_full_redraw_preserves_outside_exactly(self):
        result=edit(self.adapter,self.request(),self.original,self.path/'edit','latte',region=[53,128,50,65])
        self.assertTrue(result['edit']['outside_identical']);self.assertEqual(result['edit']['outside_mean'],0)
        self.assertGreater(result['edit']['raw_outside_mean'],0);self.assertGreaterEqual(result['edit']['inside_delta_e2000'],8)
        self.assertLessEqual(result['edit']['registration']['residual_px'],1)

    def test_delta_selects_only_second_cup_and_keeps_other_hashes(self):
        board=dict(shots=[dict(id=f's{i}',start=i-1,end=i,duration=1,motion='static',keyframe=dict(path=str(self.original),sha256=digest(self.original)),image_regions={'杯子':[53,128,50,65]}) for i in range(1,7)])
        parsed=parse('第二鏡的杯子改成拿鐵',board);change=parsed['changes'][0]
        self.assertEqual(change['target']['shot'],2);self.assertEqual(change['target']['element'],'杯子');self.assertEqual(change['change'],'image_edit')
        result=apply_delta(board,'第二鏡的杯子改成拿鐵',self.adapter,self.request(),self.path/'delta')
        self.assertEqual(result['revision']['changed_shots'],['s2']);self.assertEqual(len(self.calls()),1)
        for i in [0,2,3,4,5]:self.assertEqual(board['shots'][i],result['shots'][i])

    def test_markup_fills_ring_and_rejects_changed_size(self):
        note=Image.new('RGBA',(160,240));ImageDraw.Draw(note).ellipse((50,125,108,200),outline='red',width=3)
        path=self.path/'note.png';note.save(path);mask=region_mask(note.size,markup=path)
        self.assertGreater(mask[160,80],0)
        with self.assertRaises(ImageError):composite(self.base,self.candidate.resize((80,120)),mask)
        with self.assertRaises(ImageError):composite(self.base,self.base,mask)

    def test_image_feedback_resolves_frame_and_object(self):
        from image_common import write
        sheet=self.path/'contact.png';write(sheet.with_suffix('.json'),dict(frames_at_s=[.2,1.2],source='unused for a region edit'))
        board=dict(shots=[dict(id='s1',start=0,end=1),dict(id='s2',start=1,end=2)])
        parsed=parse('第 2 格的杯子改成拿鐵',board,image=sheet)
        self.assertEqual(parsed['changes'][0]['change'],'image_edit');self.assertEqual(parsed['changes'][0]['target']['shots'],['s2'])
