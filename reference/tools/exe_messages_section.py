"""Page exe/messages.md: log and error messages of the exe. Called from build.py: exe_messages_section.make(add, entries)
Data: data/exe_messages.json (tools/extract_exe_messages.py)."""
import collections, re

ORDER = ['Modding', 'Database', 'Localization', 'Lua libraries', 'Assets and art definitions', 'UI (ForgeUI)', 'GameCore bridge', 'World view (3D map)', 'Application and startup', 'Network and multiplayer', 'Firaxis Live']
OPEN = {'Modding', 'Database', 'Localization', 'Lua libraries', 'Assets and art definitions'}


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def make(add, entries):
    by = collections.OrderedDict((k, [e for e in entries if e['subsystem'] == k]) for k in ORDER)
    L = ['# Log and error messages\n',
         'Messages that the engine executable writes to its log files or shows when something goes wrong, as they appear in the code (%d, grouped by the subsystem of the function that uses them). '
         'Search for a fragment of a line from a log file to find what produces it. `%%s`, `%%d` and similar are filled in at run time.\n' % len(entries),
         'Verified: the text is a string literal and the named function references it. Inferred: the log file column (the subsystem normally writes to that log, see [files and paths](files.md)); '
         'what condition triggers a message is not analysed here, the function name is the best hint. Third-party library messages (OpenSSL, curl, zlib), the shader language and strings whose function has no name are left out.\n',
         '## Subsystems\n', '| Subsystem | Messages | Usual log file |', '|---|---|---|']
    for k in ORDER:
        es = by[k]
        if es:
            log = next((e['likely_log'] for e in es if e['likely_log']), None)
            L.append('| [%s](#%s) | %d | %s |' % (k, safe(k), len(es), ('`%s`' % log) if log else '—'))
    for k in ORDER:
        es = by[k]
        if not es:
            continue
        L.append('\n## <a id="%s"></a>%s\n' % (safe(k), k))
        L.append('<details%s markdown="1"><summary>%d messages</summary>\n' % (' open' if k in OPEN else '', len(es)))
        L.append('| Message | Function |')
        L.append('|---|---|')
        for e in sorted(es, key=lambda e: e['text'].lower()):
            fn = '`%s`' % e['functions'][0]['name'] if e['functions'] else '—'
            L.append('| <a id="%s"></a>%s | %s |' % (e['id'][7:], esc(e['text']), esc(fn)))
        L.append('\n</details>\n')
    add('exe/messages.md', 'Log and error messages', '\n'.join(L) + '\n')
