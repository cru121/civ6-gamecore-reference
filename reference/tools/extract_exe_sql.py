"""SQL statements and text keys the engine exe refers to as literals.
Inputs : linux_depot/out/strmaps.pkl (ASCII strings and the functions that reference them), findings/data/exe_function_index.json (function names)
Outputs: data/exe_sql.json (entities exesql:<n>), data/exe_text_keys.json (LOC_ keys, entities exeloc:<key>)."""
import collections, json, os, pickle, re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
O = os.path.join(ROOT, 'linux_depot', 'out')
ws, ls, wm, lm = pickle.load(open(os.path.join(O, 'strmaps.pkl'), 'rb'))
names = {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            names.setdefault(int(v, 16), re.sub(r'\(.*$', '', r[0]))

MODS = {'Mods', 'ModGroups', 'ModFiles', 'ModGroupItems', 'Components', 'ModProperties', 'Criteria', 'ComponentCriteria', 'SettingCriteria', 'ScannedFiles', 'AdditionalScannedFiles',
        'ModDependencies', 'ModRelationships', 'ModCompatibilityWhitelist', 'ComponentFiles', 'SettingFiles', 'ComponentProperties', 'SettingProperties', 'ComponentRelationships',
        'Settings', 'Migrations', 'MetaData', 'ModAssociations', 'ModAssociationItems', 'Associations'}
FAME = {'Games', 'GAMES', 'GameObjects', 'GamePlayers', 'ObjectDataPointValues', 'GameDataPointValues', 'DataSets', 'DataSetValues', 'ChallengeGames', 'RulesetDataPointValues'}


def split_top(s):
    out, depth, cur = [], 0, ''
    for c in s:
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        if c == ',' and depth == 0:
            out.append(cur); cur = ''
        else:
            cur += c
    if cur.strip():
        out.append(cur)
    return [x.strip() for x in out]


def parse(sql):
    op = re.match(r'\s*(\w+(?: \w+)?)', sql).group(1).upper()
    op = {'INSERT INTO': 'INSERT', 'DELETE FROM': 'DELETE', 'CREATE TABLE': 'CREATE', 'INSERT OR': 'INSERT'}.get(op, op.split()[0])
    tables = []
    for t in re.findall(r'\b(?:FROM|JOIN|INTO|UPDATE|TABLE(?: IF NOT EXISTS)?)\s+([A-Za-z_]\w*)', sql, re.I):
        if t.upper() not in ('SELECT', 'WHERE', 'SET') and t not in tables:
            tables.append(t)
    cols = []
    if op == 'SELECT':
        m = re.match(r'\s*SELECT\s+(?:DISTINCT\s+)?(.*?)\s+FROM\b', sql, re.I | re.S)
        if m:
            for c in split_top(m.group(1)):
                c = re.sub(r'\s+AS\s+\'?\w+\'?$', '', c, flags=re.I)
                c = c.split('.')[-1].strip()
                if re.match(r'^\w+$', c) and c != '*':
                    cols.append(c)
    elif op == 'INSERT':
        m = re.search(r'INTO\s+\w+\s*\(([^)]*)\)', sql, re.I)
        if m:
            cols = [c.strip().strip("'\"") for c in m.group(1).split(',') if c.strip()]
    elif op == 'UPDATE':
        m = re.search(r'\bSET\s+(.*?)(?:\bWHERE\b|$)', sql, re.I | re.S)
        if m:
            cols = [c.split('=')[0].strip() for c in split_top(m.group(1)) if '=' in c]
    return op, tables, cols


def database_of(tables, fn):
    ts = set(tables)
    if ts & FAME and not (ts & MODS):
        return 'HallofFame.sqlite (game summary)'
    if ts & MODS:
        return 'Mods.sqlite (mod framework)'
    f = fn or ''
    if 'Modding' in f:
        return 'Mods.sqlite (mod framework)'
    if 'GameSummary' in f:
        return 'game databases (summary queries)'
    return 'game databases (Gameplay, Configuration or Localization; the exe code does not say which)'


ents = []
seen = set()
for a, s in sorted(ws.items(), key=lambda kv: kv[0]):
    s = s.decode('latin1') if isinstance(s, bytes) else s
    if not (re.search(r'\b(SELECT|INSERT INTO|UPDATE|DELETE FROM|CREATE TABLE|PRAGMA)\b', s) and ' ' in s and len(s) < 2000):
        continue
    if s in seen:
        continue
    seen.add(s)
    fs = sorted(wm.get(a, ()))
    fn = names.get(fs[0]) if fs else None
    op, tables, cols = parse(s)
    ents.append({'id': 'exesql:%04d' % (len(ents) + 1), 'sql': s, 'operation': op, 'tables': tables, 'columns': cols,
                 'parameters': len(re.findall(r'\?|@\w+', s)),
                 'functions': [{'rva': '0x%x' % f, 'name': names.get(f)} for f in fs[:3]], 'function_count': len(fs),
                 'database': database_of(tables, fn), 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': 'SQL string literal referenced by %d function(s) of CivilizationVI.exe; which database it runs against is inferred' % len(fs)}]})
keys = []
for a, s in sorted(ws.items(), key=lambda kv: kv[1] if isinstance(kv[1], str) else kv[1].decode('latin1')):
    s = s.decode('latin1') if isinstance(s, bytes) else s
    if re.match(r'^LOC_[A-Z0-9_]+$', s):
        fs = sorted(wm.get(a, ()))
        keys.append({'id': 'exeloc:' + s, 'key': s, 'functions': [{'rva': '0x%x' % f, 'name': names.get(f)} for f in fs[:3]], 'function_count': len(fs),
                     'availability': 'exe', 'status': 'verified', 'evidence': [{'kind': 'exe-string', 'note': 'text key literal referenced by %d function(s)' % len(fs)}]})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_sql.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(keys, open(os.path.join(BASE, 'data', 'exe_text_keys.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
tabs = collections.Counter(t for e in ents for t in e['tables'])
print(len(ents), 'statements,', len(tabs), 'tables,', len(keys), 'text keys;', collections.Counter(e['database'][:12] for e in ents))
