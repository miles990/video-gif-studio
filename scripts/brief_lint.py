"""Measurable brief rules adapted from blank-page SKILL.md (MIT).

Copyright (c) 2026 Cekura, Inc.; see THIRD_PARTY.md. Numerical advice is
class C, author experience rather than an external design standard.
"""
import json
import math
import re
from pathlib import Path
from brief_refs import HANDLES, licence_status
from threshold_registry import value

ROOT=Path(__file__).resolve().parents[1]
NONEXEMPT={'licence','ref_provenance','refs_in_output','schema'}


def words(text):
    cjk=re.findall(r'[\u3400-\u9fff\u3040-\u30ff]',text)
    latin=re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*",text)
    return len(cjk)+len(latin),bool(cjk)


def lint(brief):
    findings=[]
    limits={k:value('brief.'+k) for k in ('hero_height.min','text_px.min','end_hold.max','turn_end.min','words.en.max','words.cjk.max','edit_words.en.max','edit_words.cjk.max','word_error_ratio','forks.max')}
    def add(rule,location,message,fix,severity='error',obj=None):
        annotations=[]
        for data in (brief,obj or {}):
            breaks=data.get('rule_break',[])
            annotations.extend([breaks] if isinstance(breaks,dict) else breaks)
        reason=next((a.get('why',a.get('reason','')).strip() for a in annotations if a.get('rule')==rule and len(a.get('why',a.get('reason','')).strip())>=6),None)
        if reason and rule not in NONEXEMPT: severity='exempted'
        findings.append(dict(rule=rule,severity=severity,location=location,message=message,fix=fix,**({'reason':reason} if reason else {})))
    if not isinstance(brief,dict): return dict(errors=1,findings=[dict(rule='schema',severity='error',location='$',message='Expected brief object',fix='Use brief.json')])
    for i,ref in enumerate(brief.get('refs',[]) if isinstance(brief.get('refs',[]),list) else []):
        if isinstance(ref,dict) and (isinstance(ref.get('role'),list) and len(ref['role'])>1 or len(ref.get('roles',[]))>1):
            add('one_ref_one_job',f'refs[{i}]','One record has multiple roles','List the file separately for each scoped role')
    from fx_schema import validate as validate_schema
    schema=json.loads((ROOT/'references/brief.schema.json').read_text(encoding='utf-8'))
    schema.pop('allOf',None)
    if brief.get('mode') in ('brief','batch','sequence'):
        schema['required']+=['aesthetic','duration','beats','refs','assets','forks']
    # Procedural lint supplies the more useful forks_max location and repair.
    schema['properties']['forks'].pop('maxItems',None)
    try:validate_schema(brief,schema)
    except ValueError as exc:
        add('schema','$',str(exc),'Use the brief schema and repair the named field')
        return result(findings)
    def check_exemptions(obj,path='$'):
        if isinstance(obj,dict):
            breaks=obj.get('rule_break',[]);breaks=[breaks] if isinstance(breaks,dict) else breaks
            for a in breaks:
                if a.get('rule') in NONEXEMPT or a.get('rule') in ('*','all'):
                    add('exemption_not_allowed',path+'.rule_break','Cannot waive provenance, licences, embedding or schema','Remove this exemption')
            for k,v in obj.items():
                if k!='rule_break': check_exemptions(v,path+'.'+k)
        elif isinstance(obj,list):
            for i,v in enumerate(obj): check_exemptions(v,f'{path}[{i}]')
    check_exemptions(brief)
    mode=brief.get('mode','brief')
    if mode not in ('brief','batch','delta','image_feedback','sequence','housekeeping'):
        add('schema','mode','Unknown mode','Choose a supported mode')
    prompt=brief.get('prompt','')
    count,cjk=words(prompt.split('refs:')[0])
    editing=mode in ('delta','image_feedback');cap=limits[('edit_words.' if editing else 'words.')+('cjk.max' if cjk else 'en.max')]
    if count>cap: add('word_cap_edit' if editing else 'word_cap','prompt',f'{count} words; advisory cap {cap}','Drop optional globals first; retain all beats and the turn','error' if count>cap*limits['word_error_ratio'] else 'warning')
    if mode in ('housekeeping','delta','image_feedback'): return result(findings)
    aesthetic=brief.get('aesthetic')
    generic={'modern','clean','minimal','simple','warm','cozy','cool','sleek','professional','現代','簡約','溫暖','質感','高級','專業'}
    first_line=prompt.splitlines()[0] if prompt else ''
    if not isinstance(aesthetic,str) or not aesthetic.strip() or re.search(r'\s(?:and|&|\+)\s|混搭|融合',aesthetic+' '+first_line,re.I) or set(aesthetic.lower().split())<=generic or not re.sub(r'現代|簡約|溫暖|質感|高級|專業|\s','',aesthetic):
        add('one_aesthetic','aesthetic','Commit to one named aesthetic','Name one child of the fence, e.g. morning-window warm film')
    beats=brief.get('beats',[]);refs=brief.get('refs',[])
    if not isinstance(beats,list) or not beats or not all(isinstance(b,dict) for b in beats):
        add('schema','beats','Nonempty beat objects required','Provide numbered beats with t_start, t_end and text');return result(findings)
    duration=brief.get('duration',0)
    if not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<=0:
        add('schema','duration','Positive finite duration required','Set duration in seconds');return result(findings)
    cursor=0.;turns=[]
    for i,b in enumerate(beats):
        loc=f'beats[{i}]'
        start,end=b.get('t_start'),b.get('t_end')
        if any(not isinstance(t,(int,float)) or not math.isfinite(t) for t in (start,end)) or start<0 or end<=start or abs(start-cursor)>.001:
            add('schema',loc,'Timeline must be positive and contiguous','Set this start to the previous end and a later end');continue
        cursor=end
        if b.get('id')!=i+1:add('schema',loc+'.id','Beat numbers must be consecutive','Renumber from 1')
        if b.get('is_turn'):
            turns.append(b)
            if not re.search(r'reveal|morph|comes back as|snaps into|becomes|turns into|zoom.?out|揭露|變成|化為|拉遠|翻開',b.get('text',''),re.I):
                add('no_turn',loc+'.text','Turn has no transformation mechanism','Describe what opens/reveals/changes medium',obj=b)
            if end<=limits['turn_end.min']*duration: add('turn_too_early',loc+'.t_end','Turn ends before 32% of duration','Extend the action beyond 0.32 × duration',obj=b)
            if b.get('hero_height',brief.get('hero_height',0))<limits['hero_height.min']: add('hero_size',loc+'.hero_height','Hero occupies less than 40% frame height','Enlarge the hero to at least 0.4 frame height',obj=b)
        if re.search(r'editorial|編輯感',b.get('text',''),re.I) and not re.search(r'from|under|reveal|corner|底下|角落|揭露',b.get('text',''),re.I):
            add('mechanism_not_adjective',loc+'.text','Adjective does not specify the mechanism','State what peels from which corner and what is underneath','warning',b)
        short=min(brief.get('width',1080),brief.get('height',1080))
        font=b.get('min_text_px',brief.get('min_text_px',24))
        if short<=0 or font*1080/max(1,short)<limits['text_px.min']: add('min_text',loc+'.min_text_px','Text below 24 px at short side 1080','Increase the smallest text to 24 × short_side / 1080',obj=b)
    if abs(cursor-duration)>.034:add('schema','duration','Beat coverage differs from duration','End the last beat at duration')
    if not turns:add('no_turn','beats','No turn','Give one beat a reveal or transformation and is_turn=true')
    if len(turns)>math.ceil(duration/5):add('one_idea','beats','Too many transformations','Keep one main idea per five seconds')
    hold=brief.get('end_hold',duration-max((b['t_end'] for b in beats if b.get('action',True)),default=0))
    if hold>=limits['end_hold.max']: add('end_hold','end_hold','Ending hold is at least one second','Continue the final action; reduce hold below 1 second')
    seen=set()
    for i,r in enumerate(refs):
        handle=r.get('handle','');loc=f'refs[{i}]({handle})'
        if handle in seen:add('schema',loc,'Duplicate handle','Give each scoped role its own handle')
        seen.add(handle)
        cited=[b['id'] for b in beats if re.search(r'(?<!\w)'+re.escape(handle)+r'(?!\w)',b.get('text',''))] if handle else []
        if not cited:add('ref_unused',loc,'Reference not used by a beat','Delete it or cite its scoped take inline in a beat')
        if cited!=r.get('cited_by',[]):add('ref_citations',loc+'.cited_by','Inline citations and cited_by disagree','Regenerate cited_by from beat text')
        use=r.get('use','');n,is_cjk=words(use)
        if n<(6 if is_cjk else 4) or use.lower() in ('reference','inspiration','參考'):
            add('ref_no_use',loc+'.use','Reference has no specific use','Name the beat, scoped quality and mechanic/time range')
        role=r.get('role')
        if not isinstance(role,str) or any(x in role for x in ('/',' + ',' and ')):
            add('one_ref_one_job',loc+'.role','One record has multiple roles','List the file separately for each scoped role')
        if r.get('source')=='web' and (not r.get('source_url') or not r.get('licence')):
            add('ref_provenance',loc,'Web reference lacks source or licence','Record actual source_url and licence; use unknown when unavailable')
        if r.get('embed') or r.get('in_output'):add('refs_in_output',loc,'Reference is marked for embedding','Move an explicitly licensed usable asset to assets; never embed reference media')
    if set(HANDLES)-seen:add('schema','refs','Missing 5+3 reference slots','Use a1–a5 and m1–m3; mark unavailable slots with placeholders')
    turn_refs=[r for r in refs if r.get('is_turn') and r.get('handle','').startswith('m')]
    if len(turn_refs)!=1 or not any(b.get('is_turn') and b['id'] in turn_refs[0].get('cited_by',[]) for b in beats):
        add('turn_reference','refs','Exactly one motion reference must feed the turn','Mark the turn motion handle and cite it in the turn beat')
    forks=brief.get('forks',[])
    markers=[m for m in re.findall(r'\[\?\s*([^]]+)\]',prompt.split('refs:')[0]) if m not in ('visual ref','motion ref','download')]
    if max(len(forks),len(markers))>limits['forks.max']:add('forks_max','forks','More than three creative forks','Keep only the three choices that change the idea')
    for i,f in enumerate(forks):
        if re.search(r'duration|loop|aspect|filename|fps|resolution|秒|直式|橫式|解析度|檔名',json.dumps(f,ensure_ascii=False),re.I):
            add('routine_fork',f'forks[{i}]','Routine choice presented as a creative fork','Set the routine default inline')
    for i,a in enumerate(brief.get('assets',[])):
        status=licence_status(a)
        if status!='allowed':add('licence',f'assets[{i}]',f'Asset licence: {status}','Use CC0, attributed CC-BY or explicit user ownership')
    return result(findings)


def result(findings):
    return dict(errors=sum(f['severity']=='error' for f in findings),warnings=sum(f['severity']=='warning' for f in findings),findings=findings)
