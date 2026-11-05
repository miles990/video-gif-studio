"""P1b regressions: timed-word identity, raster evidence and manifest-aware QA."""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import captions
from delivery import settings
from fx.effects.camera import MOVES, motion
from fx_render import render, validate_plan
from qa_media import qa, camera_event_times, rhythm_cuts, analyse_picture
from sfx import events_from_plan


def mixed_words():
    return [dict(text=text, start_ms=37+i*240, end_ms=37+(i+1)*240)
            for i, text in enumerate(('「今天', ' Ship', ' 了', ' v2.0，', ' 共', ' 1,234', ' 位使用者', ' 👍🏽」'))]


def camera_clip(root):
    """Real named effects, encoded and decoded; media stays in the OS temp dir."""
    yy, xx = np.indices((256, 144))
    plate = np.empty((256, 144, 4), np.uint8)
    plate[..., :3] = np.where(((xx//13+yy//17) % 2)[..., None], [210, 160, 80], [40, 80, 140])
    plate[..., 3] = 255
    Image.fromarray(plate).save(root/'a.png')
    plate[..., :3] = 255-plate[..., :3]
    Image.fromarray(plate).save(root/'b.png')
    plan = dict(experimental=True, fps=30, segments=[
        dict(type='still', image='a.png', duration_ms=2000),
        dict(type='still', image='b.png', duration_ms=2000)], effects=[
        dict(move='crash_in', start_ms=300, end_ms=600),
        dict(move='punch', start_ms=800, end_ms=1100, duration_ms=300),
        dict(move='crash_out', start_ms=2300, end_ms=2900),
        dict(move='whip', start_ms=3300, end_ms=3460)])
    path=root/'plan.json';path.write_text(json.dumps(plan))
    render(path, root/'render', ('mp4',), fps=30)
    manifest=root/'render/manifest.json'
    timing=json.loads(manifest.read_text());timing['downbeats_ms']=[0,2000]
    manifest.write_text(json.dumps(timing))
    movie=next((root/'render').glob('*.mp4'))
    return qa(movie, root/'qa', timeline=manifest)


class CaptionIntegrityTests(unittest.TestCase):
    def prepare(self, words, preset='pop', **style):
        return captions.prepare(dict(words=words, language='zh',
            style=dict(preset=preset, **style)), Path('.'), True)

    def test_atomic_words_survive_logical_and_pixel_wrap(self):
        for limit in (3, 8, 40):
            data=self.prepare(mixed_words(), words_per_line=limit)
            cfg=settings((540,960), platform='tiktok')
            renderer=captions.CaptionRenderer(data,cfg['size'],cfg['safe_zone'])
            for lines in (data['lines'],renderer.lines):
                words=[w for line in lines for w in line['words']]
                self.assertEqual([w['word_id'] for w in words],list(range(8)))
                self.assertEqual([w['text'] for w in words],[w['text'].strip() for w in mixed_words()])
                for line in lines:
                    self.assertEqual(line['start_ms'],min(w['start_ms'] for w in line['words']))
                    self.assertEqual(line['end_ms'],max(w['end_ms'] for w in line['words']))
                    self.assertLess(line['start_ms'],line['end_ms'])
                    for c in line['chars']:
                        self.assertEqual(c['word_start_ms'],mixed_words()[c['word_id']]['start_ms'])

    def test_mixed_and_live_words_visible_within_one_frame_all_presets(self):
        fixtures=Path(__file__).parent/'fixtures/live'
        corpora=[mixed_words()]+[json.loads((fixtures/f'whisper-raw-{lang}.json').read_text(encoding='utf-8'))['words'] for lang in ('en','zh')]
        cfg=settings((270,480),platform='tiktok');blank=Image.new('RGBA',cfg['size'])
        original=captions.draw_grapheme
        for corpus in corpora:
            for preset in captions.PRESETS:
                data=self.prepare(corpus,preset,words_per_line=5)
                renderer=captions.CaptionRenderer(data,cfg['size'],cfg['safe_zone'])
                self.assertFalse(data['dropped_codepoints'])
                for word in data['words']:
                    first=math.ceil(word['start_ms']*30/1000-1e-9)*1000/30
                    self.assertLessEqual(first-word['start_ms'],1000/30+1e-6)
                    drawn=[]
                    def record(draw,xy,text,*args,**kwargs):
                        drawn.append(text)
                        return original(draw,xy,text,*args,**kwargs)
                    with patch.object(captions,'draw_grapheme',record):
                        raster=renderer.overlay(blank,first)
                    self.assertIsNotNone(raster.getbbox())
                    # Every grapheme is actually drawn at the first eligible frame.
                    for cluster in captions.graphemes(word['text']):
                        self.assertIn(cluster,drawn,(preset,word,first))
                    # Remove only this word's ink, retaining its metrics, current
                    # highlight state and animation. Its pixels must contribute.
                    count=0;cutoff=len(drawn)-2*len(captions.graphemes(word['text']))
                    def without_current(draw,xy,text,*args,**kwargs):
                        nonlocal count
                        count+=1
                        if count<=cutoff:return original(draw,xy,text,*args,**kwargs)
                    with patch.object(captions,'draw_grapheme',without_current):
                        without=renderer.overlay(blank,first)
                    self.assertTrue(np.any(np.asarray(raster)!=np.asarray(without)),(preset,word,first))

    def test_subframe_word_gets_one_frame_without_changing_export(self):
        words=[dict(text='早',start_ms=1,end_ms=2),dict(text='晚',start_ms=34,end_ms=35)]
        cfg=settings((270,480));data=self.prepare(words,words_per_line=1)
        r=captions.CaptionRenderer(data,cfg['size'],cfg['safe_zone'])
        for word in words:
            t=math.ceil(word['start_ms']*30/1000)*1000/30
            self.assertIsNotNone(r.overlay(Image.new('RGBA',cfg['size']),t).getbbox())
        self.assertEqual(data['words'],words)

    def test_whitespace_punctuation_and_numeric_keywords_exports(self):
        words=[dict(text='  今天  ',start_ms=0,end_ms=200),
               dict(text=' Ship ',start_ms=200,end_ms=400),
               dict(text=' 了 ',start_ms=400,end_ms=600),
               dict(text='v2.0, 1,234! 3.14?:;.',start_ms=600,end_ms=1500)]
        data=self.prepare(words,words_per_line=40)
        self.assertEqual(data['words'][-1]['text'],'v2.0， 1,234！ 3.14？：；。')
        self.assertEqual(data['keywords'],['v2.0','1,234','3.14'])
        self.assertEqual(data['lines'][0]['text'],'今天 Ship 了 v2.0， 1,234！ 3.14？：；。')
        highlighted=''.join(c['char'] for line in data['lines'] for c in line['chars'] if c['highlight'])
        self.assertEqual(highlighted,'v2.01,2343.14')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'captions.srt';captions.export_srt(words,path)
            for line in path.read_text(encoding='utf-8').splitlines():self.assertEqual(line,line.strip())
        self.assertTrue(all(w['text']==w['text'].strip() for w in json.loads(json.dumps(data))['words']))
        with self.assertWarns(UserWarning):
            dropped=self.prepare([dict(text='Hi \U0010ffff',start_ms=0,end_ms=100),dict(text='v2.0',start_ms=100,end_ms=500)])
        for line in dropped['lines']:
            self.assertEqual(line['text'],''.join(c['char'] for c in line['chars']))
        self.assertEqual(''.join(c['char'] for line in dropped['lines'] for c in line['chars'] if c['highlight']),'v2.0')

    def test_traditional_also_normalizes_punctuation_without_language(self):
        with patch.object(captions,'traditional_words',side_effect=lambda words:words):
            data=captions.prepare(dict(words=[dict(text=' 好,',start_ms=0,end_ms=200)],traditional=True),Path('.'),True)
        self.assertEqual(data['words'][0]['text'],'好，')

    def test_pop_previous_word_pixels_fixed_and_colors_distinct(self):
        words=[dict(text='KEEP',start_ms=0,end_ms=500),dict(text='NOW',start_ms=500,end_ms=1000)]
        data=self.prepare(words,words_per_line=20)
        data['keywords']=['KEEP']
        for c in data['lines'][0]['chars']:c['highlight']=c['word_id']==0
        for w in data['lines'][0]['words']:
            for c in w['chars']:c['highlight']=w['word_id']==0
        cfg=settings((540,960));r=captions.CaptionRenderer(data,cfg['size'],cfg['safe_zone'])
        blank=Image.new('RGBA',cfg['size'])
        a=np.asarray(r.overlay(blank,500));b=np.asarray(r.overlay(blank,590))
        keyword=np.array(ImageColor(data['style']['keyword_color']))
        mask=np.all(a[...,:3]==keyword,axis=2)&(a[...,3]>0)
        self.assertGreater(mask.sum(),20)
        self.assertTrue(np.array_equal(a[mask],b[mask]))
        active=np.array(ImageColor(data['style']['current_word_color']))
        self.assertFalse(np.array_equal(keyword,active))
        self.assertGreater(np.count_nonzero(np.all(b[...,:3]==active,axis=2)),20)
        self.assertFalse(np.array_equal(a,b))

    def test_clean_busy_background_has_dark_outline(self):
        data=self.prepare([dict(text='清楚 READ',start_ms=0,end_ms=1000)],'clean')
        self.assertGreaterEqual(data['style']['stroke'],10)
        self.assertGreaterEqual(data['style']['shadow'],4)
        cfg=settings((540,960));r=captions.CaptionRenderer(data,cfg['size'],cfg['safe_zone'])
        yy,xx=np.indices((960,540));bg=np.repeat(np.where((xx//8+yy//8)%2,240,80)[...,None],4,axis=2).astype('uint8');bg[...,3]=255
        result=np.asarray(r.overlay(Image.fromarray(bg),500))
        self.assertGreater(np.count_nonzero(np.all(result[...,:3]<20,axis=2)),200)

    def test_caption_pop_density_not_every_line(self):
        for interval in (300,2000):
            lines=[dict(start_ms=i*interval) for i in range(12)]
            events=events_from_plan({},[],[],[],dict(lines=lines))
            times=[e['at_ms'] for e in events]
            self.assertLessEqual(len(times),6)
            self.assertTrue(all(b-a>=1500 for a,b in zip(times,times[1:])))
            self.assertTrue(all(lines.index(dict(start_ms=b))-lines.index(dict(start_ms=a))>=2 for a,b in zip(times,times[1:])))

    def test_emoji_modifier_shapes_as_one_glyph_and_colors_differ(self):
        from caption_glyphs import emoji_mask
        for preset in captions.PRESETS:
            data=self.prepare(mixed_words(),preset)
            if data['style']['current_word']:
                self.assertNotEqual(data['style']['keyword_color'],data['style']['current_word_color'])
        if sys.platform=='win32':
            base=emoji_mask('👍','Segoe UI Emoji',60)
            joined=emoji_mask('👍🏽','Segoe UI Emoji',60)
            if joined is not None:
                self.assertLessEqual(joined.width,base.width*1.2)
                self.assertIsNotNone(joined.getbbox())


def ImageColor(hex_color):
    return tuple(int(hex_color[i:i+2],16) for i in (0,2,4))


class CameraQATests(unittest.TestCase):
    def test_crash_default_frame_steps_and_short_intervals_rejected(self):
        self.assertGreaterEqual(MOVES['crash_out'][0],300)
        for fps in (24,25,30,60):
            scales=[motion('crash_out',t)[0] for t in np.arange(0,650,1000/fps)]
            self.assertLessEqual(max(abs(np.diff(scales))),.16)
            self.assertEqual(scales[0],1);self.assertEqual(scales[-1],1)
        with self.assertRaisesRegex(ValueError,'300'):motion('crash_out',40,100)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);Image.new('RGBA',(90,160),'red').save(root/'a.png')
            path=root/'plan.json';path.write_text(json.dumps(dict(experimental=True,segments=[dict(type='still',image='a.png',duration_ms=1000)],effects=[dict(move='crash_out',end_ms=100)])))
            with self.assertRaisesRegex(ValueError,'300'):validate_plan(path)

    def test_named_edges_peaks_not_whole_intervals_and_cuts_win(self):
        for move in MOVES:
            timing=dict(effects=[dict(name='camera_move',start_ms=1000,end_ms=4000,params=dict(move=move))])
            marks=camera_event_times(timing)
            self.assertIn(1000,marks);self.assertIn(4000,marks)
            observed=[dict(seconds=t/1000) for t in marks]+[dict(seconds=3.5)]
            kept,excluded=rhythm_cuts(observed,timing,34)
            self.assertEqual(kept,[dict(seconds=3.5)],move)
            self.assertEqual(len(excluded),len(marks))
            timing['cuts']=[dict(quantized_ms=4000)]
            kept,_=rhythm_cuts(observed,timing,34)
            self.assertIn(dict(seconds=4),kept)
            if move=='spring_in':
                # Spring uses physical seconds, not its nominal table duration.
                kept,_=rhythm_cuts([dict(seconds=1.7)],timing,34)
                self.assertEqual(kept,[dict(seconds=1.7)])

    def test_camera_flash_exemption_is_bounded_and_audited(self):
        n=100;d=np.ones(n);skip=np.ones(n)
        for i in (30,60):d[i:i+2]=100;skip[i]=0
        stats=dict(d=d,skip=skip,patch=np.zeros(n),mean=[100]*n,contrast=[30]*n,seam=0)
        timing=dict(effects=[dict(name='camera_move',start_ms=1000,end_ms=3000,params=dict(move='smooth_in'))])
        # The duration endpoint at 2000 is intentional; an unrelated flash survives.
        timing['effects'][0]['params']['duration_ms']=1500
        checks=analyse_picture(stats,np.arange(n+1)/30,timing=timing)
        flash=next(c for c in checks if c['name']=='flashes')
        self.assertEqual([e['frame'] for e in flash['excluded_camera_events']],[30])
        self.assertEqual([e['frame'] for e in flash['events']],[60])
        self.assertEqual(flash['level'],'FAIL')

    def test_encoded_named_moves_rhythm_and_flash_qa(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=camera_clip(Path(tmp))
        self.assertIsNotNone(report['cut_to_downbeat_median_ms'])
        self.assertLessEqual(report['cut_to_downbeat_median_ms'],5)
        self.assertEqual(next(c['level'] for c in report['checks'] if c['name']=='flashes'),'PASS')
        self.assertTrue(report['rhythm_excluded_effect_events'])


if __name__=='__main__':unittest.main()
