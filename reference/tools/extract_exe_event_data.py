"""Event data fields as read by the exe's own handlers: for each GameCore bus event, the offsets and widths that handlers read from the event data object,
and the constants they compare fields against. Source: a Ghidra parameter trace of the Windows handlers (tools/TraceBatch.java, see docs_proto/README.md).
Input : linux_depot/out/exetrace/event_handlers_trace.jsonl, event_handlers_meta.json, data/exe_events.json (event names, Lua parameters)
Output: data/exe_event_data.json (entities exeevtdata:<event id>)."""
import collections, json, os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
T = os.path.join(ROOT, 'linux_depot', 'out', 'exetrace')
meta = json.load(open(os.path.join(T, 'event_handlers_meta.json')))
events = {e['event_id']: e for e in json.load(open(os.path.join(BASE, 'data', 'exe_events.json'), encoding='utf8')) if e['bus'] == 'GameCore'}
agg = collections.defaultdict(lambda: {'fields': collections.defaultdict(lambda: {'sizes': set(), 'readers': set(), 'cmps': set()}), 'handlers': [], 'failed': 0})
for l in open(os.path.join(T, 'event_handlers_trace.jsonl'), encoding='utf8'):
    j = json.loads(l)
    key = j['key'].split('|')
    eid = int(key[0][2:]); rva = key[1]
    a = agg[eid]
    if j['status'] != 'ok':
        a['failed'] += 1
        continue
    best = None
    member = not meta[rva]['system'].startswith('WorldView')       # member handlers take the event as parameter 1, WorldView handlers as parameter 0
    cands = []
    for p in j['params']:
        d = [e for e in p['events'] if e['k'] == 'read' and not e.get('path') and not e.get('via') and 0 <= e['off'] < 0x100]
        cands.append((p, d))
    order = ([1, 0] if member else [0, 1])
    for idx in order:
        if idx < len(cands) and cands[idx][1]:
            best = cands[idx]
            break
    if not best or not best[1]:
        a['failed'] += 1
        continue
    p, d = best
    a['handlers'].append({'rva': rva, 'system': meta[rva]['system'], 'param': p['i']})
    for e in d:
        f = a['fields'][e['off']]
        f['sizes'].add(e['size']); f['readers'].add(rva)
    for e in p['events']:
        if e['k'] == 'cmp' and not e.get('path') and not e.get('via') and e['off'] >= 0 and e.get('cst') is not None:
            a['fields'][e['off']]['cmps'].add(e['cst'])
ents = []
aligned = 0
for eid, a in sorted(agg.items()):
    if not a['fields']:
        continue
    ev = events.get(eid)
    offs = sorted(o for o in a['fields'] if a['fields'][o]['sizes'])
    if not offs:
        continue
    spans = [(o, max(a['fields'][o]['sizes'])) for o in offs]
    fields = []
    for o, sz in spans:
        if any(o2 < o < o2 + sz2 for o2, sz2 in spans):
            continue                                  # inside a wider read (for example a plot pair read as 8 bytes)
        f = a['fields'][o]
        fields.append({'offset': '0x%x' % o, 'widths': sorted(f['sizes']), 'handlers_reading': len(f['readers']),
                       'compared_with': sorted(f['cmps'])[:4]})
    params = (ev or {}).get('lua_parameters') or []
    # a Lua parameter list of the same length as the field list suggests the order; plots (x, y) read as one 8-byte field count twice
    expanded = []
    for f in fields:
        expanded.append(f)
    aligned_ok = bool(params) and len(params) == len(fields)
    if aligned_ok:
        aligned += 1
    ents.append({'id': 'exeevtdata:%d' % eid, 'event_id': eid, 'name': (ev or {}).get('name', 'event %d' % eid), 'data_type': (ev or {}).get('data_type'),
                 'fields': fields, 'handlers_analysed': len(a['handlers']), 'handlers_failed': a['failed'], 'handlers': a['handlers'][:6],
                 'lua_events': (ev or {}).get('lua_events', []), 'lua_parameters': [{'name': p['name'], 'type': p['type']} for p in params],
                 'order_matches_lua_parameters': aligned_ok, 'availability': 'exe', 'status': 'inferred',
                 'evidence': [{'kind': 'exe-disassembly', 'note': 'field reads recovered from the decompiled handlers (%d analysed); handler addresses of the WorldView system were matched by registration order' % len(a['handlers'])}]})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_event_data.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'events with field reads;', aligned, 'where the field count equals the Lua parameter count;', sum(len(e['fields']) for e in ents), 'fields')
