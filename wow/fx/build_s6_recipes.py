"""Create the initial 14 recipes; independent technical review stays explicit."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def layer(ref,peak,duration=400,offset=0,control='amount',params=None,shape=None):
    return dict(ref=ref,kind='effect',params=params or {},offset_ms=offset,duration_ms=duration,
                control=control,envelope=shape or [[0,peak],[duration,0]])


def main():
    definitions=[
      ('impact','hit',.6,'hit',[layer('zoom_punch',.8),layer('flash_white',.18,160,40)],'shake replaced with stable zoom_punch; flash delayed one frame.'),
      ('reveal_subject','reveal',.35,'whoosh',[layer('cutout_card',1,900,control='mix'),layer('halation',.45,700,100)],'vignette replaced with stable halation; requires prepared transparent subject.'),
      ('breathe','breathe',.2,None,[layer('grade',.06,1600,control='temp',shape=[[0,0],[800,.06],[1600,0]])],'Slow warm grade replaces experimental slow camera movement; no sound to preserve breathing room.'),
      ('build','build',.6,'riser',[layer('halation',.9,2000,shape=[[0,.1],[400,0],[500,.2],[900,0],[1000,.4],[1400,0],[1500,.8],[2000,0]])],'Experimental shake replaced by four increasing stable highlight pulses.'),
      ('drop','drop',.7,'hit',[layer('flash_white',.45,180),layer('zoom_punch',1,350,40)],'radial_blur and shake replaced with stable zoom_punch; flash_cut replaced with flash_white for boundary-free placement.'),
      ('title_pop','title',.4,'pop',[layer('beat_bounce',.55,350),layer('halation',.3,450,80)],'Experimental text replaced by motion of a precomposed title; this recipe does not generate text.'),
      ('freeze_card','reveal',.4,'click',[layer('cutout_card',1,900,control='mix'),layer('halation',.3,600,80)],'Use a freeze source segment with alpha; recipe decorates the frozen subject, not a subject extractor.'),
      ('soft_hit','hit',.3,'pop',[layer('zoom_punch',.35,650),layer('grade',.08,550,80,control='temp')],'Restrained impact for spoken-word accents.'),
      ('bright_hit','hit',.5,'hit',[layer('flash_white',.28,240),layer('halation',.5,450,80)],'White accent followed by stable warm spill.'),
      ('playful_hit','hit',.5,'pop',[layer('beat_bounce',.9,500),layer('grade',.10,400,80,control='temp')],'Playful lift with a separate warmth tail.'),
      ('warm_memory','texture',.2,None,[layer('grade',.14,1600,control='temp',shape=[[0,0],[400,.14],[1200,.14],[1600,0]]),layer('halation',.25,1200,200)],'Quiet colour treatment; no SFX so dialogue remains clear.'),
      ('hero_glow','reveal',.4,'whoosh',[layer('halation',.85,900),layer('zoom_punch',.25,600,100)],'Stable bloom with a restrained camera accent.'),
      ('outro_settle','breathe',.2,None,[layer('grade',.08,1400,control='temp',shape=[[0,.08],[1000,.04],[1400,0]])],'Return warmth to neutral; no SFX for a clean audio tail.'),
      ('hook_snap','hit',.65,'click',[layer('zoom_punch',1,250),layer('flash_white',.32,180,40)],'Short hook accent with independent flash tail.')]
    directory=ROOT/'recipes';directory.mkdir(exist_ok=True)
    for name,intent,target,sfx,layers,note in definitions:
        needs=['subject','alpha'] if name in ('reveal_subject','freeze_card') else ['text'] if name=='title_pop' else []
        r=dict(name=name,status='experimental',intent=intent,layers=layers,sfx=sfx,perceived_target=target,needs=needs,
               good_for=[name.replace('_',' ')+' at a selected key moment'],avoid_for=['breathe'] if target>.4 else ['Repeated full-strength accents'],notes=note,
               peak_ms=1500 if name=='build' else 0,
               gate=dict(axis='technical',status='pending-review',date='2026-11-05',record_path='wow/fx/gate/s6-recipes.json',
                         basis='Stable ingredients; combination awaits measured render checks and independent technical panel. Appeal is user taste.'))
        (directory/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','additionalProperties':False,
      'required':['name','status','intent','layers','sfx','perceived_target','gate','needs','notes'],
      'properties':{'name':{'type':'string','minLength':1},'status':{'enum':['stable','experimental']},'intent':{'type':'string'},
      'layers':{'type':'array','minItems':1,'items':{'type':'object','required':['ref','kind','params','offset_ms','duration_ms','envelope'],
        'properties':{'ref':{'type':'string'},'kind':{'enum':['effect','transition']},'params':{'type':'object'},'offset_ms':{'type':'number','minimum':0},
        'duration_ms':{'type':'number','exclusiveMinimum':0},'control':{'type':'string'},'envelope':{'type':'array','minItems':2,'items':{'type':'array','minItems':2,'maxItems':2,'items':{'type':'number'}}}},'additionalProperties':False}},
      'sfx':{'enum':[None,'hit','whoosh','pop','riser','click','glitch']},'perceived_target':{'type':'number','exclusiveMinimum':0,'maximum':1},
      'gate':{'type':'object'},'needs':{'type':'array','items':{'enum':['subject','alpha','motion','text']}},'notes':{'type':'string','minLength':1},
      'good_for':{'type':'array','items':{'type':'string'}},'avoid_for':{'type':'array','items':{'type':'string'}},'peak_ms':{'type':'number'}}}
    (ROOT/'references/fx-recipe.schema.json').write_text(json.dumps(schema,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
