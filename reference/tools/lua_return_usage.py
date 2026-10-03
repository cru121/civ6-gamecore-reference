"""Mine how the game's own Lua uses the value returned by a method, to say what the returned number means.
For `local v = obj:Method(...)` look at the next lines for: GameInfo.Table[v] (row index), Players[v] (player id), GetPlotByIndex(v)
(plot index), `.Hash == v` (row hash), v passed to another method whose parameter type we know. Output: linux_depot/out/lua_return_usage.json"""
import collections
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
sigs = json.load(open(os.path.join(ROOT, 'docs_proto', 'data', 'lua_methods.json'), encoding='utf8'))

# methods by name; keep only names that belong to one object (or all objects agree on the first parameter list)
by_name = collections.defaultdict(list)
for m in sigs:
    by_name[m['method']].append(m)
unique = {n: v[0] for n, v in by_name.items() if len({x['object'] for x in v}) == 1}
obj_methods = collections.defaultdict(set)
for m in sigs:
    obj_methods[m['object'].lower()].add(m['method'])
ALIASES = {'owner': 'player', 'pl': 'player', 'plr': 'player', 'civ': 'player', 'plot': 'plot', 'adjacent': 'plot', 'city': 'city', 'unit': 'unit', 'district': 'district', 'building': 'citybuildings'}


def guess_object(recv, meth):
    tok = re.search(r'(\w+)\s*(?:\(\s*\))?\s*$', recv.strip())
    if not tok:
        return None
    t = re.sub(r'^(?:p|k|m_|g_|l_|c|tmp|src|dest|dst|target|other|my)(?=[A-Z_])', '', tok.group(1))
    t = re.sub(r'(?:Instance|Obj|Ref|\d+)$', '', t).lower()
    cand = ALIASES.get(t, t)
    if cand in obj_methods and meth in obj_methods[cand]:
        return [o for o in {m['object'] for m in sigs} if o.lower() == cand][0]
    return None

assign = re.compile(r'^\s*(?:local\s+)?(\w+)(?:\s*:\s*\w+)?\s*=\s*([\w\.\[\]\(\)\s,"\':]*?)[:.](\w+)\(([^()]*)\)\s*;?\s*(?:--.*)?$')
call = re.compile(r'(\w+)[:.](\w+)\(([^()]*)\)')
usage = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))   # method -> kind -> detail counter
varnames = collections.defaultdict(collections.Counter)
nlocal = collections.Counter()
for base in ('Base/Assets', 'DLC'):
    for root, _, files in os.walk(os.path.join(GAME, base)):
        for f in files:
            if not f.endswith('.lua'):
                continue
            lines = open(os.path.join(root, f), encoding='utf8', errors='replace').read().split('\n')
            for i, l in enumerate(lines):
                m = assign.match(l)
                if not m:
                    continue
                var, mname = m.group(1), m.group(3)
                if var in ('self',):
                    continue
                if mname in unique:
                    meth = unique[mname]['object'] + '.' + mname
                else:
                    ob = guess_object(m.group(2), mname)
                    if not ob:
                        continue
                    meth = ob + '.' + mname
                nlocal[meth] += 1
                varnames[meth][var] += 1
                w = re.compile(r'(?<![\w\.])%s(?![\w])' % re.escape(var))
                for j in range(i + 1, min(i + 40, len(lines))):
                    ln = lines[j]
                    if re.match(r'^\s*(?:local\s+)?%s\s*=' % re.escape(var), ln):
                        break           # reassigned
                    if not w.search(ln):
                        continue
                    for gm in re.finditer(r'GameInfo\.(\w+)\[\s*%s\s*\]' % re.escape(var), ln):
                        usage[meth]['index-of'][gm.group(1)] += 1
                    if re.search(r'(?:Players|PlayerConfigurations)\[\s*%s\s*\]|PlayerManager\.GetPlayer\(\s*%s\s*\)|Players\[\s*%s\s*\]' % ((re.escape(var),) * 3), ln):
                        usage[meth]['player-id']['Players[...]'] += 1
                    if re.search(r'GetPlotByIndex\(\s*%s\s*\)' % re.escape(var), ln):
                        usage[meth]['plot-index']['GetPlotByIndex'] += 1
                    if re.search(r'\.Hash\s*==\s*%s\b|\b%s\s*==\s*[\w\.\[\]"\']+\.Hash' % (re.escape(var), re.escape(var)), ln):
                        usage[meth]['hash']['== row.Hash'] += 1
                    if re.search(r'\.Index\s*==\s*%s\b|\b%s\s*==\s*[\w\.\[\]"\']+\.Index' % (re.escape(var), re.escape(var)), ln):
                        usage[meth]['index']['== row.Index'] += 1
                    if re.search(r'==\s*Game\.GetLocalPlayer\(\)|Game\.GetLocalPlayer\(\)\s*==', ln) and w.search(ln):
                        usage[meth]['player-id']['== local player'] += 1
                    for cm in call.finditer(ln):
                        args = [a.strip() for a in cm.group(3).split(',')]
                        if var in args and cm.group(2) in unique:
                            usage[meth]['passed-to'][('%s.%s:%d' % (unique[cm.group(2)]['object'], cm.group(2), args.index(var)))] += 1
out = {}
for meth in nlocal:
    out[meth] = {'assignments': nlocal[meth], 'var_names': varnames[meth].most_common(6),
                 'usage': {k: dict(v.most_common(6)) for k, v in usage[meth].items()}}
json.dump(out, open(os.path.join(ROOT, 'linux_depot', 'out', 'lua_return_usage.json'), 'w'), indent=1)
print(len(out), 'methods with captured assignments;', sum(1 for v in out.values() if v['usage']), 'with at least one usage signal')
