"""Entities for the Lua tables hosted by the engine exe: static tables (UI, Network, ...), object types, ForgeUI control types, event objects.
Inputs : findings/tables/exe_lua_methods_windows.tsv           (tools/exe/winlua.py: registration code -> wrapper RVAs)
         findings/tables/exe_lua_forgeui_methods_windows.tsv   (tools/exe/winforge.py: control methods with the exe's own signature strings)
         findings/tables/exe_lua_type_methods_linux.tsv / exe_lua_type_names_linux.tsv (Linux names for the ForgeUI types)
         data/exe_lua_signatures.json (exe_lua_signatures.py), data/exe_lua_usage.json (exe_lua_usage.py), data/exe_lua_group_names.json
         curated/_exe_lua_tables.yaml, data/function_index (exe) for callee names
Outputs: data/exe_lua.json (method entities), data/exe_lua_tables.json (one record per table/type)."""
import collections, csv, json, os, re, yaml

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
T = os.path.join(ROOT, 'findings', 'tables')
def D(n): return os.path.join(BASE, 'data', n)
def rows(p): return list(csv.DictReader(open(p, encoding='utf8'), delimiter='\t'))

sigs = json.load(open(D('exe_lua_signatures.json'), encoding='utf8'))
usage = json.load(open(D('exe_lua_usage.json'), encoding='utf8'))
gnames = json.load(open(D('exe_lua_group_names.json'), encoding='utf8'))
cur = yaml.safe_load(open(os.path.join(BASE, 'curated', '_exe_lua_tables.yaml'), encoding='utf8'))['groups']
fn_index = {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            fn_index.setdefault(int(v, 16), r[0])

EV = {'Add', 'Call', 'CallImmediate', 'Count', 'Dispatch', 'Remove', 'RemoveAll'}
groups = collections.OrderedDict()
for r in rows(os.path.join(T, 'exe_lua_methods_windows.tsv')):
    g = groups.setdefault(r['register_fn_rva'], {'interface': r['interface'], 'methods': []})
    g['methods'].append((r['lua_method'], r['wrapper_rva']))

# ------------------------------------------------------------------ tables
tables = []      # {id, name, kind, style, basis, status, group, usage_name}
entities = []
EXPLICIT = {'GameCore::App::UI::Lua::IManager': 'UI', 'GameCore::App::UI::Lua::ILenses': 'UILens', 'GameCore::App::UI::Lua::ITree': 'UITree',
            'GameCore::App::Configuration::Lua::IGame': 'GameConfiguration', 'GameCore::App::Configuration::Lua::IMap': 'MapConfiguration',
            'GameCore::App::Configuration::Lua::IUser': 'UserConfiguration', 'GameCore::App::UI::Lua::IGenericObjectContext': 'AssetPreview',
            'App::Automation::Lua::IManager': 'Automation', 'GameCore::App::WorldView::Lua::IWorldView': 'WorldView'}
DISPLAY = {}     # unchanged

def style_of(usage_name, methods):
    seps = collections.Counter()
    for m in methods:
        u = usage.get('%s.%s' % (usage_name, m))
        if u:
            for s, c in u['sep'].items():
                seps[s] += c
    if not seps:
        return None
    return 'static' if seps['.'] >= seps[':'] else 'object'

def lua_type_of(a):
    return a

def make_entity(table, kind, style, usage_name, meth, wrapper, basis_ev):
    sg = sigs.get(wrapper)
    u = usage.get('%s.%s' % (usage_name, meth)) if usage_name else None
    ev = [{'kind': 'exe-registration', 'note': 'registered in CivilizationVI.exe (DX11, Jul 2024), wrapper 0x%s' % wrapper}]
    params = []
    first = 1 if style == 'static' else 2           # first argument slot after the object itself
    code_by_slot = {p['slot']: p for p in (sg['params'] if sg else [])}
    nmax_code = max(code_by_slot) if code_by_slot else 0
    argc = {int(k): v for k, v in (u['arg_counts'].items() if u else [])}
    used_n = max(argc) if argc else 0
    n = max(nmax_code - first + 1, used_n, 0)
    if n > 12:
        n = nmax_code - first + 1 if nmax_code else 0
    for i in range(n):
        slot = first + i
        cp = code_by_slot.get(slot)
        lt = None; src = None; opt = True
        if cp and cp['lua_type'] != 'any':
            lt, src = cp['lua_type'], 'decompiled code'
            opt = cp['optional']
        if u and str(i) in u['kinds']:
            kc = u['kinds'][str(i)]
            real = {k: v for k, v in kc.items() if k not in ('name', 'expr', 'nil')}
            if lt is None and real:
                lt = max(real, key=real.get); src = 'game script call sites'
        if lt is None:
            lt, src = 'any', None
        if u and str(i) in u['kinds'] and lt in ('number', 'integer'):
            kc = u['kinds'][str(i)]
            if kc.get('string', 0) >= 0.3 * sum(kc.values()):
                lt = 'number|string'; src = 'decompiled code + game script call sites'
        if argc:
            opt = min(argc) <= i
        p = {'index': i + 1, 'lua_type': lt, 'optional': bool(opt), 'type_source': src}
        if u and str(i) in u['names'] and u['names'][str(i)]:
            nm = u['names'][str(i)][0]
            total_here = sum(u['kinds'].get(str(i), {}).values())
            share = u['names_count'][str(i)].get(nm, 0) / total_here if (total_here and 'names_count' in u and str(i) in u['names_count']) else 0
            if share >= 0.6 and total_here >= 5 and not re.match(r'^(m_|g_|k[A-Z]|[pe][A-Z]|tmp|temp)', nm) and re.match(r'^[a-z_]\w*$', nm) and not re.match(r'^(tmp|temp|v|i|k)$', nm):
                p['name'] = nm; p['name_source'] = 'game script'
        params.append(p)
    ent = {
        'id': 'exelua:%s.%s' % (table, meth), 'object': table, 'method': meth, 'object_kind': kind, 'call_style': style,
        'wrapper_rva': '0x' + wrapper, 'params': params,
        'returns': ([x for x in sg['returns'] if x not in ('nil', 'value')] if sg and sg['returns'] else []), 'return_count': sg['nret'] if sg else None,
        'param_certainty': 'partial' if (sg and sg['unparsed_helpers']) else 'complete',
        'usage': {'calls': u['calls'], 'files': u['files'], 'examples': u['examples'], 'arg_counts': u['arg_counts']} if u else None,
        'callees': [fn_index[int(c.split('_')[-1], 16) - 0x140000000] for c in (sg['callees'] if sg else [])
                    if re.match(r'(?:thunk_)?FUN_', c) and (int(c.split('_')[-1], 16) - 0x140000000) in fn_index][:3],
        'availability': 'exe', 'status': 'inferred',
        'evidence': ev + ([{'kind': 'exe-disassembly', 'note': 'argument reads and pushes recovered from the decompiled wrapper'}] if sg else []) +
                    ([{'kind': 'game-script', 'note': '%d call sites in %d game scripts' % (u['calls'], u['files'])}] if u else []),
    }
    return ent

for rva, g in groups.items():
    ms = {m for m, _ in g['methods']}
    if ms == EV:
        continue
    c = cur.get(rva)
    auto = gnames.get(rva)
    uname = auto['name'] if auto else None
    if c:
        name, kind, basis = c['name'], c['kind'], c['basis']
    elif g['interface'] in EXPLICIT:
        name, kind, basis = EXPLICIT[g['interface']], None, 'registered by exe interface %s' % g['interface']
    elif auto:
        name, kind, basis = auto['name'], None, 'named from how the game scripts call it (%d of %d methods matched)' % (auto['matched'], auto['of'])
    else:
        continue
    style = 'object' if kind == 'object' else (style_of(uname, ms) if uname else None) or 'static'
    kind_txt = 'object type' if kind == 'object' else 'static table'
    if auto and not c and g['interface'] in EXPLICIT:
        basis += '; game scripts call %d of %d methods' % (auto['matched'], auto['of'])
    tables.append({'id': 'exetable:' + name, 'name': name, 'kind': kind_txt, 'style': style, 'basis': basis, 'group_rva': '0x' + rva,
                   'methods': len(g['methods']), 'status': 'verified' if (auto and auto['matched'] / auto['of'] >= 0.5 and not c) else 'inferred',
                   'family': 'native'})
    for meth, wrap in g['methods']:
        e = make_entity(name, kind_txt, style, uname if uname else None, meth, wrap, None)
        entities.append(e)

# ------------------------------------------------------------------ event objects (one shared API)
ev_groups = [rva for rva, g in groups.items() if {m for m, _ in g['methods']} == EV]
tables.append({'id': 'exetable:Event objects', 'name': 'Event objects', 'kind': 'event object', 'style': 'object',
               'basis': '%d event objects in the exe each register the same seven methods (Add, Remove, RemoveAll, Call, CallImmediate, Dispatch, Count)' % len(ev_groups),
               'group_rva': None, 'methods': 7, 'status': 'verified', 'family': 'events', 'objects': len(ev_groups)})

# ------------------------------------------------------------------ ForgeUI control methods
lin = collections.defaultdict(set)
for r in rows(os.path.join(T, 'exe_lua_type_methods_linux.tsv')):
    lin[r['cpp_type']].add(r['lua_method'])
tnames = {r['cpp_type']: r['lua_type_name'] for r in rows(os.path.join(T, 'exe_lua_type_names_linux.tsv'))}
cand = collections.defaultdict(set)
for t, ms in lin.items():
    for m in ms:
        cand[m].add(t)
fw = rows(os.path.join(T, 'exe_lua_forgeui_methods_windows.tsv'))
fw.sort(key=lambda r: int(r['thunk_rva'], 16))
asg = [None] * len(fw); how = [None] * len(fw)
for i, r in enumerate(fw):
    c = cand.get(r['method'], set())
    if len(c) == 1:
        asg[i] = next(iter(c)); how[i] = 'unique method name'
for _ in range(5):
    for i, r in enumerate(fw):
        if asg[i]:
            continue
        c = cand.get(r['method'], set())
        for d in range(1, 8):
            hit = [asg[j] for j in (i - d, i + d) if 0 <= j < len(fw) and asg[j] in c]
            if hit:
                asg[i] = hit[0]; how[i] = 'neighbouring methods in the code'
                break

CT = [(re.compile(r'^(const )?char\*?$|^const char\*$'), 'string'), (re.compile(r'^(int|uint|short|ushort|long|ulong|size_t|uint64|int64)\*?$'), 'integer'),
      (re.compile(r'^(float|double)$'), 'number'), (re.compile(r'^bool$'), 'boolean'), (re.compile(r'^function$'), 'function'), (re.compile(r'^table$'), 'table')]
def lua_of(t):
    t = t.strip()
    for rx, lt in CT:
        if rx.match(t):
            return lt
    if t.endswith('*'):
        return t.rstrip('*').strip() + ' (object)'
    return t or 'any'

by_type = collections.defaultdict(list)
for i, r in enumerate(fw):
    by_type[asg[i]].append((r, how[i]))
for ct, lst in sorted(by_type.items(), key=lambda kv: str(kv[0])):
    tname = tnames.get(ct, ct) if ct else 'Unassigned'
    nm = tname if ct else 'Unassigned control methods'
    tables.append({'id': 'exetable:' + nm, 'name': nm, 'kind': 'control type', 'style': 'object',
                   'basis': 'ForgeUI type %s: methods registered in the exe with the exe\'s own signature strings' % (ct or 'unknown'),
                   'group_rva': None, 'methods': len(lst), 'status': 'inferred', 'family': 'forgeui', 'cpp_type': ct})
    seen_ids = collections.Counter()
    for r, h in lst:
        m = r['method']
        seen_ids[m] += 1
        eid = 'exelua:%s.%s' % (nm, m) + ('#%d' % seen_ids[m] if seen_ids[m] > 1 else '')
        sig = r['signature']
        ptypes = [a.strip() for a in r['arg_types'].split(',') if a.strip()] if r['arg_types'] else []
        params = [{'index': k + 1, 'lua_type': lua_of(a), 'optional': False, 'type_source': 'exe signature string', 'cpp_type': a} for k, a in enumerate(ptypes)]
        ret = r['return_type']
        ent = {'id': eid, 'object': nm, 'method': m, 'object_kind': 'control type', 'call_style': 'object', 'wrapper_rva': '0x' + r['thunk_rva'],
               'params': params, 'returns': [lua_of(ret)] if ret and ret != 'void' else [], 'return_count': 0 if ret == 'void' else (1 if ret else None),
               'param_certainty': 'complete' if sig else 'unknown', 'cpp_signature': sig or None,
               'usage': None, 'callees': [], 'availability': 'exe',
               'status': 'inferred',
               'evidence': [{'kind': 'exe-registration', 'note': 'registered in CivilizationVI.exe (DX11, Jul 2024), thunk 0x%s' % r['thunk_rva']}] +
                           ([{'kind': 'exe-string', 'note': 'signature string printed by the exe for this method: %s' % sig}] if sig else []),
               'owner_basis': h}
        entities.append(ent)

# the exe's own help text printer gives only the name for some methods ("CFunction: name"): parse their wrappers like the other tables
for e in entities:
    if e['object_kind'] == 'control type' and not e['cpp_signature']:
        sg = sigs.get(e['wrapper_rva'][2:])
        if sg:
            first = 2
            code_by_slot = {p['slot']: p for p in sg['params']}
            n = max(code_by_slot) - first + 1 if code_by_slot else 0
            e['params'] = [{'index': i + 1, 'lua_type': code_by_slot.get(first + i, {}).get('lua_type', 'any'), 'optional': True, 'type_source': 'decompiled code'} for i in range(max(n, 0))]
            e['param_certainty'] = 'partial'
            e['returns'] = sg['returns']; e['return_count'] = sg['nret']
            e['evidence'].append({'kind': 'exe-disassembly', 'note': 'argument reads recovered from the decompiled thunk (the exe prints no signature for it)'})


# validation of the code-derived argument counts against the game scripts
vc = collections.Counter()
for e in entities:
    if not e['usage'] or e['object_kind'] == 'control type':
        continue
    sg = sigs.get(e['wrapper_rva'][2:])
    if not sg:
        continue
    first = 1 if e['call_style'] == 'static' else 2
    slots = [p['slot'] for p in sg['params']]
    ncode = (max(slots) - first + 1) if slots else 0
    ac = {int(k): v for k, v in e['usage']['arg_counts'].items()}
    mode = max(ac, key=ac.get); mx = max(ac)
    vc['match' if ncode in (mode, mx) else ('under' if ncode < mode else 'over')] += 1
tot = sum(vc.values())
json.dump({'compared': tot, 'match': vc['match'], 'under': vc['under'], 'over': vc['over']}, open(D('exe_lua_validation.json'), 'w'))
print('validation', dict(vc))

# unique ids
cnt = collections.Counter(e['id'] for e in entities)
dups = [k for k, v in cnt.items() if v > 1]
for k in dups:
    n = 0
    for e in entities:
        if e['id'] == k:
            n += 1
            if n > 1:
                e['id'] = '%s#%d' % (k, n)
json.dump(entities, open(D('exe_lua.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(tables, open(D('exe_lua_tables.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(entities), 'methods in', len(tables), 'tables;', 'event objects', len(ev_groups),
      '| ForgeUI unassigned', len(by_type.get(None, [])), '| with usage', sum(1 for e in entities if e['usage']))
