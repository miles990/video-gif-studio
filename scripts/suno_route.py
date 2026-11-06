"""Experimental agent/MCP request planner. No network or credentials in Python.

An injected transport is for offline cassettes or a host with a real tool guard.
Codex direct-tool delivery is instruction_only and requires an explicit override.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
import unicodedata
from image_common import ImageError, write, read, digest

CREATE = {'sounds_create', 'audio_create', 'audio_covers_create', 'audio_mashups_create',
          'audio_extensions_create', 'speech_create'}
TOOLS = ('account_me account_upgrade account_usage audio_analysis audio_covers_create audio_create '
         'audio_download audio_edit audio_extensions_create audio_full_song audio_like audio_listen '
         'audio_listen_wait audio_lyrics_alignment audio_mashups_create audio_retrieve audio_unlike '
         'audio_upload_complete audio_upload_create audio_wait library_liked library_list library_search '
         'playlists_add_clips playlists_create playlists_list playlists_list_clips playlists_remove_clips '
         'sounds_create speech_create voices_list voices_start workspaces_create workspaces_list '
         'workspaces_update_clips').split()


def now():
    return datetime.now(timezone.utc).isoformat()


def normalize(value):
    if isinstance(value, dict): return {str(k): normalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list): return [normalize(v) for v in value]
    if isinstance(value, str): return unicodedata.normalize('NFKC', value).strip()
    if isinstance(value, float):
        if not math.isfinite(value): raise ValueError('Nonfinite request')
        return int(value) if value.is_integer() else value
    return value


def cache_key(tool, params, model=None):
    data = normalize(dict(tool=tool, params=params, model=model))
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def plan(request):
    kind = request['kind']; desired = {k: request.get(k) for k in ('bpm', 'key', 'meter')}
    prompt = request.get('description', request.get('mood', 'Original music'))
    if kind in ('bgm-loop', 'sfx', 'jingle'):
        tool = 'sounds_create'; params = dict(description=prompt, loop=kind == 'bgm-loop')
        if desired['bpm'] is not None: params['tempo'] = desired['bpm']
        if desired['key'] is not None:
            if desired['key'] not in [n+s for n in ('C','C#','D','D#','E','F','F#','G','G#','A','A#','B') for s in ('','m')]:
                raise ValueError('Use Suno sharp key spelling (e.g. A#m, not Bbm)')
            params['key'] = desired['key']
        reason = 'Sounds supports tempo/key/loop; duration and meter are measured, not set.'
    elif kind == 'variants':
        tool = 'audio_covers_create'; params = dict(id=request['theme'], style=prompt)
        reason = 'Cover retains a source reference; BPM/key require measurement and bounded local correction.'
    elif kind in ('score', 'theme', 'song'):
        tool = 'audio_create'; params = dict(instrumental=request.get('instrumental', True), style=prompt)
        if 'duration' in request: params.update(duration=request['duration'], duration_strict=True)
        if 'lyrics' in request: params['lyrics'] = request['lyrics']
        reason = 'Song schema has no BPM/key/meter: measure after generation; stretch <=4% or use sounds.'
    else: raise ValueError('Unknown audio kind: '+kind)
    key = cache_key(tool, params, params.get('model'))
    return dict(status='experimental', music_route='suno', tool=tool, params=params,
                cache_key=key, requested=desired, reason=reason,
                estimated_song_credits=2 if tool == 'sounds_create' else None,
                estimated_downloads=0, download_guard='instruction_only')


class Ledger:
    """Durable single-writer ledger: reservations survive process interruption.

    All host tool dispatches must go through guard() for runtime enforcement.
    This is NOT a claim that Codex's direct MCP tool has been intercepted.
    """
    def __init__(self, path, cap=5):
        self.path = Path(path)
        self.data = read(path) if self.path.exists() else dict(version=1, round='s15', cap=min(cap,5),
            calls=[], selections={}, cache={}, downloads={}, reservations={}, halted=False)

    def save(self): write(self.path, self.data)

    def record(self, tool, params, response, before=None, after=None):
        # Never ingest library metadata or signed URLs into a shareable ledger.
        if tool.startswith('library_'): raise ImageError('E_PRIVATE', 'Library responses require a private manifest')
        row = dict(tool=tool, params=normalize(params), at=now(),
                   idempotency_key=params.get('idempotency_key'),
                   clip_ids=response.get('clip_ids', [response['id']] if 'id' in response else []),
                   status=response.get('status', response.get('reason', 'complete')),
                   credits_before=before, credits_after=after,
                   replayed=bool(response.get('Idempotency-Replayed', False)))
        row['credits_spent'] = {k: max(0, before[k]-after[k]) for k in before} if before and after else None
        if response.get('url'): row['url_sha256'] = hashlib.sha256(response['url'].encode()).hexdigest()
        self.data['calls'].append(row); self.save(); return row

    def select(self, clip, by):
        if by != 'user' and not by.startswith('standing:'): raise ValueError('Selection needs user or standing:<id>')
        self.data['selections'][clip] = dict(clip_id=clip, selected_by=by, at=now()); self.save()

    def usage(self):
        calls = self.data['calls']
        first = next((r['credits_before'] for r in calls if r.get('credits_before')), {})
        after = next((r['credits_after'] for r in reversed(calls) if r.get('credits_after')), {})
        remaining = after.get('download_credits_remaining')
        return dict(create_calls=sum(r['tool'] in CREATE and not r.get('replayed',False) for r in calls),
            song_credits=max(0,first.get('credits_remaining',0)-after.get('credits_remaining',0)),
            download_credits=sum((r.get('credits_spent') or {}).get('download_credits_remaining',0) for r in calls if r['tool']=='audio_download'),
            remaining_download_credits=remaining, downloads_until_stop=max(0,remaining-9) if remaining is not None else None)

    def guard(self, tool, params, usage=None, selected=False):
        if tool.startswith('library_') or tool.startswith('playlists_') or tool in ('audio_edit','audio_like','audio_unlike','workspaces_update_clips'):
            raise ImageError('E_PRIVATE','Library and publication operations are outside this audio build route')
        if self.data['halted']: raise ImageError('E_DOWNLOAD_BUDGET', 'Queue halted; reconcile ledger before resuming')
        if tool in CREATE:
            if self.usage()['create_calls'] + len(self.data['reservations']) >= 40 or self.usage()['song_credits'] >= 500:
                raise ImageError('E_GENERATION_BUDGET','Generation allowance exhausted')
        if tool != 'audio_download': return
        clip=params['id']; fmt=params.get('format','wav')
        if clip not in self.data['selections']: raise ImageError('E_SELECTION','Select a final clip before download')
        if fmt != 'wav' and not selected: raise ImageError('E_FORMAT','MP3 needs an explicit non-loop reason')
        if usage is None: raise ImageError('E_DOWNLOAD_BUDGET','Fresh account_usage is required')
        current=clip+':'+fmt
        reserved={k for k,v in self.data['downloads'].items() if v.get('credit_reserved')}
        reserved.update(k for k,v in self.data['reservations'].items() if v.get('requires_credit'))
        # Count authorized slots even when the provider debit settles later.
        # The current pending clip keeps its one slot during preparation polls.
        used=max(self.usage()['download_credits'],len(reserved-{current}))
        remaining=usage['download_credits_remaining']
        if used >= self.data['cap'] or remaining <= 9:
            self.data['halted']=True; self.save()
            raise ImageError('E_DOWNLOAD_BUDGET','Download queue stopped', remaining=remaining, used=used,
                             suggestion='Use cached final files or preview analysis; do not bypass the queue.')
        if params.get('confirm') and not self.data['reservations'].get(clip+':'+fmt,{}).get('requires_credit'):
            raise ImageError('E_DOWNLOAD_BUDGET','No requires_credit authorization for this clip/format')


class Session:
    """Offline/host-controlled transport; intentionally no HTTP MCP client."""
    def __init__(self, ledger, transport, sleep=time.sleep):
        self.ledger=ledger; self.transport=transport; self.sleep=sleep

    def usage(self):
        r=self.transport('account_usage',{}); u=r.get('suno_account',r)
        u={k:u[k] for k in ('credits_remaining','download_credits_remaining')}
        self.ledger.record('account_usage',{}, {},u,u); return u

    def call(self,tool,params,before=None):
        self.ledger.guard(tool,params,before)
        if tool=='audio_listen':
            today=now()[:10];calls=self.ledger.data['calls']
            asked=[r for r in calls if r['tool']=='audio_listen' and r['at'][:10]==today]
            settled={i for r in calls if r['tool']=='audio_listen_wait' and r['status'] in ('complete','unavailable','error') for i in r['clip_ids']}
            outstanding=[r for r in asked if not set(r['clip_ids'])&settled]
            if len(asked)>=200 or len(outstanding)>=5:raise ImageError('E_LISTEN_LIMIT','Queue listen requests or use local analysis')
        result=self.transport(tool,params)
        after=self.usage() if tool in CREATE or tool=='audio_download' else before
        self.ledger.record(tool,params,result,before,after)
        return result

    def create(self,request,experimental=False,bypass=False):
        if not experimental: raise ImageError('E_EXPERIMENTAL','Suno requires --experimental')
        p=plan(request); key=p['cache_key']; cache=self.ledger.data['cache']
        if key in cache and not bypass: return dict(cache[key],cache='hit')
        attempt=sum(r['tool']==p['tool'] and r['params'].get('idempotency_key','').startswith(key) for r in self.ledger.data['calls']) if bypass else 0
        params=dict(p['params'],idempotency_key=key+':'+str(attempt)); before=self.usage()
        for retry in range(3):
            r=self.call(p['tool'],params,before)
            if r.get('code') not in (500,429,'rate_limited'): break
            self.sleep(2**retry)
        if r.get('error'): raise ImageError('E_ROUTE_UNAVAILABLE',str(r.get('reason',r['error'])),suggestion='Use local sfx or user audio + music_fit')
        result=dict(p,clip_ids=r.get('clip_ids',[r['id']] if 'id' in r else []),idempotency_key=params['idempotency_key'],cache='bypass:user' if bypass else 'miss')
        cache[key]=result; self.ledger.save(); return result

    def poll(self,tool,params,limit=60):
        if tool not in ('audio_analysis','audio_lyrics_alignment','audio_wait','audio_listen_wait'): raise ValueError('Not a polling tool')
        if tool=='audio_wait' and len(params.get('ids',[]))>4: raise ValueError('audio_wait accepts at most 4 IDs')
        for _ in range(limit):
            r=self.call(tool,params)
            if r.get('status') in ('complete','unavailable','error','streaming'): return r
            self.sleep(1)
        raise ImageError('E_PENDING','Polling deadline reached; resume the existing job')

    def download(self,clip,fmt='wav'):
        key=clip+':'+fmt; old=self.ledger.data['downloads'].get(key)
        if old: return dict(old,cache='hit')
        params=dict(id=clip,format=fmt); retries=0
        for _ in range(60):
            before=self.usage(); r=self.call('audio_download',params,before)
            status=r.get('status',r.get('reason'))
            if status=='requires_credit':
                self.ledger.data['reservations'][key]=dict(requires_credit=True);self.ledger.save()
                params['confirm']=True; continue
            if status in ('quota_exhausted','daily_limit_exceeded'):
                self.ledger.data['halted']=True;self.ledger.save()
                raise ImageError('E_DOWNLOAD_BUDGET',status)
            if status=='rate_limited' and retries<2: retries+=1;self.sleep(2**(retries-1));continue
            if status=='processing': self.sleep(1);continue
            if r.get('url'):
                result=dict(clip_id=clip,format=fmt,url_sha256=hashlib.sha256(r['url'].encode()).hexdigest(),at=now(),
                            credit_reserved=bool(params.get('confirm')))
                self.ledger.data['downloads'][key]=result;self.ledger.data['reservations'].pop(key,None);self.ledger.save()
                return dict(result,url=r['url'])
            raise ImageError('E_DOWNLOAD',str(r))
        raise ImageError('E_PENDING','Download pending; resume without changing the clip')


def main(argv=None):
    import sys
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0]=='demo':
        from audio_demo import main as demo_main
        return demo_main(argv[1:])
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','create','select','download','usage'])
    p.add_argument('--request',type=Path);p.add_argument('--ledger',type=Path,default=Path('.scratch/suno/suno-ledger.json'))
    p.add_argument('--clip');p.add_argument('--by',default='user');p.add_argument('--format',default='wav')
    p.add_argument('--experimental',action='store_true');p.add_argument('--json',action='store_true');p.add_argument('--out',type=Path)
    a=p.parse_args(argv)
    try:
        ledger=Ledger(a.ledger)
        if a.action in ('plan','create'):
            if a.action=='create' and not a.experimental: raise ImageError('E_EXPERIMENTAL','Suno requires --experimental')
            result=plan(read(a.request));result['dispatch']='agent_required'
            if a.action=='create': result['params']['idempotency_key']=result['cache_key']+':0'
        elif a.action=='select': ledger.select(a.clip,a.by);result=ledger.data['selections'][a.clip]
        elif a.action=='usage': result=ledger.usage()
        else: result=dict(status='pending',download_guard='instruction_only',dispatch='disabled_by_default',clip_id=a.clip,format=a.format)
        if a.out: write(a.out/'request.json',result)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,OSError,KeyError) as e:
        print(json.dumps(dict(ok=False,error=getattr(e,'error',dict(code='E_REQUEST',message=str(e))))));return 2


if __name__=='__main__': raise SystemExit(main())
