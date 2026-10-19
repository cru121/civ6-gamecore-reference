"""Input actions: the InputActions / InputCategories / InputContexts / InputActionDefaultGestures / InputKeyData rows of the Configuration database (base game and DLC XML), the actions the exe registers
by name in code (App::InputAction::Manager::SetupActions, 0x3b7f0) and how the game's Lua uses them (Input.GetActionId and friends).
Input : the game's Configuration XML files (all .xml with Input* tables, read in place; ids, localisation keys and gesture type names only), linux_depot/out/strmaps.pkl (SetupActions strings),
        the game's Lua files (argument of Input.GetActionId and counts)
Output: data/exe_input.json (entities exeinput:<kind>:<id>), data/exe_input_meta.json."""
import collections, glob, json, os, pickle, re
import xml.etree.ElementTree as ET

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
TABLES = ('InputCategories', 'InputContexts', 'InputActions', 'InputActionDefaultGestures', 'InputKeyData')
OPS = ('Row', 'Replace', 'InsertOrIgnore', 'InsertOrAbort')

rows = {t: [] for t in TABLES}
sources = collections.defaultdict(list)
for dp, dn, fn in os.walk(GAME):
    for f in fn:
        if not f.lower().endswith('.xml'):
            continue
        p = os.path.join(dp, f)
        try:
            head = open(p, 'rb').read(400000).decode('utf8', 'replace')
        except Exception:
            continue
        if not any('<%s>' % t in head or '<%s ' % t in head for t in TABLES):
            continue
        try:
            root = ET.parse(p).getroot()
        except ET.ParseError:
            continue
        rel = os.path.relpath(p, GAME).replace('\\', '/')
        src = 'Base' if rel.startswith('Base/') else rel.split('/')[1] if rel.startswith('DLC/') else rel.split('/')[0]
        for t in root:
            if t.tag in TABLES:
                for r in t:
                    if r.tag in OPS:
                        d = dict(r.attrib)
                        for c in r:
                            d[c.tag] = (c.text or '').strip()
                        d['_src'] = src
                        d['_op'] = r.tag
                        rows[t.tag].append(d)
                sources[t.tag].append(rel)

# the same row can come from several expansions (InsertOrIgnore twice): keep one row per id and list all sources
KEYS = {'InputCategories': 'CategoryId', 'InputContexts': 'ContextId', 'InputActions': 'ActionId', 'InputKeyData': 'KeyId'}
for t, k in KEYS.items():
    merged = collections.OrderedDict()
    for r in rows[t]:
        if r[k] in merged:
            merged[r[k]]['_srcs'].append(r['_src'])
        else:
            r['_srcs'] = [r['_src']]
            merged[r[k]] = r
    rows[t] = list(merged.values())

# the actions the exe names in code
ws, ls, wm, lm = pickle.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'strmaps.pkl'), 'rb'))
rva = None
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    if r[0].startswith('App::InputAction::Manager::SetupActions(') and r[2]:
        rva = int(r[2].split(',')[0], 16)
exe_names = sorted({(s.decode('latin1') if isinstance(s, bytes) else s) for a, s in ws.items() if rva in wm.get(a, ()) and re.match(r'^[A-Z][A-Za-z]+$', s.decode('latin1') if isinstance(s, bytes) else s)})

# Lua usage
GET = re.compile(r'Input\.GetActionId\(\s*"([^"]+)"')
uses = collections.Counter()
use_files = collections.defaultdict(set)
for dp, dn, fn in os.walk(GAME):
    for f in fn:
        if f.lower().endswith('.lua'):
            try:
                s = open(os.path.join(dp, f), encoding='utf8', errors='replace').read()
            except Exception:
                continue
            for m in GET.finditer(s):
                uses[m.group(1)] += 1
                use_files[m.group(1)].add(f)

gest = collections.defaultdict(list)
for g in rows['InputActionDefaultGestures']:
    gest[g.get('ActionId')].append({'index': int(g.get('Index', 0) or 0), 'type': g.get('GestureType'), 'data': g.get('GestureData')})
ctx_value = {c['ContextId']: int(c.get('Value', 0) or 0) for c in rows['InputContexts']}
ents = []
for c in rows['InputCategories']:
    n = sum(1 for a in rows['InputActions'] if a.get('CategoryId') == c['CategoryId'])
    ents.append({'id': 'exeinput:category:%s' % c['CategoryId'], 'kind': 'category', 'name': c['CategoryId'], 'source': ', '.join(c['_srcs']), 'name_key': c.get('Name'), 'visible': c.get('Visible'), 'sort_index': c.get('SortIndex'),
                 'actions': n, 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'game-script', 'note': 'InputCategories row in the %s configuration XML (ids and keys only)' % c['_src']}]})
for c in rows['InputContexts']:
    n = sum(1 for a in rows['InputActions'] if a.get('ContextId') == c['ContextId'])
    ents.append({'id': 'exeinput:context:%s' % c['ContextId'], 'kind': 'context', 'name': c['ContextId'], 'source': c['_src'], 'value': ctx_value[c['ContextId']], 'actions': n,
                 'availability': 'exe', 'status': 'verified', 'evidence': [{'kind': 'game-script', 'note': 'InputContexts row in the %s configuration XML' % c['_src']}]})
for a in rows['InputActions']:
    aid = a['ActionId']
    ents.append({'id': 'exeinput:action:%s' % aid, 'kind': 'action', 'name': aid, 'source': ', '.join(a['_srcs']), 'name_key': a.get('Name'), 'description_key': a.get('Description'), 'category': a.get('CategoryId'),
                 'context': a.get('ContextId'), 'layout': a.get('LayoutType') or 'PC', 'gestures': sorted(gest.get(aid, []), key=lambda g: g['index']), 'script_uses': uses.get(aid, 0), 'script_files': len(use_files.get(aid, ())),
                 'availability': 'exe', 'status': 'verified', 'evidence': [{'kind': 'game-script', 'note': 'InputActions row in the %s configuration XML; use counted from Input.GetActionId arguments' % a['_src']}]})
keytypes = collections.Counter(k.get('KeyType') for k in rows['InputKeyData'])
for k in rows['InputKeyData']:
    ents.append({'id': 'exeinput:key:%s' % k['KeyId'], 'kind': 'key', 'name': k['KeyId'], 'source': k['_src'], 'key_type': k.get('KeyType'), 'name_key': k.get('KeyString'), 'icon': k.get('KeyIcon'),
                 'availability': 'exe', 'status': 'verified', 'evidence': [{'kind': 'game-script', 'note': 'InputKeyData row in the %s configuration XML' % k['_src']}]})
action_ids = {a['ActionId'] for a in rows['InputActions']}
meta = {'exe_names': exe_names, 'exe_rva': '0x%x' % rva, 'exe_names_in_db': sorted(set(exe_names) & action_ids), 'exe_names_not_in_db': sorted(set(exe_names) - action_ids), 'key_types': dict(keytypes),
        'scripts_unknown_actions': sorted(n for n in uses if n not in action_ids), 'unused_actions': sorted(a for a in action_ids if a not in uses), 'sources': {k: sorted(set(v)) for k, v in sources.items()},
        'gesture_types': dict(collections.Counter(g['type'] for gs in gest.values() for g in gs)), 'layouts': dict(collections.Counter(a.get('LayoutType') or 'PC' for a in rows['InputActions']))}
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_input.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(meta, open(os.path.join(BASE, 'data', 'exe_input_meta.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), dict(collections.Counter(e['kind'] for e in ents)))
for k in ('exe_names_in_db', 'exe_names_not_in_db', 'scripts_unknown_actions', 'unused_actions', 'gesture_types', 'layouts', 'key_types'):
    print(k, meta[k])
print(meta['sources'])
