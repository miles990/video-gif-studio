"""Suno word alignment to P1 captions; reports contain indexes, never lyrics."""
from decimal import Decimal,ROUND_HALF_UP
import math
import numpy as np
from image_common import ImageError


def milliseconds(seconds):
    if not math.isfinite(float(seconds)) or float(seconds)<0:raise ValueError('Invalid word time')
    return int((Decimal(str(seconds))*1000).quantize(Decimal('1'),rounding=ROUND_HALF_UP))


def captions(alignment):
    status=alignment.get('status')
    if status=='processing':return dict(status='pending',words=[],report=dict(reason='Poll audio_lyrics_alignment with same clip ID'))
    if status=='unavailable':return dict(status='unavailable',words=[],report=dict(reason='Provider alignment unavailable',suggestion='Offer local whisper word timestamps; no paid fallback'))
    if status!='complete':raise ImageError('E_ALIGNMENT','Expected complete, processing or unavailable alignment')
    words=[];inferred=[]
    for i,w in enumerate(alignment.get('words',[])):
        a=milliseconds(w.get('start_s',w.get('start')));b=milliseconds(w.get('end_s',w.get('end')))
        if b<=a or (words and a<words[-1]['start_ms']):raise ValueError('Nonpositive or unordered aligned word span')
        text=w.get('word',w.get('text',''))
        if not text.strip():raise ValueError('Empty aligned word')
        inferred_time=w.get('success',True) is False
        if inferred_time:inferred.append(i)
        words.append(dict(text=text,start_ms=a,end_ms=b,timing_source='inferred' if inferred_time else 'suno_alignment'))
    return dict(status='complete' if words else 'no_lyrics',words=words,
        report=dict(word_count=len(words),inferred_word_indexes=inferred,rounding='decimal milliseconds half-up',
                    local_whisper_crosscheck='untested'))


def whisper_crosscheck(words,local,count=20):
    if len(words)<count or len(local)<count:return dict(status='unavailable',reason=f'Need {count} comparable words')
    # Require token equality rather than pairing unrelated word positions.
    ids=np.linspace(0,min(len(words),len(local))-1,count,dtype=int);errors=[];mismatches=[]
    for i in ids:
        if words[i]['text'].strip().casefold()!=local[i]['text'].strip().casefold():mismatches.append(int(i));continue
        errors.append(abs(words[i]['start_ms']-local[i]['start_ms']))
    med=float(np.median(errors)) if errors else None
    return dict(status='PASS' if not mismatches and med is not None and med<=150 else 'FAIL',
        compared=len(errors),median_error_ms=med,token_mismatch_indexes=mismatches,
        over_150ms_indexes=[int(i) for i,e in zip(ids,errors) if e>150] if not mismatches else [])
