"""Offline validator for the JSON-Schema vocabulary used by the FX schemas.

The emitted schemas are draft 2020-12 and also work with jsonschema. Keeping the
small used vocabulary here avoids installing packages into the supplied venv.
Unsupported assertion keywords fail closed, not silently ignored.
"""
import math

TYPES={'object':dict,'array':list,'string':str,'boolean':bool,'null':type(None)}
KEYS={'$schema','$comment','title','description','type','required','properties','additionalProperties','items',
      'minItems','maxItems','uniqueItems','minimum','maximum','exclusiveMinimum','minLength','enum','const'}


def matches(value,kind):
    if kind=='number':return type(value) in (int,float) and math.isfinite(value)
    if kind=='integer':return type(value) is int
    if kind not in TYPES:raise ValueError('Unsupported schema type '+str(kind))
    return type(value) is TYPES[kind]


def validate(value,schema,where='$'):
    unknown=set(schema)-KEYS
    if unknown:raise ValueError('Unsupported schema assertions: '+str(sorted(unknown)))
    def fail(message):raise ValueError(where+': '+message)
    kinds=schema.get('type')
    if kinds and not any(matches(value,k) for k in ([kinds] if isinstance(kinds,str) else kinds)):fail('wrong type')
    if 'enum' in schema and value not in schema['enum']:fail('not in enum')
    if 'const' in schema and value!=schema['const']:fail('wrong constant')
    if isinstance(value,dict):
        if set(schema.get('required',[]))-set(value):fail('missing required fields')
        props=schema.get('properties',{})
        if schema.get('additionalProperties') is False and set(value)-set(props):fail('unknown fields')
        for key,v in value.items():
            if key in props:validate(v,props[key],where+'.'+key)
            elif isinstance(schema.get('additionalProperties'),dict):validate(v,schema['additionalProperties'],where+'.'+key)
    if isinstance(value,list):
        if len(value)<schema.get('minItems',0) or len(value)>schema.get('maxItems',math.inf):fail('array length')
        if schema.get('uniqueItems') and any(v in value[:i] for i,v in enumerate(value)):fail('duplicate items')
        for i,v in enumerate(value):
            if 'items' in schema:validate(v,schema['items'],where+f'[{i}]')
    if isinstance(value,str) and len(value)<schema.get('minLength',0):fail('string too short')
    if type(value) in (int,float):
        if not math.isfinite(value):fail('nonfinite number')
        if value<schema.get('minimum',-math.inf) or value>schema.get('maximum',math.inf):fail('numeric bound')
        if 'exclusiveMinimum' in schema and value<=schema['exclusiveMinimum']:fail('exclusive bound')
    return value
