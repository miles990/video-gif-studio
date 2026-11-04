"""Tiny offline phone-like clips. Only FFmpeg lavfi and local metadata remuxing."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from delivery import run


def phone_timestamp_defects(root):
    """Common 700 ms offset, 400 ms video gap, and one exact duplicate PTS.

    Flash at source 1/3 s maps to output 1/3.4 s; clicks use those same times.
    FFV1/Matroska retains duplicate timestamps for the decoder to resolve.
    """
    target=Path(root)/'timestamp-defects.mkv'
    video="color=c=gray:s=192x108:r=30:d=5,drawbox=x=0:y=0:w=192:h=75:color=white:t=fill:enable='eq(n,30)+eq(n,90)'"
    video+=",setpts='(N-eq(N,31))/30/TB+0.7/TB+gte(N,60)*0.4/TB'"
    audio="aevalsrc=0.25*sin(2*PI*1000*t)*(between(t\\,1\\,1.01)+between(t\\,3.4\\,3.41)):s=48000:d=5.4,asetpts=PTS+0.7/TB"
    run(['-v','error','-copyts','-filter_threads','1','-f','lavfi','-i',video,'-f','lavfi','-i',audio,
         '-fps_mode','passthrough','-c:v','ffv1','-threads','2','-c:a','pcm_s16le',str(target)])
    return target


def phone_clip(root, kind, rotation=90, seconds=2):
    if kind=='hdr': return phone_chart(root,seconds)
    root=Path(root); target=root/(kind+str(rotation)+'.mp4')
    video=f'color=c=gray:s=192x108:r=60:d={seconds},drawbox=x=10:y=10:w=30:h=30:color=red:t=fill'
    if kind=='rotation':
        w,h=(108,192) if rotation%180 else (192,108)
        video=f'color=c=gray:s={w}x{h}:r=30:d={seconds},drawbox=x=8:y=8:w=20:h=20:color=red:t=fill'
        video+=f',drawbox=x={w//2-3}:y=30:w=6:h=40:color=white:t=fill'
        for i in range(6):
            video+=f',drawbox=x={w//2-2*i-1}:y={18+i*2}:w={2+i*4}:h=2:color=white:t=fill'
        video+=','+{90:'transpose=clock',180:'hflip,vflip',270:'transpose=cclock'}[rotation]
    if kind=='vfr':
        video += ",select='if(lt(t,1),not(mod(n,2)),not(mod(n,3)))'"
    codec=['-c:v','libx264','-pix_fmt','yuv420p']
    base=root/('base'+kind+str(rotation)+'.mp4')
    run(['-v','error','-filter_threads','1','-f','lavfi','-i',video,'-f','lavfi','-i',f'sine=frequency=440:sample_rate=48000:duration={seconds}',
         '-fps_mode','vfr',*codec,'-threads','2','-c:a','aac',str(base)])
    if kind=='rotation':
        run(['-v','error','-display_rotation:v:0',str(rotation),'-i',str(base),'-map','0','-c','copy',str(target)])
    else:base.rename(target)
    return target


def phone_chart(root, seconds=2):
    """11 gray steps and RGB/yellow/skin patches, converted to PQ/BT.2020."""
    root=Path(root)
    chart=f'color=c=black:s=220x120:r=30:d={seconds}'
    for i in range(11):
        c=round(i*255/10);color=f'0x{c:02x}{c:02x}{c:02x}'
        chart+=f',drawbox=x={i*20}:y=0:w=20:h=80:color={color}:t=fill'
    for i,color in enumerate(('0xbf0000','0x00bf00','0x0000bf','0xbfbf00','0xe0ac69')):
        chart+=f',drawbox=x={i*44}:y=80:w=44:h=40:color={color}:t=fill'
    target=root/'chart-hdr.mp4'
    conversion='format=gbrp,zscale=pin=bt709:tin=bt709:min=gbr:rin=full:p=bt709:t=linear:m=gbr:r=full:npl=100,format=gbrpf32le,zscale=pin=bt709:tin=linear:min=gbr:rin=full:p=bt2020:t=smpte2084:m=bt2020nc:r=limited,format=yuv420p10le'
    run(['-v','error','-filter_threads','1','-f','lavfi','-i',chart,
        '-f','lavfi','-i',f'sine=frequency=440:sample_rate=48000:duration={seconds}',
        '-map','0:v:0','-map','1:a:0','-vf',conversion,'-c:a','aac',
        '-c:v','libx265','-x265-params','pools=1:frame-threads=1:log-level=error:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):max-cll=1000,400',
        '-pix_fmt','yuv420p10le','-color_primaries','bt2020','-color_trc','smpte2084','-colorspace','bt2020nc',str(target)])
    return target


def phone_markers(root, seconds=10):
    """120 Hz source clock, VFR 30/24/60 with drops, binary IDs + flash/click."""
    root=Path(root);target=root/'markers.mp4'
    video=f'color=c=gray:s=192x108:r=120:d={seconds}'
    video+=",drawbox=x=0:y=0:w=192:h=75:color=white:t=fill:enable='lt(mod(t,1),0.034)'"
    video+=',drawbox=x=0:y=84:w=192:h=24:color=black:t=fill'
    for bit in range(16):
        video+=f",drawbox=x={bit*12}:y=84:w=12:h=24:color=white:t=fill:enable='mod(floor(n/{2**bit}),2)'"
    video+=",select='if(lt(t,3),not(mod(n,4)),if(lt(t,6),not(mod(n,5)),not(mod(n,2))))*not(eq(mod(n,40),36))'"
    audio=f'aevalsrc=0.03*sin(2*PI*440*t)+0.25*sin(2*PI*1000*t)*lt(mod(t\\,1)\\,0.01):s=48000:d={seconds}'
    run(['-v','error','-filter_threads','1','-f','lavfi','-i',video,'-f','lavfi','-i',audio,
         '-fps_mode','vfr','-c:v','libx264','-crf','12','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',str(target)])
    return target
