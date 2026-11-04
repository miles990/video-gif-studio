#!/usr/bin/env python3
"""Offline word captions. Optional faster-whisper adapter (SYSTRAN, MIT; THIRD_PARTY).

No model downloads: an explicitly supplied local model is required. Presets remain
experimental until independent visual review. SRT/script interpolation is explicitly
approximate, never represented as acoustic forced alignment.
"""
import argparse
import json
import math
import numbers
import os
import subprocess
from pathlib import Path
import re
import sys
import warnings
import unicodedata
from typing import Protocol
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageColor
from fx.effects.typography import resolve_font, check_glyphs, font_codepoints

LEXICON = ('台北市政府', '開放資料', '真的嗎', '我們', '今天', '參加', '活動', '效果', '太棒', '然後', '上線')
CLOSING = '，。、！？；：」』）】》…—％,.!?;:%)]}'
OPENING = '「『（【《([{'
PRESETS = {
    'pop': dict(entrance='pop', keyword_color='FFE45E', box=None, current_word=True),
    'typewriter': dict(entrance='typewriter', keyword_color='78F5DD', box='111111', current_word=True),
    'bounce': dict(entrance='bounce', keyword_color='FFD166', box='183153', current_word=True),
    'clean': dict(entrance='none', keyword_color='FFE45E', box=None, size=88, stroke=6, shadow=0),
}
DEFAULTS = dict(font='', size=112, stroke=8, stroke_color='080808', shadow=4, current_word=False,
                shadow_color='080808', color='FFFFFF', box='111111', keyword_color='FFE45E',
                entrance='pop', words_per_line=12, position='bottom', safe_zone=None)


class TimingEngine(Protocol):
    def __call__(self, audio, script=None): ...


def local_whisper_model(model, cache=None):
    """Resolve a CTranslate2 directory or Hugging Face cache without downloading."""
    root=Path(model)
    if (root/'model.bin').is_file(): return root
    if not root.is_dir():
        cache=Path(cache or os.environ.get('HF_HUB_CACHE',Path(os.environ.get('HF_HOME',Path.home()/'.cache/huggingface'))/'hub'))
        name=str(model).replace('Systran/','').removeprefix('faster-whisper-')
        root=cache/('models--Systran--faster-whisper-'+name)
    repositories=[root] if (root/'snapshots').is_dir() else sorted(root.glob('models--*'))
    models=[]
    for repo in repositories:
        ref=repo/'refs/main'
        if ref.is_file() and (repo/'snapshots'/ref.read_text().strip()/'model.bin').is_file():
            models.append(repo/'snapshots'/ref.read_text().strip())
        else: models.extend(p.parent for p in sorted((repo/'snapshots').glob('*/model.bin')))
    if len(models)==1: return models[0]
    if len(models)>1: raise ValueError('Multiple cached Whisper models; provide model name + --model-cache or a snapshot directory')
    raise ValueError('No cached local faster-whisper model found; supply --model NAME --model-cache ROOT or a model directory; no automatic download')


def decode_whisper_audio(audio):
    from media_runtime import executable
    result=subprocess.run([executable('ffmpeg'),'-v','error','-i',str(audio),'-vn','-ac','1','-ar','16000','-f','f32le','-'],capture_output=True)
    if result.returncode: raise ValueError('Cannot decode caption audio: '+result.stderr.decode(errors='replace')[-1000:])
    pcm=np.frombuffer(result.stdout,dtype='<f4').astype(np.float32,copy=True)
    if not len(pcm): raise ValueError('Caption audio is empty')
    return pcm


def traditional_words(words):
    try:
        from opencc import OpenCC
    except ImportError:
        raise RuntimeError('Traditional conversion requires optional OpenCC: pip install opencc-python-reimplemented; or omit --traditional') from None
    converter=OpenCC('s2twp')
    return [dict(word,text=converter.convert(word['text'])) for word in words]


def faster_whisper_engine(audio, model, script=None, language=None, model_cache=None, traditional=False):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError('Install optional engine: pip install faster-whisper; or use --srt / --words') from None
    model=local_whisper_model(model,model_cache)
    segments, _ = WhisperModel(str(model), device='cpu', compute_type='int8', cpu_threads=2,
                              local_files_only=True).transcribe(decode_whisper_audio(audio), word_timestamps=True,
                              language='zh' if language in ('zh-TW','zh-tw') else language,
                              initial_prompt='請使用繁體中文。' if traditional else None)
    words = [dict(text=w.word, start_ms=float(w.start)*1000, end_ms=float(w.end)*1000)
             for segment in segments for w in (segment.words or []) if w.word.strip()]
    if traditional: words=traditional_words(words)
    if script and ''.join(w['text'] for w in words).replace(' ', '') != script.replace(' ', ''):
        raise ValueError('Transcript differs from script; supply corrected word timing JSON or an injected forced aligner')
    return words


def width(text):
    return sum(1 if unicodedata.east_asian_width(c) in ('W','F') else .5 for c in text)


GRAPHEME = r'(?:[\U0001F1E6-\U0001F1FF]{2}|[^\n])(?:[\uFE0E\uFE0F\u0300-\u036F\U0001F3FB-\U0001F3FF]|\u200d[^\n])*'


def graphemes(text):
    return re.findall(GRAPHEME,text)


def sentence_end(text):
    return bool(re.search(r'[.!?。！？][」』）】》\x22\x27]*$',text.rstrip()))


def tokens(text):
    """Longest dictionary match; decimal/version/number+unit and paired marks atomic."""
    pattern = '|'.join(map(re.escape, sorted(LEXICON, key=len, reverse=True)))
    raw = re.findall(r'[vV]?\d+(?:,\d{3})*(?:\.\d+)*(?:\s*(?:GB|MB|KB|TB|%))?|[A-Za-z]+(?:[\x27’_-][A-Za-z]+)*|……|——|'+pattern+r'|\s+|'+GRAPHEME, text)
    grouped = []; pending = ''
    for token in raw:
        if token in OPENING:
            pending += token
        elif token[0] in CLOSING and grouped and not pending:
            grouped[-1] += token
        else:
            grouped.append(pending+token); pending = ''
    if pending:
        if grouped: grouped[-1] += pending
        else: grouped.append(pending)
    return grouped


def break_lines(text, limit=12):
    if not isinstance(limit,(int,float)) or not math.isfinite(limit) or limit <= 0:
        raise ValueError('words_per_line must be positive')
    lines = []; current = ''
    for token in tokens(text):
        if width(token.strip()) > limit: raise ValueError('Unbreakable token exceeds words_per_line: '+token)
        if current and width(current+token) > limit:
            lines.append(current.rstrip()); current = ''
        current += token if current else token.lstrip()
        if sentence_end(token):
            lines.append(current.rstrip());current=''
    if current.strip(): lines.append(current.rstrip())
    # Rebalance width-wrapped tails, never across an explicit sentence boundary.
    for i in range(1,len(lines)):
        tail=[t for t in tokens(lines[i]) if t.strip()]
        previous=[t for t in tokens(lines[i-1]) if t.strip()]
        if len(tail)==1 and len(previous)>=3 and not sentence_end(lines[i-1]):
            at=lines[i-1].rfind(previous[-1]);moved=lines[i-1][at:]
            sep=' ' if moved[-1:].isascii() and lines[i][:1].isascii() else ''
            if width(moved+sep+lines[i])<=limit:
                lines[i]=moved+sep+lines[i];lines[i-1]=lines[i-1][:at].rstrip()
    return lines


def validate_words(words):
    if not isinstance(words,list): raise ValueError('words must be a list of timing objects')
    result = []
    for word in words:
        if not isinstance(word,dict): raise ValueError('Each word must be a timing object')
        text = word.get('text', word.get('word', ''))
        start, end = word.get('start_ms',word.get('start')), word.get('end_ms',word.get('end'))
        if not isinstance(text,str) or not text.strip() or any(isinstance(t,(bool,np.bool_)) or not isinstance(t,numbers.Real) or not math.isfinite(t) for t in (start,end)) or not 0 <= start < end:
            raise ValueError('words require nonempty text and finite 0 <= start_ms < end_ms')
        start,end=float(start),float(end)
        if 'start_ms' not in word: start*=1000;end*=1000
        if result and start < result[-1]['start_ms']: raise ValueError('word starts must be ordered')
        result.append(dict(text=text, start_ms=start, end_ms=end))
    if not result: raise ValueError('No caption words')
    return result


def distribute(text, start, end):
    parts=[]; pending=''
    for part in tokens(text):
        if not part.strip(): pending+=part
        else: parts.append(pending+part);pending=''
    weights = [width(s) for s in parts]
    clock = start; result = []
    for token, weight in zip(parts,weights):
        finish = clock+(end-start)*weight/sum(weights)
        result.append(dict(text=token, start_ms=clock, end_ms=finish)); clock = finish
    return result


def parse_srt(text):
    def ms(value):
        h,m,s,f = map(int,re.split('[:,.]',value)); return ((h*60+m)*60+s)*1000+f
    words = []
    for block in re.split(r'\n\s*\n', text.strip().replace('\r','')):
        lines = block.splitlines()
        time_index = next((i for i,line in enumerate(lines) if '-->' in line),None)
        if time_index is None: raise ValueError('Invalid SRT: missing timing arrow')
        times = re.findall(r'\d{2}:\d{2}:\d{2}[,.]\d{3}', lines[time_index])
        if len(times) != 2: raise ValueError('Invalid SRT timestamp')
        words += distribute(' '.join(lines[time_index+1:]), ms(times[0]), ms(times[1]))
    return validate_words(words)


def load_words(spec, base=Path('.'), engine=None):
    base = Path(base)
    if 'words' in spec:
        data = spec['words']
        if isinstance(data,str): data = json.loads((base/data).read_text(encoding='utf-8-sig'))
        return validate_words(data.get('words') if isinstance(data,dict) else data), 'user_word_timing'
    if 'srt' in spec:
        return parse_srt((base/spec['srt']).read_text(encoding='utf-8-sig')), 'srt_proportional_within_cue'
    script = spec.get('script')
    if spec.get('audio') and engine:
        return validate_words(engine(base/spec['audio'], script=script)), 'injected_alignment_engine'
    if spec.get('audio') and spec.get('model'):
        model=base/spec['model'] if (base/spec['model']).is_dir() else spec['model']
        cache=base/spec['model_cache'] if spec.get('model_cache') else None
        return validate_words(faster_whisper_engine(base/spec['audio'], model, script, spec.get('language'),cache,spec.get('traditional',False))), 'faster_whisper'
    if script and spec.get('duration_ms',0) > 0:
        warnings.warn('No forced aligner: proportional script timing is approximate; review/edit words JSON',UserWarning)
        return validate_words(distribute(script,0,spec['duration_ms'])), 'approximate_script_fallback'
    raise ValueError('captions: provide words JSON, srt, script + duration_ms, or audio + cached model; use --srt without faster-whisper')


def prepare(spec, base, experimental=False):
    if not experimental: raise ValueError('Captions are experimental; pass --experimental')
    if not isinstance(spec,dict): raise ValueError('captions must be an object')
    allowed = {'words','srt','script','duration_ms','audio','model','model_cache','language','traditional','style','keywords'}
    if set(spec)-allowed: raise ValueError('Unknown captions fields: '+str(sorted(set(spec)-allowed)))
    raw = spec.get('style','pop')
    if isinstance(raw,str): raw = {'preset':raw}
    if not isinstance(raw,dict): raise ValueError('caption style must be preset name or object')
    name = raw.get('preset','pop')
    if name not in PRESETS: raise ValueError('caption preset: '+', '.join(PRESETS))
    if set(raw)-set(DEFAULTS)-{'preset'}: raise ValueError('Unknown caption style fields')
    style = dict(DEFAULTS, **PRESETS[name]); style.update({k:v for k,v in raw.items() if k != 'preset'})
    if not isinstance(style['font'],str): raise ValueError('caption font must be a file path string')
    bold=next((p for p in ('C:/Windows/Fonts/msjhbd.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc') if Path(p).is_file()),'')
    style['font'] = resolve_font(str(base/style['font']) if style['font'] else bold)
    for field in ('size','stroke','shadow','words_per_line'):
        value = style[field]
        if type(value) not in (int,float) or not math.isfinite(value) or value < (1 if field in ('size','words_per_line') else 0):
            raise ValueError('Invalid caption '+field)
    if style['entrance'] not in ('pop','typewriter','bounce','none'): raise ValueError('caption entrance: pop|typewriter|bounce|none')
    if style['position'] not in ('top','center','bottom'): raise ValueError('caption position: top|center|bottom')
    for key in ('color','stroke_color','shadow_color','keyword_color','box'):
        if style[key] is None and key=='box': continue
        if not isinstance(style[key],str) or len(style[key].lstrip('#'))!=6: raise ValueError('caption '+key+' requires six-digit RGB hex')
        ImageColor.getrgb('#'+style[key].lstrip('#'))
    words, method = load_words(spec,base)
    if spec.get('traditional') and method!='faster_whisper': words=traditional_words(words)
    # Drop an unsupported grapheme as a unit: never render tofu, half an emoji,
    # detached skin tone or ZWJ pieces. Keep the original timing in the export.
    supported=font_codepoints(style['font']);display=[];dropped=set()
    for word in words:
        kept=[]
        for cluster in graphemes(word['text']):
            missing={ord(c) for c in cluster if not c.isspace()}-supported
            if missing: dropped.update(ord(c) for c in cluster)
            else: kept.append(cluster)
        if ''.join(kept).strip(): display.append(dict(word,text=''.join(kept)))
    if dropped: warnings.warn('Dropped unsupported caption graphemes: '+', '.join(f'U+{c:04X}' for c in sorted(dropped)),UserWarning)
    content = ''.join(w['text'] for w in display)
    keywords = spec.get('keywords')
    if keywords is None: keywords = [s for s in LEXICON if s in content and s in ('台北市政府','開放資料','效果')]+re.findall(r'\d+(?:\.\d+)*',content)
    if not isinstance(keywords,list) or not all(isinstance(k,str) and k for k in keywords): raise ValueError('keywords must be a list of nonempty strings')
    # Re-tokenize the combined text so dictionary words survive upstream word boundaries.
    # Every character retains its supplied word onset (typewriter spreads within that word).
    char_times=[]
    pause_offsets=[];char_offset=0
    for index,word in enumerate(display):
        if index and word['start_ms']-display[index-1]['end_ms']>=150: pause_offsets.append(char_offset)
        for i,_ in enumerate(word['text']):
            char_times.append((word['start_ms'],word['end_ms'],word['start_ms']+(word['end_ms']-word['start_ms'])*i/len(word['text'])))
        char_offset+=len(word['text'])
    highlights = set()
    for keyword in keywords:
        for match in re.finditer(re.escape(keyword),content): highlights.update(range(match.start(),match.end()))
    lines=[]; offset=0
    edges=[0]+pause_offsets+[len(content)]
    broken=[line for a,b in zip(edges,edges[1:]) for line in break_lines(content[a:b],style['words_per_line'])]
    for line in broken:
        offset=content.find(line,offset)
        chars=[dict(char=c, start_ms=char_times[offset+i][2 if style['entrance']=='typewriter' else 0],
                    word_start_ms=char_times[offset+i][0],end_ms=char_times[offset+i][1],highlight=offset+i in highlights) for i,c in enumerate(line)]
        lines.append(dict(text=line, chars=chars, start_ms=min(c['start_ms'] for c in chars),end_ms=max(c['end_ms'] for c in chars)))
        offset+=len(line)
    for a,b in zip(lines,lines[1:]): a['end_ms']=min(a['end_ms'],b['start_ms'])
    return dict(words=words,lines=lines,style=style,preset=name,status='experimental',method=method,keywords=keywords,
                dropped_codepoints=[f'U+{c:04X}' for c in sorted(dropped)],
                warning=None if method in ('user_word_timing','faster_whisper','injected_alignment_engine') else 'Timing within cues/script is approximate; correct the exported words before final delivery')


class CaptionRenderer:
    def __init__(self, prepared, size, safe_zone):
        self.data=prepared; self.size=tuple(size); self.style=prepared['style']; self.layouts=[]
        w,h=size; s=self.style; factor=h/1920
        face=ImageFont.truetype(s['font'],max(8,round(s['size']*factor)))
        self.font=face; self.stroke=round(s['stroke']*factor); self.shadow=round(s['shadow']*factor)
        zone=dict(safe_zone)
        if s['safe_zone']:
            custom=s['safe_zone']
            if not isinstance(custom,dict) or set(custom)-{'x','y','right','bottom','text_inset_px'}: raise ValueError('Invalid caption safe_zone rectangle')
            # Overrides are fractions of the output canvas, intersected with platform limits.
            for key,dimension in (('x',w),('right',w),('y',h),('bottom',h)):
                if key in custom:
                    value=float(custom[key])
                    if not 0<=value<=1: raise ValueError('caption safe_zone coordinates are fractions 0..1')
                    zone[key]=(max if key in ('x','y') else min)(zone[key],round(value*dimension))
        pad=max(2,round(12*factor)); inset=zone.get('text_inset_px',0)
        self.bounds=(zone['x']+inset,zone['y']+inset,zone['right']-inset,zone['bottom']-inset)
        left,top,right,bottom=self.bounds
        # Width limits are upper bounds. Reflow further using the actual font and
        # maximum animated extent, preserving the tokenizer's unbreakable units.
        max_scale=1.22 if s['entrance']=='pop' else 1
        available=(right-left)/max_scale-2*self.stroke-2*pad-self.shadow
        wrapped=[]
        for line in prepared['lines']:
            pieces=[];current=''
            for token in tokens(line['text']):
                if face.getlength(token.strip())>available: raise ValueError('Caption token exceeds safe zone; choose a wider safe zone or shorter token')
                if current and face.getlength(current+token)>available:
                    pieces.append(current.rstrip());current=''
                current+=token if current else token.lstrip()
            if current:pieces.append(current.rstrip())
            # Pixel reflow must not undo the linguistic orphan prevention.
            # Rebalance when possible; a short two-word + singleton phrase may
            # stay together with bounded uniform reduction (not a stretched font).
            i=1
            while i<len(pieces):
                previous=[t for t in tokens(pieces[i-1]) if t.strip()]
                tail=[t for t in tokens(pieces[i]) if t.strip()]
                if len(tail)==1 and len(previous)>=2:
                    sep=' ' if previous[-1][-1:].isascii() and tail[0][:1].isascii() else ''
                    moved=previous[-1]+sep+pieces[i]
                    joined=pieces[i-1]+sep+pieces[i]
                    if len(previous)>=3 and face.getlength(moved)<=available:
                        pieces[i-1]=pieces[i-1][:pieces[i-1].rfind(previous[-1])].rstrip();pieces[i]=moved
                    elif face.getlength(joined)<=available*1.35:
                        pieces[i-1]=joined;pieces.pop(i);continue
                i+=1
            offset=0
            for piece in pieces:
                offset=line['text'].find(piece,offset);chars=line['chars'][offset:offset+len(piece)];offset+=len(piece)
                wrapped.append(dict(text=piece,chars=chars,start_ms=min(c['start_ms'] for c in chars),end_ms=max(c['end_ms'] for c in chars)))
        # Shape and reveal whole graphemes (including emoji) in one draw call.
        for line in wrapped:
            merged=[];at=0
            for cluster in graphemes(line['text']):
                group=line['chars'][at:at+len(cluster)];at+=len(cluster)
                merged.append(dict(group[0],char=cluster,end_ms=max(c['end_ms'] for c in group)))
            line['chars']=merged
        for a,b in zip(wrapped,wrapped[1:]): a['end_ms']=min(a['end_ms'],b['start_ms'])
        self.lines=wrapped
        for line in wrapped:
            box=face.getbbox(line['text'],stroke_width=self.stroke)
            tw=math.ceil(face.getlength(line['text']))+2*self.stroke+2*pad+self.shadow
            th=box[3]-box[1]+2*pad+self.shadow
            max_scale=1.22 if s['entrance']=='pop' else 1
            bounce=round(18*factor) if s['entrance']=='bounce' else 0
            fit_scale=min(1,(right-left)/(tw*max_scale))
            if fit_scale<1/1.35 or th*max_scale*fit_scale+2*bounce>bottom-top:
                raise ValueError('Caption exceeds safe zone; reduce words_per_line/size or enlarge safe zone')
            y={'top':top+th*max_scale*fit_scale/2+bounce,'center':(top+bottom)/2,'bottom':bottom-th*max_scale*fit_scale/2-bounce}[s['position']]
            self.layouts.append((line,tw,th,pad,box[1],(left+right)/2,y,fit_scale))

    def overlay(self, frame, t_ms):
        image=frame.copy() if isinstance(frame,Image.Image) else Image.fromarray(frame)
        s=self.style
        for line,tw,th,pad,by,cx,cy,fit_scale in self.layouts:
            if not line['start_ms']<=t_ms<line['end_ms']: continue
            visible=[c for c in line['chars'] if c['start_ms']<=t_ms+1e-7]
            if not visible: continue
            tw=min(tw,math.ceil(sum(self.font.getlength(c['char']) for c in visible))+2*self.stroke+2*pad+self.shadow)
            layer=Image.new('RGBA',(tw,th));draw=ImageDraw.Draw(layer)
            if s['box']: draw.rounded_rectangle((0,0,tw-1,th-1),radius=pad,fill='#'+s['box'].lstrip('#'))
            x=pad+self.stroke
            current=max(c.get('word_start_ms',c['start_ms']) for c in visible)
            for char in line['chars']:
                if char['start_ms']<=t_ms+1e-7:
                    pos=(x,pad-by)
                    color=s['keyword_color'] if char['highlight'] or (s['current_word'] and char.get('word_start_ms',char['start_ms'])==current) else s['color']
                    draw.text((pos[0]+self.shadow,pos[1]+self.shadow),char['char'],font=self.font,fill='#'+s['shadow_color'].lstrip('#'),stroke_width=self.stroke,stroke_fill='#'+s['shadow_color'].lstrip('#'))
                    draw.text(pos,char['char'],font=self.font,fill='#'+color.lstrip('#'),stroke_width=self.stroke,stroke_fill='#'+s['stroke_color'].lstrip('#'))
                x+=self.font.getlength(char['char'])
            elapsed=t_ms-current
            if s['entrance']=='pop' and elapsed<180:
                scale=1+.22*math.sin(math.pi*elapsed/180)
                layer=layer.resize((round(tw*scale),round(th*scale)),Image.Resampling.LANCZOS)
            if s['entrance']=='bounce' and elapsed<400:
                cy+=round(18*self.size[1]/1920*math.exp(-elapsed/95)*math.cos(elapsed/48))
            if fit_scale<1: layer=layer.resize((max(1,round(layer.width*fit_scale)),max(1,round(layer.height*fit_scale))),Image.Resampling.LANCZOS)
            image.alpha_composite(layer,(round(cx-layer.width/2),round(cy-layer.height/2)))
            break
        return image


def export_srt(words, path):
    def stamp(t):
        ms=round(t); seconds,ms=divmod(ms,1000); minutes,seconds=divmod(seconds,60); hours,minutes=divmod(minutes,60)
        return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'
    Path(path).write_text('\n\n'.join(f'{i+1}\n{stamp(w["start_ms"])} --> {stamp(w["end_ms"])}\n{w["text"]}' for i,w in enumerate(words))+'\n',encoding='utf-8')


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    group=ap.add_mutually_exclusive_group(required=True)
    for flag in ('srt','words','script','audio'): group.add_argument('--'+flag)
    ap.add_argument('--model');ap.add_argument('--model-cache');ap.add_argument('--language');ap.add_argument('--traditional',action='store_true')
    ap.add_argument('--duration-ms',type=float);ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--style',choices=PRESETS,default='pop');ap.add_argument('--experimental',action='store_true')
    a=ap.parse_args(argv)
    try:
        spec={k:v for k,v in vars(a).items() if v is not None and k not in ('out','experimental')}
        prepared=prepare(spec,Path.cwd(),a.experimental)
        if a.out.exists(): raise ValueError('Use a new output directory')
        a.out.mkdir(parents=True);(a.out/'captions.json').write_text(json.dumps(prepared,ensure_ascii=False,indent=2),encoding='utf-8')
        export_srt(prepared['words'],a.out/'captions.srt')
        return 0
    except (ValueError,RuntimeError,OSError) as exc:
        print('captions: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__': raise SystemExit(main())
