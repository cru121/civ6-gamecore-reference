"""Pages for the exe's database and text access (section exedb/). Called from build.py: exe_db_section.make(add, sql, keys)
Data: data/exe_sql.json, data/exe_text_keys.json (tools/extract_exe_sql.py)."""
import collections, re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def fn_names(e, n=2):
    ns = [f['name'] or f['rva'] for f in e['functions'][:n]]
    more = e['function_count'] - len(ns)
    return '; '.join('`%s`' % x for x in ns) + (' (+%d)' % more if more > 0 else '') if ns else '—'


def subsystem(e):
    f = e['functions'][0]['name'] if e['functions'] and e['functions'][0]['name'] else None
    if not f:
        return 'unnamed functions'
    p = f.split('::')
    return '::'.join(p[:2]) if len(p) > 2 else p[0]


def make(add, sql, keys):
    dbs = collections.Counter(e['database'] for e in sql)
    tabs = collections.OrderedDict()
    for e in sql:
        for t in e['tables']:
            d = tabs.setdefault((e['database'], t), {'ops': collections.Counter(), 'cols': collections.Counter(), 'fns': collections.OrderedDict()})
            d['ops'][e['operation']] += 1
            for c in e['columns']:
                d['cols'][c] += 1
            for f in e['functions'][:2]:
                d['fns'].setdefault(f['name'] or f['rva'], 0)
    gm = collections.OrderedDict()
    for k, v in tabs.items():
        if k[0].startswith('game databases'):
            d = gm.setdefault(('game databases', k[1]), {'ops': collections.Counter(), 'cols': collections.Counter(), 'fns': collections.OrderedDict()})
            d['ops'].update(v['ops']); d['cols'].update(v['cols']); d['fns'].update(v['fns'])
    for d in gm.values():
        d['cols'].pop('NULL', None)
    game = list(gm.items())
    mods = [(k, v) for k, v in tabs.items() if k[0].startswith('Mods')]
    fame = [(k, v) for k, v in tabs.items() if k[0].startswith('HallofFame')]

    L = ['# Database and text access\n',
         'The engine executable talks to SQLite databases in two roles: it **reads rows of the game database** (Gameplay, Configuration, Localization) for things it needs itself (fonts, audio, colors, victories, features), '
         'and it **owns two databases** of its own: `Mods.sqlite` (the mod framework: which mods and files exist, which are enabled) and `HallofFame.sqlite` (game summary and statistics). '
         'This section lists every SQL statement that appears as a literal in the exe (%d), grouped by table.\n' % len(sql),
         '**Reading the tables.** A table name that is also a table of the game database (`Features`, `Eras`, `Victories`, `Colors`...) shows which of its **columns the exe consumes**, so a mod that adds a column there is not seen by the exe, '
         'and one that changes an existing column affects the exe side too. Statements built at run time (table names assembled from parts) are not in this list.\n',
         'Verified: each statement is a string literal in the exe and the function that uses it. Inferred: which database it runs against (decided from the table names and the function).\n',
         '| Database | Statements |', '|---|---|']
    for d, n in dbs.most_common():
        L.append('| %s | %d |' % (esc(d), n))
    L.append('\nPages: [tables](tables.md) (what is read or written per table), [all statements](statements.md), [the gameplay XML data format](xml-format.md) (what the XML loader accepts).\n')

    def tbl(title, intro, items):
        L.append('\n## %s\n' % title)
        L.append(intro + '\n')
        L.append('| Table | Operations | Columns seen | Used by |')
        L.append('|---|---|---|---|')
        for (d, t), v in sorted(items, key=lambda kv: kv[0][1].lower()):
            L.append('| `%s` | %s | %s | %s |' % (esc(t), ', '.join('%s %d' % (o, n) for o, n in v['ops'].most_common()), esc(', '.join(sorted(v['cols']))[:160]) or '—',
                                                esc(', '.join('`%s`' % f for f in list(v['fns'])[:2]))))
    tbl('Game database tables the exe reads', 'These are queried by the engine for its own use. Columns are those named in the statements.', game)
    add('exedb/index.md', 'Database and text access', '\n'.join(L) + '\n')

    L = ['# Tables used by the exe\n', 'Every table named in a statement, grouped by the database it runs against (inferred).\n']
    for title, items in (('Mod framework (Mods.sqlite)', mods), ('Game summary (HallofFame.sqlite)', fame), ('Game databases', game)):
        L.append('\n## %s (%d tables)\n' % (title, len(items)))
        L.append('| Table | Operations | Columns seen | Functions |')
        L.append('|---|---|---|---|')
        for (d, t), v in sorted(items, key=lambda kv: kv[0][1].lower()):
            L.append('| <a id="%s"></a>`%s` | %s | %s | %s |' % (safe(t + '-' + d[:4]), esc(t), ', '.join('%s %d' % (o, n) for o, n in v['ops'].most_common()), esc(', '.join(sorted(v['cols']))[:200]) or '—',
                                                           esc(', '.join('`%s`' % f for f in list(v['fns'])[:3]))))
    add('exedb/tables.md', 'Tables used by the exe', '\n'.join(L) + '\n')

    L = ['# SQL statements in the exe\n', 'Grouped by the subsystem of the function that uses them. `?` and `@name` are bound parameters.\n']
    groups = collections.OrderedDict()
    for e in sorted(sql, key=lambda e: (subsystem(e), e['id'])):
        groups.setdefault(subsystem(e), []).append(e)
    for g, es in groups.items():
        L.append('<details markdown="1"><summary>%s (%d)</summary>\n' % (esc(g), len(es)))
        L.append('| Statement | Used by | Database |')
        L.append('|---|---|---|')
        for e in es:
            L.append('| <a id="%s"></a>`%s` | %s | %s |' % (e['id'][7:], esc(e['sql']), fn_names(e), esc(e['database'].split(' (')[0])))
        L.append('\n</details>\n')
    add('exedb/statements.md', 'SQL statements in the exe', '\n'.join(L) + '\n')

    L = ['# Text keys the exe refers to\n',
         '%d `LOC_` keys appear as literals in the exe. Most name maps and scenarios (`LOC_MAP_*`, `LOC_*_SCENARIO_*`) and a few system messages; the engine otherwise gets its texts from the database, so changing these keys '
         'in a text file changes what the exe shows for them.\n' % len(keys), '| Key | Used by |', '|---|---|']
    for k in keys:
        L.append('| <a id="%s"></a>`%s` | %s |' % (safe(k['key']), esc(k['key']), fn_names(k)))
    add('exedb/text-keys.md', 'Text keys in the exe', '\n'.join(L) + '\n')
