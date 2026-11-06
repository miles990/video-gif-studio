"""Offline Suno transport, validated against the 35 exposed tool input schemas.

Schemas were transcribed mechanically from the connected server's TypeScript
tool declarations on 2026-11-06. No account/library response is a fixture.
"""
import copy
import json
from pathlib import Path
import uuid
from suno_route import CREATE

SCHEMAS=json.loads(Path(__file__).with_name('suno-tool-schemas.json').read_text())


def valid(value,schema):
    if 'anyOf' in schema:return any(valid(value,s) for s in schema['anyOf'])
    if 'const' in schema:return value==schema['const']
    kind=schema['type']
    if kind=='object':
        return (isinstance(value,dict) and all(k in value for k in schema['required'])
                and not set(value)-set(schema['properties'])
                and all(valid(v,schema['properties'][k]) for k,v in value.items()))
    if kind=='array':return isinstance(value,list) and all(valid(v,schema['items']) for v in value)
    if kind=='string':return isinstance(value,str)
    if kind=='number':return isinstance(value,(int,float)) and not isinstance(value,bool)
    if kind=='boolean':return isinstance(value,bool)
    if kind=='null':return value is None
    raise ValueError('Unknown schema type '+kind)


class FakeSuno:
    def __init__(self,balance=67,song=100):
        self.balance=balance;self.song=song;self.calls=[];self.created={};self.script=[]
        self.responses={};self.clips={};self.listen_jobs={};self.balance_sequence=[]
        self.private_token='fixture-private-'+uuid.uuid4().hex

    def queue(self,tool,*responses):self.responses.setdefault(tool,[]).extend(copy.deepcopy(responses))

    @property
    def confirm_calls(self):return sum(t=='audio_download' and p.get('confirm',False) for t,p in self.calls)

    def __call__(self,tool,p):
        tool=tool.removeprefix('mcp__suno__')
        if tool not in SCHEMAS or not valid(p,SCHEMAS[tool]):
            return dict(error='invalid schema',code=400)
        self.calls.append((tool,copy.deepcopy(p)))
        scripted=self.responses.get(tool,[])
        if scripted:return scripted.pop(0)
        if tool=='account_usage':
            if self.balance_sequence:self.balance=self.balance_sequence.pop(0)
            return dict(credits_remaining=self.song,download_credits_remaining=self.balance)
        if tool in CREATE:
            key=p.get('idempotency_key',uuid.uuid4().hex)
            signature=json.dumps(dict(tool=tool,params=p),sort_keys=True)
            if key in self.created:
                old_signature,result=self.created[key]
                if signature!=old_signature:return dict(error='idempotency conflict',code=409)
                return dict(result,**{'Idempotency-Replayed':True})
            if tool=='sounds_create' and len(p['description'])>500:return dict(error='description too long',code=400)
            cost=2 if tool=='sounds_create' else 10
            if self.song<cost:return dict(error='insufficient credits',reason='quota_exhausted',code=402)
            self.song-=cost;ids=[f'fake-{len(self.created)}-{suffix}' for suffix in ('a','b')]
            result=dict(clip_ids=ids,status='processing');self.created[key]=(signature,result)
            for clip in ids:self.clips[clip]=dict(id=clip,status='complete',metadata=dict(duration=8),song_url='https://invalid.test/'+clip)
            return result
        if tool=='audio_download':
            if self.script:return self.script.pop(0)
            if not p.get('confirm'):return dict(status='requires_credit')
            if self.balance<=0:return dict(error='no credits',reason='quota_exhausted',code=402)
            self.balance-=1;return dict(url='https://invalid.test/'+p['id']+'.'+p.get('format','mp3'))
        if tool=='audio_wait':
            ids=p.get('ids',[p.get('id')])
            if len(ids)>4:return dict(error='max four IDs',code=400)
            return dict(status='complete',clips=[self.clips.get(i,dict(id=i,status='error')) for i in ids])
        if tool=='audio_retrieve':return self.clips.get(p['id'],dict(error='not found',code=404))
        if tool=='audio_analysis':return dict(status='complete',audio_id=p['id'],beats=[dict(time_s=i*.5,bar_position=i%4+1) for i in range(16)],bpm=120,key='A minor',time_signature=4,duration_s=8,sections=[])
        if tool=='audio_lyrics_alignment':return dict(status='complete',audio_id=p['id'],words=[])
        if tool=='audio_listen':
            if sum(v=='processing' for v in self.listen_jobs.values())>=5:return dict(reason='concurrency_limit_exceeded',code=429)
            job='listen-'+str(len(self.listen_jobs));self.listen_jobs[job]='processing';return dict(id=job,status='processing')
        if tool=='audio_listen_wait':self.listen_jobs[p['id']]='complete';return dict(id=p['id'],status='complete',answer='Offline fixture only')
        if tool.startswith('library_'):return dict(items=[dict(id=self.private_token+str(i),title=self.private_token) for i in range(12)])
        # Remaining zero-credit account/upload/organization operations are schema
        # checked and scriptable. They are never used by the production build route.
        return dict(status='complete',id='fake-'+tool,items=[])
