import contextlib
import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from grok_client import GrokClient, ProviderError
from grok_video import main


class Fake:
    def __init__(self): self.calls=0; self.result={'status':'pending'}; self.fail=None
    def token(self): return 'secret-not-for-output'
    def submit(self,*args):
        self.calls+=1
        if self.fail: raise self.fail
        return {'request_id':'test-job'}
    def poll(self,job): return self.result
    def download(self,url,target): target.write_bytes(b'test-video')


class GrokTests(unittest.TestCase):
    def setup_job(self,p,client):
        (p/'image.png').write_bytes(b'fake-test-image')
        (p/'prompt.txt').write_text('Original character moves.')
        args=['--out',str(p/'run')]
        main(args+['--submit','--image',str(p/'image.png'),'--prompt',str(p/'prompt.txt')],client)
        return args

    def test_submit_poll_download_idempotency_and_url_redaction(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            p=Path(d);c=Fake();args=self.setup_job(p,c)
            with self.assertRaises(SystemExit): main(args+['--submit'],c)
            main(args+['--resume'],c)
            c.result={'status':'done','video':{'url':'https://media.example/video?secret=signed'}}
            main(args+['--resume'],c);main(args+['--resume'],c)
            self.assertEqual(c.calls,1)
            text=(p/'run/job.json').read_text()
            self.assertNotIn('signed',text);self.assertNotIn('secret-not-for-output',text)
            self.assertEqual(json.loads(text)['status'],'downloaded')

    def test_uncertain_submit_never_repeats(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);c=Fake();c.fail=TimeoutError('secret')
            with self.assertRaises(SystemExit): self.setup_job(p,c)
            with self.assertRaises(SystemExit): main(['--out',str(p/'run'),'--submit'],c)
            self.assertEqual(c.calls,1)
            self.assertNotIn('secret',(p/'run/job.json').read_text())

    def test_spending_limit_is_rejected_without_refresh_or_retry(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);c=Fake();c.fail=ProviderError(403,'personal-team-blocked:spending-limit')
            with self.assertRaises(SystemExit): self.setup_job(p,c)
            self.assertEqual(json.loads((p/'run/job.json').read_text())['status'],'rejected')
            self.assertEqual(c.calls,1)

    def test_terminal_job_does_not_download_or_poll_again(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            p=Path(d);c=Fake();args=self.setup_job(p,c);c.result={'status':'failed','video':{'url':'https://example/video'}}
            with self.assertRaises(SystemExit): main(args+['--resume'],c)
            self.assertFalse((p/'run/source.mp4').exists())
            with patch.object(c,'poll',side_effect=AssertionError('must not poll')):
                with self.assertRaises(SystemExit): main(args+['--resume'],c)

    def test_oauth_inspection_never_exposes_token(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'auth.json';p.write_text(json.dumps({'session':{'auth_mode':'oidc','key':'secret-token','expires_at':'2099-01-01T00:00:00Z'}}))
            c=GrokClient(p)
            self.assertEqual(c.token(),'secret-token')
            self.assertNotIn('secret-token',json.dumps(c.inspect()))
            self.assertTrue(c.inspect()['oauth_session_present'])

    def test_expired_session_refreshes_once_via_cli(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'auth.json';record={'s':{'auth_mode':'oidc','key':'old','refresh_token':'refresh','expires_at':'2001-01-01T00:00:00Z'}};p.write_text(json.dumps(record));c=GrokClient(p)
            def refresh(*args,**kwargs):
                record['s'].update(key='new',expires_at='2099-01-01T00:00:00Z');p.write_text(json.dumps(record))
                return type('Result',(),{'returncode':0})()
            with patch('grok_client.subprocess.run',side_effect=refresh) as run:
                self.assertEqual(c.token(),'new');self.assertEqual(run.call_count,1)

    def test_connection_cli_works_outside_repo_without_adapter(self):
        import shutil, subprocess
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            for name in ('grok_client.py','grok_video.py'):
                shutil.copy2(Path(__file__).resolve().parents[1]/'scripts'/name,folder/name)
            result=subprocess.run([sys.executable,str(folder/'grok_video.py'),'--help'],cwd=folder,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('--adapter',result.stdout)

    def test_download_does_not_send_authorization(self):
        c=GrokClient()
        with tempfile.TemporaryDirectory() as d:
            with patch('grok_client.urllib.request.urlopen',return_value=io.BytesIO(b'video')) as urlopen:
                c.download('https://example/video',Path(d)/'source.mp4')
                self.assertEqual(urlopen.call_args.args,('https://example/video',))

    def test_request_shape_and_billing_error(self):
        c=GrokClient()
        with patch.object(c,'token',return_value='private-token'):
            with patch('grok_client.urllib.request.urlopen',return_value=io.BytesIO(b'{"request_id":"j"}')) as call:
                c.request('/videos/generations',{'prompt':'move'})
                request=call.call_args.args[0]
                self.assertEqual(request.get_method(),'POST')
                self.assertEqual(json.loads(request.data),{'prompt':'move'})
            error=urllib.error.HTTPError('https://api.x.ai',403,'blocked',{},io.BytesIO(b'{"code":"personal-team-blocked:spending-limit","message":"private-token"}'))
            with patch('grok_client.urllib.request.urlopen',side_effect=error):
                with self.assertRaises(ProviderError) as caught: c.request('/videos/generations',{})
                self.assertNotIn('private-token',str(caught.exception))


if __name__=='__main__': unittest.main()
