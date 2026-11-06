"""Review round 2: game assets, authored intent and decoded evidence."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import brief
from brief_lint import lint
from brief_edit import parse, apply_changes


class TransformationTests(unittest.TestCase):
    def test_authored_turn_is_never_replaced(self):
        draft = '5 秒，火焰精靈碎成星屑再聚成鳳凰'
        text = '火焰精靈先碎成明亮星屑，沿螺旋聚成鳳凰，翅膀展開'
        b = brief.expand(draft, content={'turn': text})
        turn = next(v for v in b['beats'] if v['is_turn'])
        self.assertTrue(turn['text'].startswith(text))
        authored = deepcopy(b['beats'])
        authored[-1]['shot_durations'] = [.1, .2, .7]
        b = brief.expand(draft, content={'beats': authored})
        self.assertEqual(b['beats'], authored)
        board = brief.to_storyboard(b)
        self.assertEqual(len([s for s in board['shots'] if s['beat'] == turn['id']]), 1)

    def test_result_complements_and_timing(self):
        for draft in ('5 秒，符文排成龍形', '5s slime melts into a crystal',
                      'runes weave into a dragon', '星屑旋成法陣'):
            with self.subTest(draft=draft):
                b = brief.expand(draft)
                turn = next(v for v in b['beats'] if v['is_turn'])
                self.assertIsNotNone(brief.transformation(draft))
                self.assertNotRegex(turn['text'], r'5\s*(?:秒|s)')
                bad = deepcopy(b)
                next(v for v in bad['beats'] if v['is_turn'])['text'] = 'camera pulls out to reveal a sword'
                self.assertIn('transformation_preserved', [f['rule'] for f in lint(bad)['findings']])
        self.assertIsNone(brief.transformation('walk into the dungeon'))
        b=brief.expand('5 秒，火焰精靈展示')
        self.assertNotRegex(next(v for v in b['beats'] if v['is_turn'])['text'],r'5\s*秒')


class DeltaTests(unittest.TestCase):
    def board(self):
        return brief.to_storyboard(brief.expand('game hero reveal 5s'), allow_skeleton=True)

    def test_previous_directional_quantities(self):
        b = self.board()
        b['shots'][0].update(direction='left-to-right', rotation_degrees=30)
        edit = parse('shot 1 other way', b)
        self.assertEqual(len(edit['questions']), 1)
        self.assertIn('right-to-left', edit['questions'][0])
        self.assertIn('counter-clockwise', edit['questions'][0])
        b['shots'][0].pop('rotation_degrees')
        edit = parse('shot 1 other way', b)
        self.assertFalse(edit['questions'])
        self.assertEqual(apply_changes(b, edit)['shots'][0]['direction'], 'right-to-left')
        b['shots'][0].update(direction='neutral',action='knight turns 30 degrees clockwise; animation speed 2x')
        edit=parse('shot 1 other way',b)
        self.assertEqual(len(edit['questions']),1)
        self.assertIn('counter-clockwise',edit['questions'][0])
        self.assertIn('0.5',edit['questions'][0])

    def test_speed_grammar_and_explicit_pan(self):
        b = self.board()
        for words, speed in [('一半', .5), ('half', .5), ('half speed', .5),
                             ('twice', 2), ('兩倍', 2), ('快兩倍', 2), ('2x slower', .5)]:
            edit = parse('shot 1 '+words, b)
            self.assertFalse(edit['questions'], edit)
            self.assertEqual(edit['changes'][0]['magnitude'], speed)
            self.assertEqual(edit['changes'][0]['direction']['sense'], 'slower' if speed < 1 else 'faster')
        self.assertEqual(len(parse('shot 1 more magical', b)['questions']), 1)
        self.assertEqual(len(parse('shot 1 rotate some degrees', b)['questions']),1)
        edit = parse('shot 1 pan 改由右到左', b)
        self.assertFalse(edit['questions'])
        self.assertEqual(apply_changes(b, edit)['shots'][0]['direction'], 'right-to-left')

    def test_dark_sheet_without_frame_number(self):
        import tempfile, cv2
        import numpy as np
        from brief_refs import contact_sheet
        with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as tmp:
            source=Path(tmp)/'sprite.avi'
            out=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'MJPG'),10,(96,64))
            for i in range(50):out.write(np.full((64,96,3),20 if i<10 else 180,np.uint8))
            out.release()
            sheet=Path(tmp)/'sheet.png';contact_sheet(source,sheet)
            b=self.board()
            edit=parse('太暗',b,image=sheet)
            self.assertFalse(edit['questions'],edit)
            self.assertTrue(edit['changes'])
            self.assertTrue(all(c['change']=='brightness' and c['quantified']['measured_y']<80 for c in edit['changes']))
            self.assertEqual({s for c in edit['changes'] for s in c['target']['shots']}, {b['shots'][0]['id']})


class FootageTests(unittest.TestCase):
    def test_content_assignment_beats_file_order(self):
        cards=[dict(path='explosion.png',description='fire explosion VFX'),
               dict(path='hero.png',description='knight hero',role='hero'),
               dict(path='shield.png',description='shield item icon')]
        b=brief.expand('knight hero game trailer 5s',project=cards)
        for beat in b['beats']:beat['text']='knight hero reveals a shield item icon '+ ' '.join(beat['refs'])
        board=brief.to_storyboard(b,allow_skeleton=True)
        self.assertIn('hero.png',[s.get('image') for s in board['shots']])
        self.assertNotIn('explosion.png',[s.get('image') for s in board['shots']])
        b['beats'][-1]['text']='fire explosion reveals sparks '+ ' '.join(b['beats'][-1]['refs'])
        board=brief.to_storyboard(b,allow_skeleton=True)
        self.assertEqual(board['shots'][-1]['image'],'explosion.png')

    def test_six_genres_decoded_contact_sheets_include_hero(self):
        import tempfile,json,cv2
        import numpy as np
        from PIL import Image,ImageDraw
        from brief_render import render_version
        from brief_refs import contact_sheet
        folder=Path(tempfile.mkdtemp(dir=ROOT/'.scratch',prefix='round2-genres-'))
        hero=folder/'knight-hero.png'
        # A recognizable generated game fixture: helmet, armor, shield and sword.
        sprite=Image.new('RGB',(45,30),(21,29,48));draw=ImageDraw.Draw(sprite)
        for x in range(0,45,5):draw.line((x,0,x,29),fill=(36,46,68))
        draw.rectangle((18,4,26,11),fill=(180,210,230));draw.rectangle((19,7,25,8),fill=(10,20,30))
        draw.rectangle((17,12,27,21),fill=(40,185,190));draw.rectangle((17,22,20,27),fill=(160,185,210))
        draw.rectangle((24,22,27,27),fill=(160,185,210));draw.rectangle((11,13,16,22),fill=(225,165,40))
        draw.rectangle((31,6,32,20),fill=(230,240,245));draw.line((29,18,34,18),fill=(225,165,40))
        sprite.resize((180,120),Image.Resampling.NEAREST).save(hero)
        cards=[dict(path=str(hero),role='hero',description='knight hero sprite')]
        genres=['horror','game trailer','VFX showcase','icon set','ASMR meditation','graphic typography']
        samples=[];records=[];profiles=[]
        old=cv2.getNumThreads();cv2.setNumThreads(1)
        try:
            for i,genre in enumerate(genres):
                b=brief.expand(genre+' knight 3s',project=cards)
                # Compare editorial treatments only; asset routing has separate
                # tests and must never pretend that this video is an icon set.
                b.pop('asset_spec',None)
                if genre=='icon set':
                    b['beats'][-1]['is_turn']=True
                    b['beats'][-1]['text']='reveal the knight icons ('+', '.join(b['beats'][-1]['refs'])+')'
                board=brief.to_storyboard(b,allow_skeleton=True)
                self.assertIn(str(hero),[s.get('image') for s in board['shots']])
                profiles.append(board['editorial_structure']['profile'])
                render_version(board,folder/str(i),size=(96,64),formats=('mp4',))
                movie=next((folder/str(i)/'render').glob('*.mp4'))
                sheet=folder/f'{i}-sheet.png';meta=contact_sheet(movie,sheet)
                cap=cv2.VideoCapture(str(movie));frames=[]
                for t in meta['frames_at_s']:
                    cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,frame=cap.read();self.assertTrue(ok);frames.append(frame.astype(float))
                cap.release();samples.append(np.array(frames));records.append(dict(genre=genre,sheet=str(sheet)))
            self.assertEqual(len(set(profiles)),6)
            differences=[dict(a=genres[i],b=genres[j],mean_abs=float(np.abs(samples[i]-samples[j]).mean())) for i in range(6) for j in range(i)]
            self.assertTrue(all(d['mean_abs']>1 for d in differences),differences)
            (folder/'evidence.json').write_text(json.dumps(dict(genres=records,frame_differences=differences),indent=2),encoding='utf-8')
        finally:cv2.setNumThreads(old)


class AssetRoutingTests(unittest.TestCase):
    def test_sprite_spec_and_pending_route(self):
        from brief_render import compile_plan,render_version
        import tempfile
        b=brief.expand('pixel art knight 64×64 sprite sheet, 8 frames per state, idle attack run, transparent background')
        spec=b.get('asset_spec',{})
        self.assertEqual(spec.get('size'),[64,64])
        self.assertEqual(spec.get('kind'),'sprite_sheet')
        self.assertEqual(spec.get('frame_count'),8)
        self.assertEqual(spec.get('states'),['idle','attack','run'])
        self.assertTrue(spec.get('transparent'))
        self.assertIn('pixel art',b['aesthetic'])
        self.assertIn('pixel art',brief.expand('pixel art knight reveal')['aesthetic'])
        self.assertIn('asset pipeline pending',b['prompt'])
        board=brief.to_storyboard(b)
        self.assertEqual(board['asset_spec'],spec)
        with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as tmp:
            for fn in (compile_plan,render_version):
                result=fn(board,Path(tmp)/fn.__name__)
                self.assertEqual(result['status'],'asset pipeline pending')
                self.assertEqual(result['asset_spec'],spec)

    def test_icon_sets_do_not_need_a_turn(self):
        b=brief.expand('12 item icons, icon set, 64x64 PNG, pixel art, transparent background')
        self.assertEqual(b.get('asset_spec',{}).get('kind'),'icon_set')
        self.assertEqual(b['asset_spec']['count'],12)
        self.assertFalse(any(v['is_turn'] for v in b['beats']))
        self.assertFalse({'no_turn','turn_reference'} & {f['rule'] for f in lint(b)['findings']})
        self.assertEqual(lint(b)['errors'],0,lint(b))
