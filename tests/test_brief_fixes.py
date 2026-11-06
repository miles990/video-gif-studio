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
            rate=8000;duration=90;t=np.arange(rate*duration)/rate
            audio=np.zeros_like(t)
            for start in np.arange(0,duration,60/123):
                u=t-start;audio+=.2*np.sin(2*np.pi*70*u)*np.exp(-np.maximum(u,0)*45)*(u>=0)*(u<.12)
            p=Path(tmp)/'steady.wav'
            with wave.open(str(p),'wb') as f:
                f.setparams((1,2,rate,0,'NONE',''));f.writeframes((audio*32767).astype('<i2').tobytes())
            grid=brief.music_grid(p)
            self.assertIsNone(grid['drop_ms'])
            self.assertAlmostEqual(grid['beats_ms'][50],50*60000/123,delta=25)
            self.assertAlmostEqual(grid['beats_ms'][170],170*60000/123,delta=25)
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
        # Unlabelled footage is retained deterministically, never round-robin.
        self.assertEqual({s['image'] for s in b['shots']}, {'0.png'})
        logo=skeleton_board(brief.expand('Acme kettle; logo must appear last',project=[dict(path='kettle.png'),dict(path='logo.png',role='logo')]))
        self.assertEqual(logo['shots'][-1]['image'],'logo.png')
        self.assertTrue(all(s.get('image')!='logo.png' for s in logo['shots'][:-1]))
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

    def test_delta_quantities_roll_and_no_effect(self):
        from brief_edit import parse,apply_changes
        b=skeleton_board(brief.expand('coffee 5s',music={'downbeats_ms':[0,2000,4000]}))
        for s in b['shots']:s['motion']='static';s.pop('recipe',None)
        edit=parse('make 3 2x faster and 30 degrees clockwise',b)
        self.assertEqual(len(edit['questions']),1)
        with self.assertRaisesRegex(ValueError,'E_AMBIGUOUS'):apply_changes(b,edit)
        edit=parse('第三鏡快兩倍',b)
        self.assertEqual(edit['changes'][0]['magnitude'],2)
        self.assertIn(b['shots'][2]['id'],apply_changes(b,edit)['revision']['no_visible_effect'])
        for phrase,value in [('clockwise',30),('counter-clockwise',-30),('counterclockwise',-30),('逆時針',-30)]:
            edit=parse('make 3 30 degrees '+phrase,b)
            self.assertFalse(edit['questions']);self.assertEqual(edit['changes'][0]['direction']['axis'],'roll')
            self.assertEqual(apply_changes(b,edit)['shots'][2]['rotation_degrees'],value)

    def test_screenshot_matches_prior_render_without_metadata(self):
        import cv2,tempfile
        import numpy as np
        from brief_edit import parse
        with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as tmp:
            folder=Path(tmp);video=folder/'prior.avi';writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'MJPG'),30,(96,64))
            for i in range(90):
                frame=np.full((64,96,3),(i*2,20,70),dtype=np.uint8);cv2.circle(frame,(10+i%75,30),9,(220,230,240),-1);writer.write(frame)
            writer.release();cap=cv2.VideoCapture(str(video));cap.set(cv2.CAP_PROP_POS_FRAMES,62);ok,frame=cap.read();cap.release();self.assertTrue(ok)
            screenshot=folder/'screenshot.png';cv2.imwrite(str(screenshot),cv2.resize(frame,(192,128)))
            b=skeleton_board(brief.expand('coffee 3s'));b['render_source']=str(video)
            edit=parse('too dark',b,image=screenshot)
            self.assertFalse(edit['questions']);self.assertAlmostEqual(edit['changes'][0]['time'],62/30,delta=1/30)
            self.assertEqual(edit['changes'][0]['target']['shots'],[s['id'] for s in b['shots'] if s['start']<=62/30<s['end']])

    def test_windows_delivery_rename_retry_is_bounded(self):
        from unittest.mock import Mock,patch
        from fx_render import rename_delivery
        path=Mock();path.rename.side_effect=[PermissionError('locked'),PermissionError('locked'),Path('done')]
        with patch('fx_render.time.sleep') as sleep:
            self.assertEqual(rename_delivery(path,Path('done')),Path('done'));self.assertEqual(sleep.call_count,2)
        path.rename.side_effect=PermissionError('locked')
        with patch('fx_render.time.sleep'):
            with self.assertRaises(PermissionError):rename_delivery(path,Path('done'),attempts=2)

    def test_lint_aesthetic_routine_forks_and_boilerplate(self):
        from brief_lint import lint
        from copy import deepcopy
        b=brief.expand('coffee 5s')
        for aesthetic in ('vaporwave × Swiss','vaporwave, Swiss','vaporwaveSwiss','賽博龐克巴洛克'):
            bad=deepcopy(b);bad['aesthetic']=aesthetic
            self.assertIn('one_aesthetic',[f['rule'] for f in lint(bad)['findings']])
        for routine in ('5s','9:16','square'):
            bad=deepcopy(b);bad['forks']=[dict(choice_made=routine,alternative='paper')]
            self.assertIn('routine_fork',[f['rule'] for f in lint(bad)['findings']])
        b['forks']=[dict(choice_made='秒針轉為水紋',alternative='齒輪化為月亮')]
        self.assertNotIn('routine_fork',[f['rule'] for f in lint(b)['findings']])
        b['end_hold']=2;b['rule_break']=dict(rule='end_hold',why='for lint')
        self.assertEqual(next(f['severity'] for f in lint(b)['findings'] if f['rule']=='end_hold'),'error')
        self.assertIn('exemption_reason',[f['rule'] for f in lint(b)['findings']])

    def test_fingerprint_requires_720_and_detects_embedding(self):
        import cv2,tempfile
        import numpy as np
        from brief_guard import signature,audit
        from PIL import Image
        with self.assertRaisesRegex(ValueError,'E_FINGERPRINT_RESOLUTION'):signature(np.zeros((180,320,3),np.uint8))
        with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as tmp:
            root=Path(tmp);ref=root/'ref.png';other=root/'other.png'
            rng=np.random.default_rng(8);base=rng.integers(0,256,(720,960,3),dtype=np.uint8)
            for i in range(40):cv2.putText(base,str(i),(int(rng.integers(30,900)),int(rng.integers(30,690))),cv2.FONT_HERSHEY_SIMPLEX,1.2,(255,255,255),2)
            Image.fromarray(base).save(ref);Image.fromarray(rng.integers(0,256,base.shape,dtype=np.uint8)).save(other)
            self.assertFalse(audit(ref,[ref])['pass_nonembedding'])
            report=audit(other,[ref]);self.assertTrue(report['pass_nonembedding']);self.assertEqual(report['analysis_short_side'],720)
