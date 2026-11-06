from image_fixtures import ImageCase
from unittest.mock import patch
from image_common import ImageError
import game_assets

class DemoFixTests(ImageCase):
    def test_texture_panel_isolated_without_manual_crop(self):
        from game_tiles import texture_subject
        from PIL import Image,ImageDraw
        im=Image.new('RGB',(256,256),'#202030');d=ImageDraw.Draw(im)
        d.rectangle((110,20,240,180),fill='#607080',outline='#ccddee',width=2)
        for y in range(28,174,10):d.line((115,y,235,y),fill='#405060',width=2)
        d.ellipse((10,30,65,85),fill='#ffaa55')
        cropped,record=texture_subject(im)
        self.assertEqual(record['method'],'largest framed texture panel; semantic review pending')
        self.assertLess(cropped.width,150);self.assertGreater(cropped.height,140)
        full,record=texture_subject(Image.new('RGB',(256,256),'#607080'))
        self.assertEqual(full.size,(256,256));self.assertIsNone(record)

    def test_full_prompt_pipeline_with_measured_failed_preview(self):
        from PIL import Image,ImageDraw
        from pathlib import Path
        from game_prompt_demo import build
        calls=[]
        def generate(req,out,**kwargs):
            out=Path(out);out.mkdir(parents=True,exist_ok=True);calls.append(req)
            cell=Image.new('RGBA',(128,128));ImageDraw.Draw(cell).rectangle((35,18,92,115),fill='#E07A2E',outline='#20182A',width=3)
            cols,rows=(3,2) if '3 columns by 2 rows' in req.prompt else (2,2) if '2 columns by 2 rows' in req.prompt else (1,1)
            im=Image.new('RGBA',(128*cols,128*rows))
            for y in range(rows):
                for x in range(cols):im.paste(cell,(x*128,y*128))
            file=out/'image.png';im.save(file)
            return dict(assets=[{'path':str(file)}],cache_hit=False,subscription_images=1)
        with patch.object(self.adapter,'generate',side_effect=generate):
            result=build(self.adapter,self.request(),self.path/'pack',allow_qa_fail=True)
        self.assertEqual(len(calls),19)
        self.assertEqual(result['measured_qa_status'],'FAIL')
        self.assertTrue((self.path/'pack/export/character.tres').exists())
        self.assertEqual(result['ai_video_calls'],0)
        with patch.object(self.adapter,'generate',side_effect=generate):
            replay=build(self.adapter,self.request(),self.path/'pack',allow_qa_fail=True,resume=True)
        self.assertEqual(replay['measured_qa_status'],'FAIL')
        self.assertTrue(list((self.path/'pack/export-history').glob('*/project.godot')))

    def test_prompt_routes_without_handmade_source_pack(self):
        with patch('game_demo.demo_from_prompt',return_value={'status':'experimental_preview'}) as build,patch('game_assets.print'):
            result=game_assets.main(['demo','game','--prompt','original ice fox','--out',str(self.path/'demo'),'--experimental','--cap','20','--state',str(self.path/'state')])
        self.assertEqual(result,0);self.assertTrue(build.called)
        self.assertFalse(build.call_args.kwargs.get('allow_qa_fail',False))
