"""Local PNG-keyframe motion and faithful GIF ingestion; no AI video provider."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageSequence
from image_common import ImageError,c2pa,digest,write


def validate_motion(size,frames,frame_ms):
    if not 2<=frames<=64 or not 20<=frame_ms<=2000 or any(v%16 for v in size):
        raise ImageError('E_GIF_PARAMS','Frames must be 2..64, frame-ms 20..2000, and dimensions multiples of 16.')
    if frame_ms%10:raise ImageError('E_GIF_PARAMS','GIF timing must be an integer multiple of 10 ms.')


def seam_qa(frames):
    width=min(192,frames[0].width);height=max(1,round(frames[0].height*width/frames[0].width))
    a=np.array([np.array(f.convert('RGBA').resize((width,height),Image.Resampling.BOX)) for f in frames],np.float32)
    rgb=a[...,:3]*a[...,3:4]/255
    values=np.concatenate((rgb,a[...,3:4]),axis=3)
    steps=np.mean(np.abs(np.diff(values,axis=0)),axis=(1,2,3))
    seam=float(np.mean(np.abs(values[-1]-values[0])))
    local=np.r_[steps[:3],steps[-3:]]
    normal=float(np.median(local[local>1e-5])) if np.any(local>1e-5) else 0.
    ratio=seam/max(normal,.01)
    if np.any(a[...,3]==0):
        yy,xx=np.indices(a.shape[1:3]);weights=a[...,3]
        totals=np.maximum(weights.sum(axis=(1,2)),1)
        centers=np.stack(((weights*xx).sum(axis=(1,2))/totals,(weights*yy).sum(axis=(1,2))/totals),axis=1)
        travel=np.linalg.norm(np.diff(centers,axis=0),axis=1)
        if np.max(travel)>.5:ratio=max(ratio,float(np.linalg.norm(centers[-1]-centers[0])/max(np.median(travel[travel>.01]),.01)))
    return dict(status='PASS' if ratio<=3 else 'FAIL',seam_ratio=ratio,seam_difference=seam,
                ordinary_step=normal,seam_frames=[len(frames)-1,0],moving=bool(np.any(steps>.01)),
                note='Pixel continuity proxy; existing qa_media adds position/velocity checks; articulation requires human review.')


def choose_wrap(frames,durations=None):
    """Rotate a complete cycle to a stable moving seam; do not discard any poses."""
    durations=durations or [40]*len(frames)
    width=min(192,frames[0].width);height=max(1,round(frames[0].height*width/frames[0].width))
    rgba=np.array([np.array(f.convert('RGBA').resize((width,height),Image.Resampling.BOX),np.float32) for f in frames])
    thumbs=rgba[...,:3]*rgba[...,3:4]/255
    steps=np.mean(np.abs(thumbs-np.roll(thumbs,1,axis=0)),axis=(1,2,3))
    active=steps[steps>=.01];median=float(np.median(active)) if len(active) else 0.;best=0;score=float('inf')
    for i,seam in enumerate(steps):
        moving=[j%len(steps) for j in range(i+1,i+len(steps)) if steps[j%len(steps)]>=.01]
        if not moving:continue
        incoming,outgoing=moving[-1],moving[0]
        speed_in=steps[incoming]/(durations[(incoming-1)%len(steps)]/1000)
        speed_out=steps[outgoing]/(durations[(outgoing-1)%len(steps)]/1000)
        ratio=(speed_in+.05)/(speed_out+.05)
        if .6<=ratio<=1.67 and seam<=max(.5,1.5*median):
            value=abs(float(np.log((seam+.05)/(median+.05))))+abs(float(np.log(ratio)))
            if value<score:score=value;best=i
    return frames[best:]+frames[:best],best


def deliver(frames,durations,out,manifest,sprites=True,media_qa=True):
    from gif_pipeline import encode,verify
    from sprite_export import export
    out=Path(out)
    if out.exists():raise ImageError('E_OUTPUT','Use a new motion delivery directory.')
    (out/'frames').mkdir(parents=True)
    encode(frames,durations,out/'preview.gif')
    decoded=[];times=[]
    with Image.open(out/'preview.gif') as gif:
        for frame in ImageSequence.Iterator(gif):decoded.append(frame.convert('RGBA'));times.append(frame.info['duration'])
    _,decoded_rotation=choose_wrap(decoded,times)
    rotation=int(np.searchsorted(np.cumsum([0]+durations),sum(times[:decoded_rotation])))
    indices=manifest.get('source_indices',list(range(len(frames))))
    if rotation:
        frames=frames[rotation:]+frames[:rotation];durations=durations[rotation:]+durations[:rotation];indices=indices[rotation:]+indices[:rotation]
        encode(frames,durations,out/'preview.gif')
    for i,frame in enumerate(frames):frame.save(out/'frames'/f'{i:05d}.png')
    manifest=dict(manifest,durations_ms=durations,source_indices=indices,decoded_wrap_rotation_frames=rotation,loop=seam_qa(frames))
    manifest['gif_qc']=verify(out/'preview.gif',frames,durations)
    write(out/'manifest.json',manifest)
    if sprites:
        export(out/'frames',out/'manifest.json',out/'sprites',max_size=max(2048,max(frames[0].size)+4))
    if media_qa:
        from qa_media import qa
        report=qa(out/'preview.gif',out/'qa',loop=True)
        manifest['media_qa_loop']=next(check for check in report['checks'] if check['name']=='loop')
        write(out/'manifest.json',manifest)
        if manifest['media_qa_loop']['level']=='FAIL':
            raise ImageError('E_LOOP_QA','Encoded GIF failed existing position/velocity seam QA; delivery remains a preview.',report=manifest['media_qa_loop'])
    return dict(manifest,output=str(out.resolve()))


def loop_keyframes(paths,out,frames=48,frame_ms=40,size=None,sprites=True,media_qa=True):
    from image_keyframes import fit_image
    if not paths:raise ImageError('E_KEYFRAMES','Supply at least one keyframe.')
    with Image.open(paths[0]) as im:size=size or im.size
    validate_motion(size,frames,frame_ms)
    keys=[]
    for path in paths:
        with Image.open(path) as im:keys.append(np.array(fit_image(im,size,background=(0,0,0,0))[0],np.float32))
    result=[]
    for i in range(frames):
        # Put the wrap in a moving portion, avoiding one-sided finite-difference
        # velocity estimates across a sampled stationary turning point.
        phase=(i/frames+(.25 if len(keys)==1 else .5/len(keys)))%1
        if len(keys)==1:
            # Smooth periodic camera motion, no claim of generated joint paths.
            zoom=1+.045*(1-np.cos(phase*2*np.pi))
            matrix=cv2.getRotationMatrix2D((size[0]/2,size[1]/2),0,zoom)
            rgba=cv2.warpAffine(keys[0],matrix,size,flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
        else:
            position=phase*len(keys);index=int(position);u=position-index;u=(1-np.cos(u*np.pi))/2
            a=keys[index%len(keys)];b=keys[(index+1)%len(keys)]
            alpha=(1-u)*a[...,3:4]+u*b[...,3:4]
            rgb=((1-u)*a[...,:3]*a[...,3:4]+u*b[...,:3]*b[...,3:4])/np.maximum(alpha,1e-9)
            rgba=np.concatenate((rgb,alpha),axis=2)
        result.append(Image.fromarray(np.rint(np.clip(rgba,0,255)).astype('uint8')))
    result,wrap_rotation=choose_wrap(result)
    manifest=dict(fallback='keyframe_loop',method='cyclic_cosine_dissolve' if len(keys)>1 else 'cyclic_camera_zoom',
                  ai_generated=True,ai_video_generated=False,alpha_source='keyframes',
                  derived_from=[dict(sha256=digest(p),**c2pa(p)) for p in paths],
                  discarded_frames=0,wrap_rotation_frames=wrap_rotation,visual_motion_approval='pending',
                  note='Grok/fal AI video is a separate user-approved operation; this local loop does not invent articulated motion.')
    return deliver(result,[frame_ms]*frames,out,manifest,sprites,media_qa)


def ingest_gif(path,out,sprites=True):
    """Pillow applies each disposal rectangle before converting the logical canvas."""
    from sprite_export import export
    out=Path(out)
    if out.exists():raise ImageError('E_OUTPUT','Use a new GIF ingest directory.')
    (out/'frames').mkdir(parents=True)
    durations=[];disposals=[];frames=[]
    with Image.open(path) as gif:
        if gif.format!='GIF':raise ImageError('E_FORMAT','GIF ingest requires a GIF.')
        for i,frame in enumerate(ImageSequence.Iterator(gif)):
            durations.append(int(frame.info.get('duration',0)));disposals.append(getattr(frame,'disposal_method',None))
            rgba=frame.convert('RGBA');frames.append(rgba.copy());rgba.save(out/'frames'/f'{i:05d}.png')
    manifest=dict(feature_used='gif_ingest',durations_ms=durations,disposals=disposals,
                  source_indices=list(range(len(frames))),derived_from=dict(sha256=digest(path),**c2pa(path)),
                  alpha_source='gif_binary' if any(np.any(np.array(f)[...,3]==0) for f in frames) else 'opaque',
                  loop=seam_qa(frames),browser_timing_note='Source delays preserved exactly; preview encoding may merge <=20 ms exposures.')
    write(out/'manifest.json',manifest)
    if sprites and all(t>0 for t in durations):export(out/'frames',out/'manifest.json',out/'sprites',max_size=max(2048,max(frames[0].size)+4))
    return manifest


def repair_loop(paths,durations,out):
    """Cosine-time ping-pong brings endpoints to rest; preserves source poses."""
    if len(paths)<3:raise ImageError('E_LOOP','Loop repair needs at least three frames.')
    frames=[]
    for path in paths:
        with Image.open(path) as im:frames.append(im.convert('RGBA'))
    count=2*len(frames)
    indices=[round((len(frames)-1)*(1-np.cos(2*np.pi*(i/count+.25)))/2) for i in range(count)]
    selected=[frames[i] for i in indices]
    selected,rotation=choose_wrap(selected);indices=indices[rotation:]+indices[:rotation]
    step=max(30,round(float(np.median(durations))/10)*10)
    return deliver(selected,[step]*count,out,dict(fallback='loop_repair',repair='cosine_ping_pong',discarded_frames=0,source_indices=indices))
