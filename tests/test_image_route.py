import base64
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
from image_fixtures import ImageCase,ROOT
from image_route import Adapter,Request,request_key,saved_paths
from image_common import ImageError,digest,read


class RouteTests(ImageCase):
    def test_subscription_scrubs_credentials_and_cache(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'sk-SENTINEL','OPENAI_BASE_URL':'http://127.0.0.1:1','OPENAI_ORG_ID':'bad','CODEX_API_KEY':'bad'}):
            a=self.adapter.generate(self.request(refs=[self.fixture],transparent=True),self.path/'a')
            start=time.monotonic();b=self.adapter.generate(self.request(refs=[self.fixture],transparent=True),self.path/'b')
        self.assertLess(time.monotonic()-start,1)
        self.assertEqual(len(self.calls()),1);self.assertEqual(self.calls()[0]['env'],{})
        self.assertTrue(b['cache_hit']);self.assertEqual(a['assets'][0]['sha256'],b['assets'][0]['sha256'])
        self.assertIn('referenced_image_paths',self.calls()[0]['stdin']);self.assertIn('transparent_background',self.calls()[0]['stdin'])
        self.assertIsNone(a['model_reported']);self.assertEqual(a['model'],'unreported')

    def test_concurrent_identical_requests_make_one_call(self):
        self.configure(delay=.25)
        with ThreadPoolExecutor(4) as pool:
            rows=list(pool.map(lambda i:self.adapter.generate(self.request(),self.path/str(i)),range(4)))
        self.assertEqual(len(self.calls()),1);self.assertEqual(sum(r['cache_hit'] for r in rows),3)

    def test_concurrent_cli_processes_share_cache(self):
        self.configure(delay=.3)
        cmd=[sys.executable,str(ROOT/'scripts/imagegen.py'),'generate','--experimental','--prompt','one process request',
             '--codex',str(self.fake),'--state',str(self.path/'state'),'--json']
        processes=[subprocess.Popen([*cmd,'--out',str(self.path/f'process-{i}')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for i in range(3)]
        rows=[]
        for process in processes:
            stdout,stderr=process.communicate(timeout=30);self.assertEqual(process.returncode,0,stderr+stdout);rows.append(json.loads(stdout)['result'])
        self.assertEqual(len(self.calls()),1);self.assertEqual(sum(r['cache_hit'] for r in rows),2)

    def test_cache_normalization_and_field_changes(self):
        def k(**kw):return request_key(Request(experimental=True,**kw).normalized())
        self.assertEqual(k(prompt='a  cafe\u0301'),k(prompt='a café'))
        for prompt in ('A café','a cafe','a café!'):
            self.assertNotEqual(k(prompt='a café'),k(prompt=prompt))
        ref2=self.path/'ref2.png';from PIL import Image
        Image.new('RGB',(90,160),'red').save(ref2)
        self.assertNotEqual(k(prompt='a',refs=[self.fixture,ref2]),k(prompt='a',refs=[ref2,self.fixture]))
        self.assertNotEqual(k(prompt='a'),k(prompt='a',quality='final'))
        self.adapter.generate(self.request(),self.path/'one')
        self.adapter.generate(self.request(),self.path/'two',no_cache=True)
        self.assertEqual(len(self.calls()),2)

    def test_billed_auth_and_experimental_rejected(self):
        self.configure(login='Logged in using an API key')
        with self.assertRaisesRegex(ImageError,'API key'):self.adapter.generate(self.request(),self.path/'no')
        self.assertEqual(len(self.calls()),0)
        with self.assertRaises(ImageError):self.adapter.generate(Request('a'),self.path/'flag')

    def test_failure_is_not_cached_and_auto_stops(self):
        self.configure(error='generation unavailable')
        for i in range(2):
            with self.assertRaises(ImageError):self.adapter.generate(self.request(route='auto'),self.path/str(i))
        self.assertEqual(len(self.calls()),2);self.assertFalse(list((self.path/'state/cache').glob('*/record.json')))
        self.assertEqual(read(self.path/'0/gen-manifest.json')['fallback_chain'][0]['route'],'codex')

    def test_quota_retry_is_bounded(self):
        self.configure(error='429 quota exceeded')
        with patch('image_route.time.sleep') as sleep:
            with self.assertRaises(ImageError) as err:self.adapter.generate(self.request(),self.path/'fail')
        self.assertEqual(err.exception.error['code'],'E_QUOTA');self.assertEqual(len(self.calls()),3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list],[5,10])

    def test_api_sentinel_exact_approval(self):
        calls=[];image=base64.b64encode(self.fixture.read_bytes()).decode()
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                calls.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                body=json.dumps(dict(data=[dict(b64_json=image)])).encode()
                self.send_response(200);self.end_headers();self.wfile.write(body)
            def log_message(self,*a):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            prices=dict(version='fixture-v1',date='2026-11-06',rows=[dict(model='gpt-image-2.6-flare',quality='low',size='1024x1024',unit_usd=.1)])
            adapter=Adapter(self.path/'state',api_base=f'http://127.0.0.1:{server.server_port}/v1',prices=prices)
            req=self.request(route='api');est=adapter.estimate(req)
            with patch.dict(os.environ,{'OPENAI_API_KEY':'sk-TEST'}):
                for approval,budget,code in [(None,0,'E_APPROVAL_REQUIRED'),('wrong',1,'E_APPROVAL_MISMATCH'),(est['estimate_id'],0,'E_BUDGET')]:
                    with self.assertRaises(ImageError) as err:adapter.generate(req,self.path/'denied',approval,budget)
                    self.assertEqual(err.exception.error['code'],code)
                self.assertEqual(calls,[])
                result=adapter.generate(req,self.path/'approved',est['estimate_id'],.1)
                adapter.generate(req,self.path/'cached',est['estimate_id'],.1)
            self.assertEqual(len(calls),1);self.assertEqual(calls[0]['quality'],'low');self.assertEqual(calls[0]['n'],1)
            self.assertEqual(result['cost_estimate_usd'],.1)
        finally:server.shutdown();server.server_close();thread.join()

    def test_json_error_envelope(self):
        cmd=[sys.executable,str(ROOT/'scripts/imagegen.py'),'generate','--json','--out',str(self.path/'cli')]
        result=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['error']['code'],'E_EXPERIMENTAL')
        self.assertNotIn('Traceback',result.stderr)

    def test_final_receipt_ignores_commentary_reference_paths(self):
        first=json.dumps(dict(type='item.completed',item=dict(type='agent_message',text='Inspecting '+str(self.fixture))))
        output=self.path/'result.png';output.write_bytes(self.fixture.read_bytes())
        last=json.dumps(dict(type='item.completed',item=dict(type='agent_message',text=json.dumps(dict(image_paths=[str(output)])))))
        self.assertEqual(saved_paths(first+'\n'+last),[str(output)])


if __name__=='__main__':unittest.main()
