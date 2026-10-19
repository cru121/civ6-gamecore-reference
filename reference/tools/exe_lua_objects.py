"""Name the Lua tables registered by the engine exe, from how the game's own Lua scripts use them.
Input : findings/tables/exe_lua_methods_windows.tsv (register_fn_rva, interface, lua_method, wrapper_rva), the game's Lua files.
Method: for every registering function, count `Name.method(` / `Name:method(` call sites in the game's scripts whose method is registered by that
        function; the identifier with the most distinct matching methods names the table.
Output: data/exe_lua_group_names.json {register_fn_rva: {name, matched, methods, uses, runner_up}}
"""
import collections, csv, json, os, re, sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"

groups = collections.OrderedDict()
for r in csv.DictReader(open(os.path.join(ROOT, 'findings', 'tables', 'exe_lua_methods_windows.tsv'), encoding='utf8'), delimiter='\t'):
    g = groups.setdefault(r['register_fn_rva'], {'interface': r['interface'], 'methods': set()})
    g['methods'].add(r['lua_method'])

CALL = re.compile(r'\b([A-Za-z_]\w*)\s*[.:]\s*([A-Za-z_]\w*)\s*\(')
uses = collections.defaultdict(collections.Counter)      # (name, method) -> files count
files = 0
for root, _, fs in os.walk(GAME):
    for f in fs:
        if not f.lower().endswith('.lua'):
            continue
        try:
            t = open(os.path.join(root, f), encoding='utf8', errors='replace').read()
        except OSError:
            continue
        files += 1
        for m in CALL.finditer(t):
            uses[(m.group(1), m.group(2))][f] += 1
print('lua files', files, 'distinct (name, method) pairs', len(uses))

by_name = collections.defaultdict(dict)                     # name -> {method: total uses}
for (n, m), c in uses.items():
    by_name[n][m] = sum(c.values())

out = {}
for rva, g in groups.items():
    ms = g['methods']
    if len(ms) < 4:
        continue
    scored = []
    for n, d in by_name.items():
        hit = [m for m in d if m in ms]
        if len(hit) >= 3:
            scored.append((len(hit), sum(d[m] for m in hit), n, sorted(hit)))
    scored.sort(reverse=True)
    if not scored:
        continue
    top = scored[0]
    out[rva] = {'interface': g['interface'], 'name': top[2], 'matched': top[0], 'of': len(ms), 'uses': top[1], 'methods': top[3][:12],
                'runner_up': [(s[2], s[0]) for s in scored[1:3]]}
json.dump(out, open(os.path.join(BASE, 'data', 'exe_lua_group_names.json'), 'w', encoding='utf8'), indent=1)
print(len(out), 'groups named')
for rva, v in sorted(out.items(), key=lambda kv: -len(groups[kv[0]]['methods']))[:45]:
    print(rva, v['interface'].split('::')[-2:] if '::' in v['interface'] else v['interface'], '->', v['name'], '%d/%d' % (v['matched'], v['of']), v['runner_up'])
