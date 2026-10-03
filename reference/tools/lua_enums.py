"""Lua constant tables that match an engine enum exactly (every member the Modding Companion lists has the same value in a debug-info enum
whose name resembles the table). Reads linux_depot/out/chimpang_enums.json (the Companion's Enums sheet) and linux_depot/out/enums.jsonl.
Writes data/lua_enums.json. Run before extract.py."""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ref = json.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'chimpang_enums.json')))
E = [json.loads(l) for l in open(os.path.join(ROOT, 'linux_depot', 'out', 'enums.jsonl'), encoding='utf8')]
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
out = []
for table, mem in ref.items():
    if len(mem) < 3:
        continue
    cands = [e for e in E if all(any(v == ev and norm(en).endswith(norm(n)) for en, ev in e['values']) for n, v in mem.items())]
    nk = norm(table)
    same = [e for e in cands if nk in norm(e['name']) or norm(e['name'].split('::')[-1]) in nk]
    if not same:
        continue
    e = min(same, key=lambda e: len(e['values']))
    listed = {}
    for n, v in mem.items():
        for en, ev in e['values']:
            if ev == v and norm(en).endswith(norm(n)):
                listed[en] = n
                break
    members = [{'name': n, 'value': v, **({'lua_key': listed[n]} if n in listed else {})} for n, v in e['values']]
    out.append({'table': table, 'cpp_type': e['name'], 'size': e['size'], 'companion_members': len(mem), 'members': members})
json.dump(out, open(os.path.join(ROOT, 'docs_proto', 'data', 'lua_enums.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(out), 'tables;', sum(len(o['members']) for o in out), 'members;', sum(o['companion_members'] for o in out), 'listed by the Companion')
for o in out:
    print(' ', o['table'], o['cpp_type'].replace('GameCore::', ''), len(o['members']), o['companion_members'], [m['name'] + '/' + m.get('lua_key', '-') for m in o['members'][:2]])
