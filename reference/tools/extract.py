"""Generate data/*.json from the analysis artifacts in the analysis workspace. Never hand-edit the output."""
import json, re, collections, os, zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'docs_proto', 'data')
REF_SIG = '<workspace>/community-reference/civ6-lua-signature-index.md'


def P(*a):
    return os.path.join(ROOT, *a)


def tsv(path, skip_comment=True):
    rows = []
    for l in open(path, encoding='utf8'):
        if skip_comment and l[:1] == '#':
            continue
        rows.append(l.rstrip('\n').split('\t'))
    return rows[0], rows[1:]


def dump(name, obj):
    json.dump(obj, open(os.path.join(OUT, name), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
    print('wrote', name, len(obj))


def crc(s):
    return (~zlib.crc32(s.encode())) & 0xffffffff


# ---- builds
dump('builds.json', [
    {'id': 'symbol', 'label': 'Steam depot 947510 (older build with debug symbols, GameCore_XP2)', 'role': 'names come from here'},
    {'id': 'current', 'label': 'Steam build 15038592 (July 2024; build 15296837 of August 2024 ships the identical GameCore DLL)', 'role': 'target build; addresses mapped from the symbol build'},
    {'id': 'linux', 'label': 'Steam depot 533502 (Linux port with DWARF debug info, before the New Frontier Pass)', 'role': 'layouts, member and parameter names'}])

# ---- enums
E = {}
for l in open(P('linux_depot', 'out', 'enums.jsonl'), encoding='utf8'):
    j = json.loads(l)
    E[j['name']] = j
ENUMS = [
    ('PlayerOperations', 'GameCore::Player::Operations::Types::TypeHash', 'lua-table'),
    ('PlayerOperations.Parameters', 'GameCore::Player::Operations::Parameters::ParameterTypes', 'lua-table'),
    ('UnitOperationTypes', 'GameCore::Unit::Operations::Types::TypeHash', 'lua-table'),
    ('UnitCommandTypes', 'GameCore::Unit::Commands::Types::TypeHash', 'lua-table'),
    ('CityOperationTypes', 'GameCore::City::Operations::Types::TypeHash', 'lua-table'),
    ('CityCommandTypes', 'GameCore::City::Commands::Types::TypeHash', 'lua-table'),
    ('Events', 'GameCore::Events::EventTypes', 'engine-event-id')]
enums = []
for eid, cpp, kind in ENUMS:
    mem = []
    for n, v in E[cpp]['values']:
        mem.append({'name': n, 'hash': '0x%08x' % (v & 0xffffffff), 'signed': v, 'hash_matches_name': (v & 0xffffffff) == crc(n)})
    enums.append({'id': 'enum:' + eid, 'cpp_type': cpp, 'kind': kind,
                  'hashed': sum(m['hash_matches_name'] for m in mem) >= 0.5 * len(mem),
                  'members': mem, 'status': 'verified',
                  'evidence': [{'kind': 'dwarf', 'note': 'enumerators from the Linux port debug info'}]})
# event parameters from the Modding Companion (tools/event_params.py), only where the sheet lists the event
_ep = os.path.join(OUT, 'event_params.json')
if os.path.exists(_ep):
    EP = json.load(open(_ep, encoding='utf8'))
    for e in enums:
        if e['id'] == 'enum:Events':
            for m in e['members']:
                if m['name'] in EP:
                    m['parameters'] = EP[m['name']]['parameters']
                    m['parameters_source'] = 'modding-companion'
                    m['lua_event'] = EP[m['name']]['sheet_name']
                    m['event_kind'] = EP[m['name']]['event_kind']
            e['evidence'].append({'kind': 'community-reference', 'note': 'event parameter names and types come from the Civ VI Modding Companion 2.0 (ChimpanG, expanded by WildW); they are not checked against the DLL'})
# Lua constant tables that match an engine enum (tools/lua_enums.py)
_le = os.path.join(OUT, 'lua_enums.json')
if os.path.exists(_le):
    for t in json.load(open(_le, encoding='utf8')):
        mem = [{'name': m.get('lua_key') or m['name'], 'engine_name': m['name'], 'lua_listed': 'lua_key' in m, 'hash': '0x%08x' % (m['value'] & 0xffffffff),
                'signed': m['value'], 'hash_matches_name': False} for m in t['members']]
        enums.append({'id': 'enum:' + t['table'], 'cpp_type': t['cpp_type'], 'kind': 'lua-table-companion', 'hashed': False, 'members': mem, 'status': 'inferred',
                      'companion_members': t['companion_members'],
                      'evidence': [{'kind': 'dwarf', 'note': 'engine enumerators and values from the Linux port debug info'},
                                   {'kind': 'community-reference', 'note': 'the Civ VI Modding Companion lists this Lua table; every member it lists has the same value in this engine enum'}]})
dump('enums.json', enums)

# ---- operations
T = {}
for l in open(P('linux_depot', 'out', 'types.jsonl'), encoding='utf8'):
    j = json.loads(l)
    T[j['name']] = j
ops = []
hdr, rows = tsv(P('findings', 'tables', 'player_operation_cases.tsv'), False)
for r in rows:
    if len(r) < 8 or r[0] in ('INVALID', ''):
        continue
    name, h, co, cn, n, par, ev, calls = r[:8]
    cls = co.startswith('class ')
    ops.append({
        'id': 'op:player-operation.' + name, 'kind': 'player-operation', 'name': name, 'lua': 'PlayerOperations.' + name, 'hash': h,
        'handlers': [{'type': 'class' if cls else 'switch-case',
                      'function': co.split()[1] + '::Start' if cls else 'Player::Operations::Manager::Process',
                      'builds': {'symbol': {'rva': co.split()[-1] if cls else (co or None)}, 'current': {'rva': cn or None}}}],
        'parameters': [{'name': p.strip()} for p in par.split(',') if p.strip()],
        'events': [p.strip() for p in ev.split(',') if p.strip()],
        'calls': [c.strip() for c in calls.split(';') if c.strip()],
        'status': 'verified' if co else 'unknown',
        'evidence': [{'kind': 'static-analysis',
                      'note': 'hash comparison in the Process decision tree' if not cls else 'handler class Start function'}]})

KIND = {'Unit::Operations': 'unit-operation', 'Unit::Commands': 'unit-command',
        'City::Operations': 'city-operation', 'City::Commands': 'city-command'}
LUA = {'Unit::Operations': 'UnitOperationTypes', 'Unit::Commands': 'UnitCommandTypes',
       'City::Operations': 'CityOperationTypes', 'City::Commands': 'CityCommandTypes'}
KEEP = {'CanStart', 'Start', 'MakeParameters', 'SetParameters', 'ResolveOperation', 'Continue', 'MakeRequest'}
hdr, rows = tsv(P('findings', 'tables', 'operation_handlers.tsv'), False)
for r in rows:
    cat, name, h, cls, reg_o, reg_n, meth = r[:7]
    if name in ('?', ''):
        continue
    methods = {}
    for m in meth.split('; '):
        mm = re.match(r'(\w+):(0x[0-9a-f]+)->(0x[0-9a-f]+|\?)$', m)
        if mm and mm.group(1) in KEEP:
            methods[mm.group(1)] = {'symbol': mm.group(2), 'current': None if mm.group(3) == '?' else mm.group(3)}
    cp = T.get('GameCore::%s::%s::ClassParameters' % (cat, cls))
    params = [{'name': m[0], 'type': m[2]} for m in (cp['members'] if cp else []) if m[1] is not None]
    by_name = cls.split('::')[-1].startswith('Hero') or cls in ('DisperseClan', 'RaidClan', 'XP1::Destroy', 'XP2::Purchase')
    oid = 'op:%s.%s' % (KIND[cat], name)
    handler = {'type': 'class', 'class': 'GameCore::%s::%s' % (cat, cls), 'methods': methods,
               'builds': {'symbol': {'rva': reg_o}, 'current': {'rva': reg_n or None}}}
    ev = {'kind': 'static-analysis', 'note': 'hash assigned by class-name convention' if by_name else 'hash stored by the handler Register function'}
    existing = [o for o in ops if o['id'] == oid]
    if existing:
        existing[0]['handlers'].append(handler)
        if by_name:
            existing[0]['status'] = 'inferred'
        continue
    ops.append({'id': oid, 'kind': KIND[cat], 'name': name, 'lua': '%s.%s' % (LUA[cat], name), 'hash': h,
                'handlers': [handler], 'parameters': params, 'events': [], 'calls': [],
                'status': 'inferred' if by_name else 'verified', 'evidence': [ev]})
dump('operations.json', ops)

# ---- lua objects and methods
alias = json.load(open(P('linux_depot', 'out', 'lua_compare.json')))['alias']
inv = {v[0]: k for k, v in alias.items()}          # DLL object name -> modder-facing (reference) name
refset = set()
obj = None
for l in open(REF_SIG, encoding='utf8'):
    m = re.match(r'^## (\S+)', l)
    if m:
        obj = m.group(1)
        continue
    m = re.match(r'^- `(\w+)[:.](\w+)\(', l)
    if m:
        refset.add((obj, m.group(2)))
SIGS = json.load(open(os.path.join(OUT, 'lua_signatures.json'), encoding='utf8'))


def conv_sig(s, iface):
    params = []
    for p_ in s['params']:
        q = {'name': p_.get('name') or 'arg%d' % (p_['index'] - (1 if not s['static'] else 0)), 'type': p_['lua_type'], 'optional': p_['optional']}
        if p_.get('cpp_type'): q['cpp_type'] = p_['cpp_type']
        if p_.get('note'): q['note'] = p_['note']
        if p_.get('name_source'): q['name_source'] = p_['name_source']
        params.append(q)
    return {'interfaces': [iface], 'static': s['static'], 'params': params, 'returns': s['returns'], 'return_count': s['nret'],
            'confidence': s['confidence'], **({'callee': s['callee']} if s.get('callee') else {}),
            **({'returns_constant_stub': s['returns_constant_stub']} if s.get('returns_constant_stub') else {}),
            **({'return_details': s['return_details']} if s.get('return_details') else {}), **({'may_return_nothing': True} if s.get('may_return_nothing') else {})}


hdr, rows = tsv(P('lua_registry.tsv'))
M = {}
for r in rows:
    iface, side, lname, cpp, orva, nrva, cat, glob = r[:8]
    o = re.sub(r'^I(?=[A-Z])', '', iface.split('::')[-1])
    disp = inv.get(o, o)
    m = M.setdefault((disp, lname), {
        'id': 'lua:%s.%s' % (disp, lname), 'object': disp, 'method': lname, 'dll_object': o, 'interfaces': [],
        'registered_on': [], 'cpp_function': cpp, 'builds': {}, 'in_community_reference': (disp, lname) in refset,
        'status': 'verified', 'evidence': [{'kind': 'dll-registration', 'note': 'present in the GameCore Lua registration tables'}]})
    m['interfaces'].append(iface)
    if orva in SIGS:
        cs = conv_sig(SIGS[orva], iface)
        key = json.dumps({k: v for k, v in cs.items() if k != 'interfaces'}, sort_keys=True)
        for ex in m.setdefault('signatures', []):
            if json.dumps({k: v for k, v in ex.items() if k != 'interfaces'}, sort_keys=True) == key:
                ex['interfaces'].append(iface)
                break
        else:
            m['signatures'].append(cs)
    s = 'ui-cache' if side == 'UI' else 'gameplay'
    if s not in m['registered_on']:
        m['registered_on'].append(s)
    m['builds'].setdefault('symbol', {'rva': orva})
    m['builds'].setdefault('current', {'rva': nrva if (nrva and ',' not in nrva) else None, 'map': cat})
methods = sorted(M.values(), key=lambda x: x['id'])
dump('lua_methods.json', methods)
objs = collections.defaultdict(lambda: {'methods': 0, 'sides': set()})
for m in methods:
    o = objs[m['object']]
    o['methods'] += 1
    o['sides'].update(m['registered_on'])
dump('lua_objects.json', [{'id': 'luaobj:' + k, 'name': k, 'method_count': v['methods'], 'registered_on': sorted(v['sides'])}
                          for k, v in sorted(objs.items())])
