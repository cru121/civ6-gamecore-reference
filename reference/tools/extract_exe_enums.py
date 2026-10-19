"""Lua enum tables registered by the engine exe (UI, Network, Keys, MouseEvents, InterfaceModeTypes, ...): members with their numeric values, how the game's own Lua uses them,
and the agreement with the same-named GameCore enum where one exists.
Input : findings/tables/exe_lua_enums_windows.tsv (tools/exe/winenums.py), data/enums.json and data/lua_enums.json (GameCore enums), the game's Lua files (read in place; only counts are kept)
Output: data/exe_enums.json (entities exeenum:<Table>)."""
import collections, csv, json, os, re, zlib

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
LIBS = {'LuaUIEnumsLibrary': 'LuaUIEnumsLibrary (input, mouse, keys)', 'AppLuaUIEnumsLibrary': 'AppLuaUIEnumsLibrary (UI and application)',
        'Network::LuaNetworkEnumsLibrary': 'LuaNetworkEnumsLibrary (multiplayer)', 'GameCore::App::Cache::Lua::IEnums': 'Cache IEnums (game state, interface modes)'}

tables = collections.OrderedDict()
for r in csv.DictReader(open(os.path.join(ROOT, 'findings', 'tables', 'exe_lua_enums_windows.tsv'), encoding='utf8'), delimiter='\t'):
    t = tables.setdefault(r['table'], {'libs': [], 'rvas': [], 'members': collections.OrderedDict()})
    if r['library'] not in t['libs']:
        t['libs'].append(r['library'])
        t['rvas'].append(r['register_fn_rva'])
    v = float(r['value'])
    t['members'].setdefault(r['member'], int(v) if v.is_integer() else v)

# how the game's own scripts use them
pat = re.compile(r'\b(%s)\s*\.\s*([A-Za-z_]\w*)' % '|'.join(sorted(tables, key=len, reverse=True)))
uses = collections.defaultdict(collections.Counter)
files = collections.defaultdict(set)
for dp, dn, fn in os.walk(GAME):
    for f in fn:
        if f.lower().endswith('.lua'):
            p = os.path.join(dp, f)
            try:
                s = open(p, encoding='utf8', errors='replace').read()
            except Exception:
                continue
            for m in pat.finditer(s):
                uses[m.group(1)][m.group(2)] += 1
                files[m.group(1)].add(f)

# GameCore enums with the same name
gc = {}
for e in json.load(open(os.path.join(BASE, 'data', 'enums.json'), encoding='utf8')):
    gc[e['id'].split(':', 1)[1]] = {m['name']: m.get('signed', m.get('value')) for m in e['members']}
for e in json.load(open(os.path.join(BASE, 'data', 'lua_enums.json'), encoding='utf8')):
    gc.setdefault(e['table'], {m['name']: m.get('value') for m in e['members']})

def sg(x):
    x &= 0xffffffff
    return x - (1 << 32) if x >= 1 << 31 else x


def hsh(s):
    return sg(~zlib.crc32(s.encode()))


def hash_prefix(name, mem):
    """Best prefix P such that the value equals ~crc32(P + MEMBER) for at least 80 percent of the members (None when no prefix fits)."""
    t = re.sub(r'(Types|Type)$', '', name).upper()
    cands = ['', t + '_', t.rstrip('S') + '_', name.upper() + '_', t.replace('MODE', 'MODE_')]
    ms = [(k, v) for k, v in mem.items() if v != -1]
    best = (0, None)
    for pre in cands:
        n = sum(1 for k, v in ms if hsh(pre + k) == v or hsh(pre + k.upper()) == v)
        if n > best[0]:
            best = (n, pre)
    return (best[1], best[0], len(ms)) if ms and best[0] >= 0.8 * len(ms) else (None, best[0], len(ms))


ents = []
for name, t in tables.items():
    mem = t['members']
    vals = [v for v in mem.values()]
    big = sum(1 for v in vals if isinstance(v, int) and abs(v) >= 65536)
    kind = 'hash values (32-bit, signed)' if big >= max(2, len(vals) // 2) else 'small numbers'
    hp = hash_prefix(name, mem) if kind.startswith('hash') else (None, 0, 0)
    ms = [{'name': k, 'value': v, 'script_uses': uses[name].get(k, 0)} for k, v in mem.items()]
    other = gc.get(name)
    same = diff = 0
    if other:
        for k, v in mem.items():
            if k in other and other[k] is not None:
                if other[k] == v:
                    same += 1
                else:
                    diff += 1
    ents.append({'id': 'exeenum:%s' % name, 'table': name, 'libraries': t['libs'], 'register_rvas': t['rvas'], 'kind': kind, 'members': ms,
                 'member_count': len(ms), 'hash_prefix': hp[0], 'hash_matches': hp[1] if kind.startswith('hash') else None, 'script_files': len(files[name]), 'script_uses': sum(uses[name].values()),
                 'gamecore_enum': ('enum:%s' % name) if (name in gc and any(e['id'] == 'enum:' + name for e in json.load(open(os.path.join(BASE, 'data', 'enums.json'), encoding='utf8')))) else None,
                 'gamecore_compare': {'same_value': same, 'different_value': diff, 'only_in_exe': len([k for k in mem if other is not None and k not in other])} if other else None,
                 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-registration', 'note': 'member names and double values stored by the registration code (%s)' % ', '.join('0x' + r for r in t['rvas'])},
                              {'kind': 'game-script', 'note': 'usage counts from the game\'s Lua files (%d files)' % len(files[name])}]})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_enums.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'tables,', sum(e['member_count'] for e in ents), 'members;', sum(1 for e in ents if e['gamecore_compare']), 'also GameCore enums;', sum(1 for e in ents if e['script_uses']), 'used by scripts')
for e in ents:
    c = e['gamecore_compare']
    if c:
        print(e['table'], c)
