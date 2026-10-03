"""Event parameter names and types from the Civ VI Modding Companion 2.0 (ChimpanG, expanded and maintained by WildW), matched to our
Events enum. Reads linux_depot/out/companion.json (tools/companion_parse.py) and writes data/event_params.json keyed by our member name.
Run before extract.py. Nothing but names, types and order is taken from the sheet."""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
comp = json.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'companion.json'), encoding='utf8'))['events']
ours = []
for l in open(os.path.join(ROOT, 'linux_depot', 'out', 'enums.jsonl'), encoding='utf8'):
    j = json.loads(l)
    if j['name'] == 'GameCore::Events::EventTypes':
        ours = [n for n, _ in j['values']]
norm = lambda s: s.replace('_', '').upper()
sheet = {norm(n): n for n in comp}
out = {}
for n in ours:
    s = sheet.get(norm(n))
    if not s:
        continue
    e = comp[s]
    if not e['params'] and e['header_type'] not in ('GameCoreEvent', 'PlayerGameCoreEvent'):
        continue
    out[n] = {'sheet_name': s, 'event_kind': e['header_type'] or 'unspecified',
              'parameters': [{'name': p['name'], 'type': (p['type'] or '').lstrip(':') or 'unspecified'} for p in sorted(e['params'], key=lambda p: p['order'] or 0)]}
json.dump(out, open(os.path.join(ROOT, 'docs_proto', 'data', 'event_params.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print('events matched', len(out), 'with parameters', sum(1 for v in out.values() if v['parameters']), 'parameter rows', sum(len(v['parameters']) for v in out.values()))
