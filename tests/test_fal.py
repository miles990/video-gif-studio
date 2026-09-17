import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import fal_video as f

class Fake:
    def __init__(self): self.submissions=0; self.downloads=0
    def submit(self, endpoint, payload):
        self.submissions+=1
        self.payload=payload; self.endpoint=endpoint
        return dict(request_id='job-1',status_url=f.BASE+'minimax/h3-max/requests/job-1/status',response_url=f.BASE+'minimax/h3-max/requests/job-1')
    def poll(self,url):
        return {'status':'COMPLETED'} if url.endswith('/status') else {'video':{'url':'https://example.com/video?secret=test'},'timings':{'inference':3}}
    def download(self,url,target): self.downloads+=1; target.write_bytes(b'test-video')

class FalTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.out=self.root/'run'
        patcher=patch.object(f,'KEY_FILE',self.root/'fal.key');patcher.start();self.addCleanup(patcher.stop)
        self.prompt=self.root/'prompt.txt';self.prompt.write_text('A complete greeting, then recover.')
        self.image=self.root/'base.png';self.image.write_bytes(b'png-fixture')
        self.base=['--out',str(self.out),'--prompt',str(self.prompt)]
    def run_cli(self,args,client=None):
        with contextlib.redirect_stdout(io.StringIO()) as o: f.main(args,client=client)
        return o.getvalue()
    def test_modes_and_no_secrets_in_dry_run(self):
        with patch.dict(os.environ,{'FAL_KEY':'never-write-this'}):
            result=json.loads(self.run_cli(self.base+['--dry-run','--image',str(self.image),'--end-image',str(self.image)]))
        self.assertEqual(result['endpoint'],f.MODEL+'image-to-video')
        self.assertEqual([r['role'] for r in result['inputs']],['first','last'])
        self.assertNotIn('never-write-this',json.dumps(result));self.assertFalse(self.out.exists())
    def test_submit_resume_no_duplicate_and_no_delivery_url(self):
        c=Fake();self.run_cli(self.base+['--submit','--image',str(self.image),'--end-image',str(self.image)],c)
        self.assertEqual(c.payload['image_url'],c.payload['end_image_url'])
        with self.assertRaises(f.FalError): self.run_cli(self.base+['--submit'],c)
        self.run_cli(['--out',str(self.out),'--resume'],c)
        self.run_cli(['--out',str(self.out),'--resume'],c)
        self.assertEqual((c.submissions,c.downloads),(1,1))
        self.assertNotIn('secret=test',(self.out/'job.json').read_text())
        (self.out/'source.mp4').write_bytes(b'changed')
        with self.assertRaises(f.FalError): self.run_cli(['--out',str(self.out),'--resume'],c)
    def test_ambiguous_submission_blocks_retry(self):
        c=Fake()
        with patch.object(c,'submit',side_effect=TimeoutError):
            with self.assertRaises(f.FalError): self.run_cli(self.base+['--submit'],c)
        self.assertEqual(json.loads((self.out/'job.json').read_text())['status'],'submission-unresolved')
        with self.assertRaises(f.FalError): self.run_cli(self.base+['--submit'],c)
        with self.assertRaises(f.FalError): self.run_cli(['--out',str(self.out),'--resume'],c)
        self.assertEqual(c.submissions,0)
    def test_mixed_modes_rejected_before_network(self):
        c=Fake()
        with self.assertRaises(ValueError): self.run_cli(self.base+['--submit','--image',str(self.image),'--reference-image',str(self.image)],c)
        self.assertEqual(c.submissions,0);self.assertFalse(self.out.exists())
    def test_reference_limit(self):
        with self.assertRaises(ValueError): self.run_cli(self.base+['--dry-run']+['--reference-image',str(self.image)]*13)
    def test_missing_key_no_ledger(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(f.FalError): self.run_cli(self.base+['--submit'])
        self.assertFalse(self.out.exists())
    def test_local_key_permissions(self):
        f.KEY_FILE.write_text('local-test-key'); f.KEY_FILE.chmod(0o600)
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(f.Client().key,'local-test-key')
            if os.name == 'posix':
                f.KEY_FILE.chmod(0o644)
                with self.assertRaises(f.FalError): f.Client()

    def test_queue_url_no_credentials_or_other_host(self):
        for url in ['https://evil.example/status','https://queue.fal.run/minimax/h3-max/requests/x?token=secret','http://queue.fal.run/minimax/h3-max/requests/x']:
            with self.assertRaises(f.FalError): f.queue_url(url)
    def test_download_retry_reuses_job(self):
        c=Fake();self.run_cli(self.base+['--submit'],c)
        with patch.object(c,'download',side_effect=f.FalError('interrupted')):
            with self.assertRaises(f.FalError): self.run_cli(['--out',str(self.out),'--resume'],c)
        self.run_cli(['--out',str(self.out),'--resume'],c)
        self.assertEqual(c.submissions,1)

if __name__=='__main__': unittest.main()
