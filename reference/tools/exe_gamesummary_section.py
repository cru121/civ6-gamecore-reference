"""Page exe/gamesummary.md: the game summary (Hall of Fame / statistics) data model. Called from build.py: exe_gamesummary_section.make(add, entries, meta)
Data: data/exe_gamesummary.json, data/exe_gamesummary_meta.json (tools/extract_exe_gamesummary.py)."""
import re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def make(add, entries, meta):
    by = {}
    for e in entries:
        by.setdefault(e['kind'], []).append(e)
    r = meta['rows']
    L = ['# Game summary and statistics data model\n',
         'The game summary (the Hall of Fame screens, the end-of-game graphs and reports, the per-leader and per-victory progress) is driven by data. Two parts: **configuration tables** in the game\'s Configuration database, '
         'created by `Configuration/Data/Schema/HallofFame.sql` and filled by `HallofFame.xml` (what statistics, graphs, reports and aggregates exist), and **recorded tables** in `HallofFame.sqlite`, where the exe stores every finished or running game '
         '(`Application::GameSummary` writes them, the Lua table `HallofFame` and the summary library read them; see the [`HallofFame`](../exeapi/HallofFame.md) page and the [database statements](../exedb/statements.md)). '
         '**Verified**: table and column names, shipped row counts, SQL statements (read from the files and the exe). **Inferred**: what a table is for beyond its name.\n',
         '**What the shipped data defines** (%d statistics in %d categories, %d graphs, %d reports with %d columns, %d aggregate rules: %s over the scopes %s). A modder adds a statistic by adding rows: a `DataPointAggregateUpdates` rule that sums, maximises or counts a recorded data point, '
         'a `Statistics` row (name key, category, icon) and, for a report, a `ReportColumns` row. The recorded data point values are rows of `ObjectDataPointValues` / `GameDataPointValues`; the game transfer of the exe (`Application::GameSummary::BeginGameTransfer`) creates the game, its players and objects, datasets and data point values (`CreateGame`, `CreateObject`, `CreateGameDataset`, `CreateObjectDataset`, `UpdateAggregateDataPoints`).\n' % (
             r['Statistics'], r['StatisticCategories'], r['Graphs'], r['Reports'], r['ReportColumns'], r['DataPointAggregateUpdates'], ', '.join('`%s` %d' % kv for kv in meta['operations'].items()),
             ', '.join('`%s` %d' % kv for kv in meta['scopes'].items())),
         '## Configuration tables (%d)\n' % len(by.get('config-table', []))]
    L.append('| Table | Columns | Shipped rows | Exe operations | Functions that use it |')
    L.append('|---|---|---|---|---|')
    for e in by.get('config-table', []):
        L.append('| <a id="table-%s"></a>`%s` | %s | %d | %s | %s |' % (safe(e['name']), e['name'], ', '.join('`%s`' % c['name'] for c in e['columns']), e['shipped_rows'],
                                                                      ', '.join('%s %d' % kv for kv in e['exe_ops'].items()) or '—', ', '.join('`%s`' % f.split('::')[-1] for f in e['exe_functions'][:3]) or '—'))
    L.append('\n## Recorded and queried tables (%d)\n' % len(by.get('recorded-table', [])))
    L.append('Tables the exe writes or reads that are not part of the configuration schema. Columns are the ones named in statements that mention the table, so a statement that joins several tables can list a column under more than one of them. '
             '"summary database" tables live in `HallofFame.sqlite`; "game" tables belong to the game databases (queried for names and icons).\n')
    L.append('| Table | Database | Columns named in statements | Exe operations | Functions |')
    L.append('|---|---|---|---|---|')
    for e in by.get('recorded-table', []):
        L.append('| <a id="table-%s"></a>`%s` | %s | %s | %s | %s |' % (safe(e['name']), e['name'], e['database'], ', '.join('`%s`' % c['name'] for c in e['columns']) or '—', ', '.join('%s %d' % kv for kv in e['exe_ops'].items()),
                                                                      ', '.join('`%s`' % f.split('::')[-1] for f in e['exe_functions'][:3])))
    L.append('\n## Statistic categories\n')
    L.append('| Category | Text key | Sort |')
    L.append('|---|---|---|')
    for e in by.get('category', []):
        L.append('| <a id="category-%s"></a>`%s` | `%s` | %s |' % (safe(e['name']), e['name'], esc(e['name_key']), e['sort']))
    L.append('\n## Data points (%d)\n' % len(by.get('datapoint', [])))
    L.append('Names of the recorded values and the statistics built from them: `Statistic` = has a `Statistics` row (with a category); aggregates are the `DataPointAggregateUpdates` rules that produce the value (operation of a data point over a scope).\n')
    L.append('<details markdown="1"><summary>%d data points</summary>\n' % len(by.get('datapoint', [])))
    L.append('| Data point | Statistic category | Aggregates | Reports |')
    L.append('|---|---|---|---|')
    for e in sorted(by.get('datapoint', []), key=lambda e: e['name'].lower()):
        L.append('| <a id="datapoint-%s"></a>`%s` | %s | %s | %s |' % (safe(e['name']), e['name'], esc(e['category'] or '') if e['statistic'] else '', ('; '.join(esc(a) for a in e['aggregates'][:3]) + (' (+%d)' % (e['aggregate_count'] - 3) if e['aggregate_count'] > 3 else '')) or '—',
                                                                           ', '.join('`%s`' % x for x in e['reports']) or '—'))
    L.append('\n</details>\n')
    L.append('## Graphs (%d)\n' % len(by.get('graph', [])))
    L.append('<details markdown="1"><summary>%d graphs</summary>\n' % len(by.get('graph', [])))
    L.append('| Graph | Scope | Query | Text key |')
    L.append('|---|---|---|---|')
    for e in by.get('graph', []):
        L.append('| <a id="graph-%s"></a>`%s` | %s | `%s` | `%s` |' % (safe(e['name']), e['name'], e['scope'], e['query'], esc(e['name_key'])))
    L.append('\n</details>\n')
    L.append('## Reports (%d)\n' % len(by.get('report', [])))
    L.append('| Report | Scope | Columns (data point) |')
    L.append('|---|---|---|')
    for e in by.get('report', []):
        L.append('| <a id="report-%s"></a>`%s` | %s | %s |' % (safe(e['name']), e['name'], e['scope'], ', '.join('`%s`' % (c['data_point'] or c['name_key']) for c in sorted(e['columns'], key=lambda c: int(c['sort'] or 0)))))
    L.append('\n## Game fields handed to the scripts (`PushGameData`)\n')
    L.append('`PushGameData` (`%s`) builds the table of one recorded game that the Lua functions `GetGames` / `GetGameData` return. Field names: %s.\n' % (meta['push_rva'], ', '.join('`%s`' % e['name'] for e in by.get('push-field', []))))
    add('exe/gamesummary.md', 'Game summary and statistics data model', '\n'.join(L) + '\n')
