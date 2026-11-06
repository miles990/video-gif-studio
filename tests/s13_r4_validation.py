"""Fixed-policy four-set validation and exact native 72-hole judge handoff.

Fake-oracle scores validate wiring, NOT semantic judge accuracy. No generation.
"""
import sys,json,argparse
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from image_common import write,digest

TINROOT='Tinroot, an original small gardening robot: rounded teal-green metal dome head with one large round amber eye lens, a thin rusty-orange antenna topped by a single green leaf sprout, barrel-shaped copper-brown riveted body, patches of fuzzy green moss on both shoulders, thin jointed grey arms with clamp hands, short dark-grey tank-tread feet.'
BRAMBLE='Bramble, an original hedgehog courier: chestnut-brown spines, cream face and belly, sky-blue flat cap, mustard-yellow knitted scarf, red leather mailbag, small brown boots.'
DESCRIPTIONS={
 'spHose':TINROOT+' Holding up a big coiled garden hose wreath in both hands, the coil forms a large ring whose centre is empty, you can see straight through it.',
 'spHipsClean':TINROOT+' Standing proudly with both clamp hands on its hips, elbows bent outward so there is clear empty space between each arm and the body.',
 'iconClean':'Game inventory icon of a chunky tin watering can with a large curved top handle; the space inside the handle loop is empty and see-through.',
 'r3_spRing':BRAMBLE+' Holding a large golden hoop ring up beside him with one hand; the hoop is big and its centre is empty, you can see straight through it.',
 'r3_spLegs':BRAMBLE+' Jumping star pose: legs spread wide apart and arms stretched out, clear empty space between the legs and between arms and body.',
 'r3_icon':'Game inventory icon of a chunky bronze padlock with a tall rounded shackle; the space inside the shackle loop is empty and see-through. Bold outline, painted 2D game art. True transparent background (alpha), no checkerboard, no shadow, no text.',
 'r2_akimbo':'A character standing akimbo with empty background between bent arms and body.'}


def identity(private=None):
 from s13_r3_identity_evidence import SETS
 from identity_engine import compare,verdict,LIMITS,capability
 sets=SETS+[('r4','live-s13-r4',['refFront','refSide','refBack','refAction'],['impRecolor','impPalette','impSilhouette','impTwin'])]
 rows=[]
 for name,folder,refs,negs in sets:
  p=ROOT/'tests/fixtures'/folder
  if private:p=private/'reviews'/('review-s13' if name=='r1' else 'review-s13-'+name)/'work/live'
  for n in refs+negs:
   scores=[compare(p/n/'image-1.png',p/r/'image-1.png') for r in refs if n!=r]
   aggregate={axis:max(s[axis] for s in scores) for axis in ('structure','colour')}
   rows.append(dict(set=name,name=n,label='same' if n in refs else 'different',**aggregate,status=verdict(aggregate)))
 folds=[]
 for held in ('r1','r2','r3','r4'):
  train=[r for r in rows if r['set']!=held];test=[r for r in rows if r['set']==held]
  folds.append(dict(held_out=held,validated_on=sorted({r['set'] for r in train}),limits=LIMITS,
   policy='Frozen r3 thresholds; colour-only hard rejection; both axes required for pass. No fit on held-out set.',
   training_false_pass=sum(r['label']=='different' and r['status']=='pass' for r in train),
   training_false_reject=sum(r['label']=='same' and r['status']=='identity_fail' for r in train),results=test))
 return dict(capability=capability(),rows=rows,leave_one_set_out=folds,
  false_pass=sum(r['label']=='different' and r['status']=='pass' for r in rows),false_reject=sum(r['label']=='same' and r['status']=='identity_fail' for r in rows),
  caveat='Reviewed sets, fixed-policy leave-one-set-out validation; not a fresh blind benchmark.')


def alpha(out,private):
 from image_alpha import alpha_qa,clear_haze,enclosed_regions,cleanup
 base=private/'reviews/review-s13-r4/work';holes=base/'off/holes';rows=[];controls=[]
 def run(path,tag,name,mask=None):
  with Image.open(path) as im:im=im.convert('RGBA')
  a,_=clear_haze(np.array(im));labels,regions=enclosed_regions(a[...,3]);injected=mask if mask is not None else np.zeros(labels.shape,bool)
  def oracle(_path,numbered):
   return {'regions':[dict(id=r['id'],classification='body_hole' if np.any(injected&(labels==r['label'])) else 'intended_gap',reason='Known injection mask / labelled designed control; FAKE oracle, not semantic inference') for r in numbered]}
  result=alpha_qa(im,judge=oracle,overlay_path=out/name/'full.png',description=DESCRIPTIONS[tag])
  found=[r for r in result['hole_review'].get('answers',[]) if np.any(injected&(labels==r['id']))]
  return dict(name=name,source=str(path),source_sha256=digest(path),tag=tag,mask_pixels=int(injected.sum()),
   status=result['status'],regions=len(regions),injected_region_detected=any(r['classification']=='body_hole' for r in found),
   designed_regions=sum(not np.any(injected&(labels==r['label'])) for r in regions),
   designed_false_alarm=sum(r['classification']=='body_hole' and not np.any(injected&(labels==r['id'])) for r in result['hole_review'].get('answers',[])),
   inputs=result['hole_review'].get('inputs',[]))
 for mask_path in sorted(holes.glob('*.mask.npy')):
  name=mask_path.name.removesuffix('.mask.npy');tag=next(t for t in DESCRIPTIONS if name.startswith(t+'_'))
  rows.append(run(holes/(name+'.png'),tag,name,np.load(mask_path)))
 if len(rows)!=72:raise RuntimeError(f'Expected 72 reviewer holes, found {len(rows)}')
 for tag in ('spHose','spHipsClean','iconClean','r3_spRing','r3_spLegs','r3_icon'):
  controls.append(run(base/'live'/tag/'asset.png',tag,tag+'-designed'))
 # r2 akimbo fixture has the reviewed transparent arm gaps.
 path=ROOT/'tests/fixtures/live-s13-r2/sprite2/native/image-1.png'
 with Image.open(path) as im:clean,_=cleanup(im)
 clean_path=out/'r2-akimbo.png';clean.save(clean_path)
 controls.append(run(clean_path,'r2_akimbo','r2-akimbo-designed'))
 return dict(injections=rows,designed_controls=controls,
  fake_oracle=dict(recall=sum(r['injected_region_detected'] for r in rows)/len(rows),false_pass=sum(r['status']=='PASS' for r in rows),designed_gap_false_alarm=sum(r['designed_false_alarm'] for r in rows+controls)),
  semantic_recall=None,semantic_false_pass=None,semantic_designed_gap_false_alarm=None,
  judge_status='Not run live in builder sandbox. Exact two-call inputs saved for coordinator.',
  warning='Oracle labels test exposure, ID remapping and gates only; these numbers are NOT live AI accuracy.')


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('section',choices=['identity','alpha']);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--private',type=Path)
 args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
 result=identity(args.private) if args.section=='identity' else alpha(args.out,args.private)
 write(args.out/(args.section+'.json'),result);print(args.section,'saved',args.out)
