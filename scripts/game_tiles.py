"""Periodic texture diagnostics/repair and complete edge-compatible tile families."""
from dataclasses import replace
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from image_common import ImageError,write
from game_character import rgba,originality


def tile_qa(im):
    a=np.array(im.convert('RGB')).astype(float);h,w=a.shape[:2];luma=a@np.array([.2126,.7152,.0722]);rows={};issues=[]
    for axis,name in [(1,'x'),(0,'y')]:
        interior=np.mean(np.abs(np.diff(a,axis=axis)),axis=2)
        normal=float(np.median(np.mean(interior,axis=1-axis)))
        edge=float(np.mean(np.abs(np.take(a,0,axis=axis)-np.take(a,-1,axis=axis))))
        rows[name]=dict(wrap_difference=edge,ordinary_difference=normal,ratio=edge/max(normal,1e-9))
        if edge>1.5*normal+1e-6:issues.append(dict(kind='wrap_seam',axis=name,ratio=rows[name]['ratio']))
    tiled=np.tile(luma,(2,2));sx=cv2.Sobel(tiled,cv2.CV_64F,1,0,ksize=3);sy=cv2.Sobel(tiled,cv2.CV_64F,0,1,ksize=3);mag=np.hypot(sx,sy)
    band=np.zeros(tiled.shape,bool);band[:,w-1:w+1]=True;band[h-1:h+1]=True;band[:2]=False;band[-2:]=False;band[:,:2]=False;band[:,-2:]=False
    sobel=float(np.median(mag[band])/max(1e-9,np.median(mag[~band])))
    if sobel>1.3:issues.append(dict(kind='sobel_seam',ratio=sobel))
    fft=np.abs(np.fft.fft2(luma-luma.mean()))**2
    # DC removed; compare axis energy with adjacent frequency lines.
    axis_energy=float(np.mean(np.r_[fft[0,2:-1],fft[2:-1,0]]))
    nearby=float(np.mean(np.r_[fft[1,2:-1],fft[-1,2:-1],fft[2:-1,1],fft[2:-1,-1]]))
    cross=axis_energy/max(1e-9,nearby)
    if cross>1.5:issues.append(dict(kind='spectral_cross',ratio=cross))
    dx=float(abs(luma[:,:w//2].mean()-luma[:,w//2:].mean()));dy=float(abs(luma[:h//2].mean()-luma[h//2:].mean()))
    if dx>3 or dy>3:issues.append(dict(kind='lighting_gradient',x=dx,y=dy))
    return dict(status='FAIL' if issues else 'PASS',issues=issues,axes=rows,sobel_ratio=sobel,spectral_cross_ratio=cross,half_luma_difference=dict(x=dx,y=dy),high_frequency_energy=float(cv2.Laplacian(luma,cv2.CV_64F).var()))


def repair_periodic(im):
    """Periodic-plus-smooth decomposition; global wrap-aware repair, no blur."""
    a=np.array(im.convert('RGB')).astype(float);h,w=a.shape[:2];v=np.zeros_like(a)
    v[0]=a[-1]-a[0];v[-1]=-v[0];v[:,0]+=a[:,-1]-a[:,0];v[:,-1]-=a[:,-1]-a[:,0]
    yy,xx=np.indices((h,w));denom=2*np.cos(2*np.pi*xx/w)+2*np.cos(2*np.pi*yy/h)-4;denom[0,0]=1
    smooth=np.fft.fft2(v,axes=(0,1))/denom[...,None];smooth[0,0]=0
    periodic=a-np.fft.ifft2(smooth,axes=(0,1)).real
    # A periodic sine correction removes broad half-frame exposure differences
    # without introducing a new edge discontinuity or averaging fine texture.
    for axis,n in [(1,w),(0,h)]:
        basis=np.sin(2*np.pi*(np.arange(n)+.5)/n)
        half=basis[:n//2].mean()-basis[n//2:].mean()
        left=np.take(periodic,np.arange(n//2),axis=axis).mean(axis=(0,1));right=np.take(periodic,np.arange(n//2,n),axis=axis).mean(axis=(0,1))
        correction=basis[None,:,None] if axis==1 else basis[:,None,None]
        periodic-=correction*(left-right)/half
    fixed=Image.fromarray(np.rint(np.clip(periodic,0,255)).astype(np.uint8));before=tile_qa(im);after=tile_qa(fixed)
    retained=after['high_frequency_energy']/max(1e-9,before['high_frequency_energy'])
    if retained<.85:after['issues'].append(dict(kind='detail_loss',retained=retained));after['status']='FAIL'
    return fixed,dict(before=before,after=after,method='periodic_plus_smooth_and_periodic_exposure_correction',scope='whole-image wrap-aware',high_frequency_retained=retained)


def preview(im,out):
    result=Image.new(im.mode,(im.width*3,im.height*3))
    for y in range(3):
        for x in range(3):result.paste(im,(x*im.width,y*im.height))
    result.save(out)


def texture(adapter,request,out,size=256,repair=True):
    out=Path(out);originality(request.prompt)
    result=adapter.generate(replace(request,prompt=request.prompt+f'. Seamless tileable texture, uniform exposure, no directional light gradient, {size}x{size} canvas.',transparent=False,n=1),out/'generation')
    im=rgba(result['assets'][0]['path']).convert('RGB').resize((size,size),Image.Resampling.NEAREST)
    source=im.copy();qa=tile_qa(im);correction=None
    if repair and qa['status']=='FAIL':im,correction=repair_periodic(im);qa=correction['after']
    im.save(out/'texture.png');source.save(out/'source.png');preview(im,out/'preview-3x3.png')
    manifest=dict(status='experimental',size_actual=list(source.size),size_requested=f'{size}x{size} (prompt only)',qa=qa,repair=correction,generation=result,originality=originality(request.prompt))
    write(out/'gen-manifest.json',manifest);return manifest


def variants(kind):
    if kind=='wang16':return list(range(16))
    if kind=='min13':return list(range(13))
    if kind=='blob47':
        result=[]
        # N,NE,E,SE,S,SW,W,NW clockwise; diagonal only when both neighbors exist.
        for code in range(256):
            if all(not(code&(1<<diag)) or (code&(1<<a) and code&(1<<b)) for diag,a,b in [(1,0,2),(3,2,4),(5,4,6),(7,6,0)]):result.append(code)
        return result
    raise ImageError('E_TILESET','Use wang16, blob47 or min13.')


def tileset(out,grid=16,kind='wang16',palette=('#30472C','#81704B')):
    if grid not in (16,32):raise ImageError('E_GRID','Tilesets support logical 16 or 32 pixel grids.')
    out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'tiles').mkdir(exist_ok=True)
    colors=np.array([tuple(bytes.fromhex(p.lstrip('#'))) for p in palette],np.uint8)
    if len(colors)!=2:raise ImageError('E_PALETTE','Two material colors are required.')
    codes=variants(kind);records=[];tiles=[];yy,xx=np.indices((grid,grid));u=xx/(grid-1);v=yy/(grid-1)
    for i,code in enumerate(codes):
        if kind=='wang16':
            nw,ne,se,sw=[(code>>b)&1 for b in range(4)];field=(1-u)*(1-v)*nw+u*(1-v)*ne+u*v*se+(1-u)*v*sw
            mask=field>=.5;edges={'n':[nw,ne],'e':[ne,se],'s':[sw,se],'w':[nw,sw]}
        else:
            if kind=='blob47':n,e,s,w=[(code>>b)&1 for b in (0,2,4,6)]
            else:
                # Nine outer configurations followed by four explicit concave corners.
                n,e,s,w=[(bits>>b)&1 for b in range(4) for bits in [([6,14,12,7,15,13,3,11,9,15,15,15,15][i])]]
            mask=np.ones((grid,grid),bool)
            if not n:mask[:grid//3]=False
            if not s:mask[-grid//3:]=False
            if not w:mask[:,:grid//3]=False
            if not e:mask[:,-grid//3:]=False
            if kind=='min13' and i>=9:
                corner=i-9;ys=slice(1,grid//3) if corner<2 else slice(-grid//3,-1);xs=slice(1,grid//3) if corner%2==0 else slice(-grid//3,-1);mask[ys,xs]=False
            # Boundaries are canonical edge codes; corners have a common junction pixel.
            mask[0]=n;mask[-1]=s;mask[:,0]=w;mask[:,-1]=e;mask[0,0]=mask[0,-1]=mask[-1,0]=mask[-1,-1]=False
            edges=dict(n=n,e=e,s=s,w=w)
        im=Image.fromarray(colors[mask.astype(int)]).convert('RGBA');file=f'tiles/{i:02d}.png';im.save(out/file);tiles.append(im);records.append(dict(index=i,code=code,file=file,edges=edges))
    sheet=Image.new('RGBA',(grid*8,grid*((len(tiles)+7)//8)))
    for i,im in enumerate(tiles):sheet.paste(im,((i%8)*grid,(i//8)*grid))
    sheet.save(out/'tileset.png');preview(sheet,out/'preview-3x3.png')
    qa=tileset_qa(tiles,records,kind,grid)
    result=dict(kind=kind,grid=grid,variants=records,palette=list(palette),qa=qa,source='local procedural corner/edge material topology',filter='nearest',status='experimental')
    write(out/'tileset.json',result);return result


def tileset_qa(tiles,records,kind,grid):
    expected=set(variants(kind));actual=[r['code'] for r in records];issues=[]
    if set(actual)!=expected or len(actual)!=len(expected):issues.append(dict(kind='incomplete_variants',missing=sorted(expected-set(actual))))
    for i,im in enumerate(tiles):
        if im.size!=(grid,grid):issues.append(dict(kind='grid',tile=i))
    for i,a in enumerate(records):
        for j,b in enumerate(records):
            for first,second,axis in [('e','w','x'),('s','n','y')]:
                if a['edges'][first]!=b['edges'][second]:continue
                aa=np.array(tiles[i]).astype(float);bb=np.array(tiles[j]).astype(float)
                delta=float(np.abs(aa[:,-1]-bb[:,0]).mean()) if axis=='x' else float(np.abs(aa[-1]-bb[0]).mean())
                if delta>4:issues.append(dict(kind='incompatible_edge',a=i,b=j,axis=axis,delta=delta))
    return dict(status='FAIL' if issues else 'PASS',issues=issues,variant_count=len(records))
