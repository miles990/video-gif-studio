"""Subscription-only semantic review of numbered transparent components."""
import json
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
        contours,_=cv2.findContours(selected,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(rgb,contours,-1,(255,0,120),max(1,round(min(a.size)/400)))
    result=Image.fromarray(rgb);draw=ImageDraw.Draw(result)
    font=ImageFont.load_default(size=max(14,round(min(a.size)/35)))
    for region in regions:
        x,y=region['center'];label=str(region['id']);box=draw.textbbox((x,y),label,font=font,anchor='mm')
        draw.rectangle((box[0]-3,box[1]-2,box[2]+3,box[3]+2),fill='white',outline='#ff0078')
        draw.text((x,y),label,font=font,anchor='mm',fill='black')
    path=Path(path).resolve();path.parent.mkdir(parents=True,exist_ok=True);result.save(path)
    return str(path)

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
        prompt=('Inspect the attached artwork. Pink outlines and numbers identify enclosed fully transparent regions; blue-gray is transparency. '
                'Classify EACH number by visual intent, not geometry. intended_gap means open background between limbs, inside a ring/handle/keyhole. '
                'body_hole means an accidental cut through body, face, clothing, a solid shaft or solid material. '
                'Thin enclosing walls or large/elongated holes do NOT establish intent. Use uncertain if context is insufficient. '
                'Return only strict JSON {"regions":[{"id":1,"classification":"intended_gap|body_hole|uncertain","reason":"visual evidence"}]}. '
                'No tools, image generation, file edits, network, API or paid fallback. Required ids: '+','.join(str(r['id']) for r in regions))
        args=['exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','--json',
              '-c','approval_policy="never"','-c','forced_login_method="chatgpt"','-c','model_provider="openai"',
              '--output-schema',str(schema_path),'--image',str(path),'-']
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
