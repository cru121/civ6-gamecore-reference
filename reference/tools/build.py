"""Validate data + curated notes, then emit docs/*.md, site/*.html, dist/*.json and dist/ai/*.txt."""
import urllib.parse
import json, os, re, shutil, sys, datetime, html
import yaml, markdown
from jsonschema import Draft202012Validator, RefResolver

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
def B(*a): return os.path.join(BASE, *a)

SCHEMA = json.load(open(B('schema', 'entities.schema.json'), encoding='utf8'))


def validator(name):
    sub = {'$schema': SCHEMA['$schema'], '$ref': '#/$defs/' + name, '$defs': SCHEMA['$defs']}
    return Draft202012Validator(sub)


def load(name):
    return json.load(open(B('data', name), encoding='utf8'))


methods = load('lua_methods.json')
ops = load('operations.json')
enums = load('enums.json')
objects = load('lua_objects.json')
builds = load('builds.json')
layouts = load('layouts.json')
globs = load('globals.json')
ce_methods = load('ce_methods.json')
devce = load('devce_methods.json') if os.path.exists(B('data', 'devce_methods.json')) else []
natives = load('native.json')
findex = load('function_index.json')
op_params = load('op_params.json')
ret_meanings = load('lua_return_meanings.json')
arg_meanings = load('lua_arg_meanings.json')
rt_checks = load('lua_runtime_checks.json') if os.path.exists(B('data/lua_runtime_checks.json')) else {}
for _m in methods:
    _k = '%s.%s' % (_m['object'], _m['method'])
    if _k in rt_checks:
        _m['runtime_check'] = rt_checks[_k]
        if rt_checks[_k].get('called'):
            _m['evidence'].append({'kind': 'runtime', 'note': 'called in the running game (%s, build %s, %s): %s' % (rt_checks[_k]['state'], rt_checks[_k]['build'], rt_checks[_k]['date'], rt_checks[_k]['result'])})
        else:
            _m['evidence'].append({'kind': 'runtime', 'note': 'present on the live object in the game (UI state, build 15038592, 2026-10-03); not called'})
    if _k in ret_meanings:
        _m['return_meaning'] = ret_meanings[_k]
    for _a in arg_meanings.get(_k, []):
        _ps = (_m.get('signatures') or [{'params': []}])[0]['params']
        if _a['index'] < len(_ps):
            _ps[_a['index']]['meaning'] = {k: v for k, v in _a.items() if k not in ('index', 'name')}

# ---------------------------------------------------------------- curated notes
curated = {}
for root, _, files in os.walk(B('curated')):
    for f in files:
        if f.endswith('.yaml') and not f.startswith('_'):
            c = yaml.safe_load(open(os.path.join(root, f), encoding='utf8'))
            curated[c['id']] = c

errors = []
ids = {}
for kind, recs, schema in (('lua', methods, 'lua_method'), ('op', ops, 'operation'), ('enum', enums, 'enum'), ('layout', layouts, 'layout'), ('global', globs, 'global'), ('ce', ce_methods, 'ce_method'), ('devce', devce, 'devce_method'), ('native', natives, 'native'), ('param', op_params, 'param')):
    v = validator(schema)
    for r in recs:
        for e in v.iter_errors(r):
            errors.append('%s: %s' % (r.get('id'), e.message[:120]))
        if r['id'] in ids:
            errors.append('duplicate id ' + r['id'])
        ids[r['id']] = r
cv = validator('curated')
for cid, c in curated.items():
    for e in cv.iter_errors(c):
        errors.append('curated %s: %s' % (cid, e.message[:120]))
    if cid not in ids:
        errors.append('curated note for unknown id ' + cid)
    for rel in c.get('related', []):
        if rel not in ids:
            errors.append('curated %s: related id does not exist: %s' % (cid, rel))
WO = yaml.safe_load(open(B('curated', '_windows_offsets.yaml'), encoding='utf8'))['windows_offsets']
lay_by_id = {l['id']: l for l in layouts}
for w in WO:
    l = lay_by_id.get('layout:' + w['layout'])
    if not l:
        errors.append('windows offset for unknown layout ' + w['layout']); continue
    mm = [m for m in l['members'] if m['name'] == w['member']]
    if not mm:
        errors.append('windows offset for unknown member %s.%s' % (w['layout'], w['member'])); continue
    mm[0]['windows'] = {'offset': w['windows_offset'], 'relation': w['relation'], 'status': w['status'], 'evidence': w['evidence']}
seen = {}
for o in ops:
    k = (o['kind'], o['hash'])
    if k in seen:
        errors.append('hash collision %s %s and %s' % (o['hash'], o['id'], seen[k]))
    seen[k] = o['id']
lv = validator('layout')
for l in layouts:
    for e in lv.iter_errors(l):
        errors.append('%s: %s' % (l['id'], e.message[:120]))
if errors:
    print('VALIDATION FAILED (%d):' % len(errors))
    for e in errors[:40]:
        print('  ', e)
    sys.exit(1)
print('validation ok: %d lua methods, %d operations, %d enums, %d layouts, %d globals, %d curated notes, %d windows offsets' % (len(methods), len(ops), len(enums), len(layouts), len(globs), len(curated), len(WO)))

for r in methods + ops + enums + layouts + globs + ce_methods + devce + natives:
    if r['id'] in curated:
        r['curated'] = {k: v for k, v in curated[r['id']].items() if k != 'id'}

for r in methods + ops:
    r['availability'] = 'vanilla'
for r in enums:
    r['availability'] = 'engine' if r['kind'] == 'engine-event-id' else 'vanilla'
for r in layouts + globs:
    r['availability'] = 'ce'
for r in devce:
    r['availability'] = 'devce'
# ---------------------------------------------------------------- paths and links
def safe(s): return re.sub(r'[^A-Za-z0-9_.-]', '_', s)

def page_of(rid):
    kind, rest = rid.split(':', 1)
    if kind == 'lua':
        o = rest.split('.')[0]
        return 'lua/%s.md' % safe(o), rest.split('.', 1)[1]
    if kind == 'op':
        k, n = rest.split('.', 1)
        return 'operations/%s/%s.md' % (k, safe(n)), None
    if kind == 'enum':
        return 'enums/%s.md' % safe(rest), None
    if kind == 'param':
        return 'operations/parameters.md', safe(rest).lower()
    if kind == 'ce':
        o, m = rest.split('.', 1)
        return 'ce/%s.md' % safe(o), m.lower()
    if kind == 'devce':
        o, m = rest.split('.', 1)
        return 'devce/%s.md' % safe(o), m.lower()
    if kind == 'native':
        cls = rest.split('@')[0].rsplit('::', 1)[0]
        return 'native/%s.md' % safe(cls.split('::')[0]), safe(rest).lower()
    if kind == 'layout':
        parts = rest.split('::')
        return ('layouts/%s/%s.md' % (safe(parts[0]), safe('.'.join(parts[1:]))) if len(parts) > 1 else 'layouts/Other/%s.md' % safe(parts[0])), None
    if kind == 'global':
        parts = rest.split('::')
        return 'globals/%s.md' % safe(parts[0] if len(parts) > 1 else 'Other'), safe(rest)
    raise ValueError(rid)

def link(rid, from_page, label=None):
    p, anchor = page_of(rid)
    rel = os.path.relpath(p, os.path.dirname(from_page) or '.').replace('\\', '/')
    if anchor: rel += '#' + anchor.lower()
    return '[%s](%s)' % (label or rid.split(':', 1)[1], rel)

STATUS = {'verified': 'verified', 'inferred': 'inferred', 'unknown': 'unknown'}
def rva(b, which):
    v = (b.get(which) or {}).get('rva')
    return '`%s`' % v if v else '—'

pages = {}          # path -> (title, markdown)
def add(path, title, text): pages[path] = (title, text)

def notes_md(cur, path):
    out = []
    if cur.get('summary'): out.append(cur['summary'] + '\n')
    if cur.get('lua_usage'): out.append('```lua\n' + cur['lua_usage'].rstrip() + '\n```\n')
    for n in cur.get('notes', []):
        ev = ', '.join('%s%s' % (e['kind'], ' — ' + e['note'] if e.get('note') else '') for e in n['evidence'])
        out.append('- %s\n  *[%s; evidence: %s]*' % (n['text'], n['status'], ev))
    if cur.get('related'):
        out.append('\n**See also:** ' + ', '.join(link(r, path) for r in cur['related']))
    return '\n'.join(out)

# ---------------------------------------------------------------- topics
topics = []
for f in sorted(os.listdir(B('topics'))):
    if not f.endswith('.md'): continue
    t = open(B('topics', f), encoding='utf8').read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', t, re.S)
    fm = yaml.safe_load(m.group(1)); body = m.group(2)
    name = re.sub(r'^\d+-', '', f)[:-3]
    add(name + '.md', fm['title'], body)
    topics.append((fm.get('order', 99), name + '.md', fm['title']))

# ---------------------------------------------------------------- lua
REF_BASE = 'https://sukritact.github.io/civilization-modding-wiki/civ-6/lua/'
def ret_str(r):
    t = r['type']
    if t == 'table':
        if r.get('fields'):
            fs = r['fields']
            inner = ', '.join('%s: %s' % (f['name'], ret_str({'type': f['type']}) if not isinstance(f['type'], dict) else ret_str(f['type'])) for f in fs[:6])
            return 'table{%s%s}' % (inner, ', …' if len(fs) > 6 else '')
        if r.get('array_of') is not None:
            el = r['array_of']
            return '%s[]' % (ret_str(el) if isinstance(el, dict) else el)
    out = t.replace('|', '/') if isinstance(t, str) else 'table'
    if r.get('cpp_type'):
        out += ' (%s)' % r['cpp_type']
    return out


def sig_text(o, m, s):
    def ty(t): return t.replace('|', '/')
    ps = []
    for p in s['params']:
        t = ty(p['type']) + ('[%s]' % p['cpp_type'] if p.get('cpp_type') else '')
        ps.append('%s%s: %s' % (p['name'], '?' if p['optional'] else '', t))
    if s.get('return_details'):
        rets = [ret_str(r) for r in s['return_details']]
    else:
        rets = [ty(r) for r in s['returns']]
        if not rets and s['return_count']: rets = ['%d values' % s['return_count']]
    tail = ' → ' + ', '.join(rets) if rets else ''
    if s.get('may_return_nothing'): tail += ' (or nothing)'
    return '%s%s(%s)%s%s' % (o + ('.' if s['static'] else ':'), m['method'], ', '.join(ps), tail, '' if s['confidence'] == 'high' else ' ⚠')

def sig_md(o, m):
    sigs = m.get('signatures') or []
    if not sigs: return '—'
    shown = []
    for s in sigs:
        lab = ''
        if len(sigs) > 1 and s.get('interfaces'):
            lab = '*%s:* ' % ('UI state' if s['interfaces'][0].startswith('Cache::') else 'gameplay state')
        shown.append('%s`%s`%s' % (lab, sig_text(o, m, s).replace('`', "'"), ' *(the wrapper calls a stub that returns a constant (0, 1, false or a table of zeros))*' if s.get('returns_constant_stub') else ''))
    out = '<br>'.join(shown)
    aps = [p for p in (sigs[0]['params'] if sigs else []) if p.get('meaning')]
    if aps:
        parts = ['`%s` — %s%s' % (p['name'], p['meaning']['summary'].replace('|', '/')[:110], '' if p['meaning']['status'] == 'verified' else ' (inferred)') for p in aps[:4]]
        out += '<br><small>args: ' + '; '.join(parts) + (' …' if len(aps) > 4 else '') + '</small>'
    rc = m.get('runtime_check')
    if rc and rc.get('called'):
        if rc['result'] == 'err':
            out += '<br><small>⚠ test call in the game raised: %s</small>' % rc.get('error', '').replace('|', '/')
        elif rc['result'] == 'ok-returned-nothing':
            out += '<br><small>✓ called in the game (returned nothing in that state)</small>'
        else:
            out += '<br><small>✓ called in the game: %s value(s) as documented</small>' % rc['runtime_returns'].split(':')[0]
    elif rc:
        out += '<br><small>✓ exists at runtime (not called)</small>'
    rm = m.get('return_meaning')
    if rm:
        out += '<br><small>returns: %s%s</small>' % (rm['summary'].replace('|', '/'), '' if rm['status'] == 'verified' else ' (inferred)')
    return out

def ref_obj_url(o): return REF_BASE + o + '/'
def ref_method_url(o, m): return '%s%s.%s/' % (REF_BASE, o, m)
by_obj = {}
for m in methods: by_obj.setdefault(m['object'], []).append(m)
rows = []
for o in objects:
    ms = by_obj[o['name']]
    ref = sum(1 for m in ms if m['in_community_reference'])
    rows.append('| [%s](%s.md) | %d | %s | %d%s |' % (o['name'], safe(o['name']), len(ms), ', '.join(o['registered_on']), ref, ' — [↗](%s)' % ref_obj_url(o['name']) if ref else ''))
add('lua/index.md', 'Lua API', '''# Lua API

Methods registered by GameCore, grouped by object. **Where** says which registration table lists the method (`ui-cache` = the UI-side cache interface, `gameplay` = the gameplay interface). It is not proof of which Lua state can call it; the community reference is more reliable for that.

**In reference** counts the methods that also appear in the community Lua reference by Sukrit Tan (external, ↗ links to it). Each method row links to its page there when it has one; methods without a link are registered by the game but undocumented there.

| Object | Methods | Where | In reference |
|---|---|---|---|
''' + '\n'.join(rows))
for o, ms in by_obj.items():
    path = 'lua/%s.md' % safe(o)
    in_ref = any(m['in_community_reference'] for m in ms)
    lines = ['# %s\n' % o, '%d methods. Symbol/current columns are function addresses (RVA) of the native wrapper.\n' % len(ms)]
    if in_ref:
        lines.append('Community reference for this object: [%s](%s) (Sukrit Tan, external).\n' % (o, ref_obj_url(o)))
    lines.append('**Signatures** are recovered from the game code. ⚠ = partly understood (arguments may be missing or approximate). '
                 '`?` after a name = optional argument. Types: `integer`/`number` are Lua numbers, enum-typed arguments show the C++ type in brackets. '
                 'Two signatures mean the method is registered separately for the UI and the gameplay state and each wrapper was decoded on its own. '
                 '"same code as" in the Symbol column means the compiler merged identical functions: those methods share one wrapper and cannot be told apart by address.\n')
    lines += ['| Method | Signature | Where | Reference | Symbol | Current |', '|---|---|---|---|---|---|']
    shared = {}
    for m in ms:
        shared.setdefault(m['builds']['symbol']['rva'], []).append(m['method'])
    for m in ms:
        name = m['method'] + (' ★' if 'curated' in m else '')
        same = [x for x in shared[m['builds']['symbol']['rva']] if x != m['method']]
        symcell = rva(m['builds'], 'symbol') + (('<br><small>same code as %s</small>' % ', '.join(same[:4]) + (' …' if len(same) > 4 else '')) if same and m['builds']['symbol']['rva'] else '')
        refcell = '[yes ↗](%s)' % ref_method_url(o, m['method']) if m['in_community_reference'] else '—'
        lines.append('| <a id="%s"></a>%s | %s | %s | %s | %s | %s |' % (m['method'].lower(), name, sig_md(o, m), ', '.join(m['registered_on']),
                     refcell, symcell, rva(m['builds'], 'current')))
    cur = [m for m in ms if 'curated' in m]
    if cur:
        lines.append('\n## Notes (★)\n')
        for m in cur:
            lines.append('### %s\n' % m['method'])
            lines.append(notes_md(m['curated'], path) + '\n')
    add(path, o, '\n'.join(lines))

# ---------------------------------------------------------------- operations
KIND_TITLE = {'player-operation': 'Player operations', 'unit-operation': 'Unit operations', 'unit-command': 'Unit commands',
              'city-operation': 'City operations', 'city-command': 'City commands'}
by_kind = {}
for o in ops: by_kind.setdefault(o['kind'], []).append(o)
idx = ['# Operations and commands\n',
       'Everything the game can be asked to do to a player, unit or city is identified by a hash (see [the identifier hash](../hash-function.md)). '
       'Player operations are cases of one large function; the others are handler classes. Each page lists the handler, the parameters it reads and its addresses.\n',
       '| Kind | Count | Lua table |', '|---|---|---|']
for kind, lst in by_kind.items():
    idx.append('| [%s](%s.md) | %d | `%s` |' % (KIND_TITLE[kind], kind, len(lst), lst[0]['lua'].split('.')[0]))
idx.append('\nParameters are described once, on the [parameter reference](parameters.md) page.')
add('operations/index.md', 'Operations and commands', '\n'.join(idx))
PT = {'PlayerOperations': 'Player operations', 'UnitOperationTypes': 'Unit operations', 'UnitCommandTypes': 'Unit commands',
      'CityOperationTypes': 'City operations', 'CityCommandTypes': 'City commands'}
PL = ['# Parameter reference\n',
      'Operations and commands take a table of parameters keyed by constants such as `PlayerOperations.PARAM_CITY_SRC`. This page says what each parameter means, what kind of value it takes and which operations use it.\n',
      'The **status** says how the meaning is known: *verified* = confirmed by how the game\'s own Lua fills it; *inferred* = deduced from the name and the code around it. '
      'The same name can mean different things in different tables (for example `PARAM_DISTRICT_TYPE` is an index in player operations and a hash in city operations), so each table is listed separately. '
      'Value kinds: `hash` = the `Hash` column of a database row; `db-index` = the row `Index`; `*-id` = the id returned by `GetID()`; `plot-coord` = a plot x or y coordinate.\n']
by_tbl = {}
for pr in op_params:
    by_tbl.setdefault(pr['table'], []).append(pr)
for tbl, lst in by_tbl.items():
    PL.append('## %s (`%s`)\n' % (PT[tbl], tbl))
    PL.append('| Parameter | Meaning | Value | Used by | Game examples |')
    PL.append('|---|---|---|---|---|')
    for pr in lst:
        v = pr['value']['kind'] + (' → %s' % pr['value']['db_table'] if pr['value'].get('db_table') else '') + (' (%s)' % pr['value']['form'] if pr['value'].get('form') else '')
        used = ', '.join(link(u, 'operations/parameters.md', u.split('.')[-1]) for u in pr['used_by'][:6]) + (' …' if len(pr['used_by']) > 6 else '')
        ex = ', '.join('`%s`' % x.replace('`', "'").replace('|', '/') for x in pr['examples'][:2])
        PL.append('| <a id="%s"></a>`%s` | %s *(%s)* | %s | %s | %s |' % (safe(pr['id'][6:]).lower(), pr['name'], pr['summary'], pr['status'], v, used or '—', ex or '—'))
    PL.append('')
add('operations/parameters.md', 'Parameter reference', '\n'.join(PL))
for kind, lst in by_kind.items():
    lines = ['# %s\n' % KIND_TITLE[kind], '| Name | Hash | Handler | Status | Notes |', '|---|---|---|---|---|']
    for o in sorted(lst, key=lambda x: x['name']):
        h = o['handlers'][0]
        hd = h.get('class', h.get('function', '')).replace('GameCore::', '')
        if len(o['handlers']) > 1: hd += ' (+%d variant%s)' % (len(o['handlers']) - 1, 's' if len(o['handlers']) > 2 else '')
        lines.append('| [%s](%s/%s.md) | `%s` | %s | %s | %s |' % (o['name'], kind, safe(o['name']), o['hash'], hd, o['status'], '★' if 'curated' in o else ''))
    add('operations/%s.md' % kind, KIND_TITLE[kind], '\n'.join(lines))
    for o in lst:
        path = 'operations/%s/%s.md' % (kind, safe(o['name']))
        L = ['# %s\n' % o['name'], '| | |', '|---|---|', '| Lua constant | `%s` |' % o['lua'], '| Hash | `%s` |' % o['hash'], '| Kind | %s |' % KIND_TITLE[kind],
             '| Status | %s |' % o['status']]
        for h in o['handlers']:
            if h['type'] == 'switch-case':
                L.append('| Handled in | case of `%s` (symbol %s, current %s) |' % (h['function'], rva(h['builds'], 'symbol'), rva(h['builds'], 'current')))
            else:
                L.append('| Handler class | `%s` |' % h.get('class', h.get('function')))
                L.append('| Registered at | symbol %s, current %s |' % (rva(h['builds'], 'symbol'), rva(h['builds'], 'current')))
                for mn, ad in h.get('methods', {}).items():
                    L.append('| &nbsp;&nbsp;%s | symbol `%s`, current %s |' % (mn, ad['symbol'], '`%s`' % ad['current'] if ad['current'] else '—'))
        L.append('')
        if 'curated' in o:
            L.append(notes_md(o['curated'], path) + '\n')
        if o['parameters']:
            L.append('## Parameters\n')
            L.append('Pass these as the keys of the parameter table (for example `tParameters[%s.%s] = value`). Meanings come from the [parameter reference](%s).\n' % (
                o['lua'].split('.')[0], o['parameters'][0]['name'], os.path.relpath('operations/parameters.md', os.path.dirname(path)).replace('\\', '/')))
            for pr in o['parameters']:
                pe = ids.get(pr.get('param'))
                head = '`%s`' % pr['name'] if not pe else link(pr['param'], path, pr['name']).replace('[%s]' % pr['name'], '[`%s`]' % pr['name'])
                meaning = ' — %s *(%s)*' % (pe['summary'], pe['status']) if pe else ''
                cpp = ' C++: `%s %s`.' % (pr.get('cpp_type', ''), pr['cpp_name']) if pr.get('cpp_name') else ''
                L.append('- %s%s%s' % (head, meaning, cpp))
                if pr.get('game_examples'):
                    L.append('  - the game\'s own scripts pass: ' + ', '.join('`%s`' % x.replace('`', "'") for x in pr['game_examples']))
            L.append('')
        if o['events']:
            L.append('## Events sent\n\n' + ', '.join('`%s`' % e for e in o['events']) + '\n')
        if o['calls']:
            L.append('## Functions called (names from the symbol build)\n\n' + ', '.join('`%s`' % c for c in o['calls']) + '\n')
        ev = '; '.join('%s — %s' % (e['kind'], e.get('note', '')) for e in o['evidence'])
        L.append('*Evidence: %s*' % ev)
        add(path, o['name'], '\n'.join(L))

# ---------------------------------------------------------------- enums
rows_van, rows_eng = [], []
for e in enums:
    p, _ = page_of(e['id'])
    (rows_eng if e['availability'] == 'engine' else rows_van).append('| [%s](%s) | %d | %s | %s |' % (e['id'][5:], p.split('/')[-1], len(e['members']), e['kind'], 'yes' if e['hashed'] else 'no'))
    L = ['# %s\n' % e['id'][5:], 'C++ type: `%s`\n' % e['cpp_type']]
    if 'curated' in e: L.append(notes_md(e['curated'], p) + '\n')
    if e['kind'] == 'lua-table-companion':
        L = ['# %s\n' % e['id'][5:],
             'Lua constant table `%s`. Engine enum: `%s`.\n' % (e['id'][5:], e['cpp_type']),
             'The table name and the **Lua key** column come from the [Civilization VI Modding Companion](https://docs.google.com/spreadsheets/d/1EiCTOlPx3IkeAmU0xujGEp9k0v9VuCxe95OcrsyWOVs/edit?usp=sharing) '
             '(ChimpanG, expanded and maintained by WildW). The engine names and values come from the game library\'s debug info. Every member the Companion lists has the same value in the engine enum, which is how the two were matched.\n',
             '**%d of %d** engine members are listed by the Companion. The others exist in the engine, but we do not know whether Lua exposes them, so use the Lua key column as the safe set.\n' % (sum(1 for m in e['members'] if m['lua_listed']), len(e['members'])),
             '| Lua key | Engine name | Value |', '|---|---|---|']
        for m in e['members']:
            L.append('| %s | %s | %d |' % ('`%s`' % m['name'] if m['lua_listed'] else '*not listed*', '`%s`' % m['engine_name'], m['signed']))
        add(p, e['id'][5:], '\n'.join(L))
        continue
    has_par = any('lua_event' in m for m in e['members'])
    if has_par:
        L.append('These are the engine\'s event ids. About three quarters of them are also **Lua events** that scripts can subscribe to; those are on the [Lua events](LuaEvents.md) page with their parameters. '
                 'The last column gives the Lua name where one is known.\n')
    L += ['| Name | Hash | Signed value |' + (' Lua event |' if has_par else ''), '|---|---|---|' + ('---|' if has_par else '')]
    for m in e['members']:
        par = ' %s |' % (('[%s](LuaEvents.md)' % m['lua_event']) if m.get('lua_event') else '') if has_par else ''
        L.append('| %s%s | `%s` | %d |%s' % (m['name'], '' if m['hash_matches_name'] or not e['hashed'] else ' ⚠', m['hash'], m['signed'], par))
    if has_par:
        lev = [m for m in e['members'] if m.get('lua_event')]
        LE = ['# Lua events\n',
              'Events a script can subscribe to with `Events.<Name>.Add(handler)`. Each handler receives the parameters listed here, in this order.\n',
              'The list and the parameters come from the [Civilization VI Modding Companion](https://docs.google.com/spreadsheets/d/1EiCTOlPx3IkeAmU0xujGEp9k0v9VuCxe95OcrsyWOVs/edit?usp=sharing) '
              '(ChimpanG, expanded and maintained by WildW). We matched each one to an engine event id in the game library, so the event exists; the parameters themselves have **not been checked against the game library**. '
              '"none listed" means the Companion lists no parameters, which can also mean it does not document them.\n',
              '%d of the %d engine event ids appear here. The rest are in the [engine ids](Events.md) list only: the Companion does not list them as Lua events (some may be, under a different spelling).\n' % (len(lev), len(e['members'])),
              '| Lua event | Parameters | Kind | Engine id |', '|---|---|---|---|']
        for m in sorted(lev, key=lambda x: x['lua_event'].lower()):
            LE.append('| `%s` | %s | %s | [%s](Events.md) |' % (m['lua_event'], ', '.join('`%s` (%s)' % (q['name'], q['type']) for q in m['parameters']) or 'none listed', m['event_kind'], m['name']))
        un = json.load(open(B('curated', 'event_usage_notes.json'), encoding='utf8'))
        valid = {m['lua_event'] for m in lev}
        LE += ['\n## Notes from real use\n',
               'What real handlers show about these events, beyond the Companion list. Source: %s. Timing and ordering remarks are the mod author\'s comments, not re-tested here. See also [event order and patterns from a large mod](../event-order-gco.md).\n' % un['credit'],
               '| Lua event | Note | Evidence | Status |', '|---|---|---|---|']
        for n in un['notes']:
            assert n['event'] in valid, 'event_usage_notes: unknown event ' + n['event']
            LE.append('| `%s` | %s | %s | %s |' % (n['event'], n['text'], n['evidence'], n['status']))
        add('enums/LuaEvents.md', 'Lua events', '\n'.join(LE))
        lua_event_rows = ['| [Lua events](LuaEvents.md) | %d | events with parameters | no |' % len(lev)]
    if e['hashed'] and any(not m['hash_matches_name'] for m in e['members']):
        L.append('\n⚠ = the value is not the hash of the name.')
    add(p, e['id'][5:], '\n'.join(L))
rows_van += lua_event_rows
add('enums/index.md', 'Enums and constants','# Enums and constants\n\n## Lua constant tables (available out of the box)\n\n'
    'Names the game exposes to Lua as tables such as `PlayerOperations`.\n\n| Enum | Members | Kind | Hashed |\n|---|---|---|---|\n' + '\n'.join(rows_van) +
    '\n\n## Engine ids (not scriptable)\n\nIdentifiers used inside the engine. Lua has no table for them; they are listed to decode hash values seen in code.\n\n'
    '| Enum | Members | Kind | Hashed |\n|---|---|---|---|\n' + '\n'.join(rows_eng))

# ---------------------------------------------------------------- Community Extension
CE_WIKI = 'https://github.com/Wild-W/CivilizationVI_CommunityExtension/wiki/'
CE_REPO = 'https://github.com/Wild-W/CivilizationVI_CommunityExtension'
nat_ids = {n['id'] for n in natives}


def ce_wiki_url(m):
    return CE_WIKI + m['wiki']['page'] + '#' + m['wiki']['anchor']


def ce_sig_md(m):
    out = []
    for s in m['signatures']:
        ps = ', '.join('%s: %s' % (p['name'], p['type'].replace('|', '/')) for p in s['params'])
        rs = ', '.join(r.replace('|', '/') for r in s['returns'])
        out.append('`%s%s%s(%s)%s`' % (m['object'], '.' if m['static'] else ':', m['method'], ps, ' → ' + rs if rs else ''))
    return '<br>'.join(out)


ce_by_obj = {}
for m in ce_methods:
    ce_by_obj.setdefault(m['object'], []).append(m)
rows = []
for o, ms in sorted(ce_by_obj.items()):
    rows.append('| [%s](%s.md) | %d | %s |' % (o, safe(o), len(ms), 'static functions' if all(x['static'] for x in ms) else 'methods on an object'))
add('ce/index.md', 'Community Extension', '''# Lua API added by the Community Extension

The [Community Extension](%s) (CE) is a mod that replaces the game's GameCore library loader and adds Lua functions the unmodified game does not have. Everything in this section **only works while the CE mod is active**.
It also lets Lua read and write raw game memory (`Mem`, `ObjMem`), which is how the [class layouts](../layouts/index.md) and [globals](../globals/index.md) in this reference can be used.

The CE documents its own API on [its wiki](%sHome). This page lists the same functions with signatures and links each one to the engine function it calls, so you can see what is wrapped and, in the [native functions](../native/index.md) section, what is not.
Descriptions are on the CE wiki (links in the last column); they are not copied here.

| Object | Functions | Kind |
|---|---|---|
%s
''' % (CE_REPO, CE_WIKI, '\n'.join(rows)))
for o, ms in sorted(ce_by_obj.items()):
    path = 'ce/%s.md' % safe(o)
    L = ['# %s\n' % o, '%d functions. Signatures come from the CE wiki tables; the engine function and address from the CE source.\n' % len(ms),
         '| Function | Signature | Engine function | Current address | CE docs |', '|---|---|---|---|---|']
    for m in sorted(ms, key=lambda x: x['method']):
        nat = ''
        if m['native'] and m['native'] in nat_ids:
            nat = link(m['native'], path, m['native'][7:])
        elif m['native']:
            nat = '`%s`' % m['native'][7:]
        else:
            nat = '—'
        L.append('| <a id="%s"></a>%s | %s | %s | %s | [wiki ↗](%s) |' % (m['method'].lower(), m['method'], ce_sig_md(m), nat, rva(m['builds'], 'current'), ce_wiki_url(m)))
    add(path, o, '\n'.join(L))


# ---------------------------------------------------------------- Dev CE (experimental)
def devce_tests_md(r):
    t = r['tests']
    bits = []
    if t.get('plumbing') == 'PASS':
        bits.append('plumbing ✓')
    elif t.get('plumbing') == 'NO_INSTANCE' or t.get('plumbing') == 'NOT_RUN':
        bits.append('plumbing: not run (no live object)')
    dp = t.get('delta_probe')
    if dp:
        bits.append('effect ✓ (%s)' % ', '.join(dp['changed_getters']) if dp['visible_effect'] else 'ran ±1, reversible ✓, no visible effect')
    if t.get('this_oracle'):
        bits.append('this ✓ (oracle)')
    return '<br>'.join(bits) or '—'


def devce_sig_md(r):
    s = r['signatures'][0]
    ps = ', '.join('%s: %s' % (p['name'], p['lua_type']) for p in s['params'])
    rs = ', '.join(s['returns'])
    return '`%s:%s(%s)%s`' % (r['object'], r['method'], ps, (' → ' + rs) if rs else '')


devce_by_obj = {}
for r in devce:
    devce_by_obj.setdefault(r['object'], []).append(r)
rows = ['| [%s](%s.md) | %d | %d |' % (o, safe(o), len(ms), sum(1 for m in ms if m['status'] == 'verified')) for o, ms in sorted(devce_by_obj.items())]
n_pass = sum(1 for r in devce if r['tests'].get('plumbing') == 'PASS')
n_dp = sum(1 for r in devce if r['tests'].get('delta_probe'))
n_eff = sum(1 for r in devce if r['status'] == 'verified')
add('devce/index.md', 'Dev CE (experimental)', """# Lua methods added by the Dev CE test build (experimental)

A development build of a Community-Extension-style GameCore that adds Lua methods by **calling engine functions directly**: the Lua call `object:Method(a, b)` becomes `GameCore::Class::Method(this, a, b)`.
The methods are generated from a table (address and signature from the symbol-build map and the Linux debug info; `this` from the game's own instance resolver for the Lua object); no per-function code is written.
They exist only in the Dev CE test build, which is **not released**, replaces the game's GameCore (like the Community Extension, incompatible with it for now) and has only been run in single-player on one game build.

%d methods on %d Lua objects. What was tested in the running game (build 15038592, single player, disposable games):

* **plumbing** (%d methods): the engine function is entered exactly once, `this` is not null, every argument arrives exactly as sent, the return value comes back to Lua intact.
* **this ✓ (oracle)**: for the object, a vanilla getter and the engine function of the same class give the same answer, so the object pointer is right.
* **effect ✓** (%d methods): the function was called with +1 and -1; a vanilla getter changed as the name says and everything returned to its starting value.
* "ran ±1, reversible ✓, no visible effect": called for real (%d methods), caused no error and was fully reversible, but no vanilla getter shows that state. That is not evidence that it works.

**Descriptions are written by an AI assistant from the decompiled code and are marked inferred** unless a test confirms them; read them as leads, not documentation. Many methods change synchronised game state and are marked "may desync" in multiplayer.
Where a method is not listed here, see [native functions](../native/index.md) for what has no Lua route.

| Object | Methods | Effect verified |
|---|---|---|
%s
""" % (len(devce), len(devce_by_obj), n_pass, n_eff, n_dp - n_eff, '\n'.join(rows)))
for o, ms in sorted(devce_by_obj.items()):
    path = 'devce/%s.md' % safe(o)
    L = ['# %s\n' % o, '%d methods (Dev CE test build). `this` is found with the game\'s own `%s` instance resolver (%s).\n' % (len(ms), ms[0]['interface'], ms[0]['this_resolution']),
         '| Method | Signature | Purpose (AI-written, inferred) | Tested | Engine function | Current |', '|---|---|---|---|---|---|']
    for m in sorted(ms, key=lambda x: x['method']):
        an = m.get('analysis') or {}
        nat = link(m['native'], path, m['native'][7:]) if m['native'] and m['native'] in nat_ids else ('`%s`' % m['native'][7:] if m['native'] else '—')
        L.append('| <a id="%s"></a>%s | %s | %s | %s | %s | %s |' % (m['method'].lower(), m['method'] + (' ✓' if m['status'] == 'verified' else ''), devce_sig_md(m).replace('|', '/'),
                 (an.get('purpose') or '—').replace('|', '/').replace('\n', ' '), devce_tests_md(m), nat, rva(m['builds'], 'current')))
    L.append('\n## Details\n')
    for m in sorted(ms, key=lambda x: x['method']):
        an = m.get('analysis')
        if not an:
            continue
        L.append('### %s\n' % m['method'])
        pm = [p for p in m['signatures'][0]['params'] if p.get('meaning')]
        if pm:
            L.append('Arguments: ' + '; '.join('`%s` — %s%s' % (p['name'], p['meaning']['summary'].replace('|', '/'), '' if p['meaning']['status'] == 'verified' else ' (inferred)') for p in pm) + '\n')
        def bl(label, items):
            items = [x for x in (items or []) if x]
            return ['**%s**' % label] + ['- ' + str(x).replace('|', '/') for x in items] + [''] if items else []
        for nt in m.get('notes', []):
            L.append('**Observed in the game%s:** %s\n' % ('' if nt['status'] == 'verified' else ' (inferred)', nt['text'].replace('|', '/')))
        L += bl('Writes', an.get('writes_state')) + bl('Side effects', an.get('side_effects'))
        if an.get('validation'):
            L.append('**Input checks:** %s\n' % an['validation'].replace('|', '/'))
        L += bl('Preconditions', an.get('preconditions'))
        L.append('**Multiplayer:** %s. **Risk:** %s%s. **Confidence of the reading:** %s.\n' % (an.get('multiplayer') or 'unknown', an.get('risk') or '?', (' (' + an['risk_reason'] + ')') if an.get('risk_reason') else '', an.get('confidence') or '?'))
        L += bl('Verified from the code', an.get('verified_facts')) + bl('Inferred', an.get('inferred_facts')) + bl('Open questions', an.get('open_questions'))
    add(path, o, '\n'.join(L))

# ---------------------------------------------------------------- native functions
LUA_TXT = {'none': 'no', 'indirect': 'only indirectly', 'ce': 'via the Community Extension', 'devce': 'via the Dev CE test build (experimental)'}
nby = {}
for n in natives:
    nby.setdefault(n['class'].split('::')[0], []).append(n)
n_an = sum(1 for n in natives if 'analysis' in n)
n_ce = sum(1 for n in natives if n['lua_exposure']['status'] == 'ce')
rows = ['| [%s](%s.md) | %d | %d |' % (ns, safe(ns), len(v), sum(1 for n in v if 'analysis' in n)) for ns, v in sorted(nby.items())]
add('native/index.md', 'Native functions', '''# Engine functions with no Lua access

Functions inside GameCore that the unmodified game does **not** expose to Lua, and that a mod could only reach through a change to the game library (for example by adding them to the Community Extension).
Nothing here can be called from a script today. The list is a selection, not the whole library: %d functions chosen because they change game state and have no Lua wrapper (%d), because they were analysed in detail (%d) or because the Community Extension already wraps them (%d).

The complete function inventory (all %d functions of the symbol build) is searchable on the [All functions](all.md) page.

How to read an entry: the signature is the **Linux build's** (real parameter names and types; STL types differ on Windows). Addresses are function addresses (RVA) in the symbol build and the current build.
*From Lua* says whether any Lua route reaches the function: **no**, **only indirectly** (a Lua method reaches it as a side effect, for example a city transfer), or **via the Community Extension**.
Entries marked ★ have notes from reading the decompiled code, each labelled verified or inferred.

| Namespace | Functions | Analysed |
|---|---|---|
%s
''' % (len(natives), len(natives) - n_an - n_ce, n_an, n_ce, len(findex['rows']), '\n'.join(rows)))
for ns, v in sorted(nby.items()):
    path = 'native/%s.md' % safe(ns)
    L = ['# %s\n' % ns, '| Function | Signature (Linux) | Symbol | Current | From Lua | Notes |', '|---|---|---|---|---|---|']
    for n in sorted(v, key=lambda x: x['id']):
        nm = n['id'][7:]
        sg = n['signatures'][0] if n['signatures'] else None
        sigtxt = '`%s %s(%s)`' % (sg['ret'], nm.split('@')[0], ', '.join(sg['params']).replace('|', '/')) if sg else '—'
        if sg and len(n['signatures']) > 1:
            sigtxt += ' (+%d overload%s)' % (len(n['signatures']) - 1, '' if len(n['signatures']) == 2 else 's')
        le = n['lua_exposure']
        lua = LUA_TXT[le['status']]
        if le['status'] == 'ce':
            lua = 'via CE: ' + ', '.join(link(c, path, c[3:]) for c in le['via'][:3])
        elif le['status'] == 'devce' and le.get('via'):
            lua = 'Dev CE (experimental): ' + ', '.join(link(c, path, c[6:]) for c in le['via'][:2])
        elif le['status'] == 'indirect' and le.get('via'):
            lua = 'only indirectly (' + ', '.join('`%s`' % x for x in le['via'][:2]) + ')'
        tags = ', '.join(n.get('tags', []))
        L.append('| <a id="%s"></a>%s%s | %s | %s | %s | %s | %s |' % (safe(nm).lower(), nm.split('::', 1)[-1] if '::' in nm else nm, ' ★' if 'analysis' in n else '', sigtxt,
                 rva(n['builds'], 'symbol'), rva(n['builds'], 'current'), lua, tags))
    an = [n for n in v if 'analysis' in n]
    if an:
        L.append('\n## Notes (★)\n')
        for n in an:
            L.append('### %s\n' % n['id'][7:])
            L.append(notes_md({'summary': n['analysis']['summary'], 'notes': n['analysis']['notes']}, path) + '\n')
    add(path, ns, '\n'.join(L))

# ---------------------------------------------------------------- full function index page
fc = {}
for r in findex['rows']:
    c = fc.setdefault(r[4], [0, 0])
    c[0] += 1
    c[1] += 1 if r[2] else 0
CAT_DESC = {
    'lua-wrapper': 'The C++ side of a Lua method (every method in the Lua API is one of these).',
    'game-logic': 'Game rules and state: players, cities, units, diplomacy, religion, trade and so on.',
    'ai': 'Computer-player logic.',
    'ui-cache': 'The UI-side copy of game state and its event streams.',
    'database-definitions': 'Classes that load rows of the game database (the XML/SQL data).',
    'effects': 'The modifier system: effect, requirement and collection implementations.',
    'lua-glue': 'Helpers that connect game objects to Lua.',
    'template-instance': 'Instantiations of C++ templates (containers, serialization, delegates).',
    'library': 'Third-party and standard-library code (Lua VM, XML, SQLite, STL).',
    'compiler-generated': 'Static initializers, destructors and similar code the compiler writes.'}
frows = ['| %s | %s | %d | %d (%.0f%%) |' % (c, CAT_DESC[c], fc[c][0], fc[c][1], 100.0 * fc[c][1] / fc[c][0]) for c in findex['cats'] if c in fc]
add('native/all.md', 'All functions (search)', '''# All functions: searchable index

Every function of the symbol build (%d) with its address in both builds, a category and, where the name matches, the real signature from the Linux build. Use it to look up any function by name or address.
**Mapped** means the function was found in the current build (%d of them, %.0f%%); unmapped functions have no current address, mostly because they were compiler-generated or are template instances whose bytes changed.

Rows with ★ have a detailed entry in the [native functions](index.md) section. Search matches the name, the Lua method name, the signature and the addresses (for example `0x68d7f0`).

<div id="fnapp">Loading the function index (about 8 MB)…</div>

<script src="{{ROOT}}fnsearch.js"></script>

## What the categories mean

| Category | What it is | Functions | Mapped to the current build |
|---|---|---|---|
%s
''' % (len(findex['rows']), sum(1 for r in findex['rows'] if r[2]), 100.0 * sum(1 for r in findex['rows'] if r[2]) / len(findex['rows']), '\n'.join(frows)))

# ---------------------------------------------------------------- layouts
REL_TEXT = {'same': 'same on Windows', 'minus8': 'Windows = Linux − 8', 'differs': 'differs on Windows'}
lay_ids = {l['id'][7:] for l in layouts}
LAY_NOTE = ('Offsets are from the **Linux build** (debug info). Where a Windows offset was checked against Windows code it is shown in the *Windows* column '
            'with its relation to the Linux offset. For classes built from tracked variables the Windows offset is usually the Linux offset minus 8, '
            'but this is only stated where it was checked; plain classes are usually identical; classes holding STL containers can differ.')


def type_md(t, from_page):
    base = re.sub(r'^(const |volatile )+', '', t)
    base = re.sub(r'[*&\[\]0-9 ]+$', '', base)
    if base in lay_ids:
        return link('layout:' + base, from_page, t).replace('|', '\\|')
    return '`%s`' % t.replace('|', '\\|')


by_ns = {}
for l in layouts:
    parts = l['id'][7:].split('::')
    by_ns.setdefault(parts[0] if len(parts) > 1 else 'Other', []).append(l)
rows = ['| [%s](%s.md) | %d |' % (ns, safe(ns), len(ls)) for ns, ls in sorted(by_ns.items())]
add('layouts/index.md', 'Class layouts', '''# Class layouts

Member names, offsets and sizes of %d GameCore classes, taken from the Linux port's debug information. %s

| Namespace | Classes |
|---|---|
%s
''' % (len(layouts), LAY_NOTE, '\n'.join(rows)))
for ns, ls in sorted(by_ns.items()):
    lines = ['# %s\n' % ns, '| Class | Size | Members |', '|---|---|---|']
    for l in ls:
        p, _ = page_of(l['id'])
        lines.append('| %s%s | %d (0x%x) | %d |' % (link(l['id'], 'layouts/%s.md' % safe(ns), l['id'][7:]), ' ★' if 'curated' in l else '', l['size'], l['size'], len(l['members'])))
    add('layouts/%s.md' % safe(ns), ns, '\n'.join(lines))
    for l in ls:
        p, _ = page_of(l['id'])
        L = ['# %s\n' % l['id'][7:], '`%s` — %s, size %d bytes (0x%x).\n' % (l['cpp'], l['kind'], l['size'], l['size'])]
        if l['bases']:
            L.append('**Bases:** ' + ', '.join((link('layout:' + b['name'], p, b['name']) if b['name'] in lay_ids else '`%s`' % b['name']) + ' at 0x%x' % b['offset'] for b in l['bases']) + '\n')
        if 'curated' in l:
            L.append(notes_md(l['curated'], p) + '\n')
        has_win = any('windows' in m for m in l['members'])
        L.append('| Linux offset | Member | Type |' + (' Windows |' if has_win else ''))
        L.append('|---|---|---|' + ('---|' if has_win else ''))
        for m in sorted(l['members'], key=lambda x: (x['offset'], x['name'])):
            w = ''
            if has_win:
                if 'windows' in m:
                    wi = m['windows']
                    w = ' `%s` (%s; %s) |' % (wi['offset'], REL_TEXT[wi['relation']], wi['status'])
                else:
                    w = ' |'
            bits = ' (bit-field, %d bits)' % m['bits'] if m.get('bits') else ''
            L.append('| `0x%x` | %s%s | %s |%s' % (m['offset'], m['name'], bits, type_md(m['type'], p), w))
        if has_win:
            L.append('\nThe Windows column is filled in only for members that were checked against Windows code. For the rest, use the Linux offset with the rule above.')
        add(p, l['id'][7:], '\n'.join(L))

# ---------------------------------------------------------------- globals
gby = {}
for g in globs:
    parts = g['id'][7:].split('::')
    gby.setdefault(parts[0] if len(parts) > 1 else 'Other', []).append(g)
add('globals/index.md', 'Globals', '''# Global variables

%d named global and static variables that exist in both the Linux port (name and type) and the symbol build (name and address), with their address in the current build.
Status **verified** means the address map rests on at least two references and a clear vote; otherwise it is **inferred**. Sizes are Linux sizes and can differ on Windows for STL-based types.

| Group | Variables |
|---|---|
%s
''' % (len(globs), '\n'.join('| [%s](%s.md) | %d |' % (g, safe(g), len(v)) for g, v in sorted(gby.items()))))
for grp, gs in sorted(gby.items()):
    p = 'globals/%s.md' % safe(grp)
    L = ['# %s\n' % grp, '| Name | Type | Size | Section | Symbol | Current | Status |', '|---|---|---|---|---|---|---|']
    for g in gs:
        nm = g['id'][7:]
        L.append('| <a id="%s"></a>%s%s | %s | %s | %s | %s | %s | %s |' % (safe(nm).lower(), nm.split('::', 1)[-1] if '::' in nm else nm, ' ★' if 'curated' in g else '',
                 type_md(g['type'], p), g['size'] if g['size'] is not None else '—', g['section'], rva(g['builds'], 'symbol'), rva(g['builds'], 'current'), g['status']))
    cur = [g for g in gs if 'curated' in g]
    if cur:
        L.append('\n## Notes (★)\n')
        for g in cur:
            L.append('### %s\n' % g['id'][7:])
            L.append(notes_md(g['curated'], p) + '\n')
    add(p, grp, '\n'.join(L))

# ---------------------------------------------------------------- index
n_ref = sum(1 for m in methods if m['in_community_reference'])
topic_lines = '\n'.join('- [%s](%s)' % (t, p) for _, p, t in sorted(topics))
n_ce_nat = sum(1 for n in natives if n['lua_exposure']['status'] == 'ce')
add('index.md', 'Civ VI GameCore reference', '''# Civilization VI GameCore reference

A reference for what Civ VI's GameCore contains, generated from analysis data plus short hand-written notes. **Everything is labelled by how you can use it:**

<div class="zone zone-vanilla"><b>Available out of the box.</b> Usable from Lua in the unmodified game.</div>

- [Lua API](lua/index.md): %d methods on %d objects (%d also appear in the community reference, %d do not).
- [Operations and commands](operations/index.md): %d identified, with handlers, parameters and addresses.
- [Enums and constants](enums/index.md): Lua constant tables with their hashes, and [Lua events](enums/LuaEvents.md) with their parameters.

<div class="zone zone-ce"><b>Needs the Community Extension.</b> Not available in the unmodified game; works while the Community Extension mod is active.</div>

- [Community Extension Lua API](ce/index.md): %d functions the extension adds.
- [Class layouts](layouts/index.md): %d classes with member offsets, for raw memory access (`ObjMem`).
- [Globals](globals/index.md): %d typed global variables with addresses, for `Mem`.

<div class="zone zone-engine"><b>Engine internals.</b> No scripting access today; listed for contributors and for understanding the game.</div>

- [Native functions](native/index.md): %d engine functions without a Lua route (%d already wrapped by the Community Extension).
- Engine ids such as the [event ids](enums/Events.md) are listed for decoding hash values.

## Start here
%s

## Standing on the shoulders of giants

This reference exists because other people did the hard part first.

- **[Sukrit Tan's Civilization VI Modding Wiki](https://sukritact.github.io/civilization-modding-wiki/)** (built from the [Civilization VI Modding Knowledge Base](https://github.com/Sukritact/Civilization-VI-Modding-Knowledge-Base)) is the community's Lua reference and the standard to match. We use it to mark which Lua methods it already documents, to check our recovered signatures against it, and as the target of the "community reference" links. **We do not copy its descriptions.** Where it has a page for a method we link to it, so the explanation is one click away. To learn what a method is for, start there.
- **[The Civilization VI Modding Companion 2.0](https://docs.google.com/spreadsheets/d/1EiCTOlPx3IkeAmU0xujGEp9k0v9VuCxe95OcrsyWOVs/edit?usp=sharing)**, created by **ChimpanG** and expanded and maintained by **WildW**, is a long-standing spreadsheet of Lua objects, events and constants. We take two things from it: the parameter names and types of Lua events, and the Lua names of 19 constant tables (matched to engine enums by value). Both are credited on their pages. The Companion also covers UI, input and network tables that live outside GameCore, which we do not; use it for those.
- **The [Civilization VI Community Extension](https://github.com/Wild-W/CivilizationVI_CommunityExtension)** by Wild-W and contributors showed that GameCore can be extended, and documents its additions on its [wiki](https://github.com/Wild-W/CivilizationVI_CommunityExtension/wiki). We read its source and wiki for the function list and the engine addresses it targets, and link each of its functions to the engine function it wraps. Descriptions stay on their wiki.
- **The game's own Lua scripts** are read to work out what arguments and return values mean. We publish only short call-site snippets, not the scripts.
- **Tools:** the NSA's Ghidra, pyelftools and pefile, and Steam's depot downloads, which gave us an older Linux build that still carries debug symbols.

Errors in this reference are ours. Corrections and pointers to better sources are welcome.

*Generated %s. Builds covered: %s.*
''' % (len(methods), len(objects), n_ref, len(methods) - n_ref, len(ops), len(ce_methods), len(layouts), len(globs), len(natives), n_ce_nat,
       topic_lines, datetime.date.today().isoformat(), '; '.join(b_['id'] for b_ in builds)))


# ---------------------------------------------------------------- breadcrumbs
SECTION = {'lua': ('lua/index.md', 'Lua API'), 'operations': ('operations/index.md', 'Operations'), 'enums': ('enums/index.md', 'Enums'),
           'layouts': ('layouts/index.md', 'Class layouts'), 'globals': ('globals/index.md', 'Globals'),
           'ce': ('ce/index.md', 'Community Extension'), 'devce': ('devce/index.md', 'Dev CE (experimental)'), 'native': ('native/index.md', 'Native functions')}


def parents(path):
    """Ordered list of (page, title) ancestors of a page, excluding the page itself and Home."""
    parts = path[:-3].split('/')
    if len(parts) == 1:
        return []
    sec = SECTION[parts[0]]
    chain = [sec] if path != sec[0] else []
    if parts[0] == 'operations' and len(parts) == 3:
        chain.append(('operations/%s.md' % parts[1], pages['operations/%s.md' % parts[1]][0]))
    if parts[0] == 'layouts' and len(parts) == 3:
        chain.append(('layouts/%s.md' % parts[1], parts[1]))
    if parts[0] == 'globals' and path != 'globals/index.md':
        pass
    return chain


ZONE_TEXT = {
    'vanilla': '<b>Available out of the box.</b> Usable from Lua in the unmodified game.',
    'ce': '<b>Needs the Community Extension.</b> Not available in the unmodified game; works while the Community Extension mod is active (its own functions, or raw memory access with <code>Mem</code>/<code>ObjMem</code>).',
    'devce': '<b>Experimental: needs the Dev CE test build.</b> A development GameCore that adds these Lua methods by calling engine functions directly. Not part of the Community Extension, not released, single-player testing only. Descriptions on these pages were written by an AI assistant from decompiled code and are marked inferred unless a test result confirms them.',
    'engine': '<b>Engine internals.</b> No scripting access today. Listed for contributors and for understanding the game; using it needs a change to the game library.'}


def zone_of(path):
    top = path.split('/')[0]
    if path == 'enums/Events.md':
        return 'engine'
    return {'lua': 'vanilla', 'operations': 'vanilla', 'enums': 'vanilla', 'ce': 'ce', 'devce': 'devce', 'layouts': 'ce', 'globals': 'ce', 'native': 'engine'}.get(top)


def banner_md(path):
    z = zone_of(path)
    return '<div class="zone zone-%s">%s</div>\n\n' % (z, ZONE_TEXT[z]) if z and path not in ('enums/index.md',) else ''


def crumbs_md(path):
    if path == 'index.md':
        return ''
    cs = [('index.md', 'Home')] + parents(path)
    out = ' › '.join('[%s](%s)' % (t, os.path.relpath(pp, os.path.dirname(path) or '.').replace('\\', '/')) for pp, t in cs)
    return out + ' › %s\n\n' % pages[path][0] + banner_md(path)

# ---------------------------------------------------------------- write docs
shutil.rmtree(B('docs'), ignore_errors=True)
for p, (t, text) in pages.items():
    fp = B('docs', p); os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, 'w', encoding='utf8').write(crumbs_md(p) + text)
print('wrote %d markdown pages' % len(pages))

# ---------------------------------------------------------------- html
CSS = '''body{font:16px/1.55 system-ui,sans-serif;margin:0;color:#1d2330;background:#fff}
nav{position:fixed;top:0;bottom:0;left:0;width:210px;padding:16px;background:rgba(127,127,127,.08);overflow:auto;box-sizing:border-box}
main{margin-left:210px;padding:16px 28px}main>p,main>ul,main>ol,main>blockquote,main>h1,main>h2,main>h3,main>pre,main>.zone{max-width:90ch}
@media(max-width:700px){nav{position:static;width:auto}main{margin:0;padding:16px}}
table{border-collapse:collapse;margin:1em 0;font-size:14px;width:100%}td,th{border:1px solid #ccd;padding:4px 8px;text-align:left;vertical-align:top}th{background:#eef;position:sticky;top:0}tbody tr:nth-child(even) td{background:rgba(127,127,127,.06)}td code{white-space:normal;overflow-wrap:anywhere}td{overflow-wrap:anywhere}@media(max-width:900px){table{display:block;overflow-x:auto}}
code,pre{background:#f3f4f8;color:#1d2330;border-radius:4px}code{padding:1px 4px}pre{padding:10px;overflow-x:auto}pre code{background:none;padding:0}
#q{width:100%;box-sizing:border-box;padding:8px;margin:6px 0;font-size:15px}nav a{display:block}nav.searching>*:not(b):not(#q):not(#res){display:none}#res:empty{display:none}#res{border:1px solid #9aa4bd;border-radius:6px;background:#fff;box-shadow:0 4px 14px rgba(0,0,0,.18);padding:4px;max-height:78vh;overflow-y:auto}#res .cnt{font-size:12px;color:#667;padding:2px 6px 4px}#res a{display:block;font-size:14px;padding:5px 7px;border-radius:4px;color:inherit;text-decoration:none;border-bottom:1px solid rgba(127,127,127,.15)}#res a small{display:block;font-size:11px;opacity:.7}#res a:hover,#res a.sel{background:#dbe6ff}#res mark{background:#ffe27a;color:inherit;padding:0}\n.zone{border-left:5px solid;padding:8px 12px;margin:10px 0 16px;border-radius:4px}.zone-vanilla{border-color:#2a9d4a;background:rgba(42,157,74,.13)}.zone-ce{border-color:#d9922b;background:rgba(217,146,43,.15)}.zone-engine{border-color:#8a8f99;background:rgba(138,143,153,.18)}.zone-devce{border-color:#8b5cf6;background:rgba(139,92,246,.14)}\n.grp{font-size:12px;font-weight:600;margin:14px 0 4px;padding-left:6px;border-left:4px solid #888;text-transform:uppercase;letter-spacing:.03em}.g-vanilla{border-color:#2a9d4a}.g-ce{border-color:#d9922b}.g-engine{border-color:#8a8f99}.g-devce{border-color:#8b5cf6}
@media(prefers-color-scheme:dark){body{background:#14171d;color:#dde2ec}a{color:#8ab4ff}th{background:#222833}td,th{border-color:#333b4b}
code,pre{background:#222833;color:#e6e9f0}pre code{background:none}input{background:#1d222c;color:#dde2ec;border:1px solid #333b4b}#res{background:#1b2130;border-color:#4a5880}#res a:hover,#res a.sel{background:#2c3a5e}#res mark{background:#7a6512;color:#fff}#res .cnt{color:#9aa4bd}}'''
JS = '''let idx=null;const q=document.getElementById('q'),res=document.getElementById('res'),nav=q.parentNode;let sel=-1;
function mark(el,text,w){const lo=text.toLowerCase();let at=-1,len=0;for(const x of w){const k=lo.indexOf(x);if(k>=0){at=k;len=x.length;break}}
if(at<0){el.appendChild(document.createTextNode(text));return}el.appendChild(document.createTextNode(text.slice(0,at)));const m=document.createElement('mark');m.textContent=text.slice(at,at+len);el.appendChild(m);el.appendChild(document.createTextNode(text.slice(at+len)))}
function setSel(i){const a=res.querySelectorAll('a');if(!a.length)return;sel=(i+a.length)%a.length;a.forEach((x,k)=>x.classList.toggle('sel',k===sel));a[sel].scrollIntoView({block:'nearest'})}
q.addEventListener('keydown',e=>{if(e.key==='ArrowDown'){e.preventDefault();setSel(sel+1)}else if(e.key==='ArrowUp'){e.preventDefault();setSel(sel-1)}else if(e.key==='Enter'){const a=res.querySelectorAll('a');if(a.length)location.href=a[Math.max(sel,0)].href}else if(e.key==='Escape'){q.value='';q.dispatchEvent(new Event('input'))}});
document.addEventListener('keydown',e=>{if(e.key==='/'&&document.activeElement!==q&&!/INPUT|TEXTAREA|SELECT/.test((document.activeElement||{}).tagName||'')){e.preventDefault();q.focus()}});
q.addEventListener('input',async()=>{if(!idx){idx=await (await fetch(ROOT+'search.json')).json()}
const w=q.value.toLowerCase().trim().split(/\s+/).filter(Boolean);res.innerHTML='';sel=-1;
if(!w.length||q.value.trim().length<2){nav.classList.remove('searching');return}nav.classList.add('searching');
const hits=[];for(const e of idx){const h=((e.s||'')+'.'+e.t+' '+e.t+' '+(e.s||'')).toLowerCase();if(!w.every(x=>h.includes(x))&&!w.every(x=>e.k&&e.k.includes(x)))continue;
const t=e.t.toLowerCase(),f=w.join(' ');let r=t===f?0:(t.startsWith(f)||((e.s||'')+'.'+e.t).toLowerCase().startsWith(f))?1:t.endsWith('.'+f)||t.endsWith('::'+f)?2:t.includes(f)?3:w.every(x=>h.includes(x))?4:5;if(e.s&&r<5)r+=0.5;hits.push([r,e])}
hits.sort((a,b)=>a[0]-b[0]);const n=hits.length;
const c=document.createElement('div');c.className='cnt';c.textContent=n?(n>60?'Showing 60 of '+n+' matches':n+(n==1?' match':' matches')):'No match. For engine functions try All functions (search).';res.appendChild(c);
hits.slice(0,60).forEach(([r,e])=>{const a=document.createElement('a');a.href=ROOT+e.u;mark(a,e.t,w);if(e.s){const s=document.createElement('small');s.textContent=e.s;a.appendChild(s)}res.appendChild(a)});if(n)setSel(0)});
(function(){const f=new URLSearchParams(location.search).get('find');if(!f)return;const h=f.toLowerCase();
for(const td of document.querySelectorAll('main td:first-child')){if(td.textContent.trim().toLowerCase()===h){td.scrollIntoView({block:'center'});td.parentElement.style.outline='2px solid #d9922b';break}}})();'''
shutil.rmtree(B('site'), ignore_errors=True)
os.makedirs(B('site'))
FNJS = open(B('tools', 'fnsearch.js'), encoding='utf8').read()
open(B('site', 'style.css'), 'w').write(CSS)
open(B('site', 'search.js'), 'w').write(JS)
search = []
for p, (t, text) in pages.items():
    body = markdown.markdown(crumbs_md(p) + text, extensions=['tables', 'fenced_code', 'attr_list'])
    body = body.replace('{{ROOT}}', '../' * p.count('/'))
    body = re.sub(r'href="([^"#:]+)\.md(#[^"]*)?"', lambda m: 'href="%s.html%s"' % (m.group(1), m.group(2) or ''), body)
    depth = p.count('/'); root = '../' * depth
    def grp(cls, title, items):
        return '<div class="grp %s">%s</div>' % (cls, title) + ''.join('<a href="%s%s">%s</a>' % (root, l, n) for l, n in items)
    nav = (grp('', 'Start', (('index.html', 'Home'), ('conventions.html', 'How to read'), ('hash-function.html', 'Identifier hash')))
           + grp('g-vanilla', 'Available now', (('lua/index.html', 'Lua API'), ('operations/index.html', 'Operations'), ('enums/index.html', 'Enums')))
           + grp('g-ce', 'Needs the Community Extension', (('ce/index.html', 'CE Lua API'), ('layouts/index.html', 'Class layouts'), ('globals/index.html', 'Globals')))
           + grp('g-devce', 'Experimental', (('devce/index.html', 'Dev CE Lua API'),))
           + grp('g-engine', 'Engine internals', (('native/index.html', 'Native functions'), ('native/all.html', 'All functions (search)'))))
    page = ('<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>%s</title>'
            '<style>%s</style><nav><b>GameCore reference</b><input id=q placeholder="Search methods, functions...  ( / )" type=search>'
            '<div id=res></div>%s</nav><main>%s</main><script>const ROOT="%s";</script><script src="%ssearch.js"></script>') % (
            html.escape(t), CSS, nav, body, root, root)
    fp = B('site', p[:-3] + '.html'); os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, 'w', encoding='utf8').write(page)
    search.append({'t': t, 'u': p[:-3] + '.html', 'k': re.sub(r'[#|`*\[\]()]', ' ', text[:300]).lower()})
    sect = {'lua': 'Lua API', 'ce': 'CE', 'devce': 'Dev CE', 'native': 'Native', 'operations': 'Operation', 'enums': 'Enum', 'globals': 'Global'}.get(p.split('/')[0])
    if sect and p.count('/') and not p.endswith('index.md') and not p.startswith('layouts'):
        for row in re.findall(r'<tr>\s*<td>(.*?)</td>', body, re.S):
            m = re.match(r'<a id="([^"]+)"></a>', row)
            name = html.unescape(re.sub(r'<[^>]+>', '', row)).strip()
            if not name or len(name) > 120: continue
            u = p[:-3] + '.html' + ('#' + m.group(1) if m else '?find=' + urllib.parse.quote(name))
            search.append({'t': name, 'u': u, 's': t if sect in ('Lua API', 'Native', 'Enum') or p.count('/') > 1 else sect})
json.dump(search, open(B('site', 'search.json'), 'w'))
shutil.copy(B('data', 'function_index.json'), B('site', 'function_index.json'))
open(B('site', 'fnsearch.js'), 'w', encoding='utf8').write(FNJS)
print('wrote html site (%d pages)' % len(pages))

# ---------------------------------------------------------------- dist
os.makedirs(B('dist', 'ai'), exist_ok=True)
for name, data in (('lua_methods.json', methods), ('operations.json', ops), ('enums.json', enums), ('lua_objects.json', objects), ('layouts.json', layouts), ('globals.json', globs), ('ce_methods.json', ce_methods), ('devce_methods.json', devce), ('native.json', natives), ('function_index.json', findex), ('op_params.json', op_params), ('lua_return_meanings.json', ret_meanings), ('lua_arg_meanings.json', arg_meanings), ('lua_runtime_checks.json', rt_checks)):
    json.dump(data, open(B('dist', name), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump({'generated': datetime.date.today().isoformat(), 'builds': builds, 'schema': 'schema/entities.schema.json',
           'counts': {'lua_methods': len(methods), 'operations': len(ops), 'enums': len(enums), 'layouts': len(layouts), 'globals': len(globs), 'ce_methods': len(ce_methods), 'native': len(natives)}},
          open(B('dist', 'manifest.json'), 'w'), indent=1)
with open(B('dist', 'ai', 'operations.txt'), 'w', encoding='utf8') as f:
    f.write('# Civ VI operations and commands. One line per entry: id | lua | hash | handler | parameters | events | status | summary\n')
    for o in ops:
        s = (o.get('curated', {}).get('summary') or '').replace('\n', ' ')
        h = ' / '.join(x.get('class', x.get('function', '')) for x in o['handlers'])
        f.write(' | '.join([o['id'], o['lua'], o['hash'], h, ','.join(p['name'] for p in o['parameters']), ','.join(o['events']), o['status'], s]) + '\n')
with open(B('dist', 'ai', 'lua_api.txt'), 'w', encoding='utf8') as f:
    f.write('# Civ VI Lua methods registered by GameCore, grouped by object. One method per line: [where: g=gameplay u=ui-cache] [*=documented in community reference] signature. '
            'Signature: ":" instance method, "." static; name?: optional argument; a trailing ? = partly understood; types are Lua types, C++ enum type in [].\n')
    for o, ms in by_obj.items():
        f.write('## %s\n' % o)
        for m in ms:
            where = ('g' if 'gameplay' in m['registered_on'] else '') + ('u' if 'ui-cache' in m['registered_on'] else '')
            sg = (m.get('signatures') or [None])[0]
            txt = sig_text(o, m, sg).replace(' ⚠', ' ?') if sg else '%s:%s(?)' % (o, m['method'])
            rmn = m.get('return_meaning')
            amp = [p for p in (m['signatures'][0]['params'] if m.get('signatures') else []) if p.get('meaning')]
            f.write('%s%s %s%s\n' % (where, '*' if m['in_community_reference'] else '', txt, ((' # args: ' + '; '.join('%s=%s' % (p['name'], p['meaning']['summary']) for p in amp)) if amp else '') + ((' # returns: ' + rmn['summary'] + ('' if rmn['status'] == 'verified' else ' (inferred)')) if rmn else '')))
with open(B('dist', 'ai', 'enums.txt'), 'w', encoding='utf8') as f:
    for e in enums:
        f.write('## %s (%s)\n' % (e['id'], e['cpp_type']))
        f.write(' '.join('%s=%s%s' % (m['name'], m['hash'], ('(' + ','.join('%s:%s' % (q['name'], q['type']) for q in m['parameters']) + ')') if m.get('parameters') else '') for m in e['members']) + '\n')
with open(B('dist', 'ai', 'layouts.txt'), 'w', encoding='utf8') as f:
    f.write('# Class layouts (Linux offsets; "w=" gives a checked Windows offset). One block per class: name size; then offset name:type\n')
    for l in layouts:
        f.write('%s size=%d\n' % (l['id'][7:], l['size']))
        f.write(' '.join('0x%x:%s:%s%s' % (m['offset'], m['name'], m['type'].replace(' ', ''), ('[w=%s]' % m['windows']['offset']) if 'windows' in m else '') for m in sorted(l['members'], key=lambda x: x['offset'])) + '\n')
with open(B('dist', 'ai', 'globals.txt'), 'w', encoding='utf8') as f:
    f.write('# Globals: name | type | symbol rva | current rva | status\n')
    for g in globs:
        f.write(' | '.join([g['id'][7:], g['type'], g['builds']['symbol']['rva'], g['builds']['current']['rva'] or '-', g['status']]) + '\n')
with open(B('dist', 'ai', 'ce_api.txt'), 'w', encoding='utf8') as f:
    f.write('# Lua API added by the Community Extension (works only with that mod). Signature | engine function | current rva\n')
    for m in ce_methods:
        for sg in m['signatures']:
            ps = ', '.join('%s: %s' % (p['name'], p['type']) for p in sg['params'])
            f.write('%s%s%s(%s)%s | %s | %s\n' % (m['object'], '.' if m['static'] else ':', m['method'], ps, (' -> ' + ', '.join(sg['returns'])) if sg['returns'] else '',
                    (m['native'] or '-')[7:], m['builds']['current']['rva'] or '-'))
with open(B('dist', 'ai', 'devce_api.txt'), 'w', encoding='utf8') as f:
    f.write('# Lua methods of the EXPERIMENTAL Dev CE test build (not released). Signature | engine function | current rva | tests | purpose (AI-written from decompiled code, inferred)\n')
    for m in devce:
        sg = m['signatures'][0]
        ps = ', '.join('%s: %s' % (p['name'], p['lua_type']) for p in sg['params'])
        t = m['tests']
        f.write('%s:%s(%s)%s | %s | %s | plumbing=%s%s | %s\n' % (m['object'], m['method'], ps, (' -> ' + ', '.join(sg['returns'])) if sg['returns'] else '', (m['native'] or '-')[7:], m['builds']['current']['rva'],
                t.get('plumbing'), ' effect-verified' if m['status'] == 'verified' else '', ((m.get('analysis') or {}).get('purpose') or '-').replace('\n', ' ')))
with open(B('dist', 'ai', 'native.txt'), 'w', encoding='utf8') as f:
    f.write('# Engine functions without a Lua route. Class::function | linux signature | symbol rva | current rva | from-lua | analysed\n')
    for n in natives:
        sg = n['signatures'][0] if n['signatures'] else None
        f.write(' | '.join([n['id'][7:], ('%s(%s)' % (sg['ret'], ', '.join(sg['params']))) if sg else '-', n['builds']['symbol']['rva'], n['builds']['current']['rva'] or '-',
                            n['lua_exposure']['status'], 'yes' if 'analysis' in n else 'no']) + '\n')
open(B('dist', 'ai', 'README.txt'), 'w').write('Files: lua_api.txt (out of the box), operations.txt, enums.txt, ce_api.txt (needs the Community Extension), layouts.txt and globals.txt (needs CE memory access), native.txt (engine internals, no Lua route). Hash = ~crc32(upper-case name). Full records with evidence: ../operations.json, ../lua_methods.json, ../enums.json.\n')
print('wrote dist')
