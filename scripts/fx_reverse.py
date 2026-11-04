#!/usr/bin/env python3
"""Clean-room edit analysis, inspired only by rea-video's concept; no source reused.

Heuristics describe visible structure, never ownership, identity or generation origin.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageSequence
from qa_media import media_info, frames as media_frames


def groups(indices, gap=1):
    result = []
    for i in indices:
        if result and i-result[-1][-1]<=gap: result[-1].append(i)
        else: result.append([i])
    return result


def inspect_frames(images, times_ms, duration_ms, beats_ms=()):
    """Bounded thumbnails; median chroma rejects subject motion and brightness accents."""
    rgb = np.asarray([np.asarray(im.convert('RGB').resize((160,90)),np.float32) for im in images])
    n = len(rgb); times = np.asarray(times_ms); step = float(np.median(np.diff(times))) if n>1 else 40.
    dominant = np.median(rgb,axis=(1,2)); chroma = dominant/(dominant.sum(axis=1,keepdims=True)+1e-6)
    gray = rgb @ np.array([.2126,.7152,.0722],np.float32)
    mean = gray.mean(axis=(1,2)); diff = np.r_[0,np.abs(np.diff(rgb,axis=0)).mean(axis=(1,2,3))]
    change = np.r_[0,np.linalg.norm(np.diff(chroma,axis=0),axis=1)]
    flash_idx = [int(g[np.argmax(mean[g])]) for g in groups(np.flatnonzero(mean>190))
                 if max(mean[g])-min(mean[max(0,g[0]-5):min(n,g[-1]+6)])>40]
    flashes = [{'time_ms':float(times[i]),'confidence':.9} for i in flash_idx]
    # Flat dark centers bracket an aperture closure. Require visible brighter neighbors.
    shutters = []
    for g in groups(np.flatnonzero(mean<30)):
        a,b = g[0],g[-1]; lo=max(0,a-round(300/step)); hi=min(n-1,b+round(300/step))
        if a>0 and b<n-1 and max(mean[lo:a],default=0)>45 and max(mean[b+1:hi+1],default=0)>45:
            lowest = [i for i in g if mean[i]<=min(mean[g])+1]
            center = round((lowest[0]+lowest[-1])/2); shutters.append(center)
    # Changes in median chromaticity distinguish shot edits from flashes and zooms.
    candidate = groups(np.flatnonzero(change>.045),max(1,round(160/step)))
    cuts = []; motions = []; occupied = set()
    for center in shutters:
        cuts.append({'time_ms':float(times[center]),'type':'hex_shutter','confidence':.75,'duration_ms':400,'review':True})
        occupied.update(range(max(0,center-round(300/step)),min(n,center+round(300/step)+1)))
    # A white frame erases chroma. Compare clean spatial structure on both sides,
    # including same-palette shots which a median-colour detector cannot separate.
    for center in flash_idx:
        radius=max(2,round(240/step));lo=max(0,center-radius);hi=min(n-1,center+radius)
        left=rgb[lo]/max(1,float(mean[lo]));right=rgb[hi]/max(1,float(mean[hi]))
        # A panning shot can move far across a flash without changing shots.
        # Consistent forward/backward features veto that false positive.
        prev,cur=gray[lo].astype(np.uint8),gray[hi].astype(np.uint8)
        points=cv2.goodFeaturesToTrack(prev,120,.01,4);continuous=False
        if points is not None and len(points)>=8:
            moved,ok,_=cv2.calcOpticalFlowPyrLK(prev,cur,points,None)
            back,back_ok,_=cv2.calcOpticalFlowPyrLK(cur,prev,moved,None)
            good=(ok.ravel()>0)&(back_ok.ravel()>0)&(np.linalg.norm((back-points).reshape(-1,2),axis=1)<1)
            if good.sum()>=8:
                _,inliers=cv2.estimateAffinePartial2D(points[good],moved[good])
                continuous=inliers is not None and good.sum()>.45*len(points) and inliers.sum()>.3*len(points)
        if not continuous and np.abs(left-right).mean()>.45 and np.abs(rgb[lo]-rgb[hi]).mean()>20:
            cuts.append({'time_ms':float(times[center]),'type':'flash_cut','confidence':.75,'duration_ms':160,'review':True})
            occupied.update(range(lo,hi+1))
    # Whips lose horizontal detail over a bounded window, while the two clean
    # shots need not have different dominant colours. Exclude shutter/flash windows.
    sharp=np.abs(np.diff(gray,n=2,axis=2)).mean(axis=(1,2))
    radius=max(3,round(320/step));blurred=[]
    for i in range(1,n-1):
        baseline=min(max(sharp[max(0,i-radius):i],default=0),max(sharp[i+1:min(n,i+radius+1)],default=0))
        near_flash=any(abs(times[i]-times[f])<=240 for f in flash_idx)
        if i not in occupied and not near_flash and baseline>1 and sharp[i]<baseline*.5 and diff[i]>8 and mean[i]>35:
            blurred.append(i)
    for g in groups(blurred):
        if len(g)<2 or len(g)*step>600:continue
        center=int(g[np.argmin(sharp[g])]);position=float(center)
        if 0<center<n-1:
            denominator=sharp[center-1]-2*sharp[center]+sharp[center+1]
            if denominator>1e-6:
                position+=float(np.clip(.5*(sharp[center-1]-sharp[center+1])/denominator,-.5,.5))
        at=round(float(np.interp(position,np.arange(n),times))/10)*10
        length=round((len(g)+2)*step/10)*10
        cuts.append({'time_ms':at,'type':'whip_pan','confidence':.65,'duration_ms':length,'review':True})
        motions.append({'time_ms':at,'direction':'horizontal','confidence':.65,'review':True})
        occupied.update(range(max(0,g[0]-2),min(n,g[-1]+3)))
    # A long dissolve has small *per-frame* deltas but large cumulative change.
    # Require a coherent path between endpoints rather than two threshold crossings.
    for g in groups(np.flatnonzero(change>.0015)):
        a,b=g[0],g[-1];before=max(0,a-1)
        if (b-a+1)*step<400 or any(i in occupied for i in g): continue
        path=chroma[before:b+1];delta=path[-1]-path[0];distance=float(np.linalg.norm(delta))
        travel=float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum())
        if distance<.12 or distance/max(travel,1e-8)<.92: continue
        center=round((before+b)/2)
        cuts.append({'time_ms':float(times[center]),'type':'crossfade','confidence':.7,
                     'duration_ms':float(times[b]-times[before]),'review':True})
        occupied.update(range(a,b+1))
    for g in candidate:
        if any(i in occupied for i in g): continue
        a,b = g[0],g[-1]; before=max(0,a-1); after=min(n-1,b+1)
        if np.linalg.norm(chroma[before]-chroma[after])<.12: continue
        center = int(g[np.argmax(change[g])]); kind='cut'; confidence=.85
        nearby = [i for i in flash_idx if abs(times[i]-times[center])<=240]
        if nearby:
            center = nearby[0]; kind='flash_cut'; confidence=.8
        elif b-a>=2:
            center = round((a+b)/2); kind='crossfade'; confidence=.6
        else:
            sharp = np.abs(np.diff(gray,n=2,axis=2)).mean(axis=(1,2))
            left_base = sharp[max(0,center-6)]; right_base = sharp[min(n-1,center+6)]
            left_blur = left_base>.1 and sharp[max(0,center-1)]<left_base*.5
            right_blur = right_base>.1 and sharp[center]<right_base*.5
            if left_blur or right_blur:
                kind='whip_pan'; confidence=.6
                motions.append({'time_ms':float(times[center]),'direction':'horizontal','confidence':.6,'review':True})
        cuts.append({'time_ms':float(times[center]),'type':kind,'confidence':confidence,'duration_ms':max(80,float(times[b]-times[a]+step*2)) if kind!='cut' else 0,'review':confidence<.8})
    cuts.sort(key=lambda c:c['time_ms'])
    # Runs of identical visible pixels, including their initial exposure.
    freezes = []
    for g in groups(np.flatnonzero(diff[1:]<.3)+1):
        a,b=g[0]-1,g[-1]+1
        end=float(times[b]) if b<n else duration_ms
        if end-times[a]>=700:
            nearby = [c['time_ms'] for c in cuts if 0<=c['time_ms']-end<=300 and c['type']!='cut']
            if nearby: end=min(nearby)
            freezes.append({'start_ms':float(times[a]),'end_ms':end,'confidence':.9})
    # A freeze with a beat-animated cutout retains its plate and repeatedly returns
    # to the same foreground pose. Label this weaker inference for human review.
    border=np.ones((90,160),bool);border[15:75,30:130]=False
    plate_diff=np.r_[0,np.abs(np.diff(rgb,axis=0))[:,border].mean(axis=(1,2))]
    for g in groups(np.flatnonzero(plate_diff[1:]<.3)+1,max(1,round(80/step))):
        a,b=g[0]-1,g[-1]+1
        if (b-a)*step<1000 or np.percentile(diff[a:b],90)<3:continue
        repeat=[]
        for i in range(a+round(800/step),b):
            repeat.append(min(np.abs(rgb[i]-rgb[j]).mean() for j in range(i-round(800/step),i-max(1,round(200/step))))<.6)
        if not repeat or np.mean(repeat)<.3:continue
        start=float(times[a]);end=float(times[b]) if b<n else duration_ms
        before=[c['time_ms'] for c in cuts if 0<=start-c['time_ms']<=400]
        after=[c['time_ms'] for c in cuts if 0<=c['time_ms']-end<=400]
        if before:start=max(before)
        if after:end=min(after)
        if not any(f['start_ms']<=start and f['end_ms']>=end for f in freezes):
            freezes.append({'start_ms':start,'end_ms':end,'confidence':.65,'kind':'animated_cutout_on_held_plate','review':True})
    zooms = []
    for i in range(1,n):
        if diff[i]<.5 or any(abs(times[i]-c['time_ms'])<300 for c in cuts) or any(abs(times[i]-times[f])<250 for f in flash_idx): continue
        # Track feature similarity affine scale where textured material supports it.
        prev,cur=gray[i-1].astype(np.uint8),gray[i].astype(np.uint8)
        points=cv2.goodFeaturesToTrack(prev,80,.01,3)
        scale=1.
        if points is not None and len(points)>=4:
            moved,ok,_=cv2.calcOpticalFlowPyrLK(prev,cur,points,None)
            valid=ok.ravel()>0
            if valid.sum()>=4:
                matrix,_=cv2.estimateAffinePartial2D(points[valid],moved[valid])
                if matrix is not None: scale=float(np.hypot(matrix[0,0],matrix[0,1]))
        else:
            # Stripe-like graphics have no corners; compare bright feature widths.
            widths=[]
            for image in (prev,cur):
                profile=image.mean(axis=0); widths.append(np.count_nonzero(profile>profile.min()+.75*(profile.max()-profile.min())))
            if widths[0]>2 and widths[1]>2: scale=widths[1]/widths[0]
        if 1.1<=scale<2 and (not zooms or times[i]-zooms[-1]['time_ms']>250):
            zooms.append({'time_ms':float(times[i]),'scale':scale,'confidence':.5,'review':True})
    aligned=sum(bool(beats_ms) and min(abs(c['time_ms']-t) for t in beats_ms)<=step+1e-6 for c in cuts)
    return {'cuts':cuts,'flashes':flashes,'directional_motion':motions,'zoom_punches':zooms,'freezes':freezes,
            'beat_alignment':{'numerator':aligned,'denominator':len(cuts),'ratio':aligned/len(cuts) if cuts else None,'tolerance_ms':step},
            'duration_ms':duration_ms,'analysis_frame_ms':step,'limitations':'Heuristic candidates: review low-confidence events. Natural motion, exposure changes and long dissolves can be ambiguous.'}


def reverse(source, out, beats=None, fps=25):
    source,out=Path(source).resolve(),Path(out)
    if not math.isfinite(fps) or fps<=0 or fps>50: raise ValueError('--fps must be in 0..50')
    if out.exists(): raise ValueError('Use a new output directory')
    info=media_info(source,fps)
    if source.is_dir() and (source.parent/'manifest.json').is_file():
        saved=json.loads((source.parent/'manifest.json').read_text())
        if len(saved['durations_ms'])!=len(info['durations']): raise ValueError('Source manifest timing/frame mismatch')
        info['durations']=[t/1000 for t in saved['durations_ms']]
    images=[];times=[];cursor=0.;next_sample=0.
    for im,seconds in zip(media_frames(source,info),info['durations']):
        if cursor+1e-5>=next_sample:
            images.append(im.copy());times.append(cursor);next_sample=cursor+1000/fps
        cursor+=seconds*1000
    beatdata=json.loads(Path(beats).read_text()) if beats else {'beats_ms':[]}
    report=inspect_frames(images,times,cursor,beatdata['beats_ms'])
    out.mkdir(parents=True)
    if not beats and info.get('audio'):
        from music_sync import analyze
        beatdata=analyze(source,out/'audio-analysis')
        report=inspect_frames(images,times,cursor,beatdata['beats_ms'])
    (out/'beats.json').write_text(json.dumps(beatdata,indent=2))
    # Retain an exact decoded source for provenance, plus a conservative reconstruction.
    (out/'source/frames').mkdir(parents=True)
    for i,im in enumerate(images): im.save(out/'source/frames'/f'{i:05d}.png')
    edges=[round(t/10)*10 for t in times]+[round(cursor/10)*10]
    durations=np.diff(edges).astype(int).tolist()
    (out/'source/manifest.json').write_text(json.dumps({'durations_ms':durations}))
    cut_times={round(c['time_ms']/10)*10:c for c in report['cuts']}
    bounds=sorted(set([0]+list(cut_times)+[edges[-1]]+[
        round(f[k]/10)*10 for f in report['freezes'] for k in ('start_ms','end_ms')]))
    draft={'beatmap':'beats.json','fps':fps,'review':True,'segments':[],'effects':[]}
    if not beatdata['beats_ms']: draft.pop('beatmap')
    excluded=[]
    for c in report['cuts']:
        if c['type']!='cut':
            length=240 if c['type']=='whip_pan' else c['duration_ms']
            excluded.append((c['time_ms']-length/2,c['time_ms']+length/2))
    excluded += [(e['time_ms']-40,e['time_ms']+240) for e in report['flashes']]
    excluded += [(e['time_ms']-40,e['time_ms']+400) for e in report['zoom_punches']]
    for shot,(a,b) in enumerate(zip(bounds,bounds[1:])):
        if b-a<20: continue
        selected=[i for i,t in enumerate(times) if a<=t<b]
        clean=[i for i in selected if not any(x<=times[i]<=y for x,y in excluded)] or selected
        folder=out/'shots'/f'{shot:03d}';(folder/'frames').mkdir(parents=True)
        shot_times=[]
        for j,i in enumerate(selected):
            use=i if i in clean else min(clean,key=lambda k:abs(times[k]-times[i]))
            images[use].save(folder/'frames'/f'{j:05d}.png')
            shot_times.append(durations[i])
        (folder/'manifest.json').write_text(json.dumps({'durations_ms':shot_times,'review':True,'restoration':'Effect-contaminated frames conservatively held from nearest clean sample; replace with licensed source material.'}))
        segment={'type':'animation','manifest':f'shots/{shot:03d}/manifest.json','in_ms':0,'out_ms':sum(shot_times),'duration_ms':b-a,'review':True}
        if any(max(0,min(b,f['end_ms'])-max(a,f['start_ms']))>.65*(b-a) for f in report['freezes']):
            segment.pop('in_ms');segment.pop('out_ms');segment['type']='still';segment['frame']='first'
        exact=[k for k,t in enumerate(beatdata['beats_ms']) if abs(t-b)<5]
        if exact:segment.pop('duration_ms');segment['end_beat']=exact[0]
        if a in cut_times:
            event=cut_times[a]
            if event['type']!='cut':
                length=240 if event['type']=='whip_pan' else event['duration_ms']
                length=min(length,b-a,a-bounds[shot-1])
                if length>=1000/fps:
                    segment['transition']={'name':event['type'],'duration_ms':length,'review':True}
        draft['segments'].append(segment)
    draft['effects']=[{'name':'flash_white','start_ms':e['time_ms'],'end_ms':min(edges[-1],e['time_ms']+160),'amount':{'keyframes':[[e['time_ms'],1],[e['time_ms']+120,0]]},'review':True} for e in report['flashes']
                      if not any(c['type']=='flash_cut' and abs(c['time_ms']-e['time_ms'])<200 for c in report['cuts'])]
    draft['effects'] += [{'name':'zoom_punch','start_ms':e['time_ms'],'end_ms':min(edges[-1],e['time_ms']+320),'scale':e['scale'],'amount':{'keyframes':[[e['time_ms'],1],[e['time_ms']+320,0]]},'review':True} for e in report['zoom_punches']]
    (out/'draft-plan.json').write_text(json.dumps(draft,indent=2))
    report['draft_notes']='Draft uses reviewed reconstruction candidates with clean-sample holds where effects were baked. Replace each shots/* manifest with licensed source footage; inferred effects, scale and transition lengths require review. source/ retains the decoded original.'
    report['suggested_effects']=[{'name':'flash_white','start_ms':e['time_ms'],'end_ms':min(cursor,e['time_ms']+160),'amount':{'keyframes':[[e['time_ms'],1],[e['time_ms']+120,0]]},'review':True} for e in report['flashes']]
    report['suggested_transitions']=[dict(name=c['type'],cut_ms=c['time_ms'],duration_ms=c['duration_ms'],review=True) for c in report['cuts'] if c['type']!='cut']
    (out/'report.json').write_text(json.dumps(report,indent=2))
    board=Image.new('RGB',(320*3,210*math.ceil((len(bounds)-1)/3)),(18,22,30));draw=ImageDraw.Draw(board)
    for i,(a,b) in enumerate(zip(bounds,bounds[1:])):
        j=int(np.argmin(abs(np.asarray(times)-(a+min(200,(b-a)/2)))));im=images[j].convert('RGB');im.thumbnail((320,180))
        x,y=i%3*320,i//3*210;board.paste(im,(x,y+28));draw.text((x+8,y+7),f'{a/1000:.3f} - {b/1000:.3f} s',fill='white')
    board.save(out/'shots.png')
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--beats',type=Path);ap.add_argument('--fps',type=float,default=25)
    a=ap.parse_args()
    try:
        r=reverse(a.source,a.out,a.beats,a.fps);print(json.dumps({'cuts':len(r['cuts']),'beat_alignment':r['beat_alignment']}));return 0
    except (OSError,ValueError,RuntimeError,KeyError) as exc:
        print(f'fx_reverse: {exc}',file=sys.stderr);return 2

if __name__=='__main__': raise SystemExit(main())
