import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from PIL import Image
from game_demo import isolate_single_subject

class SubjectFixTests(unittest.TestCase):
    def test_wide_weapon_is_not_erased_as_ground_rule(self):
        from game_character import prepare_subject
        from PIL import ImageDraw
        im=Image.new('RGBA',(100,100));d=ImageDraw.Draw(im)
        d.rectangle((40,10,60,35),fill='orange');d.rectangle((48,35,52,45),fill='orange')
        d.rectangle((25,41,75,85),fill='brown');d.line((0,40,99,40),fill='grey')
        subject,_=prepare_subject(im)
        self.assertEqual(subject.getpixel((50,20))[3],255)
        self.assertEqual(subject.getpixel((50,60))[3],255)

    def test_reordered_sheet_uses_reference_matches(self):
        import tempfile
        from game_character import prepare_subject
        from PIL import ImageDraw
        with tempfile.TemporaryDirectory(dir='.scratch') as folder:
            refs=[];cells=[]
            for i,color in enumerate(('red','green','blue','orange')):
                im=Image.new('RGBA',(80,100));d=ImageDraw.Draw(im);d.rectangle((20,10,60,90),fill=color)
                for j in range(i+1):d.rectangle((22+j*5,18+j*9,27+j*5,25+j*9),fill='white')
                cells.append(im)
                if i<3:
                    p=Path(folder)/f'{i}.png';im.save(p);refs.append(p)
            grid=Image.new('RGBA',(320,100))
            for j,i in enumerate((0,3,1,2)):grid.paste(cells[i],(j*80,0))
            selected,report=prepare_subject(grid,'three_quarter',refs)
            self.assertEqual(report['selected_index'],1)

    def test_live_wolf_turnaround_selects_requested_column(self):
        im=Image.open('tests/fixtures/live-s14/wolf-front.png').convert('RGBA')
        from game_character import prepare_subject
        front,report=prepare_subject(im,'front')
        side,other=prepare_subject(im,'side')
        self.assertEqual(report['subject_count'],4)
        self.assertEqual(report['selected_index'],0)
        self.assertEqual(other['selected_index'],1)
        self.assertNotEqual(front.tobytes(),side.tobytes())
        self.assertEqual(prepare_subject(side,'side')[1]['subject_count'],1)
        self.assertLess(front.getbbox()[2]-front.getbbox()[0],im.width//2)
