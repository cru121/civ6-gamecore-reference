"""Validate recovered signatures against how the game's own Lua scripts call the methods (argument counts)."""
import json, os, re, collections

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
sig = json.load(open(os.path.join(ROOT, 'docs_proto', 'data', 'lua_signatures.json'), encoding='utf8'))
reg = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'lua_registry.tsv'), encoding='utf8') if l[0] != '#' and not l.startswith('interface')]

by_name = collections.defaultdict(list)
for r in reg:
    if r[4] in sig:
        by_name[r[2]].append((r[0], sig[r[4]]))
# keep names whose signatures are consistent across registrations (same parameter count)
unique = {n: v[0][1] for n, v in by_name.items() if len({len(x[1]['params']) for x in v}) == 1 and len({x[0].split('::')[-1].lstrip('I') for x in v}) <= 2}

cache = os.path.join(ROOT, 'linux_depot', 'out', 'lua_call_counts.json')
if os.path.exists(cache):
    calls = json.load(open(cache))
else:
    calls = collections.defaultdict(collections.Counter)
    call_re = re.compile(r'([:.])(\w+)\(([^()]*)\)')
    for base in ('Base/Assets', 'DLC'):
        for root, _, files in os.walk(os.path.join(GAME, base)):
            for f in files:
                if not f.endswith('.lua'):
                    continue
                t = open(os.path.join(root, f), encoding='utf8', errors='replace').read()
                for m in call_re.finditer(t):
                    if m.group(2) in unique:
                        a = m.group(3).strip()
                        n = 0 if not a else a.count(',') + 1 - a.count('{') * 0
                        calls[m.group(2)][str((m.group(1), n))] += 1
    json.dump(calls, open(cache, 'w'))

tot = ok = 0
bad = []
for name, cnt in calls.items():
    s = unique.get(name)
    if not s:
        continue
    params = s['params']
    req = sum(1 for p in params if not p['optional'])
    mx = len(params)
    for k, c in cnt.items():
        sep, n = eval(k)
        # a ':' call on an instance method passes self implicitly; '.' call on an instance method passes self explicitly
        if not s['static'] and sep == '.':
            n -= 1
        tot += c
        if req <= n <= mx + 1 and (s['confidence'] == 'high'):
            ok += c
        elif s['confidence'] == 'high':
            bad.append((name, n, req, mx, c))
print('methods checked: %d, calls: %d, calls consistent with recovered signature (high confidence): %d (%.1f%%)' % (len(calls), tot, ok, 100.0 * ok / max(tot, 1)))
bad.sort(key=lambda x: -x[4])
for b in bad[:25]:
    print('  %s: called with %d args, recovered required=%d max=%d (%d calls)' % b)
