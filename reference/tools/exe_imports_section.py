"""Page exe/imports.md: DLLs and APIs the Windows exe imports. Called from build.py: exe_imports_section.make(add, imports, dlls)
Data: data/exe_imports.json, data/exe_import_dlls.json (tools/extract_exe_imports.py)."""
import collections, re

ROLE = {
    'HavokScript_FinalRelease.dll': ('Lua virtual machine (Havok Script)', 'game'),
    'DatabaseDLL_FinalRelease.dll': ('SQLite database layer: initialise, open connections, logger', 'game'),
    'Localization_FinalRelease.dll': ('Text database and language handling (strings, language lists, coverage)', 'game'),
    'bink2w64.dll': ('Bink video playback (intro movies, subtitles)', 'game'),
    'steam_api64.dll': ('Steamworks client API (achievements, friends, workshop, overlay, callbacks)', 'platform'),
    'EOSSDK-Win64-Shipping.dll': ('Epic Online Services SDK (lobbies, sessions, networking, ownership)', 'platform'),
    'WINHTTP.dll': ('HTTP client (Firaxis Live, telemetry, downloads)', 'system'),
    'WS2_32.dll': ('Windows sockets (multiplayer transport)', 'system'),
    'IPHLPAPI.DLL': ('Network adapter information', 'system'),
    'dbghelp.dll': ('Symbols and mini dumps (crash reports)', 'system'),
    'd3d11.dll': ('Direct3D 11 (device creation)', 'system'),
    'dxgi.dll': ('DXGI (adapters and swap chains)', 'system'),
    'IMM32.dll': ('Input method editors (text entry for Asian languages)', 'system'),
    'SETUPAPI.dll': ('Device enumeration (hardware information)', 'system'),
    'VERSION.dll': ('File version information', 'system'),
    'SHLWAPI.dll': ('Path and string helpers', 'system'),
    'SHELL32.dll': ('Shell: known folders, opening URLs and folders', 'system'),
    'ADVAPI32.dll': ('Registry and security APIs', 'system'),
    'KERNEL32.dll': ('Core Windows API: files, threads, memory, modules', 'system'),
    'USER32.dll': ('Windows, messages and input', 'system'),
    'GDI32.dll': ('Graphics device interface', 'system'),
    'ole32.dll': ('COM', 'system'),
    'OLEAUT32.dll': ('COM automation strings', 'system'),
    'WINMM.dll': ('Multimedia timers', 'system'),
    'MSVCP140.dll': ('C++ standard library runtime', 'runtime'),
    'VCRUNTIME140.dll': ('C++ runtime', 'runtime')}


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def role(d):
    if d in ROLE:
        return ROLE[d]
    if d.lower().startswith('api-ms-win-crt'):
        return ('C runtime (universal CRT): ' + d.split('-')[4], 'runtime')
    return ('', 'other')


def make(add, imports, dlls):
    by = collections.defaultdict(list)
    for e in imports:
        by[e['dll']].append(e)
    L = ['# Imports and dependencies\n',
         'The Windows executable is not a single block: it loads **game libraries** that sit next to it (`Base/Binaries/Win64Steam`), two **platform SDKs** (Steam and Epic) and the usual Windows and C runtime DLLs. '
         'This page lists every DLL the executable imports and, for each function, how many functions of the exe call it. Read from the import table of `CivilizationVI.exe` (DX11, July 2024); the role of each DLL is inferred from its name and the functions imported.\n',
         '**Why it matters for modding.** The Lua virtual machine (`HavokScript_FinalRelease.dll`), the database layer (`DatabaseDLL_FinalRelease.dll`) and the text system (`Localization_FinalRelease.dll`) are separate DLLs, so a hook on a Lua or database call can be placed in that DLL as well as in the exe. '
         'The exe imports only 4 functions from the database DLL: `Initialize`, `Shutdown`, `CreateConnection`, `SetDefaultLogger`.\n',
         '## DLLs\n', '| DLL | Role (inferred) | Kind | Imports | Called from the exe |', '|---|---|---|---|---|']
    order = {'game': 0, 'platform': 1, 'system': 2, 'runtime': 3, 'other': 4}
    for d in sorted(dlls, key=lambda d: (order[role(d['dll'])[1]], d['dll'].lower())):
        r, k = role(d['dll'])
        name = '[%s](#%s)' % (d['dll'], safe(d['dll'])) if k in ('game', 'platform') else d['dll']
        L.append('| %s | %s | %s | %d | %d |' % (name, esc(r) or '—', k, d['imports'], d['called']))
    for kind, title in (('game', 'Game libraries'), ('platform', 'Platform SDKs')):
        for d in dlls:
            if role(d['dll'])[1] != kind:
                continue
            es = by[d['dll']]
            L.append('\n## <a id="%s"></a>%s\n' % (safe(d['dll']), d['dll']))
            L.append('%s. %d imports.\n' % (role(d['dll'])[0], len(es)))
            L.append('<details markdown="1"><summary>%d functions</summary>\n' % len(es))
            L.append('| Function | Calling functions | Examples |')
            L.append('|---|---|---|')
            for e in sorted(es, key=lambda e: (-e['caller_count'], e['display'])):
                ex = ', '.join('`%s`' % (c['name'] or c['rva']) for c in e['callers'][:2]) or '—'
                L.append('| `%s` | %d | %s |' % (esc(e['display'][:110]), e['caller_count'], esc(ex)))
            L.append('\n</details>\n')
    sysimp = [e for e in imports if role(e['dll'])[1] == 'system']
    L.append('\n## System APIs by purpose\n')
    L.append('The Windows API functions the exe imports, grouped by what they do (a pattern match on the name; `other` is not listed). Useful to see how the exe touches the file system, the network, the registry and other processes.\n')
    cats = collections.OrderedDict((c, []) for c in ('file system', 'network', 'registry and system information', 'processes, threads and modules', 'windowing and input', 'debugging and crash handling'))
    for e in sysimp:
        if e['category'] in cats:
            cats[e['category']].append(e)
    for c, es in cats.items():
        if not es:
            continue
        L.append('\n### %s (%d)\n' % (c, len(es)))
        L.append('<details markdown="1"><summary>%d functions</summary>\n' % len(es))
        L.append('| Function | DLL | Calling functions |')
        L.append('|---|---|---|')
        for e in sorted(es, key=lambda e: (-e['caller_count'], e['api'])):
            L.append('| <a id="%s"></a>`%s` | %s | %d |' % (safe(e['dll'] + '-' + e['api']), esc(e['api']), esc(e['dll']), e['caller_count']))
        L.append('\n</details>\n')
    add('exe/imports.md', 'Imports and dependencies', '\n'.join(L) + '\n')
