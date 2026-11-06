"""Offline moving candidate comparison and explicit user-pick application."""
from copy import deepcopy
from dataclasses import replace
import html
import json
from pathlib import Path
import shutil
import cv2
import numpy as np
from PIL import Image
from image_common import ImageError,digest,key,read,utc,write
from image_keyframes import fit_image,keyframe_prompt

DIRECTIONS=['quiet negative space, side light, asymmetric subject placement',
            'foreground depth, layered silhouette, backlit rim',
            'graphic diagonal composition, warm bounce light',
            'intimate eye-level framing, reflected window light',
            'low viewpoint, architectural leading lines',
            'high viewpoint, bold colour-field composition',
            'soft light, tactile material details, gentle curves',
            'hard light, crisp graphic shadows, angular balance']


def phash(path):
    with Image.open(path) as im:a=np.array(im.convert('L').resize((32,32)),np.float32)
    block=cv2.dct(a)[:8,:8];return (block>np.median(block.ravel()[1:])).ravel()


def variants(adapter,req,out,shot='1',board=None,forks=None,approval=None,max_usd=0):
    if not 2<=req.n<=8:raise ImageError('E_VARIANTS_N','Variants require 2..8 candidates.')
    out=Path(out).resolve()
    selected=None
    if board:
        selected=next((s for i,s in enumerate(board['shots'],1) if shot in (s['id'],str(i))),None)
        if selected is None:raise ImageError('E_SHOT','Shot not found.')
    prompt=keyframe_prompt(board,selected) if selected else req.prompt
    replace(req,prompt=prompt).normalized();out.mkdir(parents=True,exist_ok=True)
    forks=forks or (board.get('forks') if board else None) or []
    records=[]
    from image_motion import loop_keyframes
    for i in range(req.n):
        fork=forks[i%len(forks)] if forks else None
        direction=str(fork.get('direction',fork.get('text',fork))) if isinstance(fork,dict) else str(fork) if fork else DIRECTIONS[i]
        if forks and i>=len(forks):direction+='; '+DIRECTIONS[i]
        variant_id=f'v{i+1}';folder=out/variant_id
        request=replace(req,n=1,prompt=prompt+f'\nCandidate {variant_id}: {direction}. Preserve the shared subject identity.')
        manifest=adapter.generate(request,folder,approval,max_usd)
        source=Path(manifest['assets'][0]['path'])
        with Image.open(source) as im:fitted,fit=fit_image(im,(720,1280))
        path=folder/'keyframe.png';fitted.save(path)
        identity=None
        if req.refset_path:
            from image_identity import check
            identity=check(path,req.refset_path)
        loop_keyframes([path],folder/'preview',frames=32,frame_ms=80,size=(144,256),sprites=False,media_qa=False)
        records.append(dict(id=variant_id,path=str(path),sha256=digest(path),direction=direction,
                            fork_id=fork.get('id') if isinstance(fork,dict) else None,gen_manifest=str(folder/'gen-manifest.json'),
                            preview=f'{variant_id}/preview/preview.gif',cache_hit=manifest['cache_hit'],fit=fit,identity=identity))
    distances=[]
    for i in range(len(records)):
        for j in range(i+1,len(records)):
            distance=int(np.count_nonzero(phash(records[i]['path'])!=phash(records[j]['path'])))
            distances.append(dict(a=records[i]['id'],b=records[j]['id'],phash_distance=distance,distinct=distance>=10))
    report=dict(version=1,shot=selected['id'] if selected else shot,candidates=records,pairwise=distances,
                distinct=all(d['distinct'] for d in distances),user_pick=None,advisory=True,
                calls=sum(not r['cache_hit'] for r in records),images_per_call=1,refs_sha=req.refset_sha,
                technical_status='pass' if all(d['distinct'] for d in distances) else 'variants_not_distinct',
                aesthetic_judgement='user only',ai_generated=True)
    if board:write(out/'storyboard-original.json',board)
    write(out/'variants.json',report);page(out);return report


def page(directory,out=None):
    directory=Path(directory).resolve();data=read(directory/'variants.json');out=Path(out) if out else directory/'pick.html'
    # Keep copied relative previews next to an externally requested HTML file.
    cards=[]
    for i,c in enumerate(data['candidates'],1):
        source=directory/c['preview']
        if out.parent.resolve()!=directory:
            dest=out.parent/(out.stem+'-assets')/f'{c["id"]}.gif';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
            src=dest.relative_to(out.parent).as_posix()
        else:src=c['preview']
        cards.append(f'<button class="candidate" data-id="{html.escape(c["id"])}" onclick="pick({i-1})"><span>{i} · {html.escape(c["id"])}</span><div class="frame"><img src="{html.escape(src)}" alt="Moving preview {i}"><div class="safe"></div></div><p>{html.escape(c["direction"])}</p></button>')
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    document='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Choose a direction</title><style>
*{box-sizing:border-box}body{margin:0;background:#11191d;color:#f6f0e6;font:16px system-ui;padding:36px}header{max-width:1000px;margin:auto}h1{font-size:40px;margin:0 0 12px}small{color:#b5c9c2}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin:30px auto;max-width:1400px}.candidate{background:#203039;color:inherit;border:2px solid transparent;border-radius:14px;padding:14px;cursor:pointer;text-align:left;font:inherit}.candidate:focus,.selected{border-color:#ffcd7a}.frame{position:relative;aspect-ratio:9/16;overflow:hidden;margin-top:12px}.frame img{width:100%;height:100%;object-fit:contain}.safe{position:absolute;inset:10%;border:1px dashed #ffffff70;pointer-events:none}p{line-height:1.5;font-size:14px}footer{max-width:1000px;margin:auto}#save{padding:14px 22px;background:#ffcd7a;color:#172025;border:0;border-radius:9px;font-weight:700}#status{min-height:40px}
</style><header><small>STORYBOARD / DIRECTION REVIEW</small><h1>Choose the frame that feels right.</h1><p>Compare the moving previews. Use keys 1–8 or click a candidate. Dashed frame: 9:16 title safe area. Your choice controls the storyboard; no automatic ranking.</p></header><main>CARDS</main><footer><p id="status">No direction selected.</p><button id="save" disabled onclick="save()">Save pick record</button><p>Save picks.json, then apply it with imagegen pick. The originals stay available.</p></footer><script>
const data=PAYLOAD;let record=null;
function pick(i){const c=data.candidates[i];if(!c)return;record={shot:data.shot,variant_id:c.id,sha256:c.sha256,fork_id:c.fork_id,timestamp:new Date().toISOString(),chooser:'user'};document.querySelectorAll('.candidate').forEach(e=>e.classList.toggle('selected',e.dataset.id===c.id));document.getElementById('status').textContent='Selected '+c.id+' · '+c.direction;document.getElementById('save').disabled=false;localStorage.setItem('vgs-image-pick-'+data.shot,JSON.stringify(record));}
function save(){if(!record)return;const blob=new Blob([JSON.stringify(record,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='picks.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
document.addEventListener('keydown',e=>{if(/^[1-8]$/.test(e.key))pick(Number(e.key)-1);});
</script></html>'''.replace('CARDS',''.join(cards)).replace('PAYLOAD',payload)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(document,encoding='utf-8');return str(out.resolve())


def pick(directory,choose=None,record=None,board=None,out_board=None):
    directory=Path(directory);data=read(directory/'variants.json')
    supplied=read(record) if record else None
    if supplied:
        if supplied.get('chooser')!='user' or str(supplied.get('shot'))!=str(data['shot']):raise ImageError('E_PICK','Pick record must identify this shot and chooser:user.')
        choose=supplied['variant_id']
    candidate=next((c for c in data['candidates'] if c['id']==choose),None)
    if candidate is None:raise ImageError('E_PICK','Unknown candidate.')
    if digest(candidate['path'])!=candidate['sha256'] or supplied and supplied['sha256']!=candidate['sha256']:
        raise ImageError('E_PICK_CHANGED','Candidate bytes changed; refresh the review page.')
    if candidate.get('identity',{} ) and candidate['identity']['status']=='identity_fail':raise ImageError('E_IDENTITY','Repair the failed identity before applying this pick.')
    selection=dict(shot=data['shot'],variant_id=choose,sha256=candidate['sha256'],fork_id=candidate['fork_id'],timestamp=utc(),chooser='user')
    with __import__('image_common').locked(directory/'picks.lock'):
        picks=read(directory/'picks.json') if (directory/'picks.json').exists() else []
        picks.append(selection);write(directory/'picks.json',picks)
    board=Path(board) if board else directory/'storyboard-original.json'
    if board.exists():
        b=read(board);shot=next((s for i,s in enumerate(b['shots'],1) if data['shot'] in (s['id'],str(i))),None)
        if shot is None:raise ImageError('E_SHOT','Picked shot missing from storyboard.')
        shot['keyframe']=dict(path=candidate['path'],sha256=candidate['sha256'],gen_manifest=candidate['gen_manifest'],status='user_selected',ai_generated=True)
        b['revision']=dict(changed_shots=[shot['id']],pick=selection)
        target=Path(out_board) if out_board else directory/'storyboard-picked.json';write(target,b);selection['storyboard']=str(target.resolve())
    return selection
