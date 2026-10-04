#!/usr/bin/env python3
"""Generate data/effects.json: the modifier system's effects, requirements and collections (database modding side).

Sources
  * the symbol-build DLL: every GameEffects::Effects|Requirements|Collections class and its EffectFactory / RequirementFactory /
    CollectionFactory<T>::GetTypeName, which is `lea rax,[rip+X]; ret` and returns the real EFFECT_/REQUIREMENT_/COLLECTION_ string
  * data/function_index.json   method names, symbol-build and current-build addresses, signatures
  * callgraph_old.tsv          direct calls of the effect's Apply/Remove (requirement Test..., collection GetItems...) = engine
                               functions the effect uses (static, symbol build; nothing here was observed in a running game)
  * the Companion-derived modifier list (argument names and types, availability, subject class). Descriptions are NOT copied.

If the DLL is not present the cached data/effect_typenames.json is used. Run after extract_index.py, before build.py.
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
DLL = 'C:/Program Files (x86)/Steam/steamapps/content/app_289070/depot_947510/DLC/Expansion2/Binaries/Win64/GameCore_XP2_FinalRelease.dll'
COMPANION_MD = os.path.join(ROOT, 'community-reference', 'civ6-modifiers-reference.md')
CACHE_COMPANION = os.path.join(DATA, 'effect_companion.json')
CACHE_NAMES = os.path.join(DATA, 'effect_typenames.json')

rows = json.load(open(os.path.join(DATA, 'function_index.json'), encoding='utf-8'))['rows']
natives = json.load(open(os.path.join(DATA, 'native.json'), encoding='utf-8'))
by_rva = {r[1]: r for r in rows}
native_ids = {}
for n in natives:
    native_ids.setdefault(n['id'][7:].split('@')[0], n['id'])

# ---------------------------------------------------------------- type names from the DLL
FACT = {'EffectFactory': 'effect', 'RequirementFactory': 'requirement', 'CollectionFactory': 'collection'}
NS = {'Effects': 'effect', 'Requirements': 'requirement', 'Collections': 'collection'}

def decode_names():
    import pefile, capstone
    pe = pefile.PE(DLL, fast_load=True)
    img = pe.get_memory_mapped_image()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    out = {}
    for r in rows:
        m = re.match(r'GameEffects::Factories::(\w+)<GameEffects::(\w+)::(\w+)>::GetTypeName$', r[0])
        if not m or m.group(1) not in FACT:
            continue
        rva = int(r[1], 16)
        ins = list(md.disasm(img[rva:rva + 16], rva))
        if len(ins) >= 2 and ins[0].mnemonic == 'lea' and ins[1].mnemonic == 'ret':
            tgt = ins[0].address + ins[0].size + int(ins[0].op_str.split('+')[-1].strip(' ]'), 16)
            out[m.group(2) + '::' + m.group(3)] = img[tgt:tgt + 160].split(b'\0')[0].decode('latin1')
    return out

if os.path.exists(DLL):
    names = decode_names()
    json.dump(names, open(CACHE_NAMES, 'w'), indent=0, sort_keys=True)
else:
    names = json.load(open(CACHE_NAMES))
print('type names:', len(names))

# ---------------------------------------------------------------- Companion-derived list (arguments, availability, subject class)
def parse_companion():
    md = open(COMPANION_MD, encoding='utf-8').read()
    out = {}
    section = None
    cls = None
    cur = None
    for line in md.split('\n'):
        if line.startswith('## '):
            section = line[3:].strip(); cls = None; cur = None; continue
        m = re.match(r'### Class: (.*)', line)
        if m:
            cls = m.group(1).strip(); cur = None; continue
        m = re.match(r'\*\*((?:EFFECT|REQUIREMENT)_[A-Z0-9_]+)\*\*(?:\s+_\((.*?)\)_)?', line)
        if m:
            cur = {'cls': cls, 'tag': m.group(2), 'availability': None, 'args': []}
            out[m.group(1)] = cur
            continue
        m = re.match(r'- \*\*(COLLECTION_[A-Z0-9_]+)\*\*(?:\s+_\((.*?)\)_)?\s+\u2014\s+(.*)$', line)
        if m:
            out[m.group(1)] = {'cls': cls, 'tag': m.group(2), 'availability': m.group(3).strip(), 'args': []}
            cur = None
            continue
        if cur is not None:
            if line.startswith('Availability:'):
                cur['availability'] = line[len('Availability:'):].strip()
            else:
                m = re.match(r'\s+- `([^`]*)` \[([^\]]*)\]', line)
                if m and m.group(1) != '#N/A':
                    cur['args'].append({'name': m.group(1), 'type': m.group(2)})
    return out

if os.path.exists(COMPANION_MD):
    comp = parse_companion()
    json.dump(comp, open(CACHE_COMPANION, 'w'), indent=0, sort_keys=True)
else:
    comp = json.load(open(CACHE_COMPANION))
print('companion entries:', len(comp))

# ---------------------------------------------------------------- call graph
cg = {}
for l in open(os.path.join(ROOT, 'callgraph_old.tsv')):
    if l[0] == '#' or '\t' not in l:
        continue
    a, b = l.rstrip('\n').split('\t')
    cg[a] = b.split(',')

NOISE = re.compile(r"^(0x|std::|eastl::|operator_|String::|Message::|Utilities::|floorf|ceilf|memcmp|memcpy|memset|"
                   r"MoveAssignmentDo|CopyAssignmentDo|DefaultMakeObject|Definition::DefinitionCollection|"
                   r"GameEffects::(ArgumentProcessor|MakeObject|LexicalConversion|Logging|Factories|Details)|"
                   r"Context::Globals::|`|_|\?|[A-Za-z]+_(Init|Check)|Reporting::)")
SUBJ = {'PlayerReference': 'Player', 'CityReference': 'City', 'UnitReference': 'Unit', 'DistrictReference': 'District',
        'GovernorReference': 'Governor', 'BeliefReference': 'Belief', 'GameReference': 'Game',
        'ModifierObjectReference': 'modifier object', 'PlotReference': 'Plot'}

def method_rows(ns, cls):
    pre = 'GameEffects::%s::%s::' % (ns, cls)
    return {r[0][len(pre):]: r for r in rows if r[0].startswith(pre) and '::' not in r[0][len(pre):] and '`' not in r[0][len(pre):]}

MAIN = {'effect': ('Apply', 'Remove', 'Initialize'), 'requirement': ('Test', 'TestPlot', 'TestAdjacentPlot', 'OnInitialize'),
        'collection': ('GetItems', 'OnInitialize')}

def callees(rs):
    seen = collections.OrderedDict()
    edits = set()
    for r in rs:
        for c in cg.get(r[1], []):
            row = by_rva.get(c)
            nm = row[0] if row else c
            m = re.match(r'FAutoVariable<(.+),(GameCore::)?([\w:]+)>::edit$', nm)
            if m:
                edits.add('%s on %s' % (m.group(1), m.group(3)))
                continue
            if NOISE.match(nm):
                continue
            if '<' in nm:
                nm = re.sub(r'<.*', '', nm)
            if nm.endswith('::') or '::' not in nm and len(nm) < 4:
                continue
            if nm not in seen:
                seen[nm] = {'name': nm, 'rva': row[1] if row else c, 'lua': (row[5] if row else '') or None,
                            'native': native_ids.get(nm)}
    return list(seen.values()), sorted(edits)

def rva_info(r):
    return {'symbol': r[1], 'current': r[2] or None, 'size': r[3]}

def subject_of(sig):
    m = re.search(r'\(\s*[\w:]+\*\s+this,\s*(?:const\s+)?([\w:]+)(&?)', sig or '')
    if not m:
        return None
    t = m.group(1)
    return SUBJ.get(t, t)

def camel_to_snake(s):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', s).upper()

out = []
seen_names = set()
for key, tname in sorted(names.items()):
    nsname, cls = key.split('::')
    kind = NS.get(nsname)
    if not kind:
        continue
    meths = method_rows(nsname, cls)
    main = [meths[m] for m in MAIN[kind] if m in meths]
    calls, edits = callees(main)
    c = comp.get(tname)
    ent = {
        'id': '%s:%s' % (kind, tname),
        'kind': kind,
        'name': tname,
        'cpp_class': 'GameEffects::%s::%s' % (nsname, cls),
        'methods': {m: dict(rva_info(r), sig=r[7][:200]) for m, r in sorted(meths.items())
                    if m in MAIN[kind] + ('Remove', 'Initialize', 'GetTypeInfo', 'Test', 'TestPlot', 'GetItems', 'OnInitialize')},
        'subject': subject_of(meths['Apply'][7]) if kind == 'effect' and 'Apply' in meths else None,
        'calls': calls[:14],
        'calls_more': max(0, len(calls) - 14),
        'edits': edits[:6],
        'in_companion': bool(c),
        'class': c['cls'] if c else None,
        'tag': c['tag'] if c else None,
        'availability': c['availability'] if c else None,
        'args': c['args'] if c else [],
    }
    seen_names.add(tname)
    out.append(ent)

# listed in the Companion but with no class in this build's DLL
for tname, c in sorted(comp.items()):
    if tname in seen_names:
        continue
    kind = tname.split('_')[0].lower()
    out.append({'id': '%s:%s' % (kind, tname), 'kind': kind, 'name': tname, 'cpp_class': None, 'methods': {}, 'subject': None,
                'calls': [], 'calls_more': 0, 'edits': [], 'in_companion': True, 'class': c['cls'], 'tag': c['tag'],
                'availability': c['availability'], 'args': c['args']})

json.dump(out, open(os.path.join(DATA, 'effects.json'), 'w'), indent=1)
cnt = collections.Counter((e['kind'], bool(e['cpp_class'])) for e in out)
print(dict(cnt))
print('with at least one engine call:', sum(1 for e in out if e['calls']), 'linked to a native entity:',
      sum(1 for e in out if any(c['native'] for c in e['calls'])))
