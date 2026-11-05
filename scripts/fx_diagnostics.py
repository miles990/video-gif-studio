"""Shared, actionable per-file library diagnostics (stderr, never JSON stdout)."""
import difflib
import sys


def describe(message, refs=()):
    from fx import EFFECTS, TRANSITIONS
    from fx_catalog import INTENTS
    vocabulary=sorted(set(EFFECTS)|set(TRANSITIONS)|set(INTENTS))
    suggestions=[]
    for ref in refs:
        suggestions.extend(difflib.get_close_matches(str(ref),vocabulary,n=3,cutoff=.5))
    return (str(message)+'; offending ref(s): '+(', '.join(map(str,refs)) or 'unavailable')+
            '; did-you-mean: '+(', '.join(dict.fromkeys(suggestions)) or 'no close match')+
            '; valid intents: '+', '.join(INTENTS))


def excluded(path, name, status, error, refs=()):
    print(f'Excluded {path} / {name} [{status}]: '+describe(error,refs),file=sys.stderr)
