#!/usr/bin/env python3
"""Optional local foreground masks for prepared frames; preserves source RGB and timing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import numpy as np
from PIL import Image
from gif_pipeline import natural


def separate(frames, manifest, out, model='u2netp', masker=None):
    frames, manifest, out = Path(frames), Path(manifest), Path(out)
    if out.exists():
        raise FileExistsError('Use a new output directory')
    files = sorted(frames.glob('*.png'), key=natural)
    source = json.loads(manifest.read_text())
    if not files or len(files) != len(source['durations_ms']):
        raise ValueError('Frames must match timing manifest')
    if masker is None:
        os.environ.setdefault('U2NET_HOME', str(Path(__file__).resolve().parents[1]/'.runtime/models'))
        try:
            from rembg import new_session, remove
        except ImportError:
            raise RuntimeError('Install optional backend with scripts/install.py --with-matting') from None
        session = new_session(model)
        masker = lambda im: remove(im.convert('RGB'), session=session, only_mask=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    expected_size = None
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        stage = Path(tmp)/'delivery'
        (stage/'frames').mkdir(parents=True)
        for i, file in enumerate(files):
            with Image.open(file) as im:
                rgba = np.array(im.convert('RGBA'))
                size = im.size
                expected_size = expected_size or size
                if size != expected_size:
                    raise ValueError('Shared frame canvas required')
                mask = np.array(masker(im).convert('L'))
                if mask.shape != rgba.shape[:2]:
                    raise ValueError('Foreground mask changed dimensions')
                # Never quantize colors, fill interior holes, or replace original alpha.
                rgba[:, :, 3] = ((rgba[:, :, 3].astype('uint16') * mask + 127)//255).astype('uint8')
                Image.fromarray(rgba).save(stage/'frames'/f'{i:05d}.png')
        record = dict(source)
        record['background_removal'] = {
            'backend': 'rembg', 'model': model,
            'source_manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'source_frame_sha256': [hashlib.sha256(f.read_bytes()).hexdigest() for f in files],
            'rgb': 'preserved exactly', 'alpha': 'source alpha multiplied by predicted foreground mask',
            'temporal_model': False, 'visual_review': 'required; framewise masks can flicker'}
        # Prior GIF QC/hash describes a different artifact, not these new masks.
        for key in ('qc', 'gif_sha256'):
            record.pop(key, None)
        (stage/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
        stage.rename(out)
    return {'frames': len(files), 'out': str(out), 'temporal_model': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('frames', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--model', choices=['u2netp', 'u2net'], default='u2netp')
    args = parser.parse_args()
    print(json.dumps(separate(args.frames, args.manifest, args.out, args.model)))
