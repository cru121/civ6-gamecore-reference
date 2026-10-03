"""Say what each Lua method argument means, from (1) the C++ parameter type the wrapper passes on and (2) what the game's own Lua passes
at its call sites. Output: linux_depot/out/lua_arg_usage.json (raw call-site evidence) and data/lua_arg_meanings.json."""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lua_semantics import TABLES, cpp_meaning, NAME_RULES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
OUT = os.path.join(ROOT, 'docs_proto', 'data')
methods = json.load(open(os.path.join(OUT, 'lua_methods.json'), encoding='utf8'))
by_name = collections.defaultdict(list)
obj_methods = collections.defaultdict(set)
for m in methods:
    by_name[m['method']].append(m)
    obj_methods[m['object'].lower()].add(m['method'])
unique = {n: v[0]['object'] for n, v in by_name.items() if len({x['object'] for x in v}) == 1}
objects_lc = {m['object'].lower(): m['object'] for m in methods}
ALIASES = {'owner': 'player', 'pl': 'player', 'plr': 'player', 'civ': 'player', 'adjacent': 'plot'}


def guess_object(recv, meth, sep):
    recv = recv.strip()
    tok = re.search(r'(\w+)\s*(?:\(\s*\))?\s*$', recv)
    if not tok:
        return None
    t0 = tok.group(1)
    if sep == '.' and t0 in {m['object'] for m in methods} and meth in obj_methods[t0.lower()]:
        return t0                                   # static call such as Map.GetPlot(...)
    t = re.sub(r'^(?:p|k|m_|g_|l_|c|tmp|src|dest|dst|target|other|my)(?=[A-Z_])', '', t0)
    t = re.sub(r'(?:Instance|Obj|Ref|\d+)$', '', t).lower()
    cand = ALIASES.get(t, t)
    if cand in obj_methods and meth in obj_methods[cand]:
        return objects_lc[cand]
    return None


def split_args(s):
    out, depth, cur, q = [], 0, '', None
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = None
            continue
        if ch in '"\'':
            q = ch
            cur += ch
        elif ch in '([{':
            depth += 1
            cur += ch
        elif ch in ')]}':
            depth -= 1
            cur += ch
        elif ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip() or out:
        out.append(cur.strip())
    return out


def classify(expr):
    e = expr.strip()
    m = re.search(r'GameInfo\.(\w+)(?:\s*\[[^\]]*\]|\.\w+)\s*\.(Index|Hash|ID)\b', e)
    if m:
        return ('db-' + m.group(2).lower(), m.group(1))
    m = re.match(r'^(\w+)\s*:\s*GetID\(\)$', e)
    if m:
        r = m.group(1).lower()
        return ('city-id' if 'city' in r else 'unit-id' if 'unit' in r else 'player-id' if ('player' in r or 'owner' in r) else 'id', None)
    if re.search(r'Game\.GetLocalPlayer\(\)', e) or re.search(r':\s*GetOwner\(\)$', e):
        return ('player-id', None)
    m = re.match(r'^(\w+)\s*:\s*GetIndex\(\)$', e)
    if m:
        return ('plot-index' if 'plot' in m.group(1).lower() else 'index', None)
    if re.search(r':\s*GetX\(\)$', e):
        return ('plot-x', None)
    if re.search(r':\s*GetY\(\)$', e):
        return ('plot-y', None)
    if e in ('true', 'false'):
        return ('boolean', None)
    if re.match(r'^-?\d+(\.\d+)?$', e):
        return ('number-literal', None)
    if re.match(r'^"[^"]*"$|^\'[^\']*\'$', e):
        return ('string-literal', None)
    m = re.match(r'^(\w+)\.([A-Z][A-Z0-9_]+)$', e)
    if m:
        return ('enum-constant', m.group(1))
    if re.match(r'^p[A-Z]\w*$', e):
        obj = objects_lc.get(e[1:].lower())
        if obj:
            return ('object', obj)
    if re.match(r'^[A-Za-z_]\w*$', e) and not re.match(r'^p[A-Z]', e):
        stem = re.sub(r'^(?:e|i|b|k|p|n|m_|g_|l_)(?=[A-Z])', '', e)
        for rx, kind, _ in NAME_RULES:
            if rx.search(stem) or rx.search(e):
                if kind in ('player-id', 'city-id', 'unit-id', 'plot-index', 'plot-coord', 'hash', 'turn', 'count'):
                    return ('name:' + kind, None)
                break
    return ('expression', None)


cache = os.path.join(ROOT, 'linux_depot', 'out', 'lua_arg_usage.json')
call_re = re.compile(r'([\w\.\[\]\(\)]*?)([:.])(\w+)\(')
usage = collections.defaultdict(lambda: collections.defaultdict(lambda: {'n': 0, 'kinds': collections.Counter(), 'ex': []}))
nfiles = 0
for base in ('Base/Assets', 'DLC'):
    for root, _, files in os.walk(os.path.join(GAME, base)):
        for f in files:
            if not f.endswith('.lua'):
                continue
            nfiles += 1
            text = open(os.path.join(root, f), encoding='utf8', errors='replace').read()
            lines = text.split('\n')
            for i, l in enumerate(lines):
                for cm in call_re.finditer(l):
                    meth = cm.group(3)
                    if meth not in by_name:
                        continue
                    sep = cm.group(2)
                    recv = cm.group(1)
                    obj = unique.get(meth) or guess_object(recv, meth, sep)
                    if not obj:
                        continue
                    # the instance-method call must use ':'; static '.' calls only on objects that are static
                    chunk = l[cm.end():]
                    j = i
                    while chunk.count('(') + 1 > chunk.count(')') and j < i + 3:
                        j += 1
                        chunk += ' ' + (lines[j] if j < len(lines) else '')
                    depth, end = 1, None
                    for k, ch in enumerate(chunk):
                        depth += ch == '('
                        depth -= ch == ')'
                        if depth == 0:
                            end = k
                            break
                    if end is None:
                        continue
                    args = split_args(chunk[:end])
                    for pos, a in enumerate(args):
                        kind, detail = classify(a)
                        u = usage['%s.%s' % (obj, meth)][pos]
                        u['n'] += 1
                        u['kinds'][(kind, detail)] += 1
                        if len(u['ex']) < 3 and a not in u['ex'] and len(a) <= 70:
                            u['ex'].append(a)
raw = {k: {str(p): {'n': v['n'], 'kinds': [[a, b, c] for (a, b), c in v['kinds'].most_common(5)], 'examples': v['ex']} for p, v in d.items()} for k, d in usage.items()}
json.dump(raw, open(cache, 'w'), indent=0)
print(nfiles, 'files;', len(raw), 'methods with call sites')

# ---------------------------------------------------------------- synthesis
def usage_text(kind, detail, form_hint=None):
    if kind == 'db-index':
        return ('Index of a row of the %s table (the scripts pass GameInfo.%s[...].Index).' % (detail, detail), detail)
    if kind == 'db-hash':
        return ('Hash of a row of the %s table (the scripts pass GameInfo.%s[...].Hash).' % (detail, detail), detail)
    if kind == 'db-id':
        return ('ID of a row of the %s table (the scripts pass GameInfo.%s[...].ID).' % (detail, detail), detail)
    simple = {'player-id': 'Id of a player.', 'city-id': 'Id of a city (city:GetID()).', 'unit-id': 'Id of a unit (unit:GetID()).',
              'plot-index': 'Plot index (plot:GetIndex()).', 'plot-x': 'Plot x coordinate (plot:GetX()).', 'plot-y': 'Plot y coordinate (plot:GetY()).',
              'boolean': 'A boolean flag (true/false).', 'index': 'An index.', 'id': 'An id.',
              'name:player-id': 'Id of a player (the scripts name the argument playerID / owner).', 'name:city-id': 'Id of a city (named cityID in the scripts).',
              'name:unit-id': 'Id of a unit (named unitID in the scripts).', 'name:plot-index': 'Plot index (named plotIndex / plotID in the scripts).',
              'name:plot-coord': 'A plot coordinate (named x / y / plotX / plotY in the scripts).', 'name:hash': 'A database row hash (named …Hash in the scripts).',
              'name:turn': 'A turn number (named turn in the scripts).', 'name:count': 'A count or amount (named count / num / amount in the scripts).'}
    if kind in simple:
        return (simple[kind], None)
    if kind == 'object':
        return ('A %s object (the scripts pass a variable named p%s).' % (detail, detail), None)
    if kind == 'enum-constant':
        return ('A constant from the Lua table %s.' % detail, None)
    if kind == 'string-literal':
        return ('A string.', None)
    if kind == 'number-literal':
        return ('A number.', None)
    return None


res = {}
for m in methods:
    key = '%s.%s' % (m['object'], m['method'])
    sigs = m.get('signatures') or []
    if not sigs:
        continue
    params = sigs[0]['params']
    u = raw.get(key, {})
    out = []
    for pos, p in enumerate(params):
        ev = []
        summary = status = table = None
        cm = cpp_meaning(p['cpp_type']) if p.get('cpp_type') else None
        pu = u.get(str(pos))
        dom = None
        if pu and pu['n']:
            for kind, detail, c in pu['kinds']:
                if kind == 'expression':
                    continue
                if c >= max(2, 0.5 * pu['n']) or pu['n'] == 1:
                    dom = (kind, detail, c)
                    break
        if cm:
            _, summary, table = cm
            status = 'verified'
            ev.append({'kind': 'static-analysis', 'note': 'the wrapper passes the argument on as the C++ type %s' % p['cpp_type']})
            if dom and dom[0] in ('db-hash', 'db-index', 'db-id'):
                form = {'db-hash': 'hash', 'db-index': 'index', 'db-id': 'ID'}[dom[0]]
                summary += ' The scripts pass its %s.' % form
                ev.append({'kind': 'game-script', 'note': '%d of %d call sites pass GameInfo.%s[...].%s' % (dom[2], pu['n'], dom[1], form.capitalize() if form != 'ID' else 'ID')})
        elif dom:
            ut = usage_text(dom[0], dom[1])
            if ut:
                summary, table = ut
                status = 'verified' if (dom[2] >= 2 and not dom[0].startswith('name:')) else 'inferred'
                ev.append({'kind': 'game-script', 'note': '%d of %d call sites in the game\'s scripts pass this kind of value' % (dom[2], pu['n'])})
        if summary:
            rec = {'index': pos, 'name': p['name'], 'summary': summary, 'status': status, 'evidence': ev}
            if table:
                rec['db_table'] = table
            if pu and pu['examples']:
                rec['examples'] = pu['examples'][:2]
            out.append(rec)
    if out:
        res[key] = out
json.dump(res, open(os.path.join(OUT, 'lua_arg_meanings.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
nargs = sum(len(v) for v in res.values())
total = sum(len((m.get('signatures') or [{'params': []}])[0]['params']) for m in methods)
print(len(res), 'methods with at least one argument meaning;', nargs, 'of', total, 'arguments;', dict(collections.Counter(a['status'] for v in res.values() for a in v)))
