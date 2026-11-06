import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
import json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from game_video import keyframes_video,estimate
from image_common import ImageError,write


class VideoGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.scratch');self.path=Path(self.tmp.name);self.first=self.path/'a.png';self.last=self.path/'b.png'
        Image.new('RGBA',(64,64),'orange').save(self.first);Image.new('RGBA',(64,64),'blue').save(self.last)
        self.prices=dict(route='grok',date=datetime.now(timezone.utc).date().isoformat(),version='fixture',usd_per_second=.1)
    def tearDown(self):self.tmp.cleanup()
    def test_sentinels_no_driver_import_or_process_without_approval(self):
        with patch('game_video.subprocess.run',side_effect=AssertionError('API-SENTINEL')) as sentinel:
            for route in ('grok','fal'):
                for token in (None,'wrong','expired'):
                    with self.assertRaises(ImageError) as e:keyframes_video(self.first,self.last,[],route,self.path/route,token)
                    self.assertEqual(e.exception.error['code'],'E_APPROVAL_REQUIRED');self.assertEqual(e.exception.error['network_requests'],0)
            sentinel.assert_not_called()
    def test_estimate_binds_all_inputs_price_and_expiration(self):
        out=self.path/'job';a=estimate(self.first,self.last,[self.first],'grok',out,prices=self.prices)
        self.assertEqual(a,estimate(self.first,self.last,[self.first],'grok',out,prices=self.prices))
        changed=estimate(self.first,self.last,[self.last],'grok',out,prices=self.prices);self.assertNotEqual(a['estimate_id'],changed['estimate_id'])
        changed['expires_at']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat();write(out/'video-estimate.json',changed)
        with self.assertRaises(ImageError) as e:keyframes_video(self.first,self.last,[self.last],'grok',out,changed['estimate_id'],prices=self.prices)
        self.assertEqual(e.exception.error['code'],'E_APPROVAL_REQUIRED')
    def test_approved_unsupported_route_does_not_drop_references(self):
        out=self.path/'job';est=estimate(self.first,self.last,[self.first],'grok',out,prices=self.prices)
        with patch('game_video.subprocess.run') as sentinel:
            with self.assertRaises(ImageError) as e:keyframes_video(self.first,self.last,[self.first],'grok',out,est['estimate_id'],prices=self.prices)
            self.assertEqual(e.exception.error['code'],'E_VIDEO_CAPABILITY');sentinel.assert_not_called()


if __name__=='__main__':unittest.main()
