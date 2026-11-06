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
