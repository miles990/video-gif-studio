import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import media_runtime
from background_remove import separate
from grok_client import GrokClient
from grok_video import main

class RuntimeTests(unittest.TestCase):
    def test_explicit_bad_path_never_silently_falls_back(self):
        with patch.dict(os.environ, {'VIDEO_GIF_FFMPEG':'/missing/video-gif-test'}):
            with self.assertRaises(RuntimeError): media_runtime.executable('ffmpeg')

    def test_existing_pair_does_not_download(self):
        with patch.object(media_runtime,'locate',side_effect=lambda n:'/bin/'+n), patch.object(media_runtime.subprocess,'run') as run:
            self.assertEqual(media_runtime.setup(),{'ffmpeg':'/bin/ffmpeg','ffprobe':'/bin/ffprobe'})
            self.assertEqual(run.call_count,2)

    def test_no_media_during_read_only_lookup(self):
        with patch.dict(os.environ, {},clear=True), patch('media_runtime.shutil.which',return_value=None), patch.dict(sys.modules,{'static_ffmpeg.run':None}):
            self.assertIsNone(media_runtime.locate('ffmpeg'))
            with self.assertRaises(RuntimeError):media_runtime.executable('ffmpeg')

    def test_missing_pair_fetches_both_during_setup(self):
        import types
        provider = types.ModuleType('static_ffmpeg.run')
        from unittest.mock import Mock
        provider.get_or_fetch_platform_executables_else_raise = Mock(return_value=('/managed/ffmpeg','/managed/ffprobe'))
        with patch.object(media_runtime,'locate',return_value=None), patch.dict(sys.modules,{'static_ffmpeg.run':provider}), patch.object(media_runtime.subprocess,'run'):
            self.assertEqual(media_runtime.setup()['ffprobe'],'/managed/ffprobe')
            provider.get_or_fetch_platform_executables_else_raise.assert_called_once()

    def test_resume_inherits_api_mode_without_cli_flag(self):
        from unittest.mock import Mock
        import contextlib
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'job.json').write_text(json.dumps({'auth_mode':'api-key','status':'submitted','request_id':'j'}))
            client=Mock();client.poll.return_value={'status':'pending'}
            with patch('grok_video.GrokClient',return_value=client) as constructor, contextlib.redirect_stdout(io.StringIO()):
                main(['--out',str(p),'--resume'])
            constructor.assert_called_once_with(auth_mode='api-key')
            client.poll.assert_called_once_with('j')

    def test_api_mode_has_no_cli_or_oauth_fallback(self):
        with patch.dict(os.environ,{'XAI_API_KEY':'test-api-secret'}), patch.object(GrokClient,'session',side_effect=AssertionError('OAuth must not be read')):
            self.assertEqual(GrokClient(auth_mode='api-key').token(),'test-api-secret')
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):GrokClient(auth_mode='api-key').token()

    def test_oauth_does_not_pick_up_ambient_api_key(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'XAI_API_KEY':'test-api-secret'}):
            with self.assertRaises(RuntimeError):GrokClient(Path(d)/'missing.json').token()

    def test_resume_cannot_switch_auth_mode(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'job.json').write_text(json.dumps({'auth_mode':'api-key','status':'submitted','request_id':'j'}))
            with self.assertRaises(SystemExit),patch('sys.stderr',new=io.StringIO()):
                main(['--out',str(p),'--resume','--auth','oauth'])

    def test_matting_preserves_rgb_input_alpha_and_timing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);frames=p/'frames';frames.mkdir();a=np.zeros((4,4,4),dtype='uint8');a[:,:,:3]=[123,45,67];a[:,:,3]=128
            Image.fromarray(a).save(frames/'0.png');manifest=p/'manifest.json';manifest.write_text(json.dumps({'durations_ms':[170],'qc':{'old':True},'gif_sha256':'old'}))
            mask=np.full((4,4),128,dtype='uint8');mask[1,1]=0
            separate(frames,manifest,p/'out',masker=lambda im:Image.fromarray(mask))
            b=np.array(Image.open(p/'out/frames/00000.png'));self.assertTrue(np.array_equal(a[:,:,:3],b[:,:,:3]));self.assertEqual(b[0,0,3],64);self.assertEqual(b[1,1,3],0)
            report=json.loads((p/'out/manifest.json').read_text());self.assertEqual(report['durations_ms'],[170]);self.assertNotIn('qc',report)
            with self.assertRaises(FileExistsError):separate(frames,manifest,p/'out',masker=lambda im:im)

if __name__=='__main__':unittest.main()
