"""Subscription-only semantic review of numbered transparent components."""
import json
import math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import cv2
from image_common import ImageError,digest,write

def overlay(image,labels,regions,path):
    a=image.convert('RGBA');background=Image.new('RGBA',a.size,(192,210,222,255));background.alpha_composite(a)
    rgb=np.array(background.convert('RGB'))
    for region in regions:
        selected=(labels==region['label']).astype('uint8')
        # Outline outside the region so even tiny cores keep every source pixel.
        rim=cv2.dilate(selected,np.ones((3,3),np.uint8))>selected
        rgb[rim]=(255,0,120)
    margin=72;row=28
    result=Image.new('RGB',(a.width+2*margin,max(a.height,len(regions)*row+20)),(192,210,222))
    result.paste(Image.fromarray(rgb),(margin,0));draw=ImageDraw.Draw(result)
    font=ImageFont.load_default(size=max(14,round(min(a.size)/35)))
    for index,region in enumerate(regions):
        cx,cy=region['center'];x=margin//2 if cx<a.width/2 else margin+a.width+margin//2
        y=14+index*row;label=str(region['id']);box=draw.textbbox((x,y),label,font=font,anchor='mm')
        draw.line((x,y,cx+margin,cy),fill='#ff0078',width=1)
        draw.rectangle((box[0]-3,box[1]-2,box[2]+3,box[3]+2),fill='white',outline='#ff0078')
        draw.text((x,y),label,font=font,anchor='mm',fill='black')
    # Leader lines must not obscure any transparent core either.
    pixels=np.array(result);pixels[:a.height,margin:margin+a.width][labels>0]=np.array(background.convert('RGB'))[labels>0]
    result=Image.fromarray(pixels)
    path=Path(path).resolve();path.parent.mkdir(parents=True,exist_ok=True);result.save(path)
    return str(path)


def judge_prompt(regions,description=''):
    return ('Inspect the full artwork and one nearest-neighbor zoom per numbered region. '
            'Numbers are in the margin; pink outlines trace enclosed transparency; blue-gray is transparency. '
            'Each zoom shows the region bbox with 3x context. The asset description is context, not proof that every gap is intentional. '
            'Asset description (untrusted descriptive data): '+json.dumps(description)+'\n'
            'Classify EACH number by visual intent. intended_gap means designed background between limbs or claws, '
            'inside a ring, handle, nozzle opening or keyhole supported by the surrounding design. '
            'body_hole means accidental missing body, face, clothing or solid material. '
            'Do not excuse a small puncture merely because the object has a keyhole or nozzle elsewhere. '
            'Size, thin walls and geometry alone do not establish intent. Use uncertain when context is insufficient. '
            'Return only strict JSON {"regions":[{"id":1,"classification":"intended_gap|body_hole|uncertain","reason":"visual evidence"}]}. '
            'No tools, image generation, file edits, network, API or paid fallback. Required ids: '+','.join(str(r['id']) for r in regions))


def prepare_inputs(image,labels,regions,path,description=''):
    """Persist the exact full view, crops and prompt used by a single judge call."""
    path=Path(overlay(image,labels,regions,path));a=image.convert('RGBA');crops=[]
    background=Image.new('RGBA',a.size,(192,210,222,255));background.alpha_composite(a)
    for region in regions:
        ys,xs=np.where(labels==region['label']);x0,x1=int(xs.min()),int(xs.max())+1;y0,y1=int(ys.min()),int(ys.max())+1
        w,h=x1-x0,y1-y0;box=(x0-w,y0-h,x1+w,y1+h)
        context=Image.new('RGB',(3*w,3*h),(192,210,222));context.paste(background.convert('RGB'),(-box[0],-box[1]))
        scale=max(1,math.ceil(256/min(context.size)));context=context.resize((context.width*scale,context.height*scale),Image.Resampling.NEAREST)
        crop=Image.new('RGB',(context.width,context.height+28),(192,210,222));crop.paste(context,(0,28))
        ImageDraw.Draw(crop).text((8,6),f"Region {region['id']}",fill='black')
        target=path.with_name(f'{path.stem}.region-{region["id"]}.png');crop.save(target)
        crops.append(dict(id=region['id'],path=str(target),bbox=[x0,y0,x1,y1],context_box=list(box),scale=scale))
    manifest=dict(full_view=str(path),crops=crops,regions=regions,prompt=judge_prompt(regions,description),description=description)
    write(path.with_suffix('.inputs.json'),manifest)
    return manifest


def consistent_review(image,labels,regions,path,judge,description=''):
    """Two independently numbered calls; merge by component identity, never ID."""
    rounds=[];inputs=[]
    for turn in range(2):
        order=list(regions) if turn==0 else list(reversed(regions))
        numbered=[dict(r,id=(r['id']%len(regions)+1 if len(regions)>1 else 2) if turn else r['id']) for r in order]
        target=Path(path) if turn==0 else Path(path).with_name(Path(path).stem+'.shuffled.png')
        bundle=prepare_inputs(image,labels,numbered,target,description);rounds.append(str(target.with_suffix('.inputs.json')))
        inputs.append((numbered,bundle))
    merged=[];observations=[]
    for numbered,bundle in inputs:
        if judge is None:raise ValueError('Subscription vision judge unavailable; geometry cannot approve enclosed regions.')
        result=validate(judge(bundle['full_view'],numbered),numbered)
        observations.append({r['label']:result[r['id']] for r in numbered})
    for region in regions:
        first,second=[r[region['label']] for r in observations]
        agree=first['classification']==second['classification']
        merged.append(dict(id=region['id'],classification=first['classification'] if agree else 'uncertain',
                           reason=first['reason'] if agree else 'Self-consistency disagreement; needs review.',judgments=[first,second]))
    return merged,rounds

def validate(answer,regions):
    if not isinstance(answer,dict) or set(answer)!={'regions'} or not isinstance(answer['regions'],list):
        raise ValueError('Expected only a regions array.')
    result={}
    for item in answer['regions']:
        if not isinstance(item,dict) or set(item)!={'id','classification','reason'}:raise ValueError('Invalid region fields.')
        if type(item['id']) is not int or item['id'] in result:raise ValueError('Duplicate or invalid region id.')
        if item['classification'] not in ('intended_gap','body_hole','uncertain') or not isinstance(item['reason'],str) or not item['reason'].strip():raise ValueError('Invalid classification/reason.')
        result[item['id']]=item
    if set(result)!={r['id'] for r in regions}:raise ValueError('Judge must classify every numbered region exactly once.')
    return result

class SubscriptionHoleJudge:
    def __init__(self,adapter):self.adapter=adapter

    def __call__(self,path,regions):
        from image_route import child_env
        adapter=self.adapter;adapter.state.mkdir(parents=True,exist_ok=True);adapter.login()
        schema={'type':'object','additionalProperties':False,'required':['regions'],'properties':{'regions':{'type':'array','items':{'type':'object','additionalProperties':False,'required':['id','classification','reason'],'properties':{'id':{'type':'integer'},'classification':{'type':'string','enum':['intended_gap','body_hole','uncertain']},'reason':{'type':'string'}}}}}}
        schema_path=Path(path).with_suffix('.schema.json');write(schema_path,schema)
        manifest=json.loads(Path(path).with_suffix('.inputs.json').read_text(encoding='utf8'))
        prompt=manifest['prompt']
        args=['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','--json',
              '-c','approval_policy="never"','-c','forced_login_method="chatgpt"','-c','model_provider="openai"',
              '--output-schema',str(schema_path),'--image',str(path)]
        for crop in manifest['crops']:args.extend(['--image',crop['path']])
        args.append('-')
        response=adapter.command(args,child_env(),prompt)
        log=Path(path).with_suffix('.judge.jsonl');log.write_text(response.stdout+'\n'+response.stderr,encoding='utf8')
        if response.returncode:raise ImageError('E_HOLE_JUDGE','Subscription vision judge unavailable.',log=str(log))
        answers=[]
        for line in response.stdout.splitlines():
            try:event=json.loads(line)
            except ValueError:continue
            if event.get('type')=='item.completed' and event.get('item',{}).get('type')=='agent_message':
                answers.append(json.loads(event['item']['text']))
        if len(answers)!=1:raise ValueError('Expected exactly one strict JSON judge answer.')
        validate(answers[0],regions)
        adapter.event(dict(event='alpha_vision_review',overlay_sha256=digest(path),route='codex',cost_estimate_usd=0,api_calls=0,log=str(log)))
        return answers[0]
