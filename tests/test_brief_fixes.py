from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import brief

# These fixtures explicitly exercise unfinished previs, not authored proposals.
def skeleton_board(b,**kwargs):return brief.to_storyboard(b,allow_skeleton=True,**kwargs)

class FixTests(unittest.TestCase):
    def test_modes_need_edit_context(self):
        for text in ('make 3 faster','fix shot 2','an export product launch','第三鏡往右推 30 度','咖啡新品，也做幾個版本嗎，不急'):
            self.assertEqual(brief.classify(text)[0],'brief',text)
        old={'shots':[{'id':'shot-1'}]}
        self.assertEqual(brief.classify('fix shot 2',previous=old)[0],'delta')
        self.assertEqual(brief.classify('export mp4',previous=old)[0],'housekeeping')
        self.assertEqual(brief.classify('create 4 variations')[0],'batch')

    def test_no_drop_and_fractional_tempo(self):
        import numpy as np
        import wave,tempfile
        with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as tmp:
            rate=8000;duration=30;t=np.arange(rate*duration)/rate
            audio=np.zeros_like(t)
            for start in np.arange(0,duration,60/123):
                u=t-start;audio+=.2*np.sin(2*np.pi*70*u)*np.exp(-np.maximum(u,0)*45)*(u>=0)*(u<.12)
            p=Path(tmp)/'steady.wav'
            with wave.open(str(p),'wb') as f:
                f.setparams((1,2,rate,0,'NONE',''));f.writeframes((audio*32767).astype('<i2').tobytes())
            grid=brief.music_grid(p)
            self.assertIsNone(grid['drop_ms'])
            self.assertAlmostEqual(grid['beats_ms'][50],50*60000/123,delta=25)
            b=brief.expand('coffee 10s',music=grid)
            self.assertIn('No drop detected; turn anchored to bar',b['prompt'])
            self.assertTrue(all(s['sound']['section']!='drop' for s in skeleton_board(b)['shots']))
        self.assertTrue(all(s['sound']['section']=='silent' for s in skeleton_board(brief.expand('coffee 5s'))['shots']))

    def test_transformations_and_constraints_survive(self):
        from brief_render import compile_plan
        import tempfile
        for draft,verb in [('玉山茶罐碎成粉重新聚成 logo，logo 一定要最後，不要人臉','聚成'),('玉山茶罐黑白變彩色，必須使用玉山茶罐','變彩色'),('Acme kettle dissolves into steam; no faces; logo must appear last','dissolves into')]:
            b=brief.expand(draft)
            turns=[v for v in b['beats'] if v['is_turn']]
            self.assertEqual(len(turns),1);self.assertIn(verb,turns[0]['text'])
            self.assertNotIn('the subject',b['prompt'])
            self.assertNotIn('larger working assembly',b['prompt'])
            board=skeleton_board(b)
            self.assertEqual(board['hard_constraints'],b['hard_constraints'])
            self.assertTrue(all(s['hard_constraints']==b['hard_constraints'] for s in board['shots']))
            with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as tmp:
                plan=compile_plan(board,Path(tmp),size=(64,64))
                self.assertEqual(plan['review']['hard_constraints'],b['hard_constraints'])

    def test_skeleton_guard_and_constraint_lint(self):
        from brief_lint import lint
        b=brief.expand('Acme kettle; must show logo last; no faces',content={'duration':5})
        self.assertEqual(b['status'],'skeleton');self.assertTrue(b['forks'])
        with self.assertRaisesRegex(ValueError,'E_SKELETON'):brief.to_storyboard(b)
        brief.to_storyboard(b,allow_skeleton=True)
        b['hard_constraints']=[]
        self.assertIn('hard_constraint',[f['rule'] for f in lint(b)['findings']])
        authored=brief.expand('Acme kettle',content={'turn':'the lid opens to reveal the brewing chamber'})
        self.assertEqual(authored['status'],'proposal');brief.to_storyboard(authored)

    def test_distinct_references_authored_uses_and_sheets(self):
        import tempfile
        from PIL import Image
        from brief_lint import lint
        with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as tmp:
            library=[]
            for i in range(5):
                p=Path(tmp)/f'{i}.png';Image.new('RGB',(64,64),(30*i,20,70)).save(p)
                library.append(dict(path=str(p),aesthetic_tag='obsidian macro atelier',vetted=True))
            b=brief.expand('precision watch',library=library,content={'ref_uses':{'a3':'beat 1: polished obsidian specular edges'}})
            self.assertEqual(len({r['path'] for r in b['refs'][:5]}),5)
            self.assertEqual(b['refs'][2]['use'],'beat 1: polished obsidian specular edges')
            self.assertTrue(Path(b['contact_sheets']).is_file())
            self.assertIn('ref_missing',[f['rule'] for f in lint(b)['findings']])
            self.assertNotIn('paper grain',b['prompt'])

    def test_framing_rotation_and_stable_opt_in(self):
        import numpy as np
        from animatic import framed
        from taste_director import treatment,stable_treatment
        from taste_pick import factory
        frame=np.random.default_rng(19).integers(0,256,(180,240,4),dtype=np.uint8)
        images=[framed(frame,dict(size=s,apply_framing=True),(96,64)) for s in ('WS','MS','CU','ECU')]
        for i in range(4):
            for j in range(i):self.assertGreater(np.abs(images[i].astype(float)-images[j]).mean(),20)
        self.assertTrue(np.array_equal(framed(frame,dict(size='WS'),(96,64)),framed(frame,dict(size='ECU'),(96,64))))
        for core in ('sports hype','meditation sleep','precision watch'):
            self.assertEqual(treatment(['a.png'],10,core,factory()),stable_treatment(['a.png'],10,core,factory()))
        b=skeleton_board(brief.expand('sports hype 10s',project=[dict(path=f'{i}.png') for i in range(3)]))
        self.assertEqual([s['image'] for s in b['shots'][:6]],['0.png','1.png','2.png']*2)
        for genre in ('ASMR','sleep','meditation'):
            board=skeleton_board(brief.expand(genre+' 10s'))
            self.assertEqual(board['editorial_structure']['profile'],'calm')
            self.assertTrue(all(s['recipe']['name']=='breathe' for s in board['shots']))
            self.assertEqual(len({p[1] for p in board['design_curve']}),1)

    def test_six_genres_have_distinct_rendered_sheets(self):
        import tempfile,json
        import numpy as np
        import cv2
        from PIL import Image
        from brief_render import render_version
        from brief_refs import contact_sheet
        folder=Path(tempfile.mkdtemp(dir=ROOT/'.scratch',prefix='s11-fix-genres-'))
        old_threads=cv2.getNumThreads();cv2.setNumThreads(1)
        try:
            yy,xx=np.indices((120,180));cards=[]
            for i in range(3):
                pixels=np.stack(((xx*3+i*40)%256,(yy*4+i*60)%256,((xx+yy)*2+i*20)%256),axis=-1).astype('uint8')
                p=folder/f'asset-{i}.png';Image.fromarray(pixels).save(p);cards.append(dict(path=str(p)))
            structures=[];samples=[];records=[]
            for i,genre in enumerate(('sports hype','Japanese fresh','precision watch','warm coffee','graphic typography','ASMR meditation')):
                board=skeleton_board(brief.expand(genre+' 4s',project=cards))
                structures.append(tuple((s['size'],s['duration'],s['recipe']['name'],s['motion']) for s in board['shots']))
                render_version(board,folder/str(i),size=(96,64),formats=('mp4',))
                movie=next((folder/str(i)/'render').glob('*.mp4'))
                meta=contact_sheet(movie,folder/f'{i}-sheet.png');cap=cv2.VideoCapture(str(movie));frames=[]
                for t in meta['frames_at_s']:
                    cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,f=cap.read();self.assertTrue(ok);frames.append(f.astype(float))
                cap.release();samples.append(np.array(frames));records.append(dict(genre=genre,sheet=f'{i}-sheet.png'))
            self.assertEqual(len(set(structures)),6)
            differences=[dict(a=i,b=j,mean_abs=float(np.abs(samples[i]-samples[j]).mean())) for i in range(6) for j in range(i)]
            self.assertTrue(all(v['mean_abs']>1 for v in differences),differences)
            (folder/'evidence.json').write_text(json.dumps(dict(genres=records,frame_differences=differences),indent=2),encoding='utf-8')
        finally:cv2.setNumThreads(old_threads)
