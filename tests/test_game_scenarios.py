"""Offline subscription cassette scenarios and local-only asset invariants."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
from image_fixtures import ImageCase,ROOT
from image_common import ImageError,read,write,digest
from game_character import sheet,require_alpha
from game_icons import iconset
from game_animation import layered_between
from game_video import keyframes_video,estimate


class GameScenarios(ImageCase):
    def source(self):
        im=Image.new('RGBA',(64,64));d=ImageDraw.Draw(im);d.rectangle((12,8,51,58),fill='#808060',outline='#20182A',width=2)
        im.save(self.fixture);return im

    def test_cassette_character_reference_chain_cache_and_honesty(self):
        self.source();req=self.request()
        req.prompt='original amber fox';a=sheet(self.adapter,req,self.path/'one',pixel=64)
        count=len(self.calls());self.assertEqual(count,10)
        self.assertEqual(a['identity']['status'],'unassessed');self.assertEqual(a['expressions_qa']['status'],'fail')
        for row in a['views'][1:]:self.assertGreaterEqual(len(row['refs_sent']),1)
        for row in a['expressions']:self.assertGreaterEqual(len(row['refs_sent']),1)
        b=sheet(self.adapter,req,self.path/'two',pixel=64);self.assertEqual(len(self.calls()),count)
        self.assertEqual(digest(self.path/'one/views/front.png'),digest(self.path/'two/views/front.png'))
        self.assertEqual(b['fallback'],'pixel_quantize')

    def test_opaque_and_checkerboard_sources_rejected(self):
        with self.assertRaises(ImageError):require_alpha(Image.new('RGB',(128,128),'white'))
        yy,xx=np.indices((128,128));mask=((xx//16+yy//16)%2)*25+220
        im=Image.fromarray(np.repeat(mask[...,None],3,axis=2).astype(np.uint8))
        with self.assertRaises(ImageError) as e:require_alpha(im)
        self.assertEqual(e.exception.error['code'],'E_FAKE_ALPHA')

    def test_icon_fix_regenerates_only_bad_index(self):
        self.source();token=dict(grid=64,outline_hex='#20182A',outline_px=2,light_deg=135,safe_margin=4,palette=['#20182A','#808060'],shading='cel')
        items=['shield','scroll','sword','key','potion','gem','bow','boot']
        out=self.path/'icons';first=iconset(self.adapter,self.request(),items,token,out,pixel=True)
        self.assertEqual(first['qa']['status'],'PASS',first['qa'])
        before=digest(out/'00.png');bad=Image.new('RGBA',(64,64));ImageDraw.Draw(bad).rectangle((24,24,39,39),fill='#808060');bad.save(out/'01.png')
        old=len(self.calls());result=iconset(self.adapter,self.request(),items,token,out,pixel=True,fix=True)
        self.assertEqual(len(self.calls())-old,1);self.assertEqual(digest(out/'00.png'),before);self.assertEqual(result['repairs'][-1]['indices'],[1]);self.assertEqual(result['qa']['status'],'PASS')

    def test_approved_driver_receives_all_inputs_exactly_once(self):
        from datetime import datetime,timezone
        self.source();last=self.path/'last.png';im=Image.open(self.fixture).convert('RGBA');ImageDraw.Draw(im).point((30,20),fill='red');im.save(last)
        driver=self.path/'driver.py';video=self.path/'returned.mp4';video.write_bytes(b'fake transport result; decode mocked separately')
        driver.write_text('import json,sys,hashlib\nfrom pathlib import Path\np=json.loads(sys.stdin.read());base=Path(__file__).parent\nwith (base/"video-calls.jsonl").open("a") as f:f.write(json.dumps(p)+"\\n")\ndef sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()\nprint(json.dumps(dict(video=str(base/"returned.mp4"),first_frame_sha=sha(p["first_frame"]),last_frame_sha=sha(p["last_frame"]),refs_sent=[sha(r) for r in p["reference_images"]],network_calls=1)))\n',encoding='utf-8')
        prices=dict(route='fal',version='test-only',date=datetime.now(timezone.utc).date().isoformat(),usd_per_second=.1);out=self.path/'video';est=estimate(self.fixture,last,[self.fixture,last],'fal',out,prices=prices,driver=driver)
        class Capture:
            def read(self):return True,np.array(im.convert('RGB'))[...,::-1]
            def release(self):pass
        with patch('qa_media.qa',return_value={'status':'PASS'}),patch('cv2.VideoCapture',return_value=Capture()):
            result=keyframes_video(self.fixture,last,[self.fixture,last],'fal',out,est['estimate_id'],prices=prices,driver=driver)
        calls=(self.path/'video-calls.jsonl').read_text().splitlines();self.assertEqual(len(calls),1);self.assertEqual(result['refs_sent'],[digest(self.fixture),digest(last)])
        with self.assertRaises(ImageError) as e:keyframes_video(self.fixture,last,[self.fixture,last],'fal',out,est['estimate_id'],prices=prices,driver=driver)
        self.assertEqual(e.exception.error['code'],'E_VIDEO_ALREADY_SUBMITTED');self.assertEqual(len((self.path/'video-calls.jsonl').read_text().splitlines()),1)


if __name__=='__main__':unittest.main()
