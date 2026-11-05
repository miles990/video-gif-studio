"""S-71/73 instruments. RGB is sRGB; straight RGBA composites over #808080.

No aesthetic score is produced. C instruments explicitly retain unknown when
their independent anchor calibration has not been activated in the registry.
"""
from collections import deque
from fractions import Fraction
import math
import cv2
import numpy as np
from threshold_registry import value, check

LUMA = np.array([.2126, .7152, .0722], np.float32)


def rgb(frame):
    a = np.asarray(frame, dtype=np.float32)
    if frame.dtype == np.uint8:
        a = a / 255
    if a.shape[-1] == 4:
        a = a[..., :3] * a[..., 3:4] + (128/255) * (1-a[..., 3:4])
    return np.clip(a, 0, 1)


def linear(a):
    return np.where(a <= .04045, a/12.92, ((a+.055)/1.055)**2.4)


def standard(material='STD-P', width=1280, height=720):
    """Seed 6 board; noise is added AFTER the subject (amendment A6-1)."""
    yy, xx = np.mgrid[:720, :1280]
    y = 60+130*(xx/1279+yy/719)/2 + (((xx//32+yy//32)%2)*2-1)*20
    a = np.stack([y*1.05, y, y*.9], -1)
    radius = np.hypot(xx-640, yy-360)
    a[radius <= 160] = [225, 190, 160]
    a[270:290, 600:680] = [35, 30, 25]
    bars = (xx >= 40) & (xx < 280) & ((xx-40)%20 < 3) & (yy >= 570) & (yy < 690)
    a[bars] = 255
    a[40:160, 1040:1240] = [255, 240, 200]
    a += np.random.default_rng(6).normal(0, 6, a.shape)
    if material == 'STD-HK':
        a = a*.15 + [215, 200, 170]
    alpha = np.ones((720, 1280, 1))*255
    if material == 'STD-A':
        alpha[..., 0] = np.clip((164-radius)/4, 0, 1)*255
        a[alpha[..., 0] == 0] = np.random.default_rng(7).uniform(0, 255, (int((alpha[..., 0] == 0).sum()), 3))
    result = np.concatenate([np.clip(a, 0, 255), alpha], -1).round().astype(np.uint8)
    return cv2.resize(result, (width, height), interpolation=cv2.INTER_AREA) if (width, height) != (1280, 720) else result


def moving(frame, index):
    h, w = frame.shape[:2]
    return cv2.warpAffine(frame, np.float32([[1, 0, 4*index*w/1280], [0, 1, 0]]),
                          (w, h), borderMode=cv2.BORDER_REFLECT_101)


def flash_masks(before, after):
    a, b = linear(rgb(before)), linear(rgb(after))
    la, lb = a@LUMA, b@LUMA
    delta = lb-la
    general = (np.abs(delta) >= value('wcag.general.delta.min')) & (np.minimum(la, lb) < value('wcag.general.dark.max'))
    ra = a[..., 0]/np.maximum(a.sum(-1), 1e-12)
    rb = b[..., 0]/np.maximum(b.sum(-1), 1e-12)
    red_delta = (np.maximum(0, b[..., 0]-b[..., 1]-b[..., 2])-np.maximum(0, a[..., 0]-a[..., 1]-a[..., 2]))*320
    red = (np.maximum(ra, rb) >= value('wcag.red.saturation.min')) & (np.abs(red_delta) > value('wcag.red.delta.min'))
    return general, red, delta, red_delta


def measures(reference, output, flow=True):
    a, b = rgb(reference)@LUMA*255, rgb(output)@LUMA*255
    blur = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    ma, mb = blur(a), blur(b)
    va, vb, cov = blur(a*a)-ma*ma, blur(b*b)-mb*mb, blur(a*b)-ma*mb
    c1, c2 = (.01*255)**2, (.03*255)**2
    ssim = ((2*ma*mb+c1)*(2*cov+c2))/((ma*ma+mb*mb+c1)*(va+vb+c2))
    displacement = 0.
    if flow and min(a.shape)>=32:
        f = cv2.calcOpticalFlowFarneback(a, b, None, .5, 4, 21, 3, 5, 1.1, 0)
        displacement = float(np.linalg.norm(f, axis=-1).mean())*720/a.shape[0]
    def sharp(x, quarter=False):
        if quarter:
            x = cv2.resize(x, (max(2, x.shape[1]//4), max(2, x.shape[0]//4)), interpolation=cv2.INTER_AREA)
        else:
            h, w = x.shape
            x = x[max(0,h//2-100):h//2+100, max(0,w//2-100):w//2+100]
        return float(cv2.Laplacian(x, cv2.CV_32F).var())
    def ratio(quarter):
        base = sharp(a, quarter)
        return sharp(b, quarter)/base if base > 1e-12 else None
    g, r, _, _ = flash_masks(reference, output)
    result = dict(dY=float(np.abs(b-a).mean()), area8=float((np.abs(b-a)>value('measure.area8.min')).mean()),
                  ssim_loss=float(1-ssim.mean()), disp=displacement, flash_area=float(g.mean()),
                  red_flash=float(r.mean()), center_sharp=ratio(False), sharp4=ratio(True))
    delta=lab(output)-lab(reference)
    result['deltaE76']=float(np.linalg.norm(delta,axis=-1).mean())
    result['chroma_delta']=float(np.linalg.norm(delta[...,1:],axis=-1).mean())
    supported = min(a.shape) >= 32
    result['perceived'] = perceived(result) if supported else None
    result['perceived_status'] = 'measured' if supported else 'unsupported'
    if not supported:
        result['perceived_reason'] = 'Perceived calibration requires both dimensions >=32; use native effect controls.'
    return result


def lab(frame):
    """CIELAB D65 via OpenCV float sRGB conversion (L*=0..100)."""
    return cv2.cvtColor(rgb(frame).astype(np.float32),cv2.COLOR_RGB2Lab)


def visibility_family(name):
    from fx_gate_pairs import family
    return 'motion' if family('effect',name) in ('effect-motion','effect-layout') else 'tonal'


def visibility_residual(reference, output, family='tonal'):
    """Lab residual; geometry is normalized against reference texture contrast.

    Tonal changes use actual Delta E. Motion uses the same local texture scale
    for reference and output, preventing the source contrast from becoming an
    effect-strength multiplier. The floor handles truly flat/unobservable areas.
    """
    a,b=lab(reference),lab(output)
    if family=='motion':
        y=a[...,0];mean=cv2.GaussianBlur(y,(0,0),3)
        texture=np.sqrt(np.maximum(0,cv2.GaussianBlur(y*y,(0,0),3)-mean*mean))
        scale=np.maximum(texture,1.)[...,None]
        return (b-a)/scale,a/scale
    return b-a,a


def perceived(m):
    return float(np.clip(max(m['dY']/value('perceived.luma.scale'), m['ssim_loss'],
                             m['disp']/value('perceived.displacement.scale'), m['flash_area']), 0, 1))


def onset_contrast(before, after, untreated):
    """High-pass weighted onset change divided by concurrent scene motion.

    before/after are matched effect-minus-reference residual frames. This removes
    scene motion from the numerator without removing its masking denominator.
    """
    def weighted(x):
        high = x-cv2.GaussianBlur(x, (0, 0), 2)
        magnitude=lambda v:np.linalg.norm(v,axis=-1).mean() if v.ndim==3 else np.abs(v).mean()
        return float(magnitude(high) + value('visibility.luma.weight')*magnitude(x))
    onset = weighted(np.mean(after, axis=0)-np.mean(before, axis=0))
    noise = float(np.median([weighted(b-a) for a,b in zip(untreated, untreated[1:])])) if len(untreated)>1 else 0.
    # Bounded motion masking: even a hard cut cannot change the same residual
    # by an unbounded factor. The cutoff remains a C calibration candidate.
    return onset/(value('visibility.noise.floor')+min(noise,value('visibility.noise.floor')*3))


class FlashCounter:
    """Simultaneous same-direction relative-luminance pairs, then area gating.

    Extrema follow each monotone run; unrelated subthreshold changes cannot
    accumulate across reversals. Hold the first area-qualified cohort until its
    opposite transition, rather than counting successive pixel groups in a fade.
    Rising and falling lobes are tracked separately so opposite halves cannot
    cancel, and one pair is never counted twice.
    """
    def __init__(self):
        self.previous = None
        self.states = {}
        self.lobes = {}
        self.maxima = {'general': 0, 'red': 0}
        self.windows = []

    def push_frame(self, frame, index, fps):
        """CFR clock: integer frame index / rational frame rate, never float sums."""
        self.push(frame, Fraction(index, 1)/Fraction(str(fps)))

    def push(self, frame, seconds):
        # Legacy callers supply seconds; recover their rational presentation
        # clock instead of comparing binary-float values at one-second edges.
        seconds = seconds if isinstance(seconds, Fraction) else Fraction(str(seconds)).limit_denominator(1_000_000)
        current = linear(rgb(frame))
        luma = current@LUMA
        red = np.maximum(0, current[...,0]-current[...,1]-current[...,2])*320
        saturated = current[...,0]/np.maximum(current.sum(-1),1e-12) >= value('wcag.red.saturation.min')
        # Register near-exact camera translations before comparing luminance
        # pairs. Moving scene edges are not changes in the scene's luminance.
        # A photometric change affecting the WCAG area cannot pass the strict
        # 95th-percentile residual check; it still takes the ordinary flash path.
        if self.previous is not None and min(luma.shape)>=32:
            old=self.previous
            h,w=luma.shape; size=(min(w,320),min(h,180))
            a=cv2.resize(old,size);b=cv2.resize(luma,size)
            shift,response=cv2.phaseCorrelate(a,b)
            dx,dy=shift[0]*w/size[0],shift[1]*h/size[1]
            if response>.5 and .5<math.hypot(dx,dy)<min(w,h)*.1:
                matrix=np.float32([[1,0,dx],[0,1,dy]])
                aligned=cv2.warpAffine(old,matrix,(w,h),borderMode=cv2.BORDER_REFLECT_101)
                valid=cv2.warpAffine(np.ones_like(old),matrix,(w,h))>.999
                residual=np.abs(aligned-luma)[valid]
                if residual.size and np.quantile(residual,.95)<.025 and residual.mean()<np.abs(old-luma).mean()*.5:
                    for state in self.states.values():
                        for index,array in enumerate(state):
                            warped=cv2.warpAffine(array.astype(np.float32),matrix,(w,h),flags=cv2.INTER_NEAREST)
                            array[:]=warped.astype(array.dtype)
                            if index in (1,2,5):array[~valid]=0
                    for lobes in self.lobes.values():
                        for lobe in lobes.values():
                            if lobe.get('cohort') is not None:
                                lobe['cohort']=cv2.warpAffine(lobe['cohort'].astype(np.uint8),matrix,(w,h),flags=cv2.INTER_NEAREST).astype(bool)&valid
        self.previous=luma.copy()
        for kind, signal in [('general', luma), ('red', red)]:
            if kind not in self.states:
                self.states[kind] = [signal.copy(), np.zeros(signal.shape, np.int8), np.zeros(signal.shape, bool), saturated.copy(), signal.copy(), np.zeros(signal.shape,np.int8)]
                self.lobes[kind] = {sign:dict(events=deque()) for sign in (-1,1)}
                continue
            extreme, direction, pending, was_sat, previous, trend = self.states[kind]
            step = np.sign(signal-previous).astype(np.int8)
            reversal = (step != 0) & (step != trend)
            extreme[reversal] = previous[reversal]
            trend[step != 0] = step[step != 0]
            delta = signal-extreme
            limit = value('wcag.general.delta.min') if kind=='general' else value('wcag.red.delta.min')
            eligible = ((np.abs(delta)>=limit) & (np.minimum(signal,extreme)<value('wcag.general.dark.max'))) if kind=='general' else ((np.abs(delta)>limit) & (saturated|was_sat))
            sign = np.sign(delta).astype(np.int8)
            changed = eligible & (sign != direction)
            # Area qualification precedes pairing: unrelated pixels changing
            # at different times must never assemble a synthetic flash.
            for polarity, lobe in self.lobes[kind].items():
                mask = changed & (sign == polarity)
                opposite = changed & (sign == -polarity)
                cohort = lobe.get('cohort')
                qualifies = cohort is not None and np.mean(cohort & opposite) >= value('wcag.area.min')
                recent = lobe['events']
                while recent and seconds-recent[0] >= 1:
                    recent.popleft()
                if qualifies:
                    recent.append(seconds)
                    lobe['cohort'] = None
                    count = len(recent)
                    self.maxima[kind] = max(self.maxima[kind], count)
                    if count > value('wcag.flashes.max'):
                        first = recent[0]
                        self.windows.append(dict(kind=kind, start_seconds=float(first), end_seconds=float(first+1), flashes=count))
                if lobe.get('cohort') is None and np.mean(mask) >= value('wcag.area.min'):
                    lobe['cohort'] = mask.copy()
            pending[changed] = ~pending[changed]
            direction[changed] = sign[changed]
            # Follow the current trend to its extreme, preserving small reverse
            # steps until their cumulative change crosses the fixed threshold.
            update = changed | ((direction>0)&(signal>extreme)) | ((direction<0)&(signal<extreme))
            extreme[update] = signal[update]
            was_sat[update] = saturated[update]
            previous[:] = signal

    def report(self):
        return dict(standard='WCAG 2.3.1',instrument='simultaneous area pairs v3',window='[t, t+1 s)', timing='rational integer frame clock', max_flashes_per_s=max(self.maxima.values()),
                    general_max=self.maxima['general'], red_max=self.maxima['red'],
                    status='harsh' if self.windows else 'ok', windows=self.windows)


def classify(metrics, onset, intent='hit', transition=False, consecutive=1, data=None, family='tonal'):
    if metrics.get('perceived_status')=='unsupported':
        return dict(perceived_measured=None,status='unsupported',measurements=metrics,
                    reason=metrics['perceived_reason'],advice=metrics['perceived_reason'],instrument_status={'visibility':'unknown','harshness':'unknown'})
    visibility = check('visibility.onset_contrast.min', onset, context=family,data=data, intent=intent)
    sharp = metrics.get('sharp4')
    destruction = check('harshness.sharp4.min', sharp, data=data) if sharp is not None else {'decision':'unknown'}
    structure = check('harshness.ssim_loss.max', metrics['ssim_loss'], data=data)
    status = 'invisible' if visibility['decision']=='fail' else 'unknown' if visibility['decision']=='unknown' else 'ok'
    if intent=='texture' and visibility['status']=='active':status='ok'
    if status=='ok' and not transition and 'unknown' in (destruction['decision'],structure['decision']):status='unknown'
    if not transition and consecutive >= value('harshness.frames.min') and destruction['decision']=='fail' and structure['decision']=='fail':
        status = 'destructive'
    return dict(perceived_measured=metrics['perceived'], status=status, onset_contrast=onset,visibility_family=family,
                visibility_exemption='declared texture intent' if intent=='texture' else None,
                wcag_flashes_max_per_s=0, measurements=metrics,
                instrument_status={'visibility':visibility['decision'], 'harshness':destruction['decision']},
                advice={'unknown':'Visibility unknown: independent family anchors and 2AFC calibration pending.', 'ok':'Review playback in context.', 'invisible':'Move away from the cut or increase perceived intensity.',
                        'destructive':'Reduce blur distance or shorten the effect window.'}[status])
