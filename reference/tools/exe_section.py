"""Pages for the engine-exe section (option files, command-line switches, debug console). Called from build.py:
    exe_section.make(add, options, switches, console_data)
Entities come from data/exe_*.json (tools/extract_exe.py)."""
import re, collections


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def code(v):
    return '`%s`' % esc(v) if v not in (None, '') else '—'


def make(add, options, switches, console_data):
    cmds = console_data['commands']
    matched = console_data['matched_phrases']
    secs = collections.OrderedDict()
    for o in options:
        secs.setdefault(o['section'], []).append(o)
    files = collections.OrderedDict()
    for o in options:
        files.setdefault(o['file'] or '(not in any file)', collections.OrderedDict()).setdefault(o['section'], []).append(o)

    add('exe/index.md', 'Engine executable', '''# Engine executable (CivilizationVI.exe)

The game program itself, as opposed to GameCore: the settings it reads, the switches it accepts, and the debug console it hosts. None of this needs a mod,
but much of it is **debug and configuration functionality that Firaxis never documented**, so treat the descriptions as ours where they are marked inferred.

- [Option files reference](options.md): the %d options the exe registers, spread over four files (`AppOptions.txt`, `UserOptions.txt`, `GraphicsOptions.txt`, `EOSOptions.txt`), with section, type, description and file.
- [Command-line switches](command-line.md): %d fixed switches plus the generic `-<Key> <integer>` override for any integer option.
- [Files and paths](files.md): the log files the exe writes, option and data files, folders, databases, mod discovery masks and install layout paths it refers to.
- [.modinfo vocabulary](modinfo.md): every element, component type, criterion, property and status code the exe understands in a mod, cross-checked against the shipped mods.
- [Log and error messages](messages.md): the texts the exe writes to its logs or shows on errors, by subsystem, searchable by a fragment of a log line.
- [UI XML vocabulary](uixml.md): every attribute each ForgeUI control type reads from the UI XML files, checked against the game's own UI files.
- [Telemetry configuration](telemetry.md): the events and usage counters in the default telemetry configuration built into the exe.
- [Imports and dependencies](imports.md): the DLLs the exe loads (game libraries, Steam and Epic SDKs, Windows) and the functions it calls in them.
- [Audio vocabulary](audio.md): the sound event, state, volume and playlist names the exe passes to its audio system.
- [Event data fields](event-data.md): the fields of the GameCore events as read by the exe's handlers (offsets and widths).
- [Debug console](console.md): %d commands with help text from %d handlers, plus the %d command phrases the handlers match.

**How this was made.** The Windows executable (DX11, July 2024 build) was analysed statically: option registrations and command phrases are read from the
code that registers and matches them, switch names from the strings the start-up code compares, behaviour from disassembly. Function names come from the
Linux build of the same engine, which exports its symbol names. Statuses follow the [conventions](../conventions.md): **verified** means seen in the exe (and,
for options, also present in the option file the game writes); **inferred** follows from verified facts but was not tried in the running game.

**Not covered yet:** the Lua tables hosted by the exe (`UI`, `UILens`, `Controls`, `Network`, ...), the engine event buses, and the exe function map. Their
analysis exists as topic notes; they will become entity pages here.
''' % (len(options), len([s for s in switches if s['kind'] == 'fixed']),
       len(cmds), len({c['handler'] for c in cmds}), len(matched)))

    L = ['# Option files reference\n',
         "The exe registers %d options. The game writes them into four text files in `AppData/Local/Firaxis Games/Sid Meier's Civilization VI/`; each file is read at start-up and the comment line above every key is the description the exe carries. "
         'Keys are unique across all files, names are case sensitive, and every option below is in exactly one file. This page is the merged, searchable list.\n' % len(options),
         '**Value types.** *integer*: whole numbers, booleans are 0/1. *string*: free text. A blank **Default** means the exe passes no constant I could read, most often 0; it is not "none". '
         'Floating-point options are probably missing from this list: they use a different register convention and were not scanned.\n',
         '**Command line.** Integer options can also be set for one launch with `-Key value`; see [command-line switches](command-line.md).\n',
         '**Description.** Taken from the exe where its registration call could be read, otherwise from the comment in the option file (marked in the data as `options-file`). Options with no text have none anywhere.\n',
         '**Status.** *verified*: registered in the exe and present in the file the game writes. Sections can be split between files (for example `[Video]`, `[Debug]`).\n',
         '## Files and sections\n', '| File | Sections (options) |', '|---|---|']
    for fn, ss in files.items():
        L.append('| `%s` | %s |' % (fn, ', '.join('[%s](#%s) (%d)' % (sec, safe(sec), len(v)) for sec, v in ss.items())))
    L.append('')
    for sec, os_ in secs.items():
        L.append('\n## <a id="%s"></a>[%s]\n' % (safe(sec), sec))
        L.append('| Key | File | Type | Default | Description | Status |')
        L.append('|---|---|---|---|---|---|')
        for o in os_:
            L.append('| <a id="%s"></a>%s | `%s` | %s | %s | %s | %s |' % (
                safe(o['section'] + '.' + o['key']), o['key'], (o['file'] or '—').replace('.txt', ''), o['value_type'], code(o['default']),
                esc(o['description'] or '—'), o['status']))
    L.append('\n## Worth knowing\n')
    L.append('- `[General] AvailableViews` (GraphicsOptions): 0 = strategic view only, 1 = 3D only, 2 = both. World Builder is a strategic-view-only experience in practice.')
    L.append('- `[Debug]` (AppOptions) holds the switches behind the debug menu, the FireTuner (`EnableTuner`), World Builder (`EnableWorldBuilder`), GameCore event logging (`EnableGameCoreEventLog`) and terrain logging (`EnableTerrainLogging`).')
    L.append('- `[Gameplay]` and `[Interface]` (UserOptions) are the in-game Options menu; `[Multiplayer]` has the Play By Cloud webhook settings (`TurnWebHookURL`, `TurnWebHookFrequency`).')
    add('exe/options.md', 'Option files reference', '\n'.join(L) + '\n')

    L = ['# Command-line switches\n',
         'Pass these in the Steam launch options (or a shortcut). All are read by CivilizationVI.exe. Nothing here has been tried in the running game; the behaviour is read from the code.\n',
         '## Generic option override\n']
    g = [s for s in switches if s['kind'] == 'generic'][0]
    L.append('`%s`  *(%s)*\n' % (g['switch'], g['status']))
    L.append(g['effect'] + '\n')
    L.append('Handled by `%s`. Evidence: %s\n' % (g['function'], g['evidence'][0]['note']))
    L.append('## Fixed switches\n')
    L.append('| Switch | Effect | Handled by | Status |')
    L.append('|---|---|---|---|')
    for s in switches:
        if s['kind'] != 'fixed':
            continue
        L.append('| <a id="%s"></a>`%s` | %s | `%s` (`%s`) | %s |' % (safe(s['switch']), esc(s['switch']), esc(s['effect']), esc(s['function']), s['rva'], s['status']))
    L.append('\nThe `-NoAssert*` and `-FullDump` switches are read when the app sets up error handling; `-autoscript`, `-autoparams` and `-autojson` belong to the automation harness; the `--rail_*` switches are for the Rail platform, not Steam.')
    add('exe/command-line.md', 'Command-line switches', '\n'.join(L) + '\n')

    L = ['# Debug console\n',
         'Commands typed into the in-game debug console (the `UIE_DebugConsoleInput` event). Each handler of the event matches its own commands; `help all` prints the combined list. '
         'The console is only reachable when the debug UI is enabled (see `EnableDebugMenu` in [the option files](options.md#debug)); **not tried in the running game**.\n',
         '## Commands with help text\n']
    byh = collections.OrderedDict()
    for c in cmds:
        byh.setdefault((c['handler'], c['handler_rva']), []).append(c)
    for (h, rva), cs in byh.items():
        L.append('### %s\n' % h)
        L.append('Handler `%s`.\n' % rva)
        L.append('| Command | Description |')
        L.append('|---|---|')
        for c in cs:
            L.append('| <a id="%s"></a>`%s` | %s |' % (safe(c['handler_rva'] + '-' + c['command']), esc(c['command']), esc(c['description'] or '—')))
        L.append('')
    L.append('## Command phrases matched in the code\n')
    L.append('The handlers match commands one word at a time, so a command such as `terrain rebake` appears as `terrain` and then `rebake`. This table lists every phrase literal that a handler tests, in code order, '
             'with the engine functions called before the next phrase (**heuristic**: it can include calls that belong to a neighbouring check, and names with low confidence are left out). Phrases without help text are mostly '
             'sub-words of the commands above, but a few commands have no help line at all.\n')
    mh = collections.OrderedDict()
    for m in matched:
        mh.setdefault((m['handler'], m['handler_rva']), []).append(m)
    for (h, rva), ms in mh.items():
        L.append('<details markdown="1"><summary>%s (handler %s, %d phrases)</summary>\n' % (h, rva, len(ms)))
        L.append('| Phrase | Code | Calls (heuristic) |')
        L.append('|---|---|---|')
        for m in ms:
            calls = [re.sub(r'^[0-9a-f]+ ', '', c) for c in m['calls'] if ('[high]' in c or '[medium]' in c) and not re.search(r'ConsolePrintf|Platform::|String::|std::|EXP_', c)]
            L.append('| `%s` | `%s` | %s |' % (esc(m['phrase']), m['site'], esc('; '.join(x[:90] for x in calls[:3])) or '—'))
        L.append('\n</details>\n')
    add('exe/console.md', 'Debug console', '\n'.join(L) + '\n')
