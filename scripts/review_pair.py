#!/usr/bin/env python3
"""Make timestamp-aligned A/B review boards and a machine-readable review ledger."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageDraw
from media_runtime import executable


def inspect(path):
    return json.loads(subprocess.check_output([executable('ffprobe'),'-v','error','-show_format','-show_streams','-of','json',str(path)]))


def build(source, candidate, output, samples=8, offset=0):
    if not math.isfinite(offset):
        raise ValueError("offset must be finite")
    if not 2 <= samples <= 40:
        raise ValueError('samples must be 2–40')
    source, candidate, output = Path(source), Path(candidate), Path(output)
    if output.exists():
        raise ValueError('output directory already exists')
    a, b = inspect(source), inspect(candidate)
    duration = min(float(a['format']['duration']),float(b['format']['duration'])-offset)
    start = max(0,-offset)
    if duration <= start:
        raise ValueError('no overlapping timestamps')
    times = [start+(duration-start)*i/samples for i in range(samples)]
    board = Image.new('RGB',(768, (samples+1)//2*248),'#151b22')
    draw = ImageDraw.Draw(board)
    with tempfile.TemporaryDirectory(prefix='pair-review-') as temp:
        for index,t in enumerate(times):
            x, y = index%2*384,index//2*248
            draw.text((x+8,y+8),f'A {t:.3f}s | B {t+offset:.3f}s',fill='white')
            for column,(path,at) in enumerate(((source,t),(candidate,t+offset))):
                frame = Path(temp)/f'{index}-{column}.png'
                subprocess.run([executable('ffmpeg'),'-v','error','-ss',str(at),'-i',str(path),'-frames:v','1','-vf','scale=180:210:force_original_aspect_ratio=decrease',str(frame)],check=True)
                with Image.open(frame) as im:
                    board.paste(im,(x+6+column*192,y+30))
        output.mkdir(parents=True)
        board.save(output/'comparison.jpg',quality=92)
    report={'schema':'video-gif.pair-review.v1','source':str(source.resolve()),'candidate':str(candidate.resolve()),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'candidateSha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'candidateOffsetSec':offset,'samples':[{'sourceSec':t,'candidateSec':t+offset,'identity':'unreviewed','action':'unreviewed','effectsSilhouettes':'unreviewed'} for t in times],'sourceMetadata':a,'candidateMetadata':b,'warning':'Timestamp sampling, not proof of matching frames, identity, action or sound. Inspect cuts, occlusions, effects and ending at normal speed.'}
    (output/'review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('candidate');p.add_argument('--output',required=True);p.add_argument('--samples',type=int,default=8);p.add_argument('--offset',type=float,default=0)
    args=p.parse_args();build(args.source,args.candidate,args.output,args.samples,args.offset)
    print(str(Path(args.output).resolve()/'comparison.jpg'))
