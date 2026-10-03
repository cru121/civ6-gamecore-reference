"""Say what a returned number means, from (1) the C++ type the wrapper's callee returns and (2) how the game's own Lua uses the result
(linux_depot/out/lua_return_usage.json). Output: data/lua_return_meanings.json keyed 'Object.Method'."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'docs_proto', 'data')
methods = json.load(open(os.path.join(OUT, 'lua_methods.json'), encoding='utf8'))
usage = json.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'lua_return_usage.json')))
by_key = {'%s.%s' % (m['object'], m['method']): m for m in methods}

from lua_semantics import TABLES, cpp_meaning, NAME_RULES, name_meaning


def usage_meaning(u):
    """Meaning from how scripts use the value, with the number of supporting uses."""
    best = None
    for tbl, n in (u.get('index-of') or {}).items():
        if best is None or n > best[0]:
            best = (n, 'db-row-key', 'Key of a row of the %s table: the scripts look it up with GameInfo.%s[result].' % (tbl, tbl), tbl)
    for kind, key, text in (('player-id', 'player-id', 'Id of a player: the scripts use the result as Players[result].'),
                            ('plot-index', 'plot-index', 'Plot index: the scripts pass the result to Map.GetPlotByIndex.'),
                            ('hash', 'hash', 'Hash of a database row (compared with row.Hash).'),
                            ('index', 'db-index', 'Index of a database row (compared with row.Index).')):
        n = sum((u.get(kind) or {}).values())
        if n and (best is None or n > best[0]):
            best = (n, key, text, None)
    return best


def passed_to(u):
    out = []
    for k, n in sorted((u.get('passed-to') or {}).items(), key=lambda x: -x[1])[:3]:
        meth, _, pos = k.rpartition(':')
        tm = by_key.get(meth)
        pname = None
        if tm and tm.get('signatures'):
            ps = tm['signatures'][0]['params']
            if int(pos) < len(ps) and not re.match(r'^arg\d+$', ps[int(pos)]['name']):
                pname = ps[int(pos)]['name']
        out.append((meth, pname, n))
    return out


res = {}
for key, m in by_key.items():
    sigs = m.get('signatures') or []
    if not sigs:
        continue
    s = sigs[0]
    rd = s.get('return_details') or []
    if len(rd) != 1 or rd[0]['type'] not in ('number', 'string', 'number|nil', 'nil|number'):
        continue
    u = usage.get(key, {})
    ev = []
    cm = cpp_meaning(rd[0]['cpp_type']) if rd[0].get('cpp_type') else None
    um = usage_meaning(u.get('usage', {})) if u else None
    summary = kind = table = None
    status = 'inferred'
    if cm:
        kind, summary, table = cm
        ev.append({'kind': 'static-analysis', 'note': 'the wrapper returns the C++ type %s' % rd[0]['cpp_type']})
        status = 'verified'
    if um:
        n, ukind, utext, utable = um
        if not summary:
            kind, summary, table = ukind, utext, utable
            if kind == 'db-row-key' and 'Hash' in key:
                summary = summary.replace('Key of a row', 'Hash of a row')
            status = 'verified' if n >= 2 else 'inferred'
        ev.append({'kind': 'game-script', 'note': 'used that way in %d place(s) in the game\'s scripts' % n})
    pt = passed_to(u.get('usage', {})) if u else []
    seen = [v for v, _ in u.get('var_names', [])[:4]] if u else []
    if not summary and pt:
        meth, pname, n = pt[0]
        summary = 'The scripts pass the result to `%s`%s.' % (meth, ' (parameter `%s`)' % pname if pname else '')
        kind = 'passed-on'
        ev.append({'kind': 'game-script', 'note': 'passed to %s in %d place(s)' % (meth, n)})
    mname = key.split('.', 1)[1]
    if not summary and seen and u.get('assignments', 0) >= 3 and not mname.startswith(('Create', 'Set', 'Add', 'Place', 'Remove', 'Change', 'Start', 'Can', 'Is', 'Has')):
        nm = name_meaning(u.get('var_names', []), u.get('assignments', 0))
        if nm:
            kind, summary = nm
            ev.append({'kind': 'game-script', 'note': 'inferred from the variable names the scripts use (%s) in %d assignments' % (', '.join(seen[:3]), u.get('assignments', 0))})
    if not summary:
        continue
    rec = {'summary': summary, 'kind': kind, 'status': status, 'evidence': ev}
    if table:
        rec['db_table'] = table
    if pt and kind != 'passed-on':
        rec['also_passed_to'] = ['%s%s' % (a, ' (%s)' % b if b else '') for a, b, _ in pt[:2]]
    if seen:
        rec['seen_as'] = seen
    res[key] = rec
json.dump(res, open(os.path.join(OUT, 'lua_return_meanings.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
import collections
print(len(res), 'methods with a return meaning;', dict(collections.Counter(r['kind'] for r in res.values())), dict(collections.Counter(r['status'] for r in res.values())))
