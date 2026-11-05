"""Every P2b port: endpoint, matte, dtype, determinism, shape and progress gates."""
import hashlib
import inspect
import json
from pathlib import Path
import sys
import unittest
import re
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from fx import Context, TRANSITIONS
from fx.core import catalog, premultiply
from fx.transitions.gl_ports import PORT_NAMES
from fx.transitions.gl_common import Shader, grid


# These shaders intentionally transform or relight the whole image. Their MAD
# can rise while motion/flash builds; see build-notes-p2b.md for measured ranks.
NONMONOTONIC = {
    'gl_dreamy_zoom', 'gl_rotate_scale_fade', 'gl_swirl', 'gl_overexposure',
}
RANDOM = {'gl_burn_through', 'gl_luminance_melt', 'gl_random_squares',
          'gl_wind', 'gl_crosshatch', 'gl_perlin_dissolve'}

# Sampled coverage moves with the subject; it is not clipped to the source union.
DISPLACEMENT = {'gl_cross_warp','gl_directional_warp','gl_dreamy','gl_dreamy_zoom',
    'gl_rotate_scale_fade','gl_swirl','gl_water_drop','gl_pixelize','gl_hexagonalize',
    'gl_glitch_memories','gl_scale_in','gl_bounce'}


def texture(w, h, seed, matte=False):
    rng = np.random.default_rng(seed)
    result = rng.random((h, w, 4), dtype=np.float32)
    result[..., 3] = 1
    if matte:
        yy, xx = np.indices((h,w))
        radius = min(w,h)*.32
        # Feathered circle with both exact zero and fractional alpha.
        result[...,3] = np.clip((radius-np.hypot(xx-(w-1)/2,yy-(h-1)/2))/3,0,1)
    return result


def rank(values):
    values = np.asarray(values)
    order = np.argsort(values,kind='stable')
    ranks = np.empty(len(values),float)
    for value in np.unique(values):
        mask = values[order] == value
        ranks[order[mask]] = np.flatnonzero(mask).mean()
    return ranks


def progress_measure(name, w=160, h=90):
    a,b = texture(w,h,1),texture(w,h,2)
    fn = TRANSITIONS[name]['function']; ctx = Context(w,h,seed=19)
    errors = [float(np.mean(np.abs(fn(a,b,float(p),ctx)-b))) for p in np.linspace(0,1,21)]
    rho = float(np.corrcoef(np.arange(21),rank(errors))[0,1])
    return errors,rho


class PortContract(unittest.TestCase):
    def test_inventory_defaults_attribution_and_stable_visibility(self):
        provenance = json.loads((ROOT/'wow/fx/p2b-provenance.json').read_text(encoding='utf-8'))
        self.assertEqual(len(PORT_NAMES),32)
        self.assertEqual({x['name'] for x in provenance},set(PORT_NAMES))
        for entry in provenance:
            spec = TRANSITIONS[entry['name']]
            self.assertEqual(spec['status'],'stable')
            self.assertIn(entry['name'],catalog()['transitions'])
            self.assertEqual({p['name'] for p in entry['uniforms']},set(spec['params']))
            for uniform in entry['uniforms']:
                literal=uniform['default'].split(';')[0].split('//')[0].strip()
                if uniform['type'].endswith('vec2') or uniform['type'].endswith('vec3') or uniform['type'].endswith('vec4'):
                    count=int(uniform['type'][-1])
                    values=[float(v.strip()) for v in re.search(r'\((.*)\)',literal).group(1).split(',')]
                    expected=tuple(values*count if len(values)==1 else values)
                elif literal in ('true','false'):expected=literal=='true'
                else:expected=float(literal)
                self.assertEqual(spec['params'][uniform['name']]['default'],expected)
            source = Path(spec['source']).read_text(encoding='utf-8')
            for value in (entry['author'],entry['license'],entry['source'],entry['sha256']):
                self.assertIn(value,source)
            self.assertEqual(inspect.signature(spec['function']).parameters['p'].default,inspect.Parameter.empty)

    def test_uv_pixel_centres_identity_and_border_clamp(self):
        for w,h in ((321,181),(1000,100),(181,321)):
            a = texture(w,h,9,True); ctx = Context(w,h)
            shader = Shader(a,a,ctx); x,y = grid(w,h)
            np.testing.assert_allclose(shader.sample(shader.a,x,y),premultiply(a),atol=1e-7)
            np.testing.assert_allclose(shader.sample(shader.a,x*0-10,y),np.repeat(shader.a[:,:1],w,axis=1),atol=1e-7)

    def test_hand_derived_formula_landmarks(self):
        # Independent shader landmarks, avoiding a duplicate implementation:
        # ScaleIn samples the exact image centre; ColorDistance switches identical
        # colors; a Bayer half reveal covers exactly half of each 8x8 tile;
        # grayscale uses Rec.709 luma; full-turn rotation is axis-aligned at .5.
        w=h=160; ctx=Context(w,h)
        a=np.zeros((h,w,4),np.float32);a[...,3]=1
        b=a.copy();b[...,0]=1
        output=TRANSITIONS['gl_scale_in']['function'](a,b,.25,ctx)
        np.testing.assert_allclose(output[...,0],.25,atol=1e-6)
        output=TRANSITIONS['gl_dither_dissolve']['function'](a,b,.5,ctx,dotSize=1/160)
        self.assertAlmostEqual(float(output[...,0].mean()),.5,places=6)
        output=TRANSITIONS['gl_color_distance']['function'](b,b,.5,ctx)
        np.testing.assert_allclose(output,b,atol=1e-6)
        output=TRANSITIONS['gl_fade_grayscale']['function'](b,b,.5,ctx,intensity=0)
        self.assertTrue(np.all(output[...,0] > output[...,1]))
        self.assertAlmostEqual(float(output[0,0,1]),.2126*.5,places=5)
        output=TRANSITIONS['gl_multiply_blend']['function'](b,b,.5,ctx)
        np.testing.assert_allclose(output,b,atol=1e-6)

    def test_radial_geometry_preserves_circle_axes(self):
        # A radial source is invariant to a swirl; uniform rotations/scales must
        # retain equal pixel radii on a very wide or portrait canvas.
        for w,h in ((321,181),(1000,100),(181,321)):
            yy,xx=np.indices((h,w),dtype=np.float32)
            radius=min(w,h)/24
            disk=np.clip(radius+.5-np.hypot(xx-(w-1)/2,yy-(h-1)/2),0,1)
            a=np.zeros((h,w,4),np.float32);a[...,:3]=disk[...,None];a[...,3]=1
            for name,params in (('gl_swirl',{}),('gl_rotate_scale_fade',{}),
                                ('gl_scale_in',{}),('gl_dreamy_zoom',{'rotation':0})):
                p=.25 if name=='gl_dreamy_zoom' else .5
                result=TRANSITIONS[name]['function'](a,a,p,Context(w,h),**params)
                threshold=.75 if name=='gl_dreamy_zoom' else .5
                rows,cols=np.nonzero(result[...,0]>threshold)
                ratio=(cols.max()-cols.min()+1)/(rows.max()-rows.min()+1)
                self.assertLessEqual(abs(ratio-1),.03,(name,w,h,ratio))

    def test_bounce_sparse_portrait_never_erases_both_subjects(self):
        w,h=100,181
        a=texture(w,h,1,True);b=texture(w,h,2,True)
        fn=TRANSITIONS['gl_bounce']['function'];ctx=Context(w,h)
        for p in np.linspace(0,1,48):
            result=fn(a,b,float(p),ctx)
            self.assertGreater(float(result[...,3].sum()),10,(p,'entire matte disappeared'))


def endpoint_test(name):
    def test(self):
        fn=TRANSITIONS[name]['function'];ctx=Context(640,360)
        for dtype in (np.uint8,np.float32):
            a,b=texture(640,360,1),texture(640,360,2)
            if dtype==np.uint8:a,b=np.rint(a*255).astype(dtype),np.rint(b*255).astype(dtype)
            for p,expected in ((0,a),(1,b)):
                result=fn(a,b,p,ctx)
                self.assertEqual(result.dtype,dtype)
                np.testing.assert_array_equal(result,expected)
    return test


def alpha_test(name):
    def test(self):
        fn=TRANSITIONS[name]['function'];ctx=Context(321,181,seed=19)
        a,b=texture(321,181,1,True),texture(321,181,2,True)
        clean_a,clean_b=a.copy(),b.copy()
        clean_a[clean_a[...,3]==0,:3]=0;clean_b[clean_b[...,3]==0,:3]=0
        for p in (.25,.5,.75):
            result=fn(a,b,p,ctx);clean=fn(clean_a,clean_b,p,ctx)
            self.assertTrue(np.isfinite(result).all())
            self.assertGreaterEqual(float(result.min()),0);self.assertLessEqual(float(result.max()),1)
            np.testing.assert_allclose(premultiply(result),premultiply(clean),atol=1e-6)
            if name not in DISPLACEMENT:
                self.assertTrue(np.all(result[(a[...,3]==0)&(b[...,3]==0),3]==0))
            aa,bb=a.copy(),b.copy();aa[...,3]=1;bb[...,3]=1
            np.testing.assert_allclose(fn(aa,bb,p,ctx)[...,3],1,atol=1/255)
        # Inputs are immutable from the caller's perspective.
        np.testing.assert_array_equal(a,texture(321,181,1,True))
        np.testing.assert_array_equal(b,texture(321,181,2,True))
    return test


def shape_test(name):
    def test(self):
        fn=TRANSITIONS[name]['function']
        for w,h in ((321,181),(1000,100),(181,321)):
            a,b=texture(w,h,1),texture(w,h,2);ctx=Context(w,h,seed=19)
            for p in (.25,.5,.75):
                result=fn(a,b,p,ctx)
                self.assertEqual(result.shape,a.shape);self.assertEqual(result.dtype,a.dtype)
                self.assertTrue(np.isfinite(result).all())
            aa,bb=np.rint(a*255).astype(np.uint8),np.rint(b*255).astype(np.uint8)
            result=fn(aa,bb,.37,ctx)
            self.assertEqual(result.dtype,np.uint8)
            expected=fn(aa.astype(np.float32)/255,bb.astype(np.float32)/255,.37,ctx)
            np.testing.assert_allclose(result.astype(float)/255,expected,atol=1/255)
    return test


def deterministic_test(name):
    def test(self):
        fn=TRANSITIONS[name]['function'];a,b=texture(321,181,1),texture(321,181,2)
        ctx=Context(321,181,seed=19)
        for p in (.25,.5,.75):
            first=fn(a,b,p,ctx);second=fn(a,b,p,ctx)
            self.assertEqual(hashlib.sha256(first.tobytes()).digest(),hashlib.sha256(second.tobytes()).digest())
        if name in RANDOM:
            self.assertFalse(np.array_equal(fn(a,b,.5,ctx),fn(a,b,.5,Context(321,181,seed=20))))
    return test


def progress_test(name):
    def test(self):
        errors,rho=progress_measure(name)
        self.assertEqual(errors[-1],0)
        self.assertLess(np.mean(errors[-5:]),np.mean(errors[:5]))
        if name not in NONMONOTONIC:self.assertLessEqual(rho,-.8,(name,rho,errors))
    return test


for name in PORT_NAMES:
    for kind, factory in (('endpoints',endpoint_test),('alpha',alpha_test),('canvas_dtype',shape_test),
                          ('deterministic',deterministic_test),('progress',progress_test)):
        setattr(PortContract,f'test_{name}_{kind}',factory(name))

if __name__=='__main__':unittest.main()
