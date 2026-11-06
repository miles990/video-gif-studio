import sys
from pathlib import Path
import unittest
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from game_animation import contact_qa,motion_qa,mesh_between,attack_contact


def pose(x=0,y=0):
    im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im)
    d.rectangle((24+x,20+y,39+x,48+y),fill='#E07A2E');d.rectangle((24+x,49+y,28+x,60+y),fill='#2BB5B0');d.rectangle((35+x,49+y,39+x,60+y),fill='#2BB5B0')
    return im


def manifest(n,**kwargs):
    return dict(pivot=[32,60],ground_line=60,pixel=True,frames=[dict(duration_ms=100) for _ in range(n)],**kwargs)


class AnimationTests(unittest.TestCase):
    def test_contacts_find_three_pixel_slide_and_world_compensation(self):
        frames=[pose(i) for i in range(4)];m=manifest(4,contacts=[dict(foot='left',frames=[0,3],box=[20,48,15,14])])
        result=contact_qa(frames,m)
        self.assertEqual(result['status'],'FAIL');self.assertEqual(result['issues'][-1]['slide_px'],3)
        m['root_motion']=[[-i,0] for i in range(4)]
        self.assertEqual(contact_qa(frames,m)['status'],'PASS')

    def test_mesh_keeps_exact_palette_and_moves_articulation(self):
        a=pose();b=pose(4,-2);pa=[[24,20],[39,20],[24,48],[39,48],[24,60],[39,60]];pb=[[x+4,y-2] for x,y in pa]
        result=mesh_between(a,b,pa,pb,.5)
        self.assertNotEqual(result.tobytes(),a.tobytes());self.assertNotEqual(result.tobytes(),b.tobytes())
        self.assertTrue(set(map(tuple,np.array(result).reshape(-1,4)))<=set(map(tuple,np.array(a).reshape(-1,4))))
        self.assertLessEqual(np.count_nonzero(np.array(result)[...,3]),np.count_nonzero(np.array(a)[...,3])*1.15)

    def test_duplicate_and_truncated_loop_seams(self):
        frames=[pose(x) for x in (0,1,2,3,4,3,2,1)]
        self.assertEqual(motion_qa(frames,manifest(8,loop=True))['status'],'PASS')
        for broken in [frames+[frames[0]],frames[:-2]]:
            q=motion_qa(broken,manifest(len(broken),loop=True))
            self.assertTrue(any(i['kind']=='loop_seam' for i in q['issues']))

    def test_hit_uses_visible_weapon_not_largest_trail(self):
        frames=[]
        for i in range(10):
            im=pose();d=ImageDraw.Draw(im);d.rectangle((40,30,45+(5 if i==5 else 0),31),fill='#9FE3FF')
            if i==6:d.rectangle((40,32,59,45),fill='#FF2BD6')
            frames.append(im)
        self.assertEqual(attack_contact(frames,['#9FE3FF'],[50,29,3,4]),5)


if __name__=='__main__':unittest.main()
