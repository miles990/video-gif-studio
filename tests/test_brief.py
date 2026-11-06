"""S-130..136 deterministic and decoded scenarios; all generated media in .scratch.

BL-1..BL-5 are quoted from blank-page README (MIT; THIRD_PARTY.md).
These are authoring fixtures, not human before/after preference evidence.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import brief
from brief_lint import lint
from brief_refs import CassetteProvider,ReferenceFinder,ground,licence_status,contact_sheet
from brief_edit import parse,apply_changes
from brief_render import compile_plan,render_version,diff,preflight
from storyboard import validate,lint as board_lint
from taste_pick import factory

# These fixtures explicitly exercise unfinished previs, not authored proposals.
def skeleton_board(b,**kwargs):return brief.to_storyboard(b,allow_skeleton=True,**kwargs)

TOPICS=[
    '5 sec clip for a payments api: a request leaves the code and comes back as a payment confirmed. dark mode, kind of like stripe’s style',
    'quick 5 second twitter post: our design tool just hit 10,000 users',
    '5s looping background for a saas pricing page. it sits behind the plan cards so keep it subtle. soft frosted glass, like apple’s website',
    '5 second clip for a note-taking app launch. you type one search and results pop in from docs, slack and email',
    '5 second changelog clip for a calendar app. the messy old settings page snaps into clean grouped sections. clean and minimal, lots of white',
    '我咖啡店新菜單 10 秒直式，溫暖',
    'a 5 second launch video for my app',
    "5 second clip for my coffee shop's new menu, warm and cozy",
]
DELTAS=['第二拍慢一點、保留顏色','make the final pan 3x faster at top speed','把轉折提前到 drop，其他不動','拿掉最後的字卡','第三鏡往右推 30 度','make it faster']
GRID=dict(beats_ms=list(range(0,10000,500)),downbeats_ms=list(range(0,10000,2000)),drop_ms=6000)


class BriefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'.scratch').mkdir(exist_ok=True)
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'.scratch',prefix='brief-')
        cls.path=Path(cls.temp.name)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_twenty_mode_cases(self):
        cases=[(x,'brief') for x in TOPICS]+[(x,'delta') for x in DELTAS]+[
            ('同一個菜單，做 3 個不同的版本，轉折都不一樣','batch'),('create 4 variations of the menu reveal','batch'),
            ('在 3 秒的地方，菜單翻頁之後跳出價格標，6 秒前結束','sequence'),('at 7s, after the cup exits, add a steam wipe','sequence'),
            ('把 v3 匯出成 mp4 給 IG，檔名 cafe_menu_final','housekeeping'),('check the render','housekeeping')]
        self.assertEqual(len(cases),20)
        for text,expected in cases:
            with self.subTest(text=text):self.assertEqual(brief.classify(text,previous={'shots':[{'id':'shot-1'}]})[0],expected)
        self.assertEqual(brief.classify('第 5 格太暗',image='contact.png')[0],'image_feedback')

    def test_eight_briefs_determinism_lint_schema_and_md(self):
        for i,text in enumerate(TOPICS):
            with self.subTest(i=i):
                b=brief.expand(text,offline=True);self.assertEqual(b,brief.expand(text,offline=True));self.assertEqual(lint(b)['errors'],0,lint(b))
                self.assertEqual(len(b['refs']),8);self.assertEqual(sum(x['is_turn'] for x in b['beats']),1)
                self.assertIn(b['aesthetic'],b['prompt'].splitlines()[0])
                board=skeleton_board(b);validate(board);self.assertEqual(board_lint(board)['errors'],0)
                md=self.path/f'brief-{i}.md';md.write_text(brief.markdown(b),encoding='utf-8');self.assertEqual(lint(brief.read(md)),lint(b))
                try:
                    import jsonschema
                except ImportError:pass
                else:jsonschema.validate(b,brief.read(ROOT/'references/brief.schema.json'))
        self.assertEqual(brief.expand(TOPICS[5])['height'],1920)
        from brief_render import proxy_size
        self.assertEqual(proxy_size(skeleton_board(brief.expand(TOPICS[5]))),(180,320))

    def test_existing_transformation_is_only_turn(self):
        for i,verb in ((0,'comes back as'),(4,'snaps into')):
            b=brief.expand(TOPICS[i]);turn=next(x for x in b['beats'] if x['is_turn']);self.assertIn(verb,turn['text'])
            self.assertEqual(turn['perceived'],max(x['perceived'] for x in b['beats']))
            self.assertGreater(turn['t_end'],.32*b['duration'])

    def test_housekeeping_and_edits_never_acquire(self):
        provider=CassetteProvider({})
        for draft in ['check the render','把 v3 匯出成 mp4 給 IG','make it faster']:
            b=brief.expand(draft,provider=provider,previous={'shots':[{'id':'shot-1','motion':'static'}]});self.assertNotIn('aesthetic',b)
        self.assertEqual(provider.requests,[])

    def test_user_slots_first_and_web_only_gaps(self):
        cards=[dict(id=f'C{i}',description=t,path=f'/owned/{i}.png') for i,t in enumerate(['cup brown','menu paper','hand','window light orange','OPEN shop text'],1)]
        provider=CassetteProvider({})
        b=brief.expand(TOPICS[5],project=cards,taste=dict(defaults=dict(density=.5,recipe_family='soft_hit',color='warm')),provider=provider)
        self.assertEqual([r['source'] for r in b['refs'][:5]],['user']*5)
        self.assertEqual(len(provider.requests),3);self.assertTrue(all(r.get('origin_handle') for r in b['refs'][:5]))
        board=skeleton_board(b);self.assertTrue(all(s['recipe']['name'] in ('warm_memory','breathe','soft_hit') for s in board['shots']))

    def test_offline_and_network_failure_same_except_meta(self):
        class Blocked:
            def search(self,*args,**kwargs):raise OSError('NET-BLOCK')
        a=brief.expand(TOPICS[5],offline=True);b=brief.expand(TOPICS[5],provider=Blocked())
        a.pop('meta');meta=b.pop('meta');self.assertTrue(meta['offline']);self.assertIn('NET-BLOCK',meta['attempts'][0]['error']);self.assertEqual(a,b)

    def test_refstat_timing_and_contrasting_structures(self):
        b=brief.expand('coffee 10s',refstat=dict(target=dict(asl=1.25,cv=.35)));s=skeleton_board(b)['shots'];lengths=np.array([x['duration'] for x in s])
        self.assertAlmostEqual(lengths.mean(),1.25,delta=.25);self.assertAlmostEqual(lengths.std()/lengths.mean(),.35,delta=.15)
        from taste_director import treatment
        from taste_lint import transition_family
        for expanded in (False,True):
            rows=[]
            for core in ('sports hype 30s','Japanese fresh 30s','precision watch ad 30s'):
                board=skeleton_board(brief.expand(core,taste=factory())) if expanded else treatment(['missing.png'],30,core,factory(),experimental_structure=True)
                durations=np.array([s['end']-s['start'] for s in board['shots']]);families={transition_family(s['transition']) for s in board['shots'] if s['transition']!='cut'}
                recipes={s['recipe']['name'] for s in board['shots'] if s.get('recipe')}
                rows.append((len(durations),round(durations.mean(),2),round(durations.std()/durations.mean(),2),frozenset(families),frozenset(recipes)))
            for col in range(5):self.assertEqual(len({r[col] for r in rows}),3,(expanded,col,rows))

    def test_music_turn_and_boundaries(self):
        b=brief.expand(TOPICS[5],music=GRID);turn=next(x for x in b['beats'] if x['is_turn']);self.assertEqual(turn['t_start'],6)
        board=skeleton_board(b);self.assertEqual(next(s['start'] for s in board['shots'] if s['is_turn']),6)
        self.assertEqual(next(s['transition'] for s in board['shots'] if s['is_turn']),'cut')
        for beat in b['beats']:self.assertIn(beat['t_start']*1000,GRID['downbeats_ms'])
        b5=brief.expand('coffee 5s',music=dict(GRID,drop_ms=2000));self.assertEqual(next(x for x in b5['beats'] if x['is_turn'])['t_start'],2)

    def test_music_pcm_known_drop(self):
        for duration,drop in ((10,6),(5,2)):
            rate=8000;t=np.arange(duration*rate)/rate;rng=np.random.default_rng(7)
            audio=rng.normal(0,.012,len(t));audio[t>=drop]*=4
            for start in np.arange(0,duration,.5):
                u=t-start;audio+=.16*np.sin(2*np.pi*55*u)*np.exp(-np.maximum(u,0)*35)*(u>=0)*(u<.15)
            path=self.path/f'drop{duration}.wav'
            with wave.open(str(path),'wb') as f:f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
            grid=brief.music_grid(path);self.assertAlmostEqual(grid['drop_ms']/1000,drop,delta=1/30)
            self.assertEqual(grid['downbeats_ms'][:3],[0,2000,4000])

    def test_batch_sequence_and_unknown_mechanic(self):
        for draft in ('create 4 variations of the menu reveal','at 7s, after the cup exits, add a steam wipe'):
            b=brief.expand(draft);self.assertEqual(lint(b)['errors'],0,lint(b));skeleton_board(b)
        b=brief.expand('coffee 5s');next(x for x in b['beats'] if x['is_turn'])['mechanism']='peel'
        board=skeleton_board(b);self.assertIn('no stable implementation',board['warnings'][0])

    def test_lint_negative_and_boundary_controls(self):
        b=brief.expand('coffee 5s');turn=next(i for i,x in enumerate(b['beats']) if x['is_turn'])
        cases=[('one_aesthetic',lambda x:x.update(aesthetic='vaporwave and swiss style')),
               ('ref_no_use',lambda x:x['refs'][6].update(use='參考')),
               ('ref_unused',lambda x:[v.update(text=v['text'].replace('a4','unused')) for v in x['beats']]),
               ('one_ref_one_job',lambda x:x['refs'][0].update(role='look / motion')),
               ('no_turn',lambda x:[v.update(is_turn=False) for v in x['beats']]),
               ('hero_size',lambda x:x['beats'][turn].update(hero_height=.3)),
               ('min_text',lambda x:x['beats'][turn].update(min_text_px=18)),
               ('end_hold',lambda x:x.update(end_hold=1.4)),
               ('one_idea',lambda x:x['beats'][0].update(is_turn=True)),
               ('forks_max',lambda x:x.update(forks=[dict(choice_made='paper',alternative='glass')]*4)),
               ('routine_fork',lambda x:x.update(forks=[dict(choice_made='5 秒',alternative='10 秒')])),
               ('word_cap',lambda x:x.update(prompt='字'*400)),
               ('ref_provenance',lambda x:x['refs'][0].update(source='web')),
               ('licence',lambda x:x.update(assets=[dict(licence='CC-BY-NC-4.0')]))]
        for rule,mutate in cases:
            bad=deepcopy(b);mutate(bad)
            with self.subTest(rule=rule):self.assertIn(rule,[f['rule'] for f in lint(bad)['findings']])
        for count,severity in ((290,None),(330,'warning'),(400,'error')):
            data=deepcopy(b);data['prompt']='字'*count;rows=[f for f in lint(data)['findings'] if f['rule']=='word_cap'];self.assertEqual(rows[0]['severity'] if rows else None,severity)
        for hero in (.4,.45):
            data=deepcopy(b);data['beats'][turn]['hero_height']=hero;self.assertNotIn('hero_size',[f['rule'] for f in lint(data)['findings']])
        data=deepcopy(b);data.update(end_hold=1.4,rule_break=dict(rule='end_hold',why='Client requires logo recognition for this ending'))
        self.assertEqual(next(f['severity'] for f in lint(data)['findings'] if f['rule']=='end_hold'),'exempted')
        data['rule_break']=dict(rule='licence',why='A deliberately invalid attempted waiver');self.assertIn('exemption_not_allowed',[f['rule'] for f in lint(data)['findings']])

    def test_licences_and_renderer_rejection(self):
        for licence,expected in [('CC0','allowed'),('CC-BY-4.0','allowed'),('CC-BY-SA-4.0','share_alike_review'),('CC-BY-NC-4.0','blocked'),('CC-BY-ND-4.0','blocked'),('unknown','blocked'),('Sketchfab Standard','blocked')]:
            self.assertEqual(licence_status(dict(licence=licence,author='Artist',source_url='https://example.test/asset')),expected)
        from fx_render import validate_plan
        path=self.path/'bad-plan.json';brief.write(path,dict(segments=[dict(type='image',image='not-needed.png',duration_ms=1000)],assets=[dict(licence='CC-BY-NC')]))
        with self.assertRaisesRegex(ValueError,'E_LICENCE'):validate_plan(path)
        board=skeleton_board(brief.expand('coffee 5s'));board['reference_paths']=['hidden.png'];board['shots'][0]['image']='hidden.png'
        with self.assertRaisesRegex(ValueError,'E_REF_EMBED'):preflight(board)
        b=brief.expand('coffee 5s');b['structure']['recipes'].append('unknown_or_experimental')
        with self.assertRaisesRegex(ValueError,'E_STATUS'):skeleton_board(b)

    def test_delta_six_cases_and_keep(self):
        board=skeleton_board(brief.expand(TOPICS[5],music=GRID));board['shots'][-1]['motion']='pan';board['shots'][-1]['elements']=[dict(type='title')]
        a=parse(DELTAS[0],board);self.assertEqual(a['changes'][0]['target']['beat'],2);self.assertIn('color',a['changes'][0]['keep']);self.assertEqual(a['changes'][0]['magnitude'],.8)
        b=apply_changes(board,a);self.assertEqual(b['duration'],board['duration']);self.assertTrue(b['revision']['notes'])
        for before,after in zip(board['shots'],b['shots']):self.assertEqual(before['color_script'],after['color_script']);self.assertEqual(before['start'],after['start'])
        a=parse(DELTAS[1],board)['changes'][0];self.assertEqual(a['phase'],'top speed');self.assertEqual(a['magnitude'],3);self.assertEqual(a['target']['shots'],[board['shots'][-1]['id']])
        self.assertEqual(parse(DELTAS[2],board)['changes'][0]['magnitude'],6)
        self.assertEqual(parse(DELTAS[3],board)['changes'][0]['change'],'remove')
        a=parse(DELTAS[4],board)['changes'][0];self.assertEqual(a['direction'],dict(axis='yaw',sense='screen-right'));self.assertEqual(a['magnitude'],30)
        a=parse(DELTAS[5],board);self.assertEqual(len(a['questions']),1)
        with self.assertRaisesRegex(ValueError,'E_AMBIGUOUS'):apply_changes(board,a)

    def test_provider_port_records_bounded_download_and_media_detection(self):
        calls=[]
        def transport(op,url):
            calls.append((op,url))
            if op=='bytes':return (self.path/'preview.png').read_bytes()
            return dict(channels=[dict(slug='small',length=5,follower_count=99),dict(slug='quality',length=80,follower_count=8)])
        Image.new('RGB',(24,24),'red').save(self.path/'preview.png');finder=ReferenceFinder(transport)
        self.assertEqual(finder.channels('warm film')[0]['slug'],'quality')
        record=finder.download(dict(source_url='https://example.test/wrong.jpg',page_url='https://example.test/page',role='look',use='beat 1 surface texture',licence='unknown'),self.path/'download.jpg')
        self.assertTrue(record['path'].endswith('.png'));self.assertEqual(len(record['sha256']),64);self.assertTrue(record['retrieved_at'])
        finder.downloads=30
        with self.assertRaises(ValueError):finder.download(record,self.path/'over.png')

    def test_cli_json_error_and_prompt_roundtrip(self):
        run=subprocess.run([sys.executable,str(ROOT/'scripts/brief.py'),'--draft',TOPICS[5],'--offline','--json'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(run.stdout)['mode'],'brief')
        run=subprocess.run([sys.executable,str(ROOT/'scripts/brief.py'),'lint','does-not-exist.json','--json'],capture_output=True,text=True,encoding='utf-8')
        self.assertNotEqual(run.returncode,0);self.assertIn('suggestion',json.loads(run.stdout)['error']);self.assertNotIn('Traceback',run.stderr)
        run=subprocess.run([sys.executable,str(ROOT/'scripts/brief.py'),'--unknown','--json'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(json.loads(run.stdout)['error']['code'],'E_ARGUMENT');self.assertNotEqual(run.returncode,0)


class BriefRenderScenarios(unittest.TestCase):
    def setUp(self):
        (ROOT/'.scratch').mkdir(exist_ok=True);self.temp=tempfile.TemporaryDirectory(dir=ROOT/'.scratch',prefix='brief-render-');self.path=Path(self.temp.name)
        import cv2
        self.threads=cv2.getNumThreads();cv2.setNumThreads(1)
    def tearDown(self):
        import cv2
        cv2.setNumThreads(self.threads);self.temp.cleanup()

    def test_plan_roundtrip_and_affected_shot_cache(self):
        b=skeleton_board(brief.expand('coffee 3s'))
        # Low-cost decoded cache fixture; the stable recipe route is tested below.
        for s in b['shots']:s.pop('recipe');s['motion']='pan';s['transition']='crossfade'
        first=render_version(b,self.path/'v1',size=(96,64),formats=('png',))
        revised=apply_changes(b,parse('第二拍慢一點、保留顏色',b));second=render_version(revised,self.path/'v2',self.path/'v1',size=(96,64),formats=('png',))
        affected={s['id'] for s in b['shots'] if s['beat']==2}
        self.assertEqual(set(second['rerendered_shots']),affected);self.assertEqual(set(diff(first,second)['shots']),affected)
        for old,new in zip(first['shots'],second['shots']):
            if old['id'] not in affected:self.assertEqual(old['sha256'],new['sha256'])
        self.assertGreater(revised['duration'],b['duration'])

    def test_stable_plan_validation_and_turn_time(self):
        from fx_render import validate_plan
        for i,text in enumerate(TOPICS):
            b=skeleton_board(brief.expand(text));out=self.path/f'plan-{i}';plan=compile_plan(b,out,size=(64,64));validate_plan(out/'plan.json')
            self.assertFalse(plan['experimental']);self.assertFalse(any('reference' in str(s) for s in plan['segments']))

    def test_ref_fingerprints_positive_negative(self):
        from brief_guard import signature,matches
        import cv2
        rng=np.random.default_rng(42);base=rng.integers(0,256,(360,480,3),dtype=np.uint8)
        # Structured texture gives ORB stable corners under resampling.
        for i in range(40):cv2.putText(base,str(i),(int(rng.integers(20,400)),int(rng.integers(20,340))),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2)
        overlay=np.full_like(base,70);overlay[50:194,50:242]=cv2.resize(base,(192,144))
        hsv=cv2.cvtColor(base,cv2.COLOR_BGR2HSV);hsv[:,:,1]=np.clip(hsv[:,:,1].astype(float)*1.2,0,255).astype(np.uint8);graded=cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR)
        for variant in (base,overlay,graded):self.assertTrue(matches(signature(base),signature(variant))['embedded'])
        other=rng.integers(0,256,base.shape,dtype=np.uint8);self.assertFalse(matches(signature(base),signature(other))['embedded'])


class BriefBenchTests(unittest.TestCase):
    def test_registration_and_honest_two_axis_conclusion(self):
        from brief_bench import register,score,wilson
        topics=[dict(id=str(i),draft=x,held_out=i>=6) for i,x in enumerate(TOPICS)]
        with tempfile.TemporaryDirectory(dir=ROOT/'.scratch') as tmp:
            data=register(topics,Path(tmp)/'registration.json');self.assertEqual(data['status'],'registered_uncommitted')
            with self.assertRaises(FileExistsError):register(topics,Path(tmp)/'registration.json')
        key=dict(registration_status='committed',pairs=[dict(id=str(i),role='topic',left_arm='A',panel='B',technical={}) for i in range(6)]+[
            dict(id='p',role='positive_control',left_arm='A'),dict(id='n',role='negative_control',left_arm='A')])
        votes=[dict(id=p['id'],choice='tie' if p['id']=='n' else 'left') for p in key['pairs']]
        self.assertEqual(score(key,votes)['claim'],'未證明更好')
        for p in key['pairs'][:6]:p['technical']=dict(A_auto=True,B_auto=True,panel_no_regression=True)
        self.assertEqual(score(key,votes)['claim'],'擴寫更好');self.assertGreater(wilson(6,6)[0],.5)
        with self.assertRaises(ValueError):score(key,votes+votes[:1])


if __name__=='__main__':unittest.main()
