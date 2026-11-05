"""Director metadata, independent of effect implementation and user taste."""
from copy import deepcopy
import html
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INTENTS=('hit','reveal','breathe','build','drop','transition-match','transition-energy','texture','title','conceal','play','distort')
NEEDS=('subject','motion','alpha','text')


def output_root():
    override=os.environ.get('VIDEO_GIF_FX_PREVIEWS')
    return Path(override).expanduser() if override else Path.home()/'.video-gif-studio/catalog'


def validate_plugin_card(card):
    """Partial cards remain inspectable, but never count as complete cards."""
    defaults=dict(intent=['texture'],energy=0.,needs=[],good_for=['Author declared use'],
                  avoid_for=['Unreviewed delivery'],duration_ms=[100,2000],pairs_with_sfx=[],
                  conflicts=[],gate={},style_tags=[],preview={},**{'cost_ms_per_frame@720p':None})
    validate_card(dict(defaults,**card))
    from fx_schema import validate
    merged=dict(defaults,**card)
    # Validate nested supplied fields too, before catalog enrichment uses them.
    for field in ('gate','preview'):
        if field not in card:merged.pop(field)
    schema=json.loads((ROOT/'references/fx-card.schema.json').read_text(encoding='utf-8'))
    schema['required']=[]
    validate(merged,schema)


def coverage(catalog):
    rows=[dict(id=k[:-1]+':'+n,status=c['status'],card=c.get('card','complete'))
          for k,entries in catalog.items() for n,c in entries.items()]
    return dict(total=len(rows),complete_stable=sum(r['status']=='stable' and r['card']=='complete' for r in rows),
                missing=[r for r in rows if r['card']=='missing'],incomplete=[r for r in rows if r['card']=='incomplete'])


def enrich(catalog):
    from fx import EFFECTS, TRANSITIONS
    from fx_calibrate import load_table
    metadata_path=ROOT/'references/fx-cards.json'
    metadata=json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.exists() else {}
    table=load_table()
    statuses=json.loads((ROOT/'wow/fx/gate/p2-status.json').read_text(encoding='utf-8'))
    statuses={s['item']:s for s in statuses}
    for kind,entries in catalog.items():
        registry=EFFECTS if kind=='effects' else TRANSITIONS
        singular=kind[:-1]
        for name,item in list(entries.items()):
            try:
                json.dumps(item,allow_nan=False)
                key=singular+':'+name
                builtin=(ROOT/'scripts/fx') in Path(registry[name]['source']).parents
                card=deepcopy(metadata.get(key,{})) if builtin else {}
                supplied=registry[name].get('card',{})
                if not card and not supplied:
                    item['card']='missing'
                    continue
                item['card']='complete' if card or {'intent','energy','needs','good_for','avoid_for','duration_ms','pairs_with_sfx','conflicts','style_tags'}<=set(supplied) else 'incomplete'
                if not card:
                    # Unreviewed plugins still have an inspectable card; their author
                    # can supply card={...} to declare domain-specific requirements.
                    card=dict(intent=['texture' if kind=='effects' else 'transition-match'],energy=0.,needs=[],
                        good_for=[name+' author-defined use'],avoid_for=['Unreviewed production delivery'],duration_ms=[100,2000],
                        pairs_with_sfx=['whoosh'],conflicts=[],style_tags=item.get('style_tags',[]))
                card.update(deepcopy(registry[name].get('card',{})))
                calibrated=table['effects'].get(name) if kind=='effects' else None
                if calibrated:
                    card['energy']=calibrated['default_perceived']
                    card['calibration']={'path':'references/fx-calibration.json','control':calibrated['control'],
                        'max_perceived':calibrated['max_perceived'],'material':calibrated['material']}
                    card['calibration']['perceived_addressable']=name!='cutout_card'
                    if name=='cutout_card':card['calibration']['reason']='Measured mix range <=0.0211; use native parameters, not perceived.'
                cost=table.get('costs',{}).get(key)
                card['cost_ms_per_frame@720p']=cost['ms_per_frame'] if cost else None
                card['cost_measurement']=cost or {'status':'unmeasured; run fx_calibrate.py'}
                if key in statuses:
                    s=statuses[key]
                    card['gate']=dict(axis='technical',status=s['status'],date=s['date'],record_path='wow/fx/gate/p2-status.json',
                        evidence_path=s['evidence_path'],technical_verdict=s['technical_verdict'],basis=s['basis'])
                else:
                    card.setdefault('gate',dict(axis='technical',status='pending-review',date='2026-11-05',
                        record_path='references/fx.md',basis='Legacy registry status retained; independent technical review has not been recorded.'))
                card['gate']['appeal']='user preference; not scored'
                card['gate']['record_commit']='95a039aecaf09dc34a7905b6d8384937ecaac30b' if key in statuses else table.get('commit','unrecorded')
                if name in ('hex_shutter','gl_bounce','gl_multiply_blend','gl_color_phase','gl_dreamy_zoom','gl_glitch_memories'):
                    card['gate']['record_path']='wow/fx/gate/p2-tech-recheck.md'
                legacy=ROOT/'wow/fx/gate/s6-legacy-auto.json'
                if key not in statuses and legacy.exists():
                    record=json.loads(legacy.read_text(encoding='utf-8')).get('items',{}).get(key)
                    if record:
                        card['gate'].update(record_path='wow/fx/gate/s6-legacy-auto.json',**record)
                        if record['status']=='needs-review':item['status']='needs-review'
                card['preview']={'video':key.replace(':','-')+'.mp4',
                                 'thumbnail':key.replace(':','-')+'.jpg','duration_ms':2000}
                if name=='grade':card['preview']['params']={'temp':.15};card['preview']['note']='Demonstration warmth .15; original default is identity.'
                if name=='gl_glitch_memories':
                    card['preview']['context']={'seed':'6 - floor(24 * progress)'}
                    card['preview']['note']='Smooth fixed block field for the 1.2-second catalog transition; native default retains 24 updates.'
                # Parameter metadata is immutable, including legacy history's type.
                item.update({k:v for k,v in card.items() if k not in ('status','params','doc','source','history')})
                validate_card(item)
                json.dumps(item,allow_nan=False)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
                from fx_diagnostics import excluded
                excluded(item.get('source','catalog'),name,item.get('status','unknown'),exc,[name,str(exc)])
                del entries[name]
    return catalog


def validate_card(card):
    """Cross-field checks supplement draft-2020-12 (which cannot compare siblings)."""
    import re
    required={'intent','energy','needs','good_for','avoid_for','duration_ms','pairs_with_sfx','conflicts','gate','style_tags','preview','cost_ms_per_frame@720p'}
    if required-set(card):raise ValueError('Incomplete effect card')
    if not card['intent'] or set(card['intent'])-set(INTENTS):raise ValueError('Unknown card intent: '+str(card['intent']))
    if set(card['needs'])-set(NEEDS):raise ValueError('Unknown card needs')
    if not 0<=card['energy']<=1:raise ValueError('Card energy outside 0..1')
    if len(card['duration_ms'])!=2 or not 0<=card['duration_ms'][0]<card['duration_ms'][1]:raise ValueError('Card duration must increase')
    if not card['good_for'] or not card['avoid_for'] or set(card['good_for'])&set(card['avoid_for']):raise ValueError('Card use/avoid must be nonempty and disjoint')
    for field in ('good_for','avoid_for','intent','needs','pairs_with_sfx','conflicts','style_tags'):
        for text in card[field]:
            if not isinstance(text,str) or not text.strip() or re.fullmatch(r'(?i)(todo|tbd|n/?a|none|-|\.\.\.|xxx|lorem.*|placeholder|待補)',text):raise ValueError('Empty card metadata: '+field)
    return card


def write_html(cards, target, title='Effect direction library'):
    """Offline, responsive catalog; text is escaped even for untrusted plugins."""
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    esc=lambda s:html.escape(str(s),quote=True)
    blocks=[]
    for c in cards:
        if c.get('card') in ('missing','incomplete'):continue
        video=Path(c['preview']['video']);thumb=Path(c['preview']['thumbnail'])
        def link(p):
            if not p.is_absolute():return p.as_posix()
            return os.path.relpath(p,target.parent).replace('\\','/')
        snippet=c.get('snippet',{'name':c['name']} if c.get('calibration',{}).get('perceived_addressable') is False else {'name':c['name'],'perceived':round(c['energy'],3)})
        blocks.append(f'''<article data-intent="{esc(' '.join(c['intent']))}" data-needs="{esc(' '.join(c['needs']))}">
<video autoplay muted loop playsinline preload="metadata" controls poster="{esc(link(thumb))}" src="{esc(link(video))}"></video>
<div class="body"><small>{esc(c['kind'])} · {esc(c.get('status','stable'))}</small><h2>{esc(c['name'].replace('_',' '))}</h2>
<p class="intent">{esc(' / '.join(c['intent']))}</p><p><b>Use:</b> {esc('; '.join(c['good_for']))}</p>
<p><b>Avoid:</b> {esc('; '.join(c['avoid_for']))}</p><label>Perceived intensity {c['energy']:.2f}<meter min="0" max="1" value="{c['energy']}"></meter></label>
<p>{esc(' · '.join(c.get('style_tags',[])))}<br>Technical: {esc(c['gate']['status'])}</p>
<p>{esc(c['preview'].get('note',''))}</p>
<p>Needs: {esc(', '.join(c['needs']) or 'ordinary footage')} · Cost: {esc(c.get('cost_ms_per_frame@720p'))} ms/frame</p>
<details><summary>Plan JSON</summary><pre>{esc(json.dumps(snippet,ensure_ascii=False))}</pre></details></div></article>''')
    options=''.join(f'<option>{esc(i)}</option>' for i in INTENTS)
    text=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#11151c;color:#e9eef6;font:15px/1.55 system-ui,sans-serif}}header{{padding:36px 5vw;border-bottom:1px solid #334154}}
h1{{font-size:clamp(28px,5vw,54px);margin:0}}header p{{color:#aebed0;max-width:760px}}select{{font:inherit;padding:9px;background:#213044;color:white;border:1px solid #63788c;border-radius:8px}}
main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,310px),1fr));gap:22px;padding:28px 5vw}}article{{min-width:0;background:#1b2430;border:1px solid #334154;border-radius:16px;overflow:hidden}}video{{width:100%;aspect-ratio:16/9;background:#0c1118}}.body{{padding:18px}}h2{{margin:3px 0;font-size:23px}}small{{text-transform:uppercase;letter-spacing:.08em;color:#a3bdd8}}.intent{{color:#8ee0d2}}meter{{display:block;width:100%;height:14px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}[hidden]{{display:none}}
</style><header><small>Director toolkit / S6</small><h1>{esc(title)}</h1><p>Choose the job the effect should do. Compare motion, intensity and cost. Technical status describes defects; style is your choice. Unmute a recipe to hear its sound pairing.</p><label>Intent <select id="intent"><option value="">All intents</option>{options}</select></label> <span id="count"></span></header><main>{''.join(blocks)}</main>
<script>const filter=document.querySelector('#intent');function update(){{let n=0;document.querySelectorAll('article').forEach(c=>{{c.hidden=!!filter.value&&!c.dataset.intent.split(' ').includes(filter.value);if(!c.hidden)n++;}});document.querySelector('#count').textContent=n+' cards';}}filter.addEventListener('change',update);update();</script></html>'''
    target.write_text(text,encoding='utf-8')
    return target
