"""How the game's own Lua scripts call the exe-side tables (UI, Network, Modding, Locale, ...).
Input : data/exe_lua_group_names.json (table name per registering function; tools/exe_lua_objects.py), findings/tables/exe_lua_methods_windows.tsv,
        the game's Lua files.
Output: data/exe_lua_usage.json  {"Table.method": {calls, files, sep, arg_counts, kinds, examples}}
Only short call-site snippets are kept (single line, <= 110 characters), never whole scripts."""
import collections, csv, json, os, re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"

names = json.load(open(os.path.join(BASE, 'data', 'exe_lua_group_names.json'), encoding='utf8'))
methods = collections.defaultdict(set)     # table -> methods registered
for r in csv.DictReader(open(os.path.join(ROOT, 'findings', 'tables', 'exe_lua_methods_windows.tsv'), encoding='utf8'), delimiter='\t'):
    n = names.get(r['register_fn_rva'])
    if n:
        methods[n['name']].add(r['lua_method'])
tables = set(methods)
CALL = re.compile(r'\b(%s)\s*([.:])\s*([A-Za-z_]\w*)\s*\(' % '|'.join(sorted(tables, key=len, reverse=True)))


def split_args(src):
    """Arguments of a call whose '(' is just before src[0]; returns (args, end) or None when unbalanced on this text."""
    depth = 0; args = []; cur = []; i = 0; q = None
    while i < len(src):
        c = src[i]
        if q:
            cur.append(c)
            if c == '\\' and i + 1 < len(src):
                cur.append(src[i + 1]); i += 1
            elif c == q:
                q = None
        elif c in '"\'':
            q = c; cur.append(c)
        elif c in '([{':
            depth += 1; cur.append(c)
        elif c in ')]}':
            if depth == 0:
                a = ''.join(cur).strip()
                if a or args:
                    args.append(a)
                return args, i
            depth -= 1; cur.append(c)
        elif c == ',' and depth == 0:
            args.append(''.join(cur).strip()); cur = []
        else:
            cur.append(c)
        i += 1
    return None


def kind(a):
    if re.match(r'^(".*"|\'.*\')$', a, re.S):
        return 'string'
    if re.match(r'^-?\d+(\.\d+)?$', a):
        return 'number'
    if a in ('true', 'false'):
        return 'boolean'
    if a == 'nil':
        return 'nil'
    if a.startswith('{'):
        return 'table'
    if a.startswith('function'):
        return 'function'
    if re.match(r'^[A-Za-z_][\w.]*$', a):
        return 'name'
    return 'expr'


use = collections.defaultdict(lambda: {'calls': 0, 'files': set(), 'sep': collections.Counter(), 'argc': collections.Counter(), 'kinds': collections.defaultdict(collections.Counter), 'names': collections.defaultdict(collections.Counter), 'ex': []})
for root, _, fs in os.walk(GAME):
    for f in fs:
        if not f.lower().endswith('.lua'):
            continue
        try:
            t = open(os.path.join(root, f), encoding='utf8', errors='replace').read()
        except OSError:
            continue
        for m in CALL.finditer(t):
            tbl, sep, meth = m.groups()
            if meth not in methods[tbl]:
                continue
            r = split_args(t[m.end():m.end() + 1500])
            if r is None:
                continue
            args, end = r
            u = use['%s.%s' % (tbl, meth)]
            u['calls'] += 1; u['files'].add(f); u['sep'][sep] += 1; u['argc'][len(args)] += 1
            for k, a in enumerate(args):
                u['kinds'][k][kind(a)] += 1
                if kind(a) == 'name' and '.' not in a:
                    u['names'][k][a] += 1
            line = (t[t.rfind('\n', 0, m.start()) + 1:m.end() + end + 1]).strip()
            if len(u['ex']) < 6 and '\n' not in line and len(line) <= 110 and line not in u['ex'] and not line.startswith('--'):
                u['ex'].append(line)
out = {}
for k, u in use.items():
    out[k] = {'calls': u['calls'], 'files': len(u['files']), 'sep': dict(u['sep']), 'arg_counts': {str(a): c for a, c in sorted(u['argc'].items())},
              'kinds': {str(i): dict(c) for i, c in u['kinds'].items()},
              'names': {str(i): [n for n, _ in c.most_common(3)] for i, c in u['names'].items()},
              'names_count': {str(i): dict(c.most_common(3)) for i, c in u['names'].items()},
              'examples': sorted(u['ex'], key=len)[:3]}
json.dump(out, open(os.path.join(BASE, 'data', 'exe_lua_usage.json'), 'w', encoding='utf8'), indent=0)
print(len(tables), 'tables;', len(out), 'methods used in game scripts of', sum(len(v) for v in methods.values()), 'registered; calls', sum(u['calls'] for u in use.values()))
