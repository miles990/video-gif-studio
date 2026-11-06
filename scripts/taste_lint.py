"""User-taste advice with explicit rule-break annotations; technical gates stay separate."""
from copy import deepcopy
import numpy as np
from taste_common import ROOT, read, value, compare_curve

RULES = ('intent_coverage', 'focal_hierarchy', 'deletion_test', 'weakest_window', 'default_distance',
         'eye_trace', 'cut_on_action', 'shot_cv', 'pre_peak_valley', 'mickey_mousing', 'audio_bridge',
         'token_font', 'token_transition', 'token_lut', 'token_motion', 'token_texture', 'token_sfx',
         'shot_size_variation', 'angle_30', 'axis_180', 'one_motion', 'effect_budget', 'design_curve')


def exempts(annotation,rule):
    named={'30_degree':'angle_30'}.get(annotation.get('rule'),annotation.get('rule'))
    transition=annotation.get('kind',annotation.get('transition'))
    if isinstance(transition,dict):transition=transition.get('name',transition.get('type'))
    jump=transition=='jump_cut'
    return named in (rule,'*','all') or (jump and rule in ('angle_30','eye_trace','cut_on_action'))


def finding(rule, shot, measured, threshold, suggestion, element=None, fps=30, severity='warning'):
    obj = element or {}; breaks = obj.get('rule_break', [])
    if isinstance(breaks, dict): breaks = [breaks]
    reason = next((b['reason'] for b in breaks if exempts(b,rule) and isinstance(b.get('reason'), str) and b['reason'].strip()), None)
    if reason is None and exempts({'transition':obj.get('transition')},rule):
        reason='Explicit jump_cut transition'
    time = obj.get('start', obj.get('time', obj.get('start_ms', obj.get('at_ms', 0))/1000))
    return dict(rule=rule, shot=shot, element_id=obj.get('id', str(shot)), time=round(time, 3), frame=round(time*fps),
                measured=measured, threshold=threshold, suggestion=suggestion, severity=severity,
                status='annotated' if reason else 'advice', reason=reason, axis='user_taste')


def level_design(board):
    from taste_common import curve_points
    if board.get('design_curve') is not None:
        return float(np.std(curve_points(board['design_curve'])[:,1])) < .02
    return board.get('style','').lower() in ('ambient','flat','meditative','sustained')


def exemption_summary(board, rows):
    """List declared exceptions even if no current warning triggers them."""
    declared=[]
    def walk(obj,path):
        if isinstance(obj,list):
            for i,v in enumerate(obj):walk(v,f'{path}[{i}]')
        elif isinstance(obj,dict):
            breaks=obj.get('rule_break',[])
            if isinstance(breaks,dict):breaks=[breaks]
            for b in breaks:
                if isinstance(b,dict) and str(b.get('reason','')).strip():declared.append(dict(path=path,**b))
            if exempts({'transition':obj.get('transition')},'angle_30'):
                declared.append(dict(path=path,transition=obj['transition'],reason='Explicit jump_cut transition'))
            for k,v in obj.items():
                if k!='rule_break':walk(v,path+'.'+k)
    walk(board,'storyboard')
    global_breaks=board.get('rule_break',[])
    if isinstance(global_breaks,dict):global_breaks=[global_breaks]
    switch=board.get('taste_exemptions',{})
    if isinstance(switch,dict) and switch.get('enabled') and str(switch.get('reason','')).strip():
        b=dict(rule='*',reason=switch['reason']);global_breaks=[*global_breaks,b];declared.append(dict(path='storyboard.taste_exemptions',**b))
    for row in rows:
        for b in global_breaks:
            if exempts(b,row['rule']) and str(b.get('reason','')).strip():
                row.update(status='annotated',reason=b['reason'],exemption_scope='storyboard')
    return dict(exemptions=declared,exemption_count=len(declared),annotated_findings=sum(r['status']=='annotated' for r in rows))


def elements(board):
    for i, shot in enumerate(board.get('shots', []), 1):
        yield i, shot
        for field in ('elements','effects','captions','sfx'):
            for j, item in enumerate(shot.get(field, [])):
                if isinstance(item, dict): yield i, {'start':shot.get('start',0),'id':f'{i}.{field}.{j}',**item}
        for field in ('recipe','transition'):
            if isinstance(shot.get(field), dict): yield i, {'start':shot.get('start',0),'id':f'{i}.{field}',**shot[field]}
            elif isinstance(shot.get(field),str) and shot[field] not in ('cut','hard_cut'):
                yield i,dict(start=shot.get('start',0),id=f'{i}.{field}',serves_core=shot.get(field+'_serves_core',''))
        sound=shot.get('sound',{})
        if sound.get('file') or sound.get('sfx') or sound.get('sfx_family'):
            yield i,{'start':shot.get('start',0),'id':f'{i}.sound',**sound}


def intent_lint(board):
    core=board.get('core',board.get('treatment',{}).get('core','')).strip()
    rows=[]
    for i,e in elements(board):
        why=e.get('serves_core',e.get('why',''))
        if not core or not isinstance(why,str) or not why.strip() or why.strip()==core:
            rows.append(finding('intent_coverage',i,why,'nonempty explanation distinct from core',
                                'Explain how this element serves the core, or remove this noise candidate.',e))
    return rows


def default_tokens(style='user', profile=None):
    primary=(profile or {}).get('defaults',{}).get('transition_family','dissolve')
    return dict(name=style,color=dict(script=[],lut=None,skin_protection=True,skin_hue_degrees=[15,50]),
                type=dict(fonts=['sans','serif'],size_ratio=1.25,stroke='outline',shadow='soft',style=(profile or {}).get('defaults',{}).get('caption_style','clean')),
                transitions=dict(primary=primary,accent='energy'),texture=dict(film_grain=.15,halation=.2),
                motion=['static','push','pull','pan','tilt','dolly','crane','handheld','smooth_in','drift'],
                sfx=['hit','whoosh','riser','click'])


def transition_family(name):
    if name in ('cut','hard_cut',None): return None
    cards=read(ROOT/'references/fx-cards.json')
    return cards.get('transition:'+name,{}).get('family')


def token_lint(plan, tokens):
    rows=[]; fonts=tokens.get('type',{}).get('fonts',[])
    if len(fonts)>value('taste.tokens.fonts.max'):rows.append(finding('token_font',0,fonts,value('taste.tokens.fonts.max'),'Choose two declared fonts or annotate this intentionally larger typography system.',tokens))
    transitions=tokens.get('transitions',{}); families=set(transitions.values()) if isinstance(transitions,dict) else set(transitions)
    def walk(obj, path='', shot=0, parent=None):
        if isinstance(obj,list):
            for i,x in enumerate(obj): walk(x,path+f'[{i}]',i+1 if path in ('shots','segments') else shot,parent)
        elif isinstance(obj,dict):
            current=dict(parent or {},**obj)
            for k,v in obj.items():
                rule=None; limit=None
                if k in ('font','font_family') and v not in fonts: rule='token_font';limit=fonts
                elif k=='lut' and v and v!=tokens.get('color',{}).get('lut'): rule='token_lut';limit=tokens.get('color',{}).get('lut')
                elif k=='motion' and isinstance(v,str) and v not in tokens.get('motion',[]): rule='token_motion';limit=tokens.get('motion',[])
                elif k in tokens.get('texture',{}) and isinstance(v,(int,float)) and v>tokens['texture'][k]: rule='token_texture';limit=tokens['texture'][k]
                elif k=='sfx_family' and v not in tokens.get('sfx',[]): rule='token_sfx';limit=tokens.get('sfx',[])
                elif k=='transition' and v:
                    name=v if isinstance(v,str) else v.get('name'); family=transition_family(name)
                    if name not in ('cut','hard_cut') and (family is None or family not in families): rule='token_transition';limit=sorted(families)
                elif k=='transition_family' and v not in families and v not in ('cut','hard_cut',None): rule='token_transition';limit=sorted(families)
                if rule: rows.append(finding(rule,shot,v,limit,'Use the declared token or annotate an intentional exception.',dict(current,**v) if isinstance(v,dict) else current))
                if k not in ('rule_break','tokens'): walk(v,path+'.'+k if path else k,shot,current)
    walk(plan)
    exemption_summary(plan,rows)
    return rows


def edit_lint(report, board=None):
    board=board or {}; rows=[]; shots=board.get('shots',[]); fps=report.get('media',{}).get('fps',30)
    level=level_design(board) or report.get('comparison',{}).get('metric') in ('rms_deviation','absolute_dynamics')
    if not shots and report.get('M1',{}).get('cut_times'):
        shots=[dict(start=t) for t in [0,*report['M1']['cut_times']]]
    if report.get('M10',{}).get('centroids'):
        sal=report['M10'];ts=np.array(sal['times'])
        shots=deepcopy(shots)
        for i,shot in enumerate(shots):
            content=report.get('content',{})
            labels=content.get('labels',[])
            if labels and labels[int(np.argmin(abs(np.asarray(content['times'])-shot.get('start',0))))]=='no content':
                shot['focal']=None
                continue
            if 'focal' not in shot:
                t=shot.get('start',0)+1/fps;shot['focal']=sal['centroids'][int(np.argmin(abs(ts-t)))]
    cv=report.get('M1',{}).get('cv')
    if not level and cv is not None and cv<value('taste.shot.cv.min') and len(report['M1'].get('lengths',[]))>1:
        rows.append(finding('shot_cv',0,cv,value('taste.shot.cv.min'),'Vary shot lengths or annotate the deliberate meter.',board))
    for i,shot in enumerate(shots):
        if i:
            a=shots[i-1].get('focal'); b=shot.get('focal')
            if a is not None and b is not None:
                aspect=report.get('media',{}).get('height',1)/report.get('media',{}).get('width',1)
                distance=float(np.linalg.norm((np.asarray(a)-b)*[1,aspect]))
                if distance>value('taste.eye.distance.max'):
                    rows.append(finding('eye_trace',i+1,distance,value('taste.eye.distance.max'),'Move the incoming focus toward the outgoing focus; or explain the emotional jump.',shot,fps))
            motion=report.get('M6',{}).get('pixels_per_frame',[]); c=round(shot.get('start',0)*fps)
            event=next((e for e in report.get('M1',{}).get('events',[]) if abs(e['time_ms']/1000-shot.get('start',0))<=1/fps),{})
            # A heuristic transition center is not an authored cut accurate to
            # three frames. Keep timing advice for confirmed/hard boundaries.
            if motion and c>=1 and event.get('type','cut')=='cut' and not event.get('review',False):
                radius=max(3,round(fps*.06))
                near=max(motion[max(0,c-radius):min(len(motion),c+radius+1)],default=0)
                before=max(motion[max(0,c-round(fps)):c],default=0)
                if before>value('taste.action.motion.min') and near<before*value('taste.action.ratio.min'):
                    rows.append(finding('cut_on_action',i+1,near,before*value('taste.action.ratio.min'),'Move this cut into the preceding motion peak (within three frames).',shot,fps))
        sound=shot.get('sound',{})
        for key,label in (('audio_lead_ms','J-cut'),('audio_tail_ms','L-cut')):
            if sound.get(key,shot.get(key,0)):
                rows.append(finding('audio_bridge',i+1,sound.get(key,shot.get(key)),None,label,shot,fps,'info'))
    actions=board.get('actions',[])
    if actions:
        ratio=sum(bool(a.get('sfx')) for a in actions)/len(actions)
        limit=board.get('mickey_limit',value('taste.mickey.max'))
        if ratio>limit: rows.append(finding('mickey_mousing',0,ratio,limit,'Keep selected hits; annotate deliberate comedy underscoring.',board))
    proxy=report.get('M15',{}); peaks=proxy.get('peaks',[])
    if peaks and not level:
        ts=np.asarray(proxy['times']); ys=np.asarray(proxy['values']); p=peaks[0]
        before=ys[(ts>=p['time']-2)&(ts<p['time'])]
        if len(before) and p['value']>0 and float(before.min())>=p['value']*value('taste.valley.ratio.max'):
            at=max(0,p['time']-2);shot=1+sum(s.get('start',0)<=at for s in shots[1:])
            rows.append(finding('pre_peak_valley',shot,float(before.min()/p['value']),value('taste.valley.ratio.max'),'Thin the two seconds before the peak, unless sustained intensity is intentional.',dict(board,start=at)))
    m4=report.get('M4',{})
    if not level and 'Already bright' in (m4.get('warning') or ''):
        at=m4.get('before_interval',[0,0])[0]
        shot=1+sum(s.get('start',0)<=at for s in shots[1:])
        rows.append(finding('pre_peak_valley',shot,m4.get('jump'),value('taste.luminance.jump.min'),
                            'Already bright before the drop: if a lighting payoff is intended, lower exposure in the preceding second or strengthen the drop contrast.',dict(board,start=at),fps))
    exemption_summary(board,rows)
    return rows


def focal_overlap(rgb, mask):
    from taste_report import saliency
    import cv2
    s,c,centroid=saliency(rgb); mask=cv2.resize(np.asarray(mask,np.uint8),(s.shape[1],s.shape[0]),interpolation=cv2.INTER_NEAREST)>0
    active=s>max(float(s.max())*1e-6,1e-6)
    if not active.any(): return dict(concentration=c,overlap=None,centroid=centroid,reason='No visual saliency')
    top=(s>=np.percentile(s,90))&active
    return dict(concentration=c,overlap=float(np.mean(mask[top])),centroid=centroid)


def weakest(report):
    p=report['M15']; ts=np.asarray(p['times']); y=np.asarray(p['values'])
    width=min(len(y),20)
    content=report.get('content',{});labels=content.get('labels',[])
    present=np.interp(ts,content.get('times',ts),[x!='no content' for x in labels])>.5 if labels else np.ones(len(ts),bool)
    allowed=np.convolve(present.astype(int),np.ones(width),'valid')==width
    if report.get('designed_black'):allowed[:]=True
    if 'comparison' in report and report['comparison'].get('metric')!='absolute_dynamics' and not report['comparison'].get('automatic'):
        c=report['comparison'];target=np.asarray(c['design'])
        residual=target-np.asarray(c.get('measured',y))
        scores=-np.convolve(np.maximum(residual,0),np.ones(width)/width,'valid')
        allowed &= scores < -c.get('residual_tolerance',1e-9)-1e-12
        reason='Largest negative measured-minus-design residual on planning units (aligned for measured proxies); excesses at designed dips are excluded.'
    else:
        scores=np.convolve(y,np.ones(width)/width,'valid');reason='Lowest content-bearing two-second proxy mean; review candidate, not a defect or request for more energy.'
    if not allowed.any():
        return dict(start=None,end=None,reason='No eligible content-bearing deficit window; black frames and nonnegative residuals are excluded.',components={})
    i=int(np.argmin(np.where(allowed,scores,np.inf)));start=float(ts[i])
    mask=(ts>=start)&(ts<start+2)
    return dict(start=start,end=min(report.get('media',{}).get('duration',start+2),start+2),reason=reason,components={k:float(np.mean(np.asarray(v)[mask])) for k,v in p['components'].items()})


def ablation_measure(original, removed, delta_lufs=None):
    """Lossless frames only (A7-2); infinity represented explicitly as null."""
    a=np.asarray(original,float);b=np.asarray(removed,float)
    if a.shape!=b.shape or a.size==0: raise ValueError('Ablation needs equal nonempty lossless frame arrays')
    diff=a[...,:3]-b[...,:3]; mae=float(np.mean(abs(diff@np.array([.2126,.7152,.0722]))));mse=float(np.mean(diff**2))
    psnr=float(10*np.log10(255**2/mse)) if mse>0 else None
    noop=mae<=value('taste.ablation.mae.max') and (psnr is None or psnr>=value('taste.ablation.psnr.min')) and (delta_lufs is None or abs(delta_lufs)<=value('taste.ablation.lufs.max'))
    return dict(mean_abs_delta_y=mae,psnr=psnr,psnr_reason='Identical frames: infinite PSNR' if psnr is None else None,delta_lufs=delta_lufs,
                delta_lufs_reason='No paired audio measurement supplied' if delta_lufs is None else None,
                suggestion='Suggest deletion: no measurable difference' if noop else 'Needs user paired comparison',noop=noop,
                appeal_verdict=None,appeal_reason='Only the user can decide whether the remaining difference is wanted')


def default_distance(director, seeds):
    if len(seeds)!=3: raise ValueError('A7-5 requires three autoplan seeds for the same brief')
    rows=[]
    for key,v in director.items():
        values=[s[key] for s in seeds]; spread=max(values)-min(values); delta=abs(v-float(np.mean(values)))
        rows.append(dict(metric=key,difference=delta,autoplan_seed_range=spread,exceeds=delta>spread))
    return dict(metrics=rows,distinct_metrics=sum(r['exceeds'] for r in rows),human_evidence='P-WIN required; numeric distance is not appeal')
