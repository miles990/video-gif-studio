import sys
from pathlib import Path
import unittest
import tempfile
import subprocess
import json
import re
import os
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from game_engines import export_engines
from image_common import write,ImageError


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.scratch',prefix='engine-test-');self.path=Path(self.tmp.name);self.manifests=[]
        for name in ('idle','attack'):
            folder=self.path/name;folder.mkdir();rows=[]
            for i,duration in enumerate([80,120,100]):
                im=Image.new('RGBA',(32,32));ImageDraw.Draw(im).rectangle((6+i,5,22,27),fill=(190,100,50,255));im.putpixel((7,4),(190,100,50,80));im.save(folder/f'{i}.png')
                rows.append(dict(file=f'{i}.png',duration_ms=duration))
            m=dict(state=name,canvas=[32,32],pivot=[16,27],alpha_mode='straight',pixel_scale=1,fps=10,loop=name=='idle',events=[dict(name='hit',frame=1,time_ms=80)] if name=='attack' else [],frames=rows)
            write(folder/'anim.json',m);self.manifests.append(folder/'anim.json')
    def tearDown(self):self.tmp.cleanup()

    def test_native_roundtrip_multipage_timing_events(self):
        out=self.path/'export';packed=export_engines(self.manifests,out,['godot4','unity','phaser-hash','phaser-array','pixi','aseprite'],max_size=80,padding=2,extrude=1,pixel=True)
        self.assertEqual(len(packed['pages']),2)
        for engine in packed['engines']:self.assertEqual(packed['engines'][engine]['engine_load'],'untested')
        tres=(out/'character.tres').read_text();self.assertIn('load_steps=9',tres);self.assertIn('format=3',tres)
        for page_no,page in enumerate(packed['pages']):
            atlas=json.loads((out/f'phaser-hash-{page_no:03d}.json').read_text())
            self.assertTrue(atlas['meta']['related_multi_packs'])
            with Image.open(out/page['file']) as image:
                for name,f in atlas['frames'].items():
                    state,index=name.split('/');source=self.path/state/(str(int(index))+'.png');r=f['frame']
                    with Image.open(source) as src:self.assertEqual(image.crop((r['x'],r['y'],r['x']+r['w'],r['y']+r['h'])).tobytes(),src.tobytes())
            meta=(out/(page['file']+'.meta')).read_text();self.assertIn('filterMode: 0',meta);self.assertRegex(meta,r'guid: [a-f0-9]{32}')
            rects=re.findall(r'      name: "([^"]+)"\n      rect:\n        serializedVersion: 2\n        x: (\d+)\n        y: (\d+)\n        width: (\d+)\n        height: (\d+)',meta)
            for name,x,y,w,h in rects:
                x,y,w,h=map(int,(x,y,w,h));top=page['size'][1]-y-h;state,index=name.split('/')
                with Image.open(out/page['file']) as sheet,Image.open(self.path/state/(str(int(index))+'.png')) as src:self.assertEqual(sheet.crop((x,top,x+w,top+h)).tobytes(),src.tobytes())
        anims=json.loads((out/'anims.json').read_text())['anims'];a=anims[1]
        self.assertEqual([f['duration'] for f in a['frames']],[80,120,100]);self.assertEqual(a['events'][0]['frame'],1)

    def test_shared_contract_and_bad_events_rejected(self):
        data=json.loads(self.manifests[1].read_text());data['pivot']=[15,27];write(self.manifests[1],data)
        with self.assertRaises(ImageError):export_engines(self.manifests,self.path/'bad')
        self.assertFalse((self.path/'bad').exists())

    def test_real_godot4_load_and_playback(self):
        engine=Path('C:/Users/User/src/vgs-fx-private/tools/godot4/Godot_v4.7.2-stable_win64_console.exe')
        if not engine.exists():self.skipTest('Godot 4 portable engine not installed')
        out=self.path/'godot';export_engines(self.manifests,out,['godot4'])
        userdata=self.path/'userdata';userdata.mkdir();env=dict(os.environ,APPDATA=str(userdata),LOCALAPPDATA=str(userdata))
        imported=subprocess.run([str(engine),'--headless','--editor','--path',str(out),'--quit'],capture_output=True,text=True,timeout=60,env=env)
        self.assertEqual(imported.returncode,0,imported.stdout+imported.stderr)
        played=subprocess.run([str(engine),'--headless','--path',str(out),'--fixed-fps','120','--script','check_frames.gd'],capture_output=True,text=True,timeout=60,env=env)
        self.assertEqual(played.returncode,0,played.stdout+played.stderr);self.assertIn('S14_GODOT_PASS',played.stdout);self.assertNotIn('SCRIPT ERROR',played.stderr)


if __name__=='__main__':unittest.main()
