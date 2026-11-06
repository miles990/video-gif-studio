"""Small result-complement grammar; no catalogue of transformation verbs.

English accepts an open verb slot before into/to/as plus a result noun phrase.
Locative motion clauses are excluded. Chinese resultative 成/為 accepts an open
verb slot. This is a conservative surface grammar, not a semantic NLP model.
"""
import re

TRANSFORMATION = (r'\b\w+(?:\s+back)?\s+into\s+(?:an?\s+|the\s+)?[\w-]+'
                  r'|\b\w+\s+back\s+as\s+[\w-]+|\bbecomes?\s+[\w-]+'
                  r'|[\u3400-\u9fff](?:成|為)[\u3400-\u9fff]+'
                  r'|變(?=[\u3400-\u9fff])[^，,。；;\s]+')
LOCATIVE = r'\b(?:walk|run|go|slide|move|step|jump|look|enter)s?\s+into\b'
TIMING = r'\b\d+(?:\.\d+)?\s*(?:seconds?|secs?|s\b)|\d+(?:\.\d+)?\s*秒'


def transformation(text):
    for clause in re.split(r'[。；;!?！？\n]|(?<!\d)\.(?!\d)', text):
        if re.search(TRANSFORMATION, clause, re.I) and not re.search(LOCATIVE, clause, re.I):
            return re.sub(TIMING, '', clause, flags=re.I).strip(' ，,:：')
    return None


def results(text):
    """Result heads, used to check preservation without copying source wording."""
    clause = transformation(text)
    if not clause:
        return []
    heads = re.findall(r'(?:into|back\s+as|becomes?)\s+(?:an?\s+|the\s+)?([\w-]+)', clause, re.I)
    heads += re.findall(r'[\u3400-\u9fff](?:成|為)([\u3400-\u9fff]+?)(?=再|重新|然後|並|，|,|\s|$)', clause)
    return heads


def required_subjects(constraints):
    subjects=[]
    for clause in constraints:
        patterns=(r'^(.+?)(?:一定要|必須)(?:出現|呈現|展示|保留)',
                  r'(?:一定要|必須)(?:使用|呈現|展示|保留)\s*(.+)$',
                  r'^(.+?)\s+must\s+(?:appear|be shown|remain)',
                  r'\bmust\s+(?:show|include|use|feature)\s+(.+?)(?:\s+last|$)')
        for pattern in patterns:
            match=re.search(pattern,clause,re.I)
            if match:
                name=match[1].strip(' ，,:：')
                if not re.search(r'\blogo\b',name,re.I):subjects.append(name)
                break
    return subjects


def positive_text(text):
    return re.sub(r'\b(?:no|without)\s+(?:human\s+)?faces?\b|(?:不要|不得|禁止|無)(?:出現|呈現)?(?:人臉|臉孔)|\bno\s+logo\b','',text,flags=re.I)


def constraint_violations(document,sequence=True):
    """Verify explicit text contracts; pixels still require human semantic QA."""
    constraints=document.get('hard_constraints',[])
    beats=document.get('beats',[]);shots=document.get('shots',[])
    groups=[('beats',beats,'text'),('shots',shots,'action')]
    violations=[]
    logo=any(re.search(r'logo.*(?:最後|last)|(?:最後|last).*logo',c,re.I) for c in constraints)
    no_faces=any(re.search(r'\b(?:no|without)\s+(?:human\s+)?faces?\b|(?:不要|不得|禁止|無).*人臉',c,re.I) for c in constraints)
    for kind,rows,field in groups:
        if not rows:continue
        texts=[positive_text(row.get(field,'')) for row in rows]
        if sequence and logo and not re.search(r'\blogo\b',texts[-1],re.I):
            violations.append((f'{kind}[-1]','Logo must appear in the last '+kind[:-1]))
        if sequence:
            for subject in required_subjects(constraints):
                if not any(subject.casefold() in text.casefold() for text in texts):
                    violations.append((kind,'Required subject is absent: '+subject))
        if no_faces:
            for i,text in enumerate(texts):
                if re.search(r'\bfaces?\b|人臉|臉孔',text,re.I):violations.append((f'{kind}[{i}]','Positive face description violates no faces'))
    return violations
