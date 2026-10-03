"""Scan the game's own Lua for how operation/command parameters are filled: table[Enum.PARAM_X] = <expression>, attributed to the
operation named in the Request call that follows. Output: linux_depot/out/op_param_usage.json"""
import collections
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
ENUMS = 'PlayerOperations|UnitOperationTypes|UnitCommandTypes|CityOperationTypes|CityCommandTypes'
assign = re.compile(r'(\w+)\s*\[\s*(%s)\.(PARAM_\w+)\s*\]\s*=\s*([^\n]+)' % ENUMS)
request = re.compile(r'Request(?:PlayerOperation|Operation|Command)\s*\(([^\n]*)')
opname = re.compile(r'(%s)\.([A-Z][A-Z0-9_]+)' % ENUMS)
usage = collections.defaultdict(lambda: collections.defaultdict(list))   # (enum,op) -> param -> [rhs]
by_param = collections.defaultdict(list)
files = 0
for base in ('Base/Assets', 'DLC'):
    for root, _, fs in os.walk(os.path.join(GAME, base)):
        for f in fs:
            if not f.endswith('.lua'):
                continue
            files += 1
            lines = open(os.path.join(root, f), encoding='utf8', errors='replace').read().split('\n')
            for i, l in enumerate(lines):
                rm = request.search(l)
                if not rm:
                    continue
                om = opname.search(rm.group(1)) or opname.search(' '.join(lines[i:i + 3]))
                if not om:
                    continue
                enum, op = om.group(1), om.group(2)
                if op.startswith('PARAM_'):
                    continue
                for j in range(max(0, i - 45), i):
                    am = assign.search(lines[j])
                    if am and am.group(2) == enum:
                        rhs = am.group(4).strip().rstrip(';')
                        if rhs not in usage[(enum, op)][am.group(3)]:
                            usage[(enum, op)][am.group(3)].append(rhs[:90])
                        by_param[(am.group(2), am.group(3))].append(rhs[:90])
out = {'ops': {'%s.%s' % k: {p: v[:4] for p, v in d.items()} for k, d in usage.items()},
       'params': {'%s.%s' % k: [x for x, _ in collections.Counter(v).most_common(6)] for k, v in by_param.items()}}
json.dump(out, open(os.path.join(ROOT, 'linux_depot', 'out', 'op_param_usage.json'), 'w'), indent=1)
print(files, 'lua files;', len(out['ops']), 'operations with parameter usage;', len(out['params']), 'distinct parameters')
