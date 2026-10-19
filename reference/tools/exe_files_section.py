"""Page exe/files.md: files, folders and paths the engine exe refers to. Called from build.py: exe_files_section.make(add, entries, meta)
Data: data/exe_files.json, data/exe_files_meta.json (tools/extract_exe_files.py)."""
import collections, re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def fn_cell(e):
    names = [f['name'] or f['rva'] for f in e['functions'][:2]]
    more = e['function_count'] - len(names)
    return esc('; '.join('`%s`' % n for n in names) + (' (+%d more)' % more if more > 0 else '')) if names else '—'


def make(add, entries, meta):
    by = collections.OrderedDict()
    for e in entries:
        by.setdefault(e['kind'], []).append(e)
    logs = by.get('log', [])
    seen = [e for e in logs if e['seen_in_logs_folder']]
    L = ['# Files, folders and paths in the engine executable\n',
         'Every file name, folder and path that the code of `CivilizationVI.exe` refers to as a literal string, with the function that uses it. This tells you **what the engine reads and writes**: '
         'which log files it creates, which option and data files it loads, where it looks for mods and maps, and which database files it opens. '
         'It does not show names the engine builds at run time (for example `%s.log`), and files that GameCore (the rules library) writes are not here, such as the `AI_*.csv` and `Game_*.csv` logs.\n',
         'Paths starting with `../../../` are relative to the game\'s binary folder; `Base/` is the base game folder and `DLC/` holds the expansions. **All entries are verified string literals**; '
         'what each file is for is inferred from the name and the function that uses it.\n',
         '## Log files the exe writes\n',
         '%d log names appear in the exe; %d of them are also present in a normal `Logs` folder of an installed game (the rest are written only in special modes, or in builds and settings that enable them, for example when a logging option in the '
         '[option files](options.md) is on). The `Logs` folder is `AppData/Local/Firaxis Games/Sid Meier\'s Civilization VI/Logs`.\n' % (len(logs), len(seen)),
         '| Log file | Written by | In a normal Logs folder |', '|---|---|---|']
    for e in logs:
        L.append('| <a id="%s"></a>`%s` | %s | %s |' % (safe(e['id']), esc(e['text']), fn_cell(e), 'yes' if e['seen_in_logs_folder'] else '—'))
    if meta.get('logs_folder_only'):
        L.append('\nFiles found in a normal `Logs` folder that **no string in the exe names**: ' + ', '.join('`%s`' % f for f in meta['logs_folder_only']) +
                 '. They are written by GameCore (the AI and game statistics csv files, `GameCore.log`, `UnitOperations.log`, `AStar_*.log`), or their names are built from parts at run time (`FiraxisLive.log`, `ForgeUI_BLPTextureLoader.log`).')

    def table(kind, title, intro, cols=('Name', 'Used by')):
        es = by.get(kind, [])
        if not es:
            return
        L.append('\n## %s\n' % title)
        L.append(intro + '\n')
        L.append('| %s | %s |' % cols)
        L.append('|---|---|')
        for e in es:
            L.append('| <a id="%s"></a>`%s` | %s |' % (safe(e['id']), esc(e['text']), fn_cell(e)))

    table('user or runtime file', 'Option, user and runtime files', 'Files in the user data folder or next to the game that the exe loads or creates. The four `*Options.txt` files are described in [the option files reference](options.md).')
    table('folder', 'Folders and sub-folders', 'Folder names the code uses: the user data sub-folders (`Logs`, `Dumps`, `Saves`, `Temp`), the save sub-folders (`auto`, `quick`, `Hotseat`, `Multi`, `Single`, `WorldBuilder`), the content roots (`Base`, `DLC`) and UI context names.')
    table('database', 'Database files', 'The databases the exe opens or creates: gameplay, configuration, localization and modding databases in the install, `Mods.sqlite` and `HallofFame.sqlite` in the user folder, and the debug dumps under `Cache/`.')
    table('file mask', 'File masks and extensions', 'Patterns used when the exe scans folders for content; the first four are how mods, maps and scenarios are discovered.')
    es = by.get('install path', [])
    if es:
        groups = collections.OrderedDict()
        for e in es:
            t = re.sub(r'^(\.\./)+|^/', '', e['text'])
            key = t.split('/')[0] + ('/' + t.split('/')[1] if t.split('/')[0] in ('Base', 'DLC', 'Platforms') and '/' in t else '')
            if key == '' or ('.' in key and '/' not in t):
                key = '(game root and root files)'
            groups.setdefault(key, []).append(e)
        L.append('\n## Install layout paths\n')
        L.append('Paths inside the game folders, grouped by their first folders. They show where the engine expects its data: databases under `Base/Assets/Database`, text under `Base/Assets/Text`, UI definitions under `Base/Assets/UI`, '
                 'and per-platform folders for every platform the engine has ever targeted (the exe lists them, including some that never shipped).\n')
        for g, ee in groups.items():
            L.append('<details markdown="1"><summary>%s (%d)</summary>\n' % (esc(g), len(ee)))
            L.append('| Path | Used by |')
            L.append('|---|---|')
            for e in ee:
                L.append('| <a id="%s"></a>`%s` | %s |' % (safe(e['id']), esc(e['text']), fn_cell(e)))
            L.append('\n</details>\n')
    table('other file', 'Other files', 'Remaining file names the code mentions: UI art, fonts, cursors, telemetry configuration, benchmark saves, and similar.')
    table('asset ownership check', 'Asset ownership check', 'One function (`App::Ownership::Local::Startup`) lists a set of hash-named asset files under `Base/Assets` and tests whether they exist, which is how the exe decides which content packages are present.')
    add('exe/files.md', 'Files and paths', '\n'.join(L) + '\n')
