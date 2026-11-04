#!/usr/bin/env python3
"""Explicit Kenney CC0 audio downloader; never called by tests or rendering.

Kenney (https://kenney.nl/assets/interface-sounds), CC0-1.0. Audio retains original
filenames and License.txt; no full pack is committed. See THIRD_PARTY.md.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
import zipfile

PACKS={name:'https://kenney.nl/assets/'+name for name in ('interface-sounds','impact-sounds','digital-audio')}


def install_zip(data, out, source):
    out=Path(out)
    if out.exists(): raise ValueError('Use a new pack directory')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members=archive.infolist()
        if sum(m.file_size for m in members)>200*1024*1024: raise ValueError('Pack exceeds 200 MiB unpacked limit')
        for m in members:
            destination=(out/m.filename).resolve()
            if not destination.is_relative_to(out.resolve()): raise ValueError('Unsafe archive path')
            if (m.external_attr >> 16)&0o170000 == 0o120000: raise ValueError('Archive symlinks not supported')
        licenses=[m for m in members if 'license' in m.filename.lower() and not m.is_dir()]
        if not any(b'CC0' in archive.read(m) or b'Creative Commons Zero' in archive.read(m) for m in licenses):
            raise ValueError('Expected Kenney CC0 license not found in archive')
        out.mkdir(parents=True);archive.extractall(out)
    record=dict(author='Kenney',license='CC0-1.0',source=source,archive_sha256=hashlib.sha256(data).hexdigest())
    (out/'provenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    return record


def download(pack, out):
    page=PACKS[pack]
    def fetch(url):
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'vgs-fx CC0 downloader'}),timeout=60) as response:
            data=response.read(100*1024*1024+1)
        if len(data)>100*1024*1024: raise ValueError('Download exceeds 100 MiB')
        return data
    html=fetch(page).decode('utf-8')
    links=re.findall(r'href=["\x27]([^"\x27]+\.zip(?:\?[^"\x27]*)?)["\x27]',html)
    if not links: raise ValueError('No direct zip link found; download official pack manually and use --zip')
    url=urllib.parse.urljoin(page,links[-1])
    if urllib.parse.urlparse(url).hostname not in ('kenney.nl','www.kenney.nl'): raise ValueError('Unexpected download host; use reviewed --zip')
    return install_zip(fetch(url),out,page)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--pack',choices=PACKS,default='interface-sounds')
    ap.add_argument('--zip',type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args(argv)
    try:
        print(json.dumps(install_zip(a.zip.read_bytes(),a.out,PACKS[a.pack]) if a.zip else download(a.pack,a.out)));return 0
    except (OSError,ValueError,zipfile.BadZipFile) as exc:
        print('kenney: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__': raise SystemExit(main())
