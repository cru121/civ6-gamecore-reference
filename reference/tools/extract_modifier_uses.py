#!/usr/bin/env python3
"""Generate data/modifier_uses.json: where each modifier effect, requirement and collection is used in the game's own data.

Reads the gameplay data XML of the installed game (Base and every DLC/expansion, nothing from mods) and joins
  DynamicModifiers   modifier type -> collection + effect
  Modifiers          modifier id -> modifier type, requirement sets
  ModifierArguments  argument values (also: attach-modifier arguments link a modifier to the one it attaches)
  ModifierStrings    text keys of a modifier
  *Modifiers         owner tables (PolicyModifiers, GovernmentModifiers, TraitModifiers, ...) -> the object that carries a modifier
  RequirementSets / RequirementSetRequirements / Requirements / RequirementArguments
and looks up the Name / Description text keys of each owner.

Only identifiers, numbers and text KEYS are written (no game text). The keys are what the strings-file tool (see the site's
"Game text" page) looks up in the reader's own copy of the game.

Set CIV6_DIR to the game folder if it is not the default Steam location. Run after extract_effects.py, before build.py.
"""
import collections, json, os, re, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
GAME = os.environ.get('CIV6_DIR', "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI")

# ---------------------------------------------------------------- read all tables
tables = collections.defaultdict(list)       # table name -> [(row dict, source)]
def read_dir(d, source):
    for dp, dn, fn in os.walk(d):
        for f in fn:
            if not f.lower().endswith('.xml'):
                continue
            try:
                root = ET.parse(os.path.join(dp, f)).getroot()
            except ET.ParseError:
                continue
            if root.tag not in ('GameInfo', 'GameData'):
                continue
            for tbl in root:
                for row in tbl:
                    if row.tag not in ('Row', 'Replace'):
                        continue
                    r = dict(row.attrib)
                    for ch in row:
                        r[ch.tag] = (ch.text or '').strip()
                    tables[tbl.tag].append((r, source))

read_dir(os.path.join(GAME, 'Base', 'Assets', 'Gameplay', 'Data'), 'Base')
dlc = os.path.join(GAME, 'DLC')
for name in sorted(os.listdir(dlc)):
    d = os.path.join(dlc, name, 'Data')
    if os.path.isdir(d):
        read_dir(d, name)
print('tables:', len(tables), 'rows:', sum(len(v) for v in tables.values()))

def rows(t):
    return tables.get(t, [])

# ---------------------------------------------------------------- core joins
dyn = {}                                      # modifier type -> (collection, effect)
for r, s in rows('DynamicModifiers'):
    if 'ModifierType' not in r:
        continue
    dyn[r['ModifierType']] = (r.get('CollectionType'), r.get('EffectType'))
mods = {}                                     # modifier id -> dict
for r, s in rows('Modifiers'):
    if 'ModifierId' not in r:
        continue
    mods[r['ModifierId']] = {'type': r.get('ModifierType'), 'sr': r.get('SubjectRequirementSetId') or None,
                             'or': r.get('OwnerRequirementSetId') or None, 'src': s}
margs = collections.defaultdict(dict)
for r, s in rows('ModifierArguments'):
    if 'ModifierId' not in r or 'Name' not in r:
        continue
    margs[r['ModifierId']][r['Name']] = r.get('Value', '')
mstrings = collections.defaultdict(list)
for r, s in rows('ModifierStrings'):
    if 'ModifierId' not in r:
        continue
    mstrings[r['ModifierId']].append((r.get('Context'), r.get('Text')))

# requirement sets
req_args = collections.defaultdict(dict)
for r, s in rows('RequirementArguments'):
    if 'RequirementId' not in r or 'Name' not in r:
        continue
    req_args[r['RequirementId']][r['Name']] = r.get('Value', '')
reqs = {}
for r, s in rows('Requirements'):
    if 'RequirementId' not in r:
        continue
    reqs[r['RequirementId']] = r
setreqs = collections.defaultdict(list)
for r, s in rows('RequirementSetRequirements'):
    if 'RequirementSetId' not in r or 'RequirementId' not in r:
        continue
    setreqs[r['RequirementSetId']].append(r['RequirementId'])
setkind = {r['RequirementSetId']: r.get('RequirementSetType') for r, s in rows('RequirementSets') if 'RequirementSetId' in r}
def reqset(sid):
    out = []
    for rid in setreqs.get(sid, []):
        q = reqs.get(rid)
        if not q:
            continue
        e = {'t': q.get('RequirementType'), 'a': req_args.get(rid, {})}
        if q.get('Inverse') in ('1', 'true', 'True'):
            e['inv'] = True
        out.append(e)
    return out

# ---------------------------------------------------------------- owners
# any table (other than the modifier definition tables) that has a column holding a modifier id owns that modifier;
# the owner id is another column ending in Type/ID (first one), and the row's own Description/Name/Text keys are kept
CORE = {'Modifiers', 'DynamicModifiers', 'ModifierArguments', 'ModifierStrings', 'Types', 'Kinds'}
owner_rows = collections.defaultdict(list)    # modifier id -> [(table, owner id, row text keys)]
for tname, lst in tables.items():
    if tname in CORE:
        continue
    for r, s in lst:
        mcols = [k for k, v in r.items() if k.lower().startswith('modifier') and k.lower().endswith('id') and v in mods]
        if not mcols:
            continue
        oid = next((v for k, v in r.items() if k not in mcols and (k.endswith('Type') or k.lower().endswith('id')) and v), None)
        tk = {k: v for k, v in r.items() if k in ('Name', 'Description', 'Text', 'Summary') and isinstance(v, str) and v.startswith('LOC_')}
        for c in mcols:
            owner_rows[r[c]].append((tname, oid, tk))

# text keys of owners: any row that carries a '<X>Type' column equal to the owner value and has Name/Description
named = {}
for tname, lst in tables.items():
    if tname.endswith('Modifiers') or tname.endswith('Strings'):
        continue
    for r, s in lst:
        if 'Name' not in r and 'Description' not in r:
            continue
        for k, v in r.items():
            if k.endswith('Type') and v and v not in named:
                named[v] = (r.get('Name'), r.get('Description'), tname)

attach = collections.defaultdict(list)        # attached modifier id -> [parent modifier ids]
for mid, args in margs.items():
    for n, v in args.items():
        if n == 'ModifierId' and v in mods:
            attach[v].append(mid)

def owners_of(mid, seen=None, depth=0):
    seen = seen or set()
    if mid in seen or depth > 6:
        return []
    seen.add(mid)
    out = []
    for t, val, tk in owner_rows.get(mid, []):
        nm = named.get(val)
        o = {'t': t, 'id': val}
        n = tk.get('Name') or (nm[0] if nm else None)
        d = tk.get('Description') or tk.get('Text') or tk.get('Summary') or (nm[1] if nm else None)
        if n: o['n'] = n
        if d: o['d'] = d
        if depth:
            o['via'] = depth
        out.append(o)
    for p in attach.get(mid, []):
        out += owners_of(p, seen, depth + 1)
    return out

# ---------------------------------------------------------------- build the output
uses = collections.defaultdict(list)
used_sets = set()
keys = set()
def keyof(v):
    return v if isinstance(v, str) and v.startswith('LOC_') else None
for mid, m in sorted(mods.items()):
    coll, eff = dyn.get(m['type'], (None, None))
    if not eff:
        continue
    owners = owners_of(mid)
    # drop duplicate owners
    seen, ow = set(), []
    for o in owners:
        k = (o['t'], o['id'], o.get('via'))
        if k not in seen:
            seen.add(k); ow.append(o)
    for o in ow:
        for kk in (o.get('n'), o.get('d')):
            if keyof(kk): keys.add(kk)
    strs = [[c, t] for c, t in mstrings.get(mid, []) if t]
    for c, t in strs:
        if keyof(t): keys.add(t)
    for v in margs.get(mid, {}).values():
        if keyof(v): keys.add(v)
    e = {'m': mid, 'mt': m['type'], 'c': coll, 'a': margs.get(mid, {}), 'o': ow[:6], 'src': m['src']}
    if len(ow) > 6:
        e['o_more'] = len(ow) - 6
    if m['sr']: e['sr'] = m['sr']; used_sets.add(m['sr'])
    if m['or']: e['or'] = m['or']; used_sets.add(m['or'])
    if strs: e['s'] = strs
    uses[eff].append(e)

reqsets = {sid: reqset(sid) for sid in sorted(used_sets)}
req_use = collections.Counter()
for sid, lst in reqsets.items():
    for q in lst:
        req_use[q['t']] += 1
coll_use = collections.Counter(c for c, e in dyn.values())
out = {'game_sources': sorted({m['src'] for m in mods.values()}), 'effect_uses': uses, 'reqsets': reqsets,
       'requirement_sets_using': dict(req_use), 'collection_modifier_types': dict(coll_use)}
json.dump(out, open(os.path.join(DATA, 'modifier_uses.json'), 'w', encoding='utf-8'), separators=(',', ':'))
json.dump(sorted(keys), open(os.path.join(DATA, 'strings_keys.json'), 'w', encoding='utf-8'))
print('effects with uses:', len(uses), 'uses:', sum(len(v) for v in uses.values()), 'modifiers:', len(mods), 'dynamic types:', len(dyn))
print('owner coverage: modifiers with an owner', sum(1 for u in uses.values() for e in u if e['o']), '/', sum(len(v) for v in uses.values()))
print('keys:', len(keys), 'reqsets:', len(reqsets))
