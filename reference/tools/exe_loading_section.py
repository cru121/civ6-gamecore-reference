"""Page exe/loading.md: game start, save and load sequence. Called from build.py: exe_loading_section.make(add, entries)
Data: data/exe_loading.json (tools/extract_exe_loading.py)."""
import re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def make(add, entries):
    by = {}
    for e in entries:
        by.setdefault(e['kind'], []).append(e)
    L = ['# Game start, save and load sequence\n',
         'When a game starts (a new game or a loaded save) the exe runs one state machine, `LoadGameViewState::LaunchNextStage` (`0x84870`), and writes its progress to `LoadGameViewState.log` (see the [files](files.md) page). '
         'This page lists its states in the order the code reaches them, the log lines each state writes (useful to read a load log), the steps of the game state loader, the flags of a save location and the keys of the save metadata. '
         '**Verified**: state numbers, assigned next states, log texts and names (decompiled code and strings). **Inferred**: the conditions behind a transition and the meaning of state 8 and the failure state 11, which were not analysed.\n',
         '**Flow.** New game: `0 -> 1 -> 2 -> 3 -> 6 -> 8`. Loading a save: `0 -> 1 -> 4 -> 5 -> 2 -> 3 -> 7`. State 11 is the failure exit used by most states.\n',
         '## States\n', '| State | Name | Next | Log lines it writes | Timed steps | What it does |', '|---|---|---|---|---|---|']
    for e in by.get('state', []):
        marks = ', '.join('`%s Begin`' % m for m in e['log_markers']) + (', ' if e['log_markers'] and e['timed_blocks'] else '') + ', '.join('`%s took ...`' % m for m in e['timed_blocks'])
        lab = ('Stage label `Stage: %s`. ' % e['stage_label'][0]) if e['stage_label'] else ''
        L.append('| <a id="state-%s"></a>%s | %s | %s | %s | %s | %s%s |' % (e['name'], e['name'], esc(e['title']), esc(e['next']), marks or '—', ', '.join('`%s`' % t for t in e['timed_steps']) or '—', lab, esc(e['detail'])))
    L.append('\nEach block logs `<NAME> Begin` and `<NAME> took N seconds` with a timestamp prefix; sub-steps are logged as `,<step> took N seconds`. The times of new-game and load runs are also recorded under `Timings` / `StartupGameTimings` (keys `Session`, `InitializeNewGame`, `PostLoad`).\n')
    L.append('## Game state loader steps\n')
    L.append('`GameCore::Serializer::Manager::UnserializeGameState` (`0x16e340`) logs "<step> - Complete" in this order:\n')
    L.append('| # | Step |')
    L.append('|---|---|')
    for k, e in enumerate(by.get('unserialize-step', []), 1):
        L.append('| %d | <a id="unserialize-step-%s"></a>`%s` |' % (k, safe(e['name']), e['name']))
    L.append('\n## Gameplay logging options read in state 3\n')
    L.append('Switches of the [Gameplay section of UserOptions.txt](options.md) that are applied before the game starts; the second column is the log id the exe passes along.\n')
    L.append('| Option | Log id |')
    L.append('|---|---|')
    for e in by.get('logging-option', []):
        L.append('| <a id="logging-option-%s"></a>`%s` | %s |' % (safe(e['name']), e['name'], ('`%s`' % e['title']) if e['title'] else '—'))
    L.append('\n## Save location flags\n')
    L.append('Fields of the table `GetSaveLocation` builds for a save location (`0x168310`): ' + ', '.join('`%s`' % e['name'] for e in by.get('save-location-key', [])) + '.\n')
    L.append('## Save metadata\n')
    L.append('A save carries a `MetaData` table of name and value rows (`INSERT INTO MetaData (Name, Value) VALUES (?,?)`). The keys the exe writes or reads by name:\n')
    L.append('| Key | Meaning | Function |')
    L.append('|---|---|---|')
    for e in by.get('metadata-key', []):
        L.append('| <a id="metadata-key-%s"></a>`%s` | %s | `%s` (%s) |' % (safe(e['name']), e['name'], esc(e['detail']), esc(e['function'].split('::')[-1]), e['function_rva']))
    L.append('\nWhen a save is applied, `ApplyModdingState` also reads the save\'s `Players` (`CivilizationType`), `ModDependencies` (`ID`, `Title`), `StartPositions` (`Type`, `Value`) and `MapAttributes` (`Name` = `Ruleset`) tables; see the [database statements](../exedb/statements.md).\n')
    add('exe/loading.md', 'Game start, save and load sequence', '\n'.join(L) + '\n')
