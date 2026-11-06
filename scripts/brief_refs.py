"""Reference acquisition adapted from blank-page find_refs.py / finding-references.md.

MIT, Copyright (c) 2026 Cekura, Inc.; full notice in THIRD_PARTY.md.
Rewritten: injectable transport, bounded downloads, sequential sheets, explicit
vetting and provenance, no Pinterest crawler and no implicit network access.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import quote, urlencode

ROLES=('look','palette','material','composition','detail','main mechanic','turn','exit')
HANDLES=('a1','a2','a3','a4','a5','m1','m2','m3')
MOTION_SEEDS=('mo-graph-1uxjlkjqqhc','type-animation-references','design-moving-l9-xt3sxtne',
              'motion-inspo-tfrw-gidqfw','ad-device-tech','product-video-mf4kzs1zbo0')
UMBRELLAS=('vis-4hvdpzvvua4','flat-ovcn8k0nwa0','form-glcjdzmigiq','mercenary')


def licence_status(asset):
    licence=str(asset.get('licence',asset.get('license','unknown'))).upper().replace(' ','-')
    if licence in ('USER-OWNED','OWNED') and asset.get('owned') is True: return 'allowed'
    if licence in ('CC0','CC0-1.0','PUBLIC-DOMAIN'): return 'allowed'
    if re.fullmatch(r'CC-BY(?:-\d\.\d)?',licence): return 'allowed' if asset.get('author') and (asset.get('page_url') or asset.get('source_url')) else 'missing_attribution'
    if re.fullmatch(r'CC-BY-SA(?:-\d\.\d)?',licence): return 'share_alike_review'
    return 'blocked'


def validate_assets(assets):
    if not isinstance(assets,list) or any(not isinstance(a,dict) for a in assets):raise ValueError('E_LICENCE assets: expected asset records')
    for i,asset in enumerate(assets):
        if asset.get('role')=='reference' or asset.get('read_only'):
            raise ValueError(f'E_REF_EMBED assets[{i}]: references are read-only; supply an owned/licensed asset')
        if licence_status(asset)!='allowed':
            raise ValueError(f'E_LICENCE assets[{i}]: {asset.get("licence","unknown")}; use CC0, attributed CC-BY or explicitly owned media')
    return [dict(author=a['author'],title=a.get('title',''),licence=a['licence'],url=a.get('page_url',a.get('source_url')))
            for a in assets if str(a.get('licence','')).upper().startswith('CC-BY')]


class CassetteProvider:
    """One high-level lookup per empty slot; records are agent-vetted candidates."""
    def __init__(self, data): self.data=data; self.requests=[]
    def search(self, role, query, moving=False):
        self.requests.append(dict(role=role,query=query,moving=moving))
        return deepcopy(self.data.get(role,self.data.get(query,[])))


class ReferenceFinder:
    """Transport receives an operation and URL; callers record/replay every request.

    `web_search` is an agent/browser search adapter, never a Pinterest scraper.
    Search returns candidates only. Selection requires an explicit vetted record.
    """
    def __init__(self, transport, web_search=None):
        self.transport=transport; self.web_search=web_search; self.requests=[]; self.downloads=0

    def request(self, path):
        url='https://api.are.na/'+path
        self.requests.append(dict(operation='json',url=url))
        return self.transport('json',url)

    def channels(self, query):
        rows=self.request('v2/search/channels?'+urlencode(dict(q=query,per=60))).get('channels',[])
        return sorted((r for r in rows if r.get('length',0)>=20),key=lambda r:(-(r.get('follower_count') or 0),r['slug']))

    def combined(self, query):
        return self.request('v2/search?'+urlencode(dict(q=query,per=50,page=1)))

    def user_channels(self, user, max_pages=10):
        rows=[]
        for page in range(1,max_pages+1):
            data=self.request(f'v3/users/{quote(user)}/contents?type=Channel&per=100&page={page}')
            rows.extend(data.get('data',[]))
            if not data.get('meta',{}).get('has_more_pages'): break
        return rows

    def contents(self, slug, max_pages=3):
        rows=[]
        for page in range(1,max_pages+1):
            data=self.request(f'v2/channels/{quote(slug)}/contents?per=100&page={page}&direction=desc').get('contents',[])
            rows.extend(data)
            if len(data)<100: break
        return rows

    def umbrella(self, slug, pattern='.'):
        return sorted((r for r in self.contents(slug) if r.get('class')=='Channel' and re.search(pattern,r.get('title',''),re.I)),key=lambda r:-(r.get('length') or 0))

    def connections(self, block_id):
        return sorted(self.request(f'v2/blocks/{block_id}/channels?per=50').get('channels',[]),key=lambda r:-(r.get('length') or 0))[:12]

    @staticmethod
    def block(row, channel=''):
        attachment=row.get('attachment') or {}; media=attachment.get('url') or ((row.get('image') or {}).get('original') or {}).get('url')
        return dict(page_url=f'https://www.are.na/block/{row["id"]}',source_url=media,channel=channel,
                    original_url=(row.get('source') or {}).get('url'),title=row.get('title',''),
                    moving=bool(media and ('.gif' in media.split('?')[0] or attachment.get('extension') in ('mp4','mov','webm','gif'))),
                    licence='unknown',author=row.get('author',''),vetted=False)

    def search(self, role, query, moving=False):
        rows=[]
        channels=self.channels(query)[:3] if not moving else [dict(slug=s) for s in MOTION_SEEDS[:3]]
        for channel in channels:
            for block in self.contents(channel['slug']):
                if block.get('class')=='Channel': continue
                row=self.block(block,channel['slug'])
                if row['source_url'] and row['moving']==moving: rows.append(row)
        if not rows and self.web_search:
            # The host performs search and vetting; this module never scrapes pins.
            rows=self.web_search(query+(' animation gif' if moving else ''),domains=['pinterest.com'])
        return rows

    def sketchfab(self, query, max_faces=300000):
        url='https://api.sketchfab.com/v3/search?'+urlencode(dict(type='models',q=query,downloadable='true',count=24,max_face_count=max_faces,sort_by='-likeCount'))
        self.requests.append(dict(operation='json',url=url))
        rows=[]
        for r in self.transport('json',url).get('results',[]):
            archive=(r.get('archives') or {}).get('glb') or {}
            rows.append(dict(uid=r['uid'],title=r['name'],author=r['user']['username'],licence=(r.get('license') or {}).get('label','unknown'),
                             faces=r.get('faceCount'),animations=r.get('animationCount'),bytes=archive.get('size'),textures=archive.get('textureCount'),
                             tex_max=archive.get('textureMaxResolution'),page_url=f'https://sketchfab.com/3d-models/{r["uid"]}',parts_review='required before animating hinges/limbs'))
        return rows

    def model_route(self, uid, mirror_paths=None, authenticated_url=None):
        # Supply a local mirror index; never silently download the 20 MB index.
        if (mirror_paths or {}).get(uid): return 'https://huggingface.co/datasets/allenai/objaverse/resolve/main/'+mirror_paths[uid]
        return authenticated_url or dict(page_url=f'https://sketchfab.com/3d-models/{uid}',placeholder='[? download]')

    def download(self, row, destination):
        if self.downloads>=30: raise ValueError('Reference download limit: 30 per brief')
        if not row.get('source_url'): raise ValueError('source_url required')
        if any(not row.get(key) for key in ('page_url','role','use')):raise ValueError('Reference download requires page_url, role and scoped use')
        self.requests.append(dict(operation='bytes',url=row['source_url']))
        data=self.transport('bytes',row['source_url'])
        if not isinstance(data,bytes) or len(data)>2_000_000: raise ValueError('Reference must be at most 2 MB; supply a smaller preview')
        ext=real_ext(data)
        if not ext: raise ValueError('Unsupported media signature')
        out=Path(destination).with_suffix('.'+ext);out.parent.mkdir(parents=True,exist_ok=True)
        if out.exists(): raise ValueError('Use a new reference path')
        out.write_bytes(data);self.downloads+=1
        record=dict(row,path=str(out.resolve()),licence=row.get('licence') or 'unknown',retrieved_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(data).hexdigest(),read_only=True)
        out.with_suffix(out.suffix+'.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        return record


def real_ext(data):
    for magic,ext in ((b'\x89PNG','png'),(b'\xff\xd8\xff','jpg'),(b'GIF8','gif'),(b'glTF','glb'),(b'\x1aE\xdf\xa3','webm')):
        if data.startswith(magic): return ext
    if data[4:8]==b'ftyp': return 'mp4'
    if data[:4]==b'RIFF' and data[8:12]==b'WEBP': return 'webp'


def contact_sheet(path, out, frames=9):
    """Sequential decode; actual timestamps printed and saved for image feedback."""
    import cv2
    from PIL import Image, ImageDraw
    if frames not in (9,16,25): raise ValueError('Choose 9, 16 or 25 frames')
    cap=cv2.VideoCapture(str(path));fps=cap.get(cv2.CAP_PROP_FPS);count=cap.get(cv2.CAP_PROP_FRAME_COUNT)
    if fps<=0 or count<=0: cap.release();raise ValueError('Cannot decode motion reference')
    duration=count/fps;cols=math.ceil(math.sqrt(frames));sheet=Image.new('RGB',(cols*240,cols*160),'white');times=[]
    for i in range(frames):
        index=round(i*(count-1)/frames);cap.set(cv2.CAP_PROP_POS_FRAMES,index);ok,frame=cap.read()
        if not ok: cap.release();raise ValueError('Cannot decode reference frame')
        time=index/fps;times.append(time);tile=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));tile.thumbnail((240,132))
        x=(i%cols)*240;y=(i//cols)*160;sheet.paste(tile,(x,y));ImageDraw.Draw(sheet).text((x+3,y+134),f'{i+1}: {time:.3f}s / {duration:.3f}s',fill='black')
    cap.release();out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);sheet.save(out)
    metadata=dict(duration_s=duration,frames_at_s=times,source=str(Path(path).resolve()))
    out.with_suffix('.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8');return metadata


def ground(aesthetic, cards=(), taste=None, refstat=None, library=(), provider=None, offline=False):
    """User slots first; authored taste/refstat reference slots next; web only gaps.

    Statistics alone never pretend to be a visual reference. Missing slots remain
    explicit local placeholders, with attempted queries, in both offline paths.
    """
    refs=[];attempts=[];failed=False;used=set()
    def identity(row):
        path=row.get('path')
        return str(Path(path).resolve()).casefold() if path else row.get('source_url',row.get('id',str(row)))
    def available(row):return identity(row) not in used
    for i,(handle,role) in enumerate(zip(HANDLES,ROLES)):
        moving=i>=5;query=role+' animation' if moving else aesthetic
        chosen=None;source='local_lib'
        if not moving and cards:
            terms={'look':['light','window','cup','光','杯'],'palette':['light','orange','光','橘'],
                   'material':['menu','paper','菜單','紙'],'composition':['cup','杯'],'detail':['open','text','字','店']}[role]
            ranked=sorted(((j,c) for j,c in enumerate(cards) if available(c)),key=lambda pair:(-sum(t in json.dumps(pair[1],ensure_ascii=False).lower() for t in terms),pair[0]))
            if ranked:chosen=deepcopy(ranked[0][1]);source='user';chosen['origin_handle']='u'+str(ranked[0][0]+1)
        for origin,data in (('taste',taste),('refstat',refstat)):
            if chosen is None:
                chosen=next((deepcopy(r) for r in (data or {}).get('refs',[]) if r.get('role')==role and available(r)),None)
                if chosen: source=origin
        if chosen is None:
            chosen=next((deepcopy(r) for r in library if available(r) and r.get('vetted') and bool(r.get('moving'))==moving and (moving or r.get('aesthetic_tag')==aesthetic)),None)
            if chosen: source='local_lib'
        if chosen is None and provider and not offline and not failed:
            try:
                candidates=provider.search(role,query,moving=moving)
                chosen=next((deepcopy(r) for r in candidates if available(r) and r.get('vetted') and bool(r.get('moving'))==moving and (moving or r.get('aesthetic_tag')==aesthetic)),None)
                attempts.append(dict(role=role,query=query,provider=type(provider).__name__,result='selected' if chosen else 'no vetted candidate'))
                if chosen: source='web'
            except (OSError,TimeoutError) as exc:
                failed=True;attempts.append(dict(role=role,query=query,provider=type(provider).__name__,error=str(exc)))
        if chosen is None:
            chosen=dict(placeholder='[? motion ref]' if moving else '[? visual ref]',status='ref_missing',queries_tried=[query],licence='unknown')
        else:used.add(identity(chosen))
        chosen.update(handle=handle,role=role,source=source,read_only=True)
        chosen.setdefault('licence','unknown');refs.append(chosen)
    return refs,dict(offline=offline or failed or provider is None,attempts=attempts)


def reference_sheets(refs,root):
    """Create inspectable local sheets; absent media never gets a fictitious path."""
    from PIL import Image,ImageDraw
    root=Path(root);still=[];outputs=[]
    for ref in refs:
        path=Path(ref.get('path',''))
        if not path.is_file():
            ref['status']='ref_missing';continue
        try:
            if ref['handle'].startswith('m'):
                out=root/(ref['handle']+'.png');contact_sheet(path,out);outputs.append(str(out))
            else:
                with Image.open(path) as im:tile=im.convert('RGB');tile.thumbnail((240,150))
                still.append((ref['handle'],tile))
        except (OSError,ValueError):ref['status']='ref_missing'
    if still:
        root.mkdir(parents=True,exist_ok=True);sheet=Image.new('RGB',(240*len(still),180),'white')
        for i,(handle,tile) in enumerate(still):
            sheet.paste(tile,(i*240,0));ImageDraw.Draw(sheet).text((i*240+5,155),handle,fill='black')
        out=root/'aesthetic.png';sheet.save(out);outputs.insert(0,str(out))
    return outputs
