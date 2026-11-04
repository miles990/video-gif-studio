"""Merge gate: stable defaults, explicit opt-in, and auditable deliveries."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fx import EFFECTS,TRANSITIONS
from fx.core import catalog,load_directory
from fx_render import main,preview,render,validate_plan


class FeatureFlagTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.path=self.root/'plan.json'
        Image.new('RGBA',(24,16),(80,120,160,255)).save(self.root/'a.png')
        self.plan={'segments':[{'type':'still','image':'a.png','duration_ms':400},
                               {'type':'still','image':'a.png','duration_ms':400}]}
        self.env=patch.dict(os.environ,{'VIDEO_GIF_INTERPOLATE':''});self.env.start();self.addCleanup(self.env.stop)

    def save(self):self.path.write_text(json.dumps(self.plan))

    def test_catalog_exact_stable_set_and_cli(self):
        stable=catalog()
        self.assertEqual(set(stable['effects']),{'flash_white','beat_bounce','halation','grade','zoom_punch','cutout_card'})
        self.assertEqual(set(stable['transitions']),{'crossfade','whip_pan','hex_shutter','flash_cut'})
        for reg in catalog(True).values():
            for spec in reg.values():self.assertIn(spec['status'],('stable','experimental'))
        for args,expected in (([],10),(['--experimental'],len(EFFECTS)+len(TRANSITIONS))):
            stream=io.StringIO()
            with contextlib.redirect_stdout(stream):self.assertEqual(main(['--list','--json','--no-user-fx']+args),0)
            self.assertEqual(sum(map(len,json.loads(stream.getvalue()).values())),expected)

    def test_every_experimental_entry_requires_opt_in_before_backends(self):
        for registry,kind in ((EFFECTS,'effect'),(TRANSITIONS,'transition')):
            for name,spec in registry.items():
                if spec['status']!='experimental':continue
                with self.subTest(name=name):
                    if kind=='effect':self.plan['effects']=[{'name':name}]
                    else:self.plan['segments'][1]['transition']={'name':name,'duration_ms':160}
                    self.save()
                    with self.assertRaisesRegex(ValueError,'[Ee]xperimental.*--experimental'):validate_plan(self.path)
                    self.plan.pop('effects',None);self.plan['segments'][1].pop('transition',None)

    def test_plan_and_cli_opt_in_and_manifest(self):
        self.plan['effects']=[{'name':'rgb_split'}]
        self.plan['segments'][1]['transition']={'name':'push','duration_ms':160}
        self.save()
        validate_plan(self.path,experimental=True)
        self.plan['experimental']=True;self.save()
        render(self.path,self.root/'out',('png',))
        manifest=json.loads((self.root/'out/manifest.json').read_text())
        self.assertEqual(manifest['experimental_items'],['effect:rgb_split','transition:push'])
        self.assertEqual(manifest['effects'][0]['status'],'experimental')
        self.plan['experimental']='true';self.save()
        with self.assertRaisesRegex(ValueError,'boolean'):validate_plan(self.path,experimental=True)

    def test_remap_and_interpolation_gates(self):
        for field,value in (('speed',1),('speed',.5),('ramp',{'into_beat':1})):
            with self.subTest(field=field,value=value):
                self.plan['segments'][0][field]=value;self.save()
                with self.assertRaisesRegex(ValueError,field+'.*--experimental'):validate_plan(self.path)
                self.plan['segments'][0].pop(field)
        for mode in ('blend','flow','rife'):
            self.plan['interpolate']=mode;self.save()
            with self.assertRaisesRegex(ValueError,'interpolate:'+mode):validate_plan(self.path)
        self.plan['interpolate']='none';self.save();validate_plan(self.path)
        with patch.dict(os.environ,{'VIDEO_GIF_INTERPOLATE':'flow'}):
            with self.assertRaisesRegex(ValueError,'interpolate:flow'):validate_plan(self.path)
            validate_plan(self.path,interpolate='none')

    def test_cli_interpolation_validation_does_not_leak_environment(self):
        self.save()
        with contextlib.redirect_stderr(io.StringIO()),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.path),'--validate','--no-user-fx','--interpolate','blend']),2)
            self.assertEqual(main([str(self.path),'--validate','--no-user-fx','--interpolate','blend','--experimental']),0)
        self.assertEqual(os.environ['VIDEO_GIF_INTERPOLATE'],'')
        validate_plan(self.path)

    def test_legacy_export_records_usage(self):
        self.save();render(self.path,self.root/'stable',('png',))
        self.assertEqual(json.loads((self.root/'stable/manifest.json').read_text())['experimental_items'],[])
        self.plan['segments'][0]['speed']=1;self.save()
        render(self.path,self.root/'unity',('png',),experimental=True)
        self.assertEqual(json.loads((self.root/'unity/manifest.json').read_text())['experimental_items'],['speed'])

    def test_preview_filters_before_invoking_functions(self):
        calls=[]
        def fake(name):
            def call(a,*args,**kwargs):calls.append(name);return a
            return call
        with contextlib.ExitStack() as stack:
            for registry in (EFFECTS,TRANSITIONS):
                for name,spec in registry.items():stack.enter_context(patch.dict(spec,{'function':fake(name)}))
            preview(self.root/'stable.png')
            self.assertEqual(set(calls),set(catalog()['effects'])|set(catalog()['transitions']))
            self.assertEqual(len(calls),18)
            calls.clear();preview(self.root/'all.png',experimental=True)
            self.assertEqual(set(calls),set(EFFECTS)|set(TRANSITIONS))

    def test_directory_plugins_default_stable_or_explicit_experimental(self):
        self.addCleanup(lambda:EFFECTS.pop('slice_stable',None))
        self.addCleanup(lambda:EFFECTS.pop('slice_experimental',None))
        (self.root/'plugin.py').write_text('from fx import effect\n@effect()\ndef slice_stable(a,t,ctx): return a\n@effect(status="experimental")\ndef slice_experimental(a,t,ctx): return a\n')
        load_directory(self.root)
        self.assertIn('slice_stable',catalog()['effects'])
        self.assertNotIn('slice_experimental',catalog()['effects'])
        self.plan['effects']=[{'name':'slice_experimental'}];self.save()
        with self.assertRaisesRegex(ValueError,'slice_experimental'):validate_plan(self.path)
        validate_plan(self.path,experimental=True)


if __name__=='__main__':unittest.main()
