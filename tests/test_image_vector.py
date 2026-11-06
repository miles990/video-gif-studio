import numpy as np
from PIL import Image,ImageDraw
from image_fixtures import ImageCase
from image_common import ImageError,write
from image_vector import safe_svg,trace,rasterize


class VectorTests(ImageCase):
    def test_static_safety_positive_and_seven_negative_controls(self):
        safe='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient></defs><path fill="url(#g)" d="M0,0 L50,0 L50,50 Z"/></svg>'
        self.assertEqual(safe_svg(safe)[1]['status'],'PASS')
        bad=['<script/>','<path onload="x()"/>','<foreignObject/>','<use href="https://example.test/x"/>','<image href="data:image/png;base64,eA=="/>','<path style="fill:url(http://example.test)"/>']
        for node in bad:
            with self.assertRaises(ImageError):safe_svg('<svg>'+node+'</svg>')
        with self.assertRaises(ImageError):safe_svg('<!DOCTYPE svg [<!ENTITY a "x">]><svg>&a;</svg>')
        with self.assertRaises(ImageError):safe_svg('<svg><text>system font</text></svg>')

    def test_trace_no_raster_and_resolution_consistency(self):
        im=Image.new('RGBA',(128,128));d=ImageDraw.Draw(im);d.rectangle((24,24,104,104),fill='#c03020');d.rectangle((45,45,83,83),fill='#edc421');im.save(self.fixture)
        svg=self.path/'graphic.svg';report=trace(self.fixture,svg,colors=3)
        self.assertEqual(report['svg_source'],'traced');self.assertNotIn('<image',svg.read_text())
        images={size:rasterize(svg,size) for size in (512,2048,4096)}
        high=np.array(images[4096].resize((512,512),Image.Resampling.LANCZOS)).astype(float)
        low=np.array(images[512]).astype(float)
        # Area-normalized error is sensitive to inflated/coarsely scaled raster edges.
        self.assertLess(np.mean(abs(high-low)),1)
        for size,im in images.items():
            alpha=np.array(im)[size//2,:,3]/255
            edge=np.where((alpha>.1)&(alpha<.9))[0]
            self.assertLessEqual(len(edge),4)  # two boundaries, <=2 samples each

    def test_fx_input_rejects_unsafe_and_renders_traced_svg(self):
        from fx_render import validate_plan,render
        bad=self.path/'bad.svg';bad.write_text('<svg><script>bad()</script></svg>')
        plan=self.path/'plan.json';write(plan,dict(segments=[dict(type='still',image=str(bad),duration_ms=100)]))
        with self.assertRaises(ImageError):validate_plan(plan)
        im=Image.new('RGBA',(64,64),'red');im.save(self.fixture);svg=self.path/'ok.svg';trace(self.fixture,svg)
        write(plan,dict(segments=[dict(type='still',image=str(svg),duration_ms=100)]))
        validate_plan(plan);render(plan,self.path/'render',('png',))
        self.assertTrue(list((self.path/'render/frames').glob('*.png')))
