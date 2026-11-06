"""Reference key poses, nearest mesh inbetweens, and measured contact/phase QA.

No video imports, network, alpha crossfades, per-frame recentering, or mirroring.
Landmarks are explicit author annotations; automatic silhouette landmarks are
only a preview fallback and cannot establish semantic joint correctness.
"""
from dataclasses import replace
from pathlib import Path
import math
import cv2
import numpy as np
from PIL import Image
from image_common import ImageError,digest,read,write
from game_character import rgba,quantize,originality,require_alpha

DEFAULTS={'idle':(8,8,True),'walk':(8,10,True),'run':(8,12,True),'jump':(12,12,False),'attack':(10,12,False),'hurt':(8,10,False),'death':(10,10,False)}
KEY_POSES={
 'idle':['neutral breath halfway rising','inhale shoulders raised a little, feet planted','exhale halfway descending','relaxed lowest breath, feet planted'],
 'walk':['left foot planted, right passing','left foot planted, right stepping forward','right foot planted, left passing','right foot planted, left stepping forward'],
 'run':['left foot weight acceptance, crouched','airborne passing stride, bent knees','right foot weight acceptance, crouched','airborne opposite passing stride'],
 'jump':['standing then crouching preparation','ascending jump tuck','descending jump, legs extending','landing compression then recover'],
 'attack':['anticipation: shift weight back, sword drawn back','swing: hand drives sword toward target','contact: sword tip reaches target at screen right','follow through then recover neutral guard'],
 'hurt':['neutral guard','recoil away from impact, bent knees','weight acceptance recovering','neutral guard restored'],
 'death':['guard before impact','collapse knees lose support','body falling to ground','settled body, hold, no rebound']}


def centers(frames):
    result=[]
    for im in frames:
        a=np.array(im)[...,3].astype(float);y,x=np.indices(a.shape);total=max(1,a.sum())
        result.append([float((a*x).sum()/total),float((a*y).sum()/total)])
    return np.array(result)


def frame_distance(a,b):
    aa=np.array(a).astype(float);bb=np.array(b).astype(float);mask=(aa[...,3]>0)|(bb[...,3]>0)
    aa[...,:3]*=aa[...,3:4]/255;bb[...,:3]*=bb[...,3:4]/255
    return (float(np.abs(aa-bb)[mask].mean()) if mask.any() else 0)+float(np.linalg.norm(centers([a,b])[0]-centers([a,b])[1]))


def foot_position(im,box):
    a=np.array(im)[...,3];x,y,w,h=map(int,box);crop=a[max(0,y):y+h,max(0,x):x+w]
    yy,xx=np.where(crop>127)
    if not len(xx):return None
    bottom=int(yy.max());xs=xx[yy==bottom]
    return [float(xs.min()+max(0,x)),float(bottom+max(0,y))]


def contact_qa(frames,manifest):
    w,h=frames[0].size;ground=manifest.get('ground_line',manifest['pivot'][1]);issues=[];rows=[]
    tolerance=1 if manifest.get('pixel') else h*.005
    root=manifest.get('root_motion',[[0,0] for _ in frames])
    if len(root)!=len(frames):raise ImageError('E_ROOT_MOTION','Root motion needs one sample per frame.')
    for contact in manifest.get('contacts',[]):
        first,last=contact['frames'];foot=contact['foot'];samples=[]
        if first<0 or last>=len(frames) or first>last:raise ImageError('E_CONTACT','Invalid contact interval.')
        boxes=manifest.get('foot_boxes',{}).get(foot)
        box=contact.get('box',[0 if foot=='left' else w//2,int(h*.7),w//2,h-int(h*.7)])
        for i in range(first,last+1):
            pos=foot_position(frames[i],boxes[i] if boxes else box)
            if pos is None:issues.append(dict(kind='missing_foot',frame=i,foot=foot));continue
            samples.append((i,pos[0]+root[i][0],pos[1]+root[i][1]))
            if abs(pos[1]-ground)>1:issues.append(dict(kind='ground_contact',frame=i,foot=foot,delta_px=pos[1]-ground))
        if samples:
            origin=samples[0][1]
            for i,x,y in samples:
                if abs(x-origin)>tolerance:issues.append(dict(kind='foot_slide',frame=i,foot=foot,slide_px=x-origin))
        rows.append(dict(foot=foot,frames=[first,last],samples=samples))
    if abs(manifest['pivot'][1]-ground)>1:issues.append(dict(kind='pivot_ground_mismatch'))
    return dict(status='FAIL' if issues else 'PASS' if rows else 'unassessed',contacts=rows,issues=issues)


def attack_contact(frames,weapon_colors,target):
    x,y,w,h=map(int,target);hits=[]
    palette=np.array([tuple(bytes.fromhex(c.lstrip('#'))) for c in weapon_colors],np.uint8)
    for i,im in enumerate(frames):
        a=np.array(im);region=a[y:y+h,x:x+w]
        mask=(region[...,3]>127)&np.any(np.all(region[...,:3][...,None,:]==palette,axis=-1),axis=-1)
        if mask.any():hits.append(i)
    return hits[0] if hits else None


def motion_qa(frames,manifest):
    if len(frames)<2:raise ImageError('E_FRAMES','At least two motion frames are required.')
    if len({im.size for im in frames})!=1:raise ImageError('E_CANVAS','All frames must share one canvas.')
    if len(manifest.get('frames',[]))!=len(frames):raise ImageError('E_TIMING','Motion metadata must have one duration record per frame.')
    if any(not isinstance(r.get('duration_ms'),(int,float)) or not math.isfinite(r['duration_ms']) or r['duration_ms']<=0 for r in manifest['frames']):raise ImageError('E_TIMING','Frame durations must be finite positive milliseconds.')
    w,h=frames[0].size;state=manifest.get('state','');c=centers(frames);issues=[]
    contact=contact_qa(frames,manifest);issues.extend(contact['issues'])
    alpha=[np.array(im)[...,3] for im in frames]
    heights=[im.getbbox()[3]-im.getbbox()[1] if im.getbbox() else 0 for im in frames]
    ground=manifest.get('ground_line',manifest['pivot'][1]);grounded=[]
    for i,a in enumerate(alpha):
        border=np.concatenate((a[0],a[-1],a[:,0],a[:,-1]))
        if np.mean(border==0)<.999:issues.append(dict(kind='clipping',frame=i))
        ys=np.where(a>127)[0];grounded.append(bool(len(ys) and abs(ys.max()-ground)<=1))
    amplitude=float(np.ptp(c[:,1]));spectrum=np.abs(np.fft.rfft(c[:,1]-c[:,1].mean()));frequency=int(np.argmax(spectrum[1:])+1)
    if state=='idle':
        if c[:,0].std()>.02*w or not .005*h<=amplitude<=.04*h:issues.append(dict(kind='idle_balance',vertical_amplitude_px=amplitude))
    if state=='walk':
        if frequency!=2 or not .015*max(heights)<=amplitude<=.06*max(heights):issues.append(dict(kind='walk_bob',cycles=frequency,amplitude_px=amplitude))
        if not all(grounded):issues.append(dict(kind='walk_airborne',frames=[i for i,v in enumerate(grounded) if not v]))
    if state=='run' and all(grounded):issues.append(dict(kind='run_missing_flight'))
    jump=None
    if state=='jump':
        air=np.where(~np.array(grounded))[0]
        if len(air)<3:issues.append(dict(kind='jump_missing_flight'))
        else:
            y=c[air,1];fit=np.polyfit(air,y,2);pred=np.polyval(fit,air);r2=1-float(((y-pred)**2).sum()/max(1e-9,((y-y.mean())**2).sum()))
            apex=float(-fit[1]/(2*fit[0])) if fit[0] else -1
            preparation=air[0]>=2 and float(c[1:air[0],1].max())>c[0,1]+.25
            landing=any(heights[i]<=heights[0]*.97 for i in range(int(air[-1])+1,len(frames)))
            jump=dict(r_squared=r2,apex_frame=apex,preparation=bool(preparation),landing_compression=bool(landing))
            if r2<.95 or fit[0]<=0 or abs(apex-(air[0]+air[-1])/2)>1:issues.append(dict(kind='jump_arc',**jump))
            if not preparation:issues.append(dict(kind='jump_missing_preparation'))
            if not landing:issues.append(dict(kind='jump_missing_compression'))
    steps=[frame_distance(a,b) for a,b in zip(frames,frames[1:])];median=float(np.median(steps));seam=frame_distance(frames[-1],frames[0]);ratio=seam/max(median,1e-9)
    seam_report=None
    if manifest.get('loop'):
        from image_motion import seam_qa
        seam_report=seam_qa(frames,[r['duration_ms'] for r in manifest['frames']])
        if not .3<=ratio<=1.5:issues.append(dict(kind='loop_seam',ratio=ratio,frames=[len(frames)-1,0]))
        if seam_report['status']!='PASS':issues.append(dict(kind='loop_velocity_or_color',details=seam_report))
    elif state in ('jump','attack','hurt','death') and manifest.get('loop') is not False:
        issues.append(dict(kind='nonloop_state'))
    if state=='death' and frames[-1].tobytes()!=frames[-2].tobytes():issues.append(dict(kind='death_missing_terminal_hold'))
    if state=='hurt' and manifest.get('idle_first'):
        if frame_distance(frames[-1],rgba(manifest['idle_first']))>1.5*max(median,1e-6):issues.append(dict(kind='hurt_idle_transition'))
    if state=='attack':
        phases=[f.get('phase') for f in manifest['frames']];order=['anticipation','swing','contact','follow_through','recovery']
        compressed=[v for i,v in enumerate(phases) if i==0 or v!=phases[i-1]]
        if compressed!=order:issues.append(dict(kind='attack_phase_order',observed=compressed))
        if manifest.get('weapon_colors') and manifest.get('target_box'):
            hit=attack_contact(frames,manifest['weapon_colors'],manifest['target_box'])
            events=[e['frame'] for e in manifest.get('events',[]) if e['name']=='hit']
            if hit is None or events!=[hit]:issues.append(dict(kind='attack_contact_event',measured_frame=hit,events=events))
        else:issues.append(dict(kind='attack_contact_unassessed'))
    for i,record in enumerate(manifest['frames']):
        if record.get('source')=='inbetween' and record.get('adjacent_key_frames'):
            a,b=record['adjacent_key_frames'];limit=(np.count_nonzero(alpha[a])+np.count_nonzero(alpha[b]))/2*1.15
            if np.count_nonzero(alpha[i])>limit:issues.append(dict(kind='double_silhouette',frame=i))
    missing_contact=state in ('idle','walk','run','attack','hurt') and contact['status']=='unassessed'
    return dict(status='FAIL' if issues else 'unassessed' if missing_contact else 'PASS',issues=issues,unassessed=['semantic foot contact intervals'] if missing_contact else [],contacts=contact,grounded=grounded,vertical_amplitude_px=amplitude,bob_cycles=frequency,jump=jump,
                seam_ratio=ratio,seam=seam_report,centers=c.tolist(),visual_review='pending')


def silhouette_points(im):
    """Preview fallback only. Explicit guides are needed to assess joint motion."""
    a=np.array(im)[...,3];box=im.getbbox()
    if not box:raise ImageError('E_POSE_EMPTY','Empty key pose.')
    x0,y0,x1,y1=box;points=[]
    for t in (.05,.25,.5,.7,.9):
        y=min(im.height-1,round(y0+(y1-y0-1)*t));xs=np.where(a[y]>127)[0]
        lo,hi=(int(xs.min()),int(xs.max())) if len(xs) else (x0,x1-1)
        points.extend([[lo,y],[(lo+hi)/2,y],[hi,y]])
    return points


def mesh_between(a,b,points_a,points_b,t):
    """Piecewise affine integer pixel displacement from the nearer key; no blend."""
    if a.size!=b.size or len(points_a)!=len(points_b):raise ImageError('E_POSE_GUIDES','Corresponding pose guides and canvas sizes must match.')
    if not 0<=t<=1:raise ImageError('E_POSE_TIME','Interpolation must be in [0,1].')
    if t==0:return a.copy()
    if t==1:return b.copy()
    w,h=a.size;corners=[[0,0],[w-1,0],[w-1,h-1],[0,h-1]]
    pa=np.array([*corners,*points_a],np.float32);pb=np.array([*corners,*points_b],np.float32);dest=(1-t)*pa+t*pb
    if not np.isfinite(dest).all() or (dest[:,0]<0).any() or (dest[:,0]>=w).any() or (dest[:,1]<0).any() or (dest[:,1]>=h).any():raise ImageError('E_POSE_GUIDES','Pose guides must lie inside the shared canvas.')
    # Delaunay topology is fixed at the midpoint for either direction.
    middle=(pa+pb)/2;sub=cv2.Subdiv2D((0,0,w,h))
    for p in middle:sub.insert(tuple(map(float,p)))
    src=pa if t<.5 else pb;image=np.array(a if t<.5 else b)
    # Build ONE inverse sampling field. Independently warping/pasting triangle
    # images can erase neighboring opaque pixels along rounded raster edges.
    yy,xx=np.indices((h,w),dtype=np.float32);map_x=xx.copy();map_y=yy.copy()
    for tri in sub.getTriangleList().reshape(-1,3,2):
        indices=[int(np.argmin(np.linalg.norm(middle-p,axis=1))) for p in tri]
        if any(np.linalg.norm(middle[i]-p)>.1 for i,p in zip(indices,tri)):continue
        st,dt=src[indices],dest[indices]
        if abs(cv2.contourArea(dt))<.1:continue
        matrix=cv2.getAffineTransform(dt,st)
        mask=np.zeros((h,w),np.uint8);cv2.fillConvexPoly(mask,np.rint(dt).astype(np.int32),1)
        inside=mask>0
        map_x[inside]=(matrix[0,0]*xx+matrix[0,1]*yy+matrix[0,2])[inside]
        map_y[inside]=(matrix[1,0]*xx+matrix[1,1]*yy+matrix[1,2])[inside]
    result=cv2.remap(image,map_x,map_y,cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT)
    result[result[...,3]==0]=0
    return Image.fromarray(result)


def layered_between(a,b,points_a,points_b,t,parts,left_index,right_index):
    """Occlusion-aware authored parts with width-preserving nearest bone warps.

    Crossing legs cannot share one continuous 2D mesh. Explicit polygons keep
    their volume, and each part is sampled once without transparent crossfades.
    """
    aa=np.array(a);bb=np.array(b);layers=[];w,h=a.size
    for part in parts:
        ka,kb=part['keys'][left_index],part['keys'][right_index]
        masks=[]
        for record in (ka,kb):
            mask=np.zeros((h,w),np.uint8);cv2.fillPoly(mask,[np.array(record['polygon'],np.int32)],1);masks.append(mask>0)
        source=a if t<.5 else b;spec=ka if t<.5 else kb;mask=masks[0] if t<.5 else masks[1]
        patch=np.array(source).copy();patch[~mask]=0;aa[masks[0]]=0;bb[masks[1]]=0
        sa,sb=np.array(spec['axis'],float);ta=(1-t)*np.array(ka['axis'][0])+t*np.array(kb['axis'][0]);tb=(1-t)*np.array(ka['axis'][1])+t*np.array(kb['axis'][1])
        sv=sb-sa;tv=tb-ta;sl=np.linalg.norm(sv);tl=np.linalg.norm(tv)
        if min(sl,tl)<1:raise ImageError('E_POSE_PART','Part axes must have nonzero length.')
        # Longitudinal length follows the authored poses; perpendicular width is
        # retained, avoiding the needle-like leg produced by a folded body mesh.
        source_basis=np.column_stack((sv/sl,[-sv[1]/sl,sv[0]/sl]));target_basis=np.column_stack((tv/sl,[-tv[1]/tl,tv[0]/tl]));linear=target_basis@source_basis.T
        matrix=np.column_stack((linear,ta-linear@sa)).astype(np.float32)
        warped=cv2.warpAffine(patch,matrix,(w,h),flags=cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT);layers.append(Image.fromarray(warped))
    result=mesh_between(Image.fromarray(aa),Image.fromarray(bb),points_a,points_b,t)
    for layer in layers:result.alpha_composite(layer)
    return result


def previews(frames,durations,out,loop):
    from gif_pipeline import encode,verify,contact
    out=Path(out);encode(frames,durations,out/'preview.gif')
    # gif_pipeline defaults to loop forever; one-shot derivatives omit loop.
    if not loop:
        # Remove only the loop application extension. Re-encoding decoded GIF
        # frames would lose durations when transparent frames were coalesced.
        file=out/'preview.gif';raw=file.read_bytes()
        file.write_bytes(raw.replace(b'!\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00',b'',1))
    qc=verify(out/'preview.gif',frames,durations)
    frames[0].save(out/'preview.png',save_all=True,append_images=frames[1:],duration=durations,loop=0 if loop else 1,disposal=0,blend=0)
    scale=max(1,min(4,192//max(frames[0].size)))
    contact([im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST) for im in frames],out/'contact.png');return qc


def animate(adapter,request,charsheet,out,states=('idle','run','attack','hurt'),plan=None,fps=None):
    charsheet=Path(charsheet);contract=read(charsheet);out=Path(out);originality(request.prompt or 'original character')
    plan=read(plan) if isinstance(plan,(str,Path)) else (plan or {});fps=fps or {};size=tuple(contract['canvas']);palette=read(charsheet.parent/contract['palette'])
    refs=[str((charsheet.parent/v['file']).resolve()) for v in contract['views'] if v['name'] in ('front','three_quarter')]
    all_results={};generations=[]
    for state in states:
        if state not in DEFAULTS:raise ImageError('E_STATE','Unknown animation state: '+state)
        count,rate,loop=DEFAULTS[state];spec=plan.get(state,{})
        count=int(spec.get('frame_count',count));rate=float(fps.get(state,spec.get('fps',rate)))
        if count<4 or count>64 or not math.isfinite(rate) or rate<=0:raise ImageError('E_TIMING','Invalid frame count/fps.')
        indices=spec.get('key_indices',[0,count//4,count//2,3*count//4] if loop else [0,count//3,2*count//3,count-1])
        if not 2<=len(indices)<=4 or indices!=sorted(set(indices)) or indices[0]!=0 or indices[-1]>=count:raise ImageError('E_KEYS','Supply 2..4 ordered key indices starting at zero.')
        keys=[];key_records=[];folder=out/state;(folder/'keys').mkdir(parents=True,exist_ok=True)
        for j,index in enumerate(indices):
            supplied=spec.get('keys',[])
            key=supplied[j] if supplied else {}
            if key.get('image'):
                source=Path(key['image']);generation=None;sent=key.get('refs_sent',[])
            else:
                description=key.get('prompt',KEY_POSES[state][min(j,3)])
                req=replace(request,refs=refs,prompt=f'{request.prompt or "Same original reference character"}. State {state}: {description}. ONE full-body key pose. Use front reference for identity and three-quarter reference for orientation. Same fixed camera, scale and {size[0]}x{size[1]} canvas, ground line y={contract["pivot"][1]}. Preserve all accessories and handedness. No text, no ghosting, transparent.',transparent=True,n=1)
                generation=adapter.generate(req,folder/'generation'/str(j));source=Path(generation['assets'][0]['path']);sent=[digest(p) for p in refs];generations.append(generation)
            im=rgba(source);require_alpha(im);im=im.resize(size,Image.Resampling.NEAREST)
            if contract.get('pixel'):im=quantize(im,palette)
            im.save(folder/'keys'/f'{j:02d}.png');keys.append(im)
            from image_identity import compare
            metrics=[compare(folder/'keys'/f'{j:02d}.png',ref) for ref in refs]
            key_records.append(dict(frame=index,file=f'keys/{j:02d}.png',refs_sent=sent,source_sha=digest(source),points=key.get('points') or silhouette_points(im),guide_source='annotated' if key.get('points') else 'silhouette_preview',
                identity=dict(status='pass' if metrics and all(m['bhattacharyya']<=.35 and m['orb_good_matches']>=25 for m in metrics) and contract.get('identity',{}).get('controls_valid') else 'unassessed',measurements=metrics)))
        frames=[];records=[];durations=spec.get('durations_ms',[round(1000/rate/10)*10]*count)
        if len(durations)!=count or any(not isinstance(v,(float,int)) or not math.isfinite(v) or v<20 for v in durations):raise ImageError('E_TIMING','Supply one finite duration >=20 ms per frame.')
        phases=spec.get('phases',[])
        for i in range(count):
            if i in indices:
                j=indices.index(i);im=keys[j].copy();record=dict(source='key',key_index=j)
            else:
                left=max(j for j,k in enumerate(indices) if k<i);right=(left+1)%len(keys)
                end=indices[right] if right else count;t=(i-indices[left])/(end-indices[left])
                if not loop and right==0:im=keys[left].copy()
                elif spec.get('rigid_parts'):im=layered_between(keys[left],keys[right],key_records[left]['points'],key_records[right]['points'],t,spec['rigid_parts'],left,right)
                else:im=mesh_between(keys[left],keys[right],key_records[left]['points'],key_records[right]['points'],t)
                record=dict(source='inbetween',key_index=left,next_key_index=right,method='nearest_piecewise_affine_pixel_displacement',adjacent_key_frames=[indices[left],indices[right]])
                if spec.get('rigid_parts'):record['method']='nearest_layered_pose_displacement'
                if spec.get('cleanup_inbetween_components'):
                    # Explicitly reviewed sprite-only cleanup, never VFX. These
                    # components are introduced by resampling, not source edits.
                    a=np.array(im);n,labels,stats,_=cv2.connectedComponentsWithStats((a[...,3]>0).astype('uint8'),8);removed=[]
                    for label in range(1,n):
                        if stats[label,cv2.CC_STAT_AREA]<=2:
                            yy,xx=np.where(labels==label);removed.extend([[int(x),int(y)] for x,y in zip(xx,yy)]);a[labels==label]=0
                    im=Image.fromarray(a);record['reviewed_resampling_specks_removed']=removed
            frames.append(im);records.append(dict(index=i,file=f'frames/{i:05d}.png',duration_ms=durations[i],phase=phases[i] if phases else None,**record))
        manifest={**spec,'version':1,'state':state,'fps':rate,'loop':loop,'frames':records,'keys':key_records,'canvas':list(size),'pivot':contract['pivot'],'ground_line':spec.get('ground_line',contract['pivot'][1]),
                  'contacts':spec.get('contacts',[]),'events':spec.get('events',[]),'alpha_mode':'straight','pixel':contract.get('pixel',False),'pixel_scale':1,'fallback':'pixel_quantize' if contract.get('pixel') else 'mesh_inbetween',
                  'root_motion_mode':'separate' if spec.get('root_motion') else 'visual_displacement','mirror_used':False,'review':'pending'}
        for event in manifest['events']:
            if not 0<=event['frame']<count:raise ImageError('E_EVENT','Event frame is out of range.')
            event['time_ms']=sum(durations[:event['frame']])
        (folder/'frames').mkdir(exist_ok=True)
        for i,im in enumerate(frames):im.save(folder/'frames'/f'{i:05d}.png')
        manifest['qa']=motion_qa(frames,manifest);manifest['gif_qc']=previews(frames,durations,folder,loop)
        write(folder/'anim.json',manifest);all_results[state]=manifest
    if 'hurt' in all_results and 'idle' in all_results:
        hurt=all_results['hurt'];images=[rgba(out/'hurt'/r['file']) for r in hurt['frames']]
        median=float(np.median([frame_distance(a,b) for a,b in zip(images,images[1:])]))
        distance=frame_distance(images[-1],rgba(out/'idle'/all_results['idle']['frames'][0]['file']))
        hurt['qa']['idle_return']=dict(distance=distance,maximum=1.5*median,status='PASS' if distance<=1.5*median else 'FAIL')
        if distance>1.5*median:hurt['qa']['issues'].append(dict(kind='hurt_idle_transition'));hurt['qa']['status']='FAIL'
        write(out/'hurt/anim.json',hurt)
    if 'run' in all_results and 'walk' in all_results:
        run=all_results['run'];run_amp=run['qa']['vertical_amplitude_px'];walk_amp=all_results['walk']['qa']['vertical_amplitude_px']
        if run_amp<walk_amp:
            run['qa']['issues'].append(dict(kind='run_bob_less_than_walk',run=run_amp,walk=walk_amp));run['qa']['status']='FAIL';write(out/'run/anim.json',run)
    write(out/'gen-manifest.json',dict(status='experimental',originality=contract.get('originality'),states=list(all_results),generations=generations,review='pending'))
    return dict(states={name:dict(path=str(out/name/'anim.json'),qa=m['qa']) for name,m in all_results.items()},status='experimental')
