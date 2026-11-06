"""Decode standard preview transports into analysis-only PCM with FFmpeg.

HLS must be opened as a playlist, not downloaded as an alleged MP4. Remote
playlists cannot reference local files; local fixtures cannot contact a network.
Provider encoding version strings are not codec/container identifiers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit
import numpy as np
from media_runtime import executable
from image_common import ImageError,write


def decode_preview(source,out,encoding=None,max_seconds=120,timeout=45):
    out=Path(out)
    if 'analysis' not in out.parts:
        raise ImageError('E_PREVIEW_ONLY','Preview outputs must be inside an analysis directory')
    if not 0<max_seconds<=600 or not 0<timeout<=120:
        raise ValueError('Preview duration/timeout outside bounds')
    value=str(source);url=urlsplit(value)
    remote=url.scheme in ('http','https')
    if url.scheme and not remote and not Path(value).is_file():
        raise ValueError('Expected a local file or HTTP(S) URL')
    protocols='http,https,tcp,tls,crypto' if remote else 'file,crypto,data'
    common=['-protocol_whitelist',protocols,'-rw_timeout','15000000']
    try:
        probe=subprocess.run([executable('ffprobe'),'-v','error',*common,'-i',value,
                              '-select_streams','a:0','-show_entries','format=format_name:stream=codec_name,sample_rate',
                              '-of','json'],capture_output=True,timeout=timeout,check=True)
        info=json.loads(probe.stdout)
        if not info.get('streams'):raise ValueError('No audio stream')
        result=subprocess.run([executable('ffmpeg'),'-v','error',*common,'-i',value,
                               '-map','0:a:0','-t',str(max_seconds),'-ac','2','-ar','48000',
                               '-f','f32le','pipe:1'],capture_output=True,timeout=timeout,check=True)
        pcm=np.frombuffer(result.stdout,'<f4').reshape(-1,2).copy()
        if not len(pcm) or not np.isfinite(pcm).all():raise ValueError('Invalid decoded PCM')
    except (subprocess.SubprocessError,ValueError,KeyError) as exc:
        # Do not echo FFmpeg stderr, which may contain a signed URL or credentials.
        raise ImageError('E_PREVIEW_ENCODING','Preview could not be decoded; do not guess its codec or deliver its bytes',
                         provider_encoding=encoding,preview_only=True,
                         diagnostic=type(exc).__name__) from None
    out.mkdir(parents=True,exist_ok=True)
    # Analysis PCM is explicitly tagged and never accepted by audio_provenance.
    path=out/'preview.f32';path.write_bytes(result.stdout)
    report=dict(status='PASS',preview_only=True,source='stream_preview',
                provider_encoding=encoding,container=info.get('format',{}).get('format_name'),
                codec=info['streams'][0].get('codec_name'),sample_rate=48000,channels=2,
                samples=len(pcm),duration_ms=len(pcm)/48,sha256=hashlib.sha256(result.stdout).hexdigest(),
                protocol_whitelist=protocols,source_url_saved=False)
    write(out/'preview.json',report)
    return pcm,report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--encoding');p.add_argument('--max-seconds',type=float,default=120)
    p.add_argument('--experimental',action='store_true');a=p.parse_args(argv)
    try:
        if not a.experimental:raise ImageError('E_EXPERIMENTAL','Preview decoding requires --experimental')
        _,r=decode_preview(a.source,a.out,a.encoding,a.max_seconds);print(json.dumps(r));return 0
    except (ValueError,OSError) as e:
        print(json.dumps(dict(error=getattr(e,'error',dict(code='E_PREVIEW',message=str(e))))));return 2


if __name__=='__main__':raise SystemExit(main())
