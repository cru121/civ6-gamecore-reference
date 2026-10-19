"""Game summary (Hall of Fame / statistics) data model: the configuration tables of HallofFame.sql and the rows of HallofFame.xml (statistics, graphs, reports, aggregate data points), the tables the exe
reads and writes for recorded games (from its SQL statements), and the game fields PushGameData hands to the scripts.
Input : the game's Configuration/Data/Schema/HallofFame.sql and Configuration/Data/HallofFame.xml (read in place; names, column definitions and counts only), data/exe_sql.json (statements of the exe),
        linux_depot/out/strmaps.pkl (PushGameData strings)
Output: data/exe_gamesummary.json (entities exegs:<kind>:<name>), data/exe_gamesummary_meta.json."""
import collections, json, os, pickle, re
import xml.etree.ElementTree as ET

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
CFG = GAME + '/Base/Assets/Configuration/Data'

# 1. configuration schema
sql = open(CFG + '/Schema/HallofFame.sql', encoding='utf8', errors='replace').read()
schema = collections.OrderedDict()
for m in re.finditer(r"CREATE TABLE\s+'?(\w+)'?\s*\((.*?)\n\);", sql, re.S):
    cols = []
    fks = []
    for line in m.group(2).split('\n'):
        line = line.strip().rstrip(',')
        cm = re.match(r"'?(\w+)'?\s+(TEXT|INTEGER|BOOLEAN|REAL|FLOAT|NUMERIC|BLOB)\b(.*)$", line, re.I)
        if cm:
            cols.append({'name': cm.group(1), 'type': cm.group(2).upper(), 'rest': cm.group(3).strip()})
        elif line.upper().startswith('FOREIGN KEY'):
            fks.append(line)
        elif line.upper().startswith('PRIMARY KEY'):
            fks.append(line)
    schema[m.group(1)] = {'columns': cols, 'keys': fks}

# 2. shipped rows
rows = collections.OrderedDict()
root = ET.parse(CFG + '/HallofFame.xml').getroot()
for t in root:
    rr = []
    for r in t:
        d = dict(r.attrib)
        for c in r:
            d[c.tag] = (c.text or '').strip()
        rr.append(d)
    rows[t.tag] = rr

# 3. what the exe does with the tables
sqlents = json.load(open(os.path.join(BASE, 'data', 'exe_sql.json'), encoding='utf8'))
exe_tables = collections.OrderedDict()
for e in sqlents:
    db = e.get('database') or ''
    if 'game summary' not in db and 'summary queries' not in db:
        continue
    for t in e['tables']:
        if t in ('GAMES', 'sqlite_sequence'):
            continue
        d = exe_tables.setdefault(t, {'ops': collections.Counter(), 'columns': set(), 'functions': set(), 'config': t in schema, 'db': set()})
        d['db'].add('summary' if 'game summary' in db else 'game')
        d['ops'][e['operation']] += 1
        d['columns'] |= {c for c in (e.get('columns') or []) if not c.isdigit()}
        d['functions'] |= {f['name'] or f['rva'] for f in e['functions']}

# 4. PushGameData fields
ws, ls, wm, lm = pickle.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'strmaps.pkl'), 'rb'))
rva = None
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    if r[0].startswith('PushGameData(') and r[2]:
        rva = int(r[2].split(',')[0], 16)
push = sorted({(s.decode('latin1') if isinstance(s, bytes) else s) for a, s in ws.items() if rva in wm.get(a, ()) and re.match(r'^[A-Za-z]+$', s.decode('latin1') if isinstance(s, bytes) else s)})

ents = []
for name, t in schema.items():
    rr = rows.get(name, [])
    ents.append({'id': 'exegs:table:%s' % name, 'kind': 'config-table', 'name': name, 'columns': t['columns'], 'keys': t['keys'], 'shipped_rows': len(rr),
                 'exe_ops': dict(exe_tables.get(name, {}).get('ops', {})), 'exe_functions': sorted(exe_tables.get(name, {}).get('functions', []))[:6], 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'game-script', 'note': 'CREATE TABLE in Configuration/Data/Schema/HallofFame.sql and rows of HallofFame.xml (column names and counts only)'}]})
for name, d in exe_tables.items():
    if name in schema:
        continue
    ents.append({'id': 'exegs:table:%s' % name, 'kind': 'recorded-table', 'name': name, 'database': ' and '.join(sorted(d['db'])) + (' database' if 'summary' in d['db'] and len(d['db']) == 1 else ''), 'columns': [{'name': c, 'type': '', 'rest': ''} for c in sorted(d['columns'])], 'keys': [], 'shipped_rows': 0,
                 'exe_ops': dict(d['ops']), 'exe_functions': sorted(d['functions'])[:6], 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': 'table named in SQL statements of the exe (columns are those the statements name)'}]})
# data points: Statistics, report columns, aggregate updates
dp = collections.OrderedDict()
for r in rows.get('Statistics', []):
    dp.setdefault(r['DataPoint'], {'statistic': True, 'category': r.get('Category') or r.get('CATEGORY'), 'name_key': r.get('Name'), 'aggregates': [], 'reports': []})
for r in rows.get('DataPointAggregateUpdates', []):
    d = dp.setdefault(r['AggregateDataPoint'], {'statistic': False, 'category': None, 'name_key': None, 'aggregates': [], 'reports': []})
    d['aggregates'].append('%s of %s over %s' % (r.get('Operation'), r.get('DataPoint'), r.get('Scope')))
for r in rows.get('ReportColumns', []):
    d = dp.setdefault(r['DataPoint'], {'statistic': False, 'category': None, 'name_key': None, 'aggregates': [], 'reports': []})
    d['reports'].append(r['Report'])
for n, d in dp.items():
    ents.append({'id': 'exegs:datapoint:%s' % n, 'kind': 'datapoint', 'name': n, 'statistic': d['statistic'], 'category': d['category'], 'name_key': d['name_key'], 'aggregates': d['aggregates'][:6],
                 'aggregate_count': len(d['aggregates']), 'reports': sorted(set(d['reports'])), 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'game-script', 'note': 'DataPoint name in Statistics, DataPointAggregateUpdates or ReportColumns of HallofFame.xml'}]})
for r in rows.get('Graphs', []):
    ents.append({'id': 'exegs:graph:%s' % r['Graph'], 'kind': 'graph', 'name': r['Graph'], 'scope': r.get('Scope'), 'name_key': r.get('Name'), 'query': r.get('Query'), 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'game-script', 'note': 'Graphs row of HallofFame.xml'}]})
reports = collections.OrderedDict()
for r in rows.get('Reports', []):
    reports[r['Report']] = {'scope': r.get('Scope'), 'name_key': r.get('Name'), 'columns': []}
for r in rows.get('ReportColumns', []):
    reports.setdefault(r['Report'], {'scope': None, 'name_key': None, 'columns': []})['columns'].append({'name_key': r.get('Name'), 'data_point': r.get('DataPoint'), 'sort': r.get('SortOrder')})
for n, d in reports.items():
    ents.append({'id': 'exegs:report:%s' % n, 'kind': 'report', 'name': n, 'scope': d['scope'], 'name_key': d['name_key'], 'columns': d['columns'], 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'game-script', 'note': 'Reports and ReportColumns rows of HallofFame.xml'}]})
for r in rows.get('StatisticCategories', []):
    ents.append({'id': 'exegs:category:%s' % r['Category'], 'kind': 'category', 'name': r['Category'], 'name_key': r.get('Name'), 'sort': r.get('SortOrder'), 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'game-script', 'note': 'StatisticCategories row of HallofFame.xml'}]})
for f in push:
    ents.append({'id': 'exegs:push-field:%s' % f, 'kind': 'push-field', 'name': f, 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': 'field name string of PushGameData (0x%x)' % rva}]})
ops = collections.Counter(r.get('Operation') for r in rows.get('DataPointAggregateUpdates', []))
scopes = collections.Counter(r.get('Scope') for r in rows.get('DataPointAggregateUpdates', []))
meta = {'rows': {k: len(v) for k, v in rows.items()}, 'operations': dict(ops), 'scopes': dict(scopes), 'push_rva': '0x%x' % rva, 'tables_config': len(schema), 'tables_exe': len(exe_tables)}
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_gamesummary.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(meta, open(os.path.join(BASE, 'data', 'exe_gamesummary_meta.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), dict(collections.Counter(e['kind'] for e in ents)))
print(meta)
print(sorted(exe_tables))
print(push)
