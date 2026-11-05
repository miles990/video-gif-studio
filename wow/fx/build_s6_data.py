"""Rebuild additive S6 metadata. Does not touch specs or acceptance documents."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from fx import EFFECTS,TRANSITIONS
from fx_catalog import INTENTS,NEEDS


def save(path,data):
    (ROOT/path).parent.mkdir(parents=True,exist_ok=True)
    (ROOT/path).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def main():
    path=ROOT/'references/thresholds.json'
    registry=json.loads(path.read_text(encoding='utf-8'))
    constants={
      'audio.sfx.codec_headroom':(.2,'U','min','dB'),
      'wcag.general.delta.min':(.10,'F','min','linear L'), 'wcag.general.dark.max':(.80,'F','max','linear L'),
      'wcag.red.saturation.min':(.8,'F','min','R/(R+G+B)'), 'wcag.red.delta.min':(20,'F','min','red contrast x320'),
      'wcag.area.min':(.111,'F','min','fraction'), 'wcag.flashes.max':(3,'F','max','flashes/s'),
      'calibration.monotonic.tolerance':(.01,'F','max','perceived'),
      'calibration.grid.points':(11,'F','equal','samples'),
      'measure.area8.min':(8,'C','min','sRGB Y'), 'perceived.luma.scale':(64,'C','equal','sRGB Y'),
      'perceived.displacement.scale':(24,'C','equal','720p px'),
      'visibility.luma.weight':(.1,'C','equal','weight'),'visibility.noise.floor':(1,'C','min','sRGB Y'),
      'harshness.ssim_loss.max':(.35,'C','max','loss'),'harshness.frames.min':(4,'C','min','frames'),
      'director.energy.low':(.4,'U','max','energy'), 'director.energy.high':(.8,'U','min','energy'),
      'director.budget.base':(.4,'U','equal','perceived/4s'),'director.budget.gain':(5.5,'U','equal','perceived/4s/energy'),
      'director.density.base':(1,'U','equal','events/bar'),'director.density.gain':(4,'U','equal','events/bar/energy'),
      'director.breathe.max':(.25,'U','max','perceived'),'director.flash.run.max':(8,'U','max','events'),
      'query.history.window':(3,'U','equal','choices'),'query.intent.weight':(4,'U','equal','score'),
      'query.related.match':(.5,'U','equal','intent match'),
      'query.gate.weight':(1,'U','equal','score'),'query.cost.weight':(.01,'U','equal','score/ms'),
      'query.diversity.weight':(10,'U','equal','score/occurrence')}
    existing={e['id'] for e in registry['thresholds']}
    for ident,(v,cls,direction,unit) in constants.items():
        if ident in existing:continue
        anchors=[] if cls!='C' else [dict(id=ident+'.'+role,path='references/fx-instrument-anchors.json#'+role,
            role=role,expected=expected,label_source='fixture',held_out=True) for role,expected in [('positive_control','pass'),('negative_control','fail')]]
        registry['thresholds'].append(dict(id=ident,value=v,**{'class':cls},unit=unit,direction=direction,
            measures='S6 '+ident,anchors=anchors,history=[],status='active' if cls!='C' else 'calibrate_first',
            provenance={'source_class':'EXT' if cls=='F' else 'GUESS',
              'ref':('WCAG 2.3.1 / acceptance-6 fixed MEAS' if ident.startswith('wcag.') else 'acceptance-6 S-71 fixed reproducibility contract') if cls=='F' else 'references/fx.md S6 method; independent panel calibration pending',
              'agent_invented':cls!='F'}))
    registry['calibration_tables']={'fx_perceived':'references/fx-calibration.json'}
    save('references/thresholds.json',registry)
    profiles={
      'flash_white':('hit',.9,[],['Emphasize a single impact'],['Dense consecutive beats'],['hit'],['flash_cut','gl_overexposure']),
      'grade':('texture',.0,[],['Unify the colour of a quiet scene'],['Large shifts on skin tones'],['riser'],[]),
      'halation':('reveal',.3,[],['Soften highlights around a reveal'],['Already clipped highlights'],['whoosh'],[]),
      'beat_bounce':('play',.5,[],['Give an isolated beat a playful lift'],['Long readable text'],['pop'],['zoom_punch']),
      'zoom_punch':('hit',.6,[],['Pull attention toward a central impact'],['Subjects cropped at frame edges'],['hit'],['beat_bounce']),
      'cutout_card':('title',.25,['subject','alpha'],['Present a prepared transparent subject card'],['Opaque source without a subject matte'],['pop'],[])}
    groups={
      'transition-match':['crossfade','gl_cross_warp','gl_directional_warp','gl_color_distance','gl_scale_in','gl_crosshatch'],
      'transition-energy':['whip_pan','spin','gl_rotate_scale_fade','gl_wind','gl_glitch_memories','gl_swirl'],
      'breathe':['gl_dreamy','gl_water_drop','gl_fade_grayscale','gl_perlin_dissolve','gl_multiply_blend'],
      'reveal':['gl_clock_wipe','gl_luminance_melt','gl_polka_dots_curtain','gl_window_slices','gl_curved_wipe','gl_arrow_wipe'],
      'conceal':['hex_shutter','gl_bow_tie_horizontal','gl_squares_wipe','gl_random_squares'],
      'drop':['flash_cut','gl_dreamy_zoom','gl_burn_through','gl_overexposure'],
      'play':['gl_bounce','gl_pinwheel','gl_pixelize','gl_dither_dissolve','gl_hexagonalize','gl_color_phase']}
    cards={}
    for kind,reg in [('effect',EFFECTS),('transition',TRANSITIONS)]:
        for name,item in reg.items():
            intent,energy,needs,good,avoid,sfx,conflicts=profiles.get(name,('texture',.4,[],[f'{name.replace("_"," ")} accent on a prepared shot'],['Unreviewed final delivery'],['whoosh'],[]))
            if kind=='transition':
                intent=next((i for i,names in groups.items() if name in names),'transition-energy')
                energy={'breathe':.2,'transition-match':.35,'reveal':.5,'conceal':.55,'play':.65,'transition-energy':.8,'drop':.95}[intent]
                good=[f'{name.replace("_"," ")}: '+{'breathe':'a quiet scene handoff','transition-match':'joining related compositions','reveal':'unveiling the next shot','conceal':'covering a hard scene change','play':'a playful rhythmic chapter change','transition-energy':'carrying momentum across a cut','drop':'marking a major musical drop'}[intent]]
                avoid=['breathe' if energy>.7 else 'Rapid alternating scene changes']
                conflicts=['flash_white'] if name in ('flash_cut','gl_overexposure') else []
            cards[kind+':'+name]=dict(intent=[intent],energy=energy,needs=needs,good_for=good,avoid_for=avoid,
                duration_ms=[80,600] if energy>.7 else [200,2000],pairs_with_sfx=sfx,conflicts=conflicts,
                style_tags=item.get('style_tags') or [intent])
    save('references/fx-cards.json',cards)
    string={'type':'string','minLength':1}
    strings={'type':'array','items':string}
    props={k:strings for k in ['good_for','avoid_for','pairs_with_sfx','conflicts','style_tags']}
    props.update(intent={'type':'array','minItems':1,'items':{'enum':list(INTENTS)}},energy={'type':'number','minimum':0,'maximum':1},
        needs={'type':'array','uniqueItems':True,'items':{'enum':list(NEEDS)}},duration_ms={'type':'array','minItems':2,'maxItems':2,'items':{'type':'number','minimum':0}},
        gate={'type':'object','required':['axis','status','date','record_path'],'properties':{'axis':{'const':'technical'}},'additionalProperties':True},
        preview={'type':'object','required':['video','thumbnail','duration_ms'],'properties':{'video':string,'thumbnail':string},'additionalProperties':True},
        **{'cost_ms_per_frame@720p':{'type':['number','null'],'minimum':0}})
    save('references/fx-card.schema.json',{'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','required':list(props),'properties':props,'additionalProperties':True,
        '$comment':'Additive legacy registry fields are permitted. Duration min<max is checked by validate_card; JSON Schema cannot compare sibling numbers.'})


if __name__=='__main__':main()
