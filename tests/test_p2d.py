"""P2d technical gate regressions (appeal does not decide availability)."""
import json
from pathlib import Path
import sys
import unittest
import contextlib
import io
import tempfile
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fx import Context, TRANSITIONS
from fx.core import premultiply, catalog, transition
from fx.transitions.gl_common import Shader, random_field
from fx_gate_kit import edge_streaks, endpoint_checks


def mattes(w=160, h=90):
    a = np.zeros((h, w, 4), np.float32)
    b = a.copy()
    a[h//4:3*h//4, w//8:3*w//8] = [.2, .5, .7, .6]
    b[h//4:3*h//4, 5*w//8:7*w//8] = [.8, .3, .4, .8]
    return a, b


def render(name, a, b, p, **params):
    return TRANSITIONS[name]['function'](a, b, p, Context(a.shape[1], a.shape[0]), **params)


def old_glitch(a, p, ctx):
    """Negative control: unbounded block offsets replicate edge texels."""
    s = Shader(a, a, ctx)
    bx, by = np.meshgrid(np.arange((ctx.width+15)//16), np.arange((ctx.height+15)//16))
    dx = (random_field(bx, by, int(p*24))-.5)*.045*np.sin(np.pi*p)
    dy = (random_field(bx, by, 41+int(p*24))-.5)*.045*np.sin(np.pi*p)
    ix = np.arange(ctx.width)//16
    iy = (ctx.height-1-np.arange(ctx.height))//16
    return s.finish(s.sample(s.a, s.x+dx[iy[:, None], ix]/s.ratio,
                             s.y+dy[iy[:, None], ix]), displacement=True)


class Defects(unittest.TestCase):
    def test_bounce_no_incoming_under_panel_or_endpoint_jump(self):
        for w, h in ((160, 90), (90, 160)):
            a, b = mattes(w, h)
            near = render('gl_bounce', a, b, 1e-5)
            self.assertLess(float(np.abs(premultiply(near)-premultiply(a)).mean()), 1e-5)
            np.testing.assert_allclose(premultiply(render('gl_bounce',a,b,1e-7)),
                                       premultiply(a), atol=5e-5)
            clear = np.zeros_like(a)
            solid = np.ones_like(a)
            p = .08
            out = render('gl_bounce', clear, solid, p)
            y = 1-(np.arange(h)+.5)/h
            d = y-abs(np.cos(p*np.pi*3))*(1-np.sin(p*np.pi/2))
            self.assertTrue(np.all(out[d <= 0, :, 3] == 0))
            np.testing.assert_allclose(out[d > .075], 1, atol=1e-6)
            self.assertTrue(np.any(out[(d > 0) & (d <= .075), :, :3] < 1))

    def test_multiply_union_coverage_and_overlap_compositing(self):
        a, b = mattes()
        out = render('gl_multiply_blend', a, b, .5)
        np.testing.assert_allclose(out[..., 3], a[..., 3]+b[..., 3], atol=1e-6)
        for src in (a, b):
            mask = src[..., 3] > 0
            np.testing.assert_allclose(out[mask], src[mask], atol=1e-6)
        a[:] = [.2, .5, .7, .4]
        b[:] = [.8, .3, .4, .6]
        alpha = .4+.6-.4*.6
        rgb = ((1-.6)*.4*np.array([.2,.5,.7]) +
               (1-.4)*.6*np.array([.8,.3,.4]) +
               .4*.6*np.array([.2,.5,.7])*np.array([.8,.3,.4]))/alpha
        np.testing.assert_allclose(render('gl_multiply_blend', a, b, .5)[0,0],
                                   np.r_[rgb, alpha], atol=1e-6)

    def test_color_phase_straight_mix_crossfill_and_pm_bound(self):
        a, b = mattes()
        for p in (.15, .5, .75, .85):
            captured = []
            finish = Shader.finish
            def capture(s, pm, **kwargs):
                captured.append(pm.copy())
                return finish(s, pm, **kwargs)
            with patch.object(Shader, 'finish', capture):
                out = render('gl_color_phase', a, b, p)
            self.assertLessEqual(float((captured[0][...,:3]-captured[0][...,3:4]).max()), 1e-7)
            alpha_phase = p*p*(3-2*p)
            np.testing.assert_allclose(out[...,3],a[...,3]*(1-alpha_phase)+b[...,3]*alpha_phase,atol=1e-6)
            for src in (a, b):
                mask = src[...,3] > 0
                np.testing.assert_allclose(out[mask,:3], src[mask,:3], atol=1e-6)
            hidden_a, hidden_b = a.copy(), b.copy()
            hidden_a[a[...,3]==0,:3] = [1,0,1]
            hidden_b[b[...,3]==0,:3] = [0,1,0]
            np.testing.assert_allclose(render('gl_color_phase', hidden_a, hidden_b, p), out, atol=1e-6)
        a[:] = [.2,.5,.7,.4]
        b[:] = [.8,.3,.4,.6]
        # At p=.5 the independent RGB phases are 25/27, 1/2, 2/27;
        # alpha has its own phase 1/2, irrespective of those RGB phases.
        weights = np.array([25/27,.5,2/27])
        expected = np.array([.2,.5,.7])*(1-weights)+np.array([.8,.3,.4])*weights
        np.testing.assert_allclose(render('gl_color_phase',a,b,.5)[0,0],np.r_[expected,.5],atol=1e-6)

    def check_coverage_crossfade(self, name, lo, hi, **params):
        for w, h in ((160, 90), (90, 160)):
            a, b = mattes(w, h)
            middle = render(name, a, b, .5, **params)
            np.testing.assert_allclose(middle[...,3], (a[...,3]+b[...,3])/2, atol=1e-6)
            np.testing.assert_allclose(render(name,a,b,lo,**params)[...,3],a[...,3],atol=2e-6)
            np.testing.assert_allclose(render(name,a,b,hi,**params)[...,3],b[...,3],atol=2e-6)
            for p in (lo, .5, hi):
                before = render(name,a,b,p-1e-5)
                after = render(name,a,b,p+1e-5)
                self.assertLess(float(np.abs(premultiply(after)-premultiply(before)).mean()), .001)

    def test_dreamy_zoom_coverage_crossfade(self):
        self.check_coverage_crossfade('gl_dreamy_zoom', .45, .55, rotation=0, scale=1)

    def test_hex_shutter_coverage_crossfade(self):
        self.check_coverage_crossfade('hex_shutter', .47, .53)

    def test_glitch_offsets_inside_frame_and_coherent_per_block(self):
        sample = Shader.sample
        for w,h in ((160,90),(270,480),(17,9)):
            a,b = mattes(w,h)
            def capture(s, frame, x, y):
                self.assertGreaterEqual(float(x.min()), .5/w-1e-7)
                self.assertLessEqual(float(x.max()), 1-.5/w+1e-7)
                self.assertGreaterEqual(float(y.min()), .5/h-1e-7)
                self.assertLessEqual(float(y.max()), 1-.5/h+1e-7)
                # A block translates rigidly, including the partial boundary cells.
                for yy in range(0,h,16):
                    rows = slice(max(0,h-yy-16), h-yy)
                    for xx in range(0,w,16):
                        cols = slice(xx, min(w,xx+16))
                        self.assertLess(float(np.ptp((x-s.x)[rows,cols])), 2e-7)
                        self.assertLess(float(np.ptp((y-s.y)[rows,cols])), 2e-7)
                return sample(s,frame,x,y)
            for p in (.1,.51,.53,.57,.9):
                with patch.object(Shader,'sample',capture):
                    render('gl_glitch_memories',a,b,p)


class GateControls(unittest.TestCase):
    def test_shape_edges_partial_cells_and_flat_borders_are_not_streaks(self):
        h,w = 96,160
        y,x = np.indices((h,w))
        for pattern in ((y>h//2), ((x+5)//16+(y+3)//16)%2, np.zeros((h,w))):
            frame = np.ones((h,w,4),np.float32)
            frame[...,:3] = np.asarray(pattern)[...,None]
            self.assertEqual(edge_streaks(frame), [])

    def test_real_glitch_streak_negative_and_fixed_positive(self):
        w,h = 270,480
        rng = np.random.default_rng(42)
        a = rng.random((h,w,4),dtype=np.float32);a[...,3]=1
        ctx = Context(w,h)
        bad = [edge_streaks(old_glitch(a,p,ctx)) for p in (.51,.53,.55,.57)]
        self.assertTrue(any(bad), 'negative control must retain the original glitch streak')
        for p in (.51,.53,.55,.57):
            self.assertEqual(edge_streaks(render('gl_glitch_memories',a,a,p)), [])

    def test_bounce_endpoint_positive_and_broken_negative(self):
        a,b = mattes()
        ctx = Context(160,90)
        bad = {'function': lambda a,b,p,c: a if p==0 else b}
        self.assertEqual(endpoint_checks(bad,a,b,ctx)['level'],'FAIL')
        self.assertEqual(endpoint_checks(TRANSITIONS['gl_bounce'],a,b,ctx)['level'],'PASS')


class Promotion(unittest.TestCase):
    def test_verdict_status_tags_evidence_and_cli_agree(self):
        from fx_render import main
        verdicts = json.loads((ROOT/'wow/fx/gate/p2-tech-verdicts.json').read_text(encoding='utf-8'))
        records = json.loads((ROOT/'wow/fx/gate/p2-status.json').read_text(encoding='utf-8'))
        records = {r['item']:r for r in records}
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(main(['--list','--json','--no-user-fx']),0)
        listing = json.loads(stream.getvalue())['transitions']
        for verdict in verdicts:
            item = verdict['item'];name = item.split(':')[1]
            self.assertEqual(TRANSITIONS[name]['status'],'stable')
            self.assertEqual(listing[name]['style_tags'],verdict['style_tags'])
            self.assertEqual(records[item]['status'],'stable')
            self.assertEqual(records[item]['date'],'2026-11-05')
            self.assertTrue((ROOT/records[item]['evidence_path']).is_file())
        self.assertTrue(all(isinstance(v['style_tags'],list) for v in catalog(True)['transitions'].values()))

    def test_tags_are_editable_metadata_not_parameters(self):
        self.addCleanup(lambda: TRANSITIONS.pop('p2d_tag_test',None))
        @transition(name='p2d_tag_test', style_tags=['custom'])
        def tagged(a,b,p,ctx):return a
        self.assertEqual(catalog()['transitions']['p2d_tag_test']['style_tags'],['custom'])
        TRANSITIONS['p2d_tag_test']['style_tags'] = ['edited']
        self.assertEqual(catalog()['transitions']['p2d_tag_test']['style_tags'],['edited'])
        self.assertNotIn('style_tags',TRANSITIONS['p2d_tag_test']['params'])

    def test_gl_plans_validate_without_experimental(self):
        from PIL import Image
        from fx_render import validate_plan
        from fx.transitions.gl_ports import PORT_NAMES
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new('RGBA',(16,16),(80,120,160,255)).save(root/'a.png')
            for name in PORT_NAMES:
                plan = {'segments':[{'type':'still','image':'a.png','duration_ms':400},
                                    {'type':'still','image':'a.png','duration_ms':400,
                                     'transition':{'name':name,'duration_ms':160}}]}
                (root/'plan.json').write_text(json.dumps(plan))
                validate_plan(root/'plan.json')


if __name__ == '__main__':
    unittest.main()
