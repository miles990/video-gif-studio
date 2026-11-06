"""Explicit expiring approval before ANY model-video adapter can run.

Bundled Grok/fal routes cannot currently preserve first+last+identity refs
together. An explicit capability-declaring driver can bridge a verified route;
unsupported combinations fail before dispatch, never silently drop inputs.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json
import math
import subprocess
import sys
from image_common import ImageError,digest,key,read,write
from game_character import rgba,originality


def estimate(first,last,refs,route,out,duration=5,prices=None,driver=None,prompt='Original character motion'):
    first,last,out=Path(first),Path(last),Path(out)
    if route not in ('grok','fal'):raise ImageError('E_ROUTE','Video model route must be grok or fal.')
    if not math.isfinite(duration) or not 1<=duration<=15:raise ImageError('E_DURATION','Video duration must be 1..15 seconds.')
    originality(prompt)
    request=dict(first_frame_sha=digest(first),last_frame_sha=digest(last),refs_sent=[digest(p) for p in refs],route=route,duration_seconds=duration,prompt=prompt,
                 driver_sha=digest(driver) if driver else None,prices=prices)
    binding=key(request);receipt=out/'estimates'/(route+'-'+binding+'.json');now=datetime.now(timezone.utc)
    # Honour explicit expiry edits to the legacy latest-estimate receipt, while
    # retaining independent immutable request slots for every route.
    latest=out/'video-estimate.json'
    if latest.exists():
        previous=read(latest)
        if previous.get('request_sha')==binding and datetime.fromisoformat(previous['expires_at'])<=now:
            write(receipt,previous)
    if receipt.exists():
        previous=read(receipt)
        if previous.get('request_sha')==binding and datetime.fromisoformat(previous['expires_at'])>now:return previous
    cost=None
    if prices:
        if prices.get('route')!=route or not prices.get('version'):raise ImageError('E_PRICE_REQUIRED','Reviewed video prices must identify route and version.')
        date=datetime.fromisoformat(prices['date']).replace(tzinfo=timezone.utc)
        age=(now-date).total_seconds()/86400;unit=float(prices['usd_per_second'])
        if not 0<=age<=31 or not math.isfinite(unit) or unit<=0:raise ImageError('E_PRICE_REQUIRED','Video prices must be recent and positive.')
        cost=round(duration*unit,8)
    result=dict(request_sha=binding,request=request,route=route,duration_seconds=duration,cost_estimate_usd=cost,
                cost_status='reviewed' if cost is not None else 'unknown; reviewed price table required before model dispatch',
                created_at=now.isoformat(),expires_at=(now+timedelta(minutes=30)).isoformat(),local_alternatives=['nearest key-pose inbetweens','2.5D camera move','local composition'])
    result['estimate_id']=key(result);write(receipt,result);write(latest,result);return result


def local_video(first,last,out,duration=5,frames=24):
    from game_animation import mesh_between,silhouette_points,previews
    from media_runtime import locate
    a,b=rgba(first),rgba(last)
    if a.size!=b.size:raise ImageError('E_CANVAS','First and last frames must share one canvas.')
    if not 2<=frames<=64 or not 0<duration<=30:raise ImageError('E_TIMING','Local clips support 2..64 frames and 0..30 seconds.')
    out=Path(out);(out/'frames').mkdir(parents=True,exist_ok=True);pa,pb=silhouette_points(a),silhouette_points(b)
    images=[mesh_between(a,b,pa,pb,i/(frames-1)) for i in range(frames)];times=[round(duration*1000/frames/10)*10]*frames
    for i,im in enumerate(images):im.save(out/'frames'/f'{i:05d}.png')
    previews(images,times,out,False)
    ffmpeg=locate('ffmpeg')
    if not ffmpeg:raise ImageError('E_FFMPEG','Local video encoding needs ffmpeg; RGBA/APNG previews retained.')
    # MP4 is explicitly opaque over black. RGBA/APNG masters preserve alpha.
    command=[ffmpeg,'-v','error','-y','-framerate',str(1000/times[0]),'-i',str(out/'frames/%05d.png'),'-filter_complex',
             f'color=c=black:s={a.width}x{a.height}:r={1000/times[0]}[bg];[bg][0:v]overlay=shortest=1:format=auto,pad=ceil(iw/2)*2:ceil(ih/2)*2',
             '-frames:v',str(frames),'-c:v','libx264','-pix_fmt','yuv420p',str(out/'local.mp4')]
    result=subprocess.run(command,capture_output=True,text=True,timeout=120)
    if result.returncode:raise ImageError('E_ENCODE',result.stderr)
    manifest=dict(route='local',network_requests=0,method='nearest_piecewise_affine_preview',first_frame_sha=digest(first),last_frame_sha=digest(last),duration_ms=sum(times),video='local.mp4',video_alpha='opaque black; RGBA and APNG masters retained',review='pending')
    write(out/'gen-manifest.json',manifest);return manifest


def keyframes_video(first,last,refs,route,out,approval=None,duration=5,prices=None,driver=None,prompt='Original character motion'):
    if route=='local':return local_video(first,last,out,duration)
    out=Path(out);refs=[Path(p) for p in refs];prices=read(prices) if isinstance(prices,(Path,str)) else prices
    est=estimate(first,last,refs,route,out,duration,prices,driver,prompt)
    # This check intentionally precedes imports, credential reads, child processes,
    # driver construction, auth inspection and all remote transport.
    if approval!=est['estimate_id'] or datetime.fromisoformat(est['expires_at'])<=datetime.now(timezone.utc):
        raise ImageError('E_APPROVAL_REQUIRED','Model video needs explicit user consent for this exact, unexpired estimate.',estimate=est,
                         suggestion='After explicit consent pass --approve-video '+est['estimate_id']+'. Local inbetweens, 2.5D camera motion and composition need no approval.',network_requests=0)
    if prices is None:raise ImageError('E_PRICE_REQUIRED','Supply reviewed video prices; no cost is guessed.',network_requests=0)
    if driver is None:
        raise ImageError('E_VIDEO_CAPABILITY','Bundled '+route+' adapter cannot send first frame, last frame and identity refs together.',
                         suggestion='Supply a verified --video-driver implementing the documented first+last+refs contract, or use --route local.',network_requests=0)
    job=out/'video-job.json'
    if job.exists():raise ImageError('E_VIDEO_ALREADY_SUBMITTED','A submission receipt exists. Reconcile it; automatic duplicate calls are forbidden.')
    payload=dict(route=route,prompt=prompt,duration_seconds=duration,first_frame=str(Path(first).resolve()),last_frame=str(Path(last).resolve()),reference_images=[str(p.resolve()) for p in refs],estimate_id=approval)
    receipt=dict(status='submitting',estimate=est,first_frame_sha=digest(first),last_frame_sha=digest(last),refs_sent=[digest(p) for p in refs])
    write(job,receipt)
    command=[sys.executable,str(driver)] if str(driver).endswith('.py') else [str(driver)]
    try:
        response=subprocess.run(command,input=json.dumps(payload),text=True,capture_output=True,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if response.returncode:raise ImageError('E_VIDEO_DRIVER','Approved driver failed. Submission remains unresolved; no automatic retry.')
        result=json.loads(response.stdout)
        if result.get('refs_sent')!=receipt['refs_sent'] or result.get('first_frame_sha')!=receipt['first_frame_sha'] or result.get('last_frame_sha')!=receipt['last_frame_sha']:raise ImageError('E_VIDEO_RECEIPT','Driver did not confirm sending every approved input.')
        video=Path(result['video']);receipt.update(status='returned',video=str(video),video_sha=digest(video),network_calls_reported=result.get('network_calls','unreported'))
        write(job,receipt)
        # Decode and assess the returned media locally. A transport receipt alone
        # cannot establish animation or identity acceptance.
        from qa_media import qa
        receipt['media_qa']=qa(video,out/'qa')
        import cv2
        from image_identity import compare
        capture=cv2.VideoCapture(str(video));ok,frame=capture.read();capture.release()
        if not ok:raise ImageError('E_VIDEO_DECODE','Returned video could not be decoded.')
        from PIL import Image
        path=out/'first-decoded.png';Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).save(path)
        receipt['identity']=dict(first=compare(first,path),references=[compare(p,path) for p in refs],status='unassessed',visual_review='pending')
        receipt['status']='preview_pending_identity_and_motion_review';write(out/'gen-manifest.json',receipt);return receipt
    except Exception:
        receipt['status']='submission_unresolved';write(job,receipt);raise
