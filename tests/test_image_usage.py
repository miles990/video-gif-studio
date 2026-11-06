from concurrent.futures import ThreadPoolExecutor
import json
import struct
import zlib
from image_fixtures import ImageCase,ROOT
from image_common import ImageError,c2pa,read
from image_route import Adapter
from image_usage import summarize


class UsageTests(ImageCase):
    def test_caps_are_atomic_and_cache_does_not_consume(self):
        self.adapter.cap=2
        self.adapter.generate(self.request(),self.path/'one')
        self.adapter.generate(self.request(),self.path/'hit')
        def run(i):
            req=self.request(seed=i)
            try:return self.adapter.generate(req,self.path/f'req{i}')['status']
            except ImageError as exc:return exc.error['code']
        with ThreadPoolExecutor(4) as pool:result=list(pool.map(run,range(4)))
        self.assertEqual(result.count('ok'),1);self.assertEqual(result.count('E_CAP'),3);self.assertEqual(len(self.calls()),2)
        usage=summarize(self.adapter.records());total=usage['totals']
        self.assertEqual(total['reserved_images'],2);self.assertEqual(total['cache_hits'],1);self.assertEqual(total['failures'],3)
        self.assertEqual(total['subscription_images'],2);self.assertEqual(total['cache_saved_images'],1)

    def test_c2pa_chunk_detected_and_stripped(self):
        raw=self.fixture.read_bytes();payload=b'jumb fake unsigned fixture';kind=b'caBX'
        chunk=struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
        tagged=self.path/'tagged.png';tagged.write_bytes(raw[:33]+chunk+raw[33:])
        self.assertTrue(c2pa(tagged)['c2pa_present']);self.assertFalse(c2pa(self.fixture)['c2pa_present'])
        self.assertIn('not verified',c2pa(tagged)['c2pa_validation'])

    def test_manifest_schema_success_failure_and_run_groups(self):
        from fx_schema import validate
        schema=read(ROOT/'references/image-manifest.schema.json')
        # The repo's offline schema validator has no regex keyword; assert hashes
        # separately while validating the rest of the exact published schema.
        patterns={name:prop.pop('pattern') for name,prop in schema['properties'].items() if 'pattern' in prop}
        result=self.adapter.generate(self.request(),self.path/'ok');validate(result,schema)
        for name,pattern in patterns.items():self.assertRegex(result[name],pattern)
        self.configure(error='unavailable')
        with self.assertRaises(ImageError):self.adapter.generate(self.request(seed=4),self.path/'failed')
        failed=read(self.path/'failed/gen-manifest.json');validate(failed,schema)
        summary=summarize(self.adapter.records(),since='2026-01-01')
        self.assertEqual(len(summary['groups']['run_id']),1);self.assertEqual(summary['totals']['failures'],1)
        self.assertEqual(summary['totals']['reserved_images'],2)
