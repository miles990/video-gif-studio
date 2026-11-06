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
