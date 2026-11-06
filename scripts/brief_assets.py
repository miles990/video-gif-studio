"""Content-based owned-footage selection and asset intent."""
import json
from pathlib import Path
import re


def terms(text):
    text=text.casefold()
    tokens=set(re.findall(r'[a-z][a-z0-9_-]+',text))
    for run in re.findall(r'[\u3400-\u9fff]+',text):
        tokens.update(run[i:i+2] for i in range(len(run)-1))
    return tokens-{'the','and','with','into','from','reveal','reveals','subject','asset','png','jpg'}


def select_asset(assets,beat,subject,first=False):
    """An explicit hero opens the sequence; subsequent beats match card content.

    Unknown semantics retain a deterministic first eligible card. File ordering
    never causes unrelated footage to rotate through a scene.
    """
    heroes=[a for a in assets if a.get('role')=='hero']
    if first and heroes:return heroes[0]
    wanted=terms(beat);context=terms(subject)
    def score(asset):
        labels=' '.join(str(asset.get(k,'')) for k in ('title','id','description','tags','subject','role'))+' '+Path(asset.get('path','')).stem
        known=terms(labels)
        return len(wanted&known)*4+len(context&known)
    return max(assets,key=score) if assets else {}


def asset_spec(draft):
    size=re.search(r'(\d+)\s*[x×＊*]\s*(\d+)\s*(?:px)?',draft,re.I)
    sheet=re.search(r'sprite[ -]?sheet|精靈圖集|精靈表|雪碧圖',draft,re.I)
    icons=re.search(r'icon[ -]?sets?|item\s+icons|圖示集|圖標集|道具圖示',draft,re.I)
    frames=re.search(r'(\d+)\s*(?:frames?\b|幀|格)',draft,re.I)
    states=[s for s in ('idle','attack','run','walk','jump','hurt','death') if re.search(r'\b'+s+r'\b',draft,re.I)]
    for zh,en in (('待機','idle'),('攻擊','attack'),('跑步','run'),('行走','walk'),('跳躍','jump'),('受傷','hurt'),('死亡','death')):
        if zh in draft and en not in states:states.append(en)
    transparent=bool(re.search(r'transparent\s+(?:background|bg)|透明背景|去背',draft,re.I))
    if not (sheet or icons or frames or states or transparent or size and max(map(int,size.groups()))<=512):return None
    result=dict(kind='icon_set' if icons else 'sprite_sheet' if sheet else 'animation' if frames or states else 'image',states=states,transparent=transparent)
    if size:result['size']=[int(v) for v in size.groups()]
    if frames:
        result['frame_count']=int(frames[1]);result['frame_scope']='per_state' if re.search('per state|每個狀態|每狀態',draft,re.I) else 'total'
    if icons:
        count=re.search(r'(\d+)\s*(?:item\s+icons?|icons?|個)',draft,re.I)
        if count:result['count']=int(count[1])
    formats=re.findall(r'\b(?:png|gif|apng|mp4|webm)\b',draft,re.I)
    if formats:result['formats']=list(dict.fromkeys(f.upper() for f in formats))
    if re.search(r'pixel[ -]?art|像素',draft,re.I):result['style']='pixel art'
    return result


def pending_asset(brief,out=None):
    """Spec-14 is not implemented; never send an asset brief to video rendering."""
    result=dict(version=1,route='asset',status='asset pipeline pending',
                note='asset pipeline pending: spec-14 is not built; asset_spec retained for handoff.',
                asset_spec=brief['asset_spec'])
    if out is not None:
        path=Path(out);path.mkdir(parents=True,exist_ok=True)
        (path/'asset-pending.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result
