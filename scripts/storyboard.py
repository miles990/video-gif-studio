"""Extension of the planning.md shot table, shared by preflight, animatic and prompts."""
from copy import deepcopy
import hashlib
import json
import numpy as np
from taste_common import ROOT, read, curve_points, value, compare_curve, smooth
from taste_lint import finding, intent_lint, token_lint, default_tokens, level_design, exemption_summary

SIZES=('EWS','WS','MS','CU','ECU')
MOVES=('static','push','pull','pan','tilt','dolly','crane','handheld','crash_in','crash_out','expo_in','smooth_in','whip','punch','drift','spring_in')


def normalize(board):
    """Add defaults only to a copy. Legacy start/end/duration_ms clocks accepted."""
    b=deepcopy(board)
    if not isinstance(b.get('shots'),list) or not b['shots']: raise ValueError('storyboard requires nonempty shots')
    cursor=0.
    for i,s in enumerate(b['shots']):
        s.setdefault('id',f'shot-{i+1}'); s.setdefault('start',cursor)
        duration=s.get('duration',s.get('duration_ms',0)/1000)
        s.setdefault('end',s['start']+duration);s['duration']=s['end']-s['start']
        if not np.isfinite([s['start'],s['end']]).all() or s['start']<0 or s['duration']<=0 or abs(s['start']-cursor)>1e-6:
            raise ValueError(f'Shot {i+1}: timeline must be finite, contiguous and positive')
        s.setdefault('size','MS');s.setdefault('motion','static');s.setdefault('angle',0);s.setdefault('lens','standard')
        s.setdefault('direction','neutral');s.setdefault('axis','default');cursor=s['end']
    b.setdefault('fps',30);b['duration']=cursor
    if not isinstance(b['fps'],(int,float)) or not np.isfinite(b['fps']) or b['fps']<=0: raise ValueError('fps must be positive')
    return b


def validate(board):
    schema=read(ROOT/'references/storyboard.schema.json')
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        from fx_schema import validate as schema_validate
        schema_validate(board,schema)
    else:
        errors=sorted(Draft202012Validator(schema).iter_errors(board),key=lambda e:str(list(e.path)))
        if errors: raise ValueError('; '.join(f'{list(e.path)}: {e.message}' for e in errors))
    return normalize(board)


def design_curve(board):
    if board.get('design_curve') is not None:
        return curve_points(board['design_curve']).tolist(),'authored'
    shots=board['shots']; points=[]
    for s in shots:
        energy=s.get('sound',{}).get('energy',.5)
        points.append([s['start'],energy])
    points.append([board['duration'],shots[-1].get('sound',{}).get('energy',.5)])
    return points,'automatic from declared music section energy (not analyzed beats)'


def predicted(board):
    times=np.arange(0,board['duration'],.1); raw=np.zeros(len(times));parts=[];previous=None
    for s in board['shots']:
        recipe=s.get('recipe',{});perceived=recipe.get('perceived',s.get('perceived',0)) if isinstance(recipe,dict) else s.get('perceived',0)
        components=[1/(1+s['duration']),float(previous is not None and previous['size']!=s['size']),float(s['motion']!='static'),perceived,s.get('sound',{}).get('energy',.5)]
        weights=[.15,.1,.15,.25,.35];energy=float(np.dot(weights,components))
        raw[(times>=s['start'])&(times<s['end'])]=energy
        parts.append(dict(shot=s['id'],components=components,intensity=energy)); previous=s
    return dict(times=np.round(times,3).tolist(),values=smooth(raw).tolist(),shots=parts,weights=[.15,.1,.15,.25,.35],
                formula='smooth_2s(.15/(1+duration) + .10*size_change + .15*moving + .25*perceived + .35*music_energy)',
                reason='Planning hypothesis, not measured arousal; footage can disagree')


def lint(board, tokens=None):
    b=normalize(board);rows=intent_lint(b);tokens=tokens or b.get('tokens')
    if tokens: rows+=token_lint(b,tokens)
    design,origin=design_curve(b);points=curve_points(design);prev=None;run=0;budgets=[]
    for i,s in enumerate(b['shots'],1):
        motion=s['motion'];recipe=s.get('recipe'); recipe_name=recipe.get('name',recipe.get('recipe')) if isinstance(recipe,dict) else recipe
        extra=[]
        if recipe_name:
            path=ROOT/'recipes'/f'{recipe_name}.json'
            if path.is_file():
                extra=[l['ref'] for l in read(path)['layers'] if l['ref'] in ('camera_move','zoom_punch','parallax')]
        if not isinstance(motion,str) or motion not in MOVES or (motion!='static' and extra):
            rows.append(finding('one_motion',i,[motion,*extra],1,'Choose one camera movement; remove the competing recipe camera layer.',s,b['fps'],'error'))
        run=run+1 if prev and prev['size']==s['size'] else 1
        if run>=value('taste.shot_size.repeat'):rows.append(finding('shot_size_variation',i,run,value('taste.shot_size.repeat'),'Change this shot to a closer or wider framing, or annotate the repeated setup.',s))
        if prev:
            if s.get('subject') and prev.get('subject')==s['subject'] and s['size']==prev['size'] and abs(float(s['angle'])-float(prev['angle']))<value('taste.angle.min'):
                rows.append(finding('angle_30',i,abs(float(s['angle'])-float(prev['angle'])),value('taste.angle.min'),'Change shot size or separate camera angles by at least 30 degrees.',s))
            if s['axis']==prev['axis'] and s['direction']!=prev['direction'] and 'neutral' not in (s['direction'],prev['direction']) and not s.get('visible_axis_crossing'):
                rows.append(finding('axis_180',i,[prev['direction'],s['direction']],'consistent screen direction','Insert a neutral shot or show the camera crossing the axis.',s))
        energy=float(np.interp((s['start']+s['end'])/2,points[:,0],points[:,1]));budget=value('taste.budget.base')+value('taste.budget.slope')*energy
        perceived=(recipe.get('perceived',s.get('perceived',0)) if isinstance(recipe,dict) else s.get('perceived',0))
        budgets.append(dict(shot=i,start=s['start'],end=s['end'],design_intensity=energy,perceived_limit=budget,perceived_used=perceived))
        if perceived>budget:rows.append(finding('effect_budget',i,perceived,budget,'Move the heavy recipe to the drop or lower its perceived target.',s))
        prev=s
    lengths=np.array([s['duration'] for s in b['shots']]);cv=float(lengths.std()/lengths.mean())
    if not level_design(b) and len(lengths)>1 and cv<value('taste.shot.cv.min'):rows.append(finding('shot_cv',0,cv,value('taste.shot.cv.min'),'Vary durations or annotate deliberate metrical repetition.',b))
    pred=predicted(b);comparison=compare_curve(np.asarray(pred['times']),pred['values'],design,b.get('bar_seconds',2))
    if (origin!='authored' and np.std(points[:,1])<.02) or 'provisional' in b.get('design_origin',''):
        comparison.update(revise=False,reason='Automatic design is a planning placeholder, not an authored revision target',deviations=[])
    if comparison['revise']:
        for dev in comparison['deviations']:
            for i,s in enumerate(b['shots'],1):
                if s['start']<dev['end'] and s['end']>dev['start']:
                    dev.setdefault('shots',[]).append(i)
                    rows.append(finding('design_curve',i,dev['deficit'],comparison.get('rms_limit'),f"{max(s['start'],dev['start']):.2f}s, shot {i}: "+dev['suggestion'],s))
    exemptions=exemption_summary(b,rows)
    return dict(**exemptions,findings=rows,errors=sum(r['severity']=='error' and r['status']!='annotated' for r in rows),
                warnings=sum(r['severity']=='warning' and r['status']!='annotated' for r in rows),design_curve=design,design_origin=origin,
                predicted=pred,comparison=comparison,budgets=budgets,policy='U advice is overridable with a reason; technical defects retain their independent gates')


def fingerprint(board):
    return hashlib.sha256(json.dumps(board,sort_keys=True,allow_nan=False).encode()).hexdigest()


def prompts(board, animatic_receipt=None):
    b=validate(board);check=lint(b)
    receipt_valid=False
    if animatic_receipt is not None and animatic_receipt.get('storyboard_sha256')==fingerprint(board):
        from pathlib import Path
        movie=Path(animatic_receipt.get('movie',''))
        receipt_valid=movie.is_file() and animatic_receipt.get('movie_sha256')==hashlib.sha256(movie.read_bytes()).hexdigest()
    ready=check['errors']==0 and receipt_valid
    locks={};rows=[]
    for s in b['shots']:
        subject=s.get('subject','subject');ref=s.get('reference_id',b.get('references',{}).get(subject,'unsupplied'))
        if subject in locks and locks[subject]!=ref:raise ValueError('Character reference changed across shots: '+subject)
        locks[subject]=ref
        for size in ([s['size'],'MS','CU'] if s.get('coverage') else [s['size']]):
            fields=dict(shot=s['id'],size=size,motion=s['motion'],action=s.get('action',''),lighting=s.get('lighting',''),duration=s['duration'],reference_id=ref)
            fields['prompt']=f"{size}; camera movement: {s['motion']}; {fields['action']}; light: {fields['lighting']}; {s['duration']:.3f} seconds; reference: {ref}."
            rows.append(fields)
    complete=all(r['action'] and r['lighting'] and r['reference_id']!='unsupplied' for r in rows)
    blockers=[] if ready else ['Pass storyboard errors and render an animatic for this exact storyboard first.']
    if not complete:blockers.append('Supply action, lighting and character reference IDs before generation.')
    return dict(prompts=rows,ready_for_authorized_generation=ready and complete,provider_calls=0,
                blockers=blockers,
                generation='Prompts only. No provider calls; spending requires user authorization.')


def generation_gate(board,receipt,authorized=False):
    """Pure preflight. Does not construct/import any paid provider client."""
    report=prompts(board,receipt)
    if not report['ready_for_authorized_generation']:raise ValueError('; '.join(report['blockers']))
    if not authorized:raise ValueError('Generation needs explicit user spending authorization')
    return report['prompts']


def shot_table(board):
    b=normalize(board)
    columns=('id','start','end','size','angle','lens','motion','composition','direction','axis','lighting','color_script','sound','intent','recipe','perceived','transition','beats','why','serves_core')
    def cell(x):return (json.dumps(x,ensure_ascii=False) if isinstance(x,(dict,list)) else str(x)).replace('|','\\|').replace('\n',' ')
    return '| '+' | '.join(columns)+' |\n| '+' | '.join('---' for _ in columns)+' |\n'+'\n'.join('| '+' | '.join(cell(s.get(c,'')) for c in columns)+' |' for s in b['shots'])+'\n'
