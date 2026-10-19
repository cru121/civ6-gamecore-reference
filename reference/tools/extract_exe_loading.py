"""Game start, save and load sequence: the state machine of LoadGameViewState::LaunchNextStage (0x84870), the steps of GameCore::Serializer::Manager::UnserializeGameState (0x16e340), the save location
flags (GetSaveLocation 0x168310), the metadata keys of a save (SaveMetaData 0x16d500, ApplyModdingState 0x1639b0) and the gameplay logging options read while loading.
Input : linux_depot/out/exetrace/save_decomp.txt (DecompList.java on ghi-exe, RVAs in save_rvas.txt), data/exe_options.json (to link the logging options)
Output: data/exe_loading.json (entities exeload:<kind>:<name>)."""
import collections, json, os, re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
BS = chr(92)
text = open(os.path.join(ROOT, 'linux_depot', 'out', 'exetrace', 'save_decomp.txt'), encoding='utf8').read().replace('\r', '')
ch = {c.split('\t')[0].strip().lower(): c for c in re.split(r'\n?@@@ ', text)[1:]}
opts = {o['key']: o for o in json.load(open(os.path.join(BASE, 'data', 'exe_options.json'), encoding='utf8'))}
CRLF = BS + 'r' + BS + 'n'
TAB = BS + 't'


def clean(t):
    return t.replace(CRLF, '').replace(TAB, '')


# 1. the load state machine
fn = ch['0x84870']
parts = re.split(r'\n\s*case (\d+):', fn)
STATES = collections.OrderedDict()
for i in range(1, len(parts), 2):
    n = int(parts[i])
    b = parts[i + 1]
    items = []
    for m in re.finditer(r'"([^"]*)"', b):
        t = m.group(1)
        if 'BuildAgent' in t or t.startswith('[%04d') or t.endswith('.log'):
            continue
        t = clean(t)
        if t not in items:
            items.append(t)
    markers = [t[:-len(' Begin')] for t in items if t.endswith(' Begin')]
    stage = [t[len('Stage: '):] for t in items if t.startswith('Stage: ')]
    sub = [t.lstrip(',')[:-len(' took %.4f seconds')] for t in items if t.startswith(',') and t.endswith('took %.4f seconds')]
    whole = [t[:-len(' took %.4f seconds')] for t in items if t.endswith('took %.4f seconds') and not t.startswith(',')]
    STATES[n] = {'markers': markers, 'stage': stage, 'sub': sub, 'whole': whole}
OPTS = []
b3 = parts[parts.index('3') + 1]
for t in re.findall(r'"([A-Za-z_]+)"', b3):
    if t in opts and t not in [o[0] for o in OPTS]:
        OPTS.append([t, None])
    elif t.isupper() and '_' in t and OPTS and OPTS[-1][1] is None:
        OPTS[-1][1] = t
TRANS = {
    0: ('1', 'Entry: moves on to state 1 (to state 11, the failure state, when the start fails).'),
    1: ('2 or 4', 'Asks the serializer for the request type (function 0x167ce0): when the result is 2 (inferred: a saved game is to be loaded) the next state is 4, otherwise 2.'),
    2: ('3', 'Configure Content: the game content is configured and the asset load restarted; then state 3 (11 on failure).'),
    3: ('6 or 7', 'Reads the gameplay logging options (listed below), then goes to 6 (new game) or 7 (unserialize a game state): the value is (x != 0) + 6 for a pointer x read in this state (inferred: whether a saved game stream was loaded).'),
    4: ('5', 'Loads the save file, then state 5 (11 on failure).'),
    5: ('2', 'Save load pending: when done the mod state is applied (`ApplyModdingState`) and the sequence continues with Configure Content (state 2); 11 on failure.'),
    6: ('8', 'Starts a new game (`InitializeNewGame`), records the `StartupGameTimings` numbers, goes to state 8; 11 on failure.'),
    7: ('(not read)', 'Unserializes the game state, initialises the cache, runs post-initialisation and records the timings; the successor state was not read out.')}
TITLE = {0: 'Start', 1: 'Decide: load a save or start new', 2: 'Configure Content', 3: 'Set gameplay logging', 4: 'Load a save file', 5: 'Save load pending (apply mod state)', 6: 'New game', 7: 'Unserialize game state'}
ents = []
for n, d in STATES.items():
    if n > 7:
        continue
    ents.append({'id': 'exeload:state:%d' % n, 'kind': 'state', 'name': str(n), 'title': TITLE.get(n, ''), 'detail': TRANS[n][1], 'next': TRANS[n][0],
                 'stage_label': d['stage'], 'log_markers': d['markers'], 'timed_steps': d['sub'], 'timed_blocks': d['whole'], 'function': 'LoadGameViewState::LaunchNextStage', 'function_rva': '0x84870',
                 'availability': 'exe', 'status': 'verified' if n in (2, 4, 5, 6, 7) else 'inferred',
                 'evidence': [{'kind': 'exe-disassembly', 'note': 'case %d of the state switch in LoadGameViewState::LaunchNextStage (0x84870), decompiled; transition conditions are partly inferred' % n}]})
for o, lid in OPTS:
    ents.append({'id': 'exeload:logging-option:%s' % o, 'kind': 'logging-option', 'name': o, 'title': lid or '',
                 'detail': 'Option read in state 3 (section Gameplay of %s)%s.' % (opts[o]['file'], (', passed on as log id `%s`' % lid) if lid else ''),
                 'option_id': opts[o]['id'], 'function': 'LoadGameViewState::LaunchNextStage', 'function_rva': '0x84870', 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': 'option name and log id string read in state 3 of LaunchNextStage'}]})
uns = [clean(t).replace(' - Complete', '').lstrip(',') for t in re.findall(r'"(' + re.escape(TAB) + r',[A-Za-z]+ - Complete' + re.escape(CRLF) + r')"', ch['0x16e340'])]
uns = list(dict.fromkeys(uns))
for k, u in enumerate(uns):
    ents.append({'id': 'exeload:unserialize-step:%s' % u, 'kind': 'unserialize-step', 'name': u, 'title': 'step %d' % (k + 1),
                 'detail': 'Logged as "%s - Complete" by UnserializeGameState when the step is done (order of the messages in the code).' % u,
                 'function': 'GameCore::Serializer::Manager::UnserializeGameState', 'function_rva': '0x16e340', 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': 'completion messages of UnserializeGameState (0x16e340)'}]})
for k in ('AccountReference', 'IsDirectory', 'IsAutosave', 'IsQuicksave', 'IsPrevious'):
    ents.append({'id': 'exeload:save-location-key:%s' % k, 'kind': 'save-location-key', 'name': k, 'title': '', 'detail': 'Field name written for a save location by GetSaveLocation (a table handed to the UI scripts).',
                 'function': 'GameCore::Serializer::Manager::GetSaveLocation', 'function_rva': '0x168310', 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': 'field name pushed by GetSaveLocation (0x168310), decompiled'}]})
for k, d in (('MetaDataVersion', 'Version of the save metadata layout (written by SaveMetaData).'), ('AppVersion', 'Game version, written as "%d.%d.%d.%d (%d)" from the application version fields.'),
             ('DisplayName', 'Display name of the save.'), ('IsMod', 'Read back by ApplyModdingState (`SELECT Value from MetaData where Name = \'IsMod\'`): whether the game was started with mods.')):
    ents.append({'id': 'exeload:metadata-key:%s' % k, 'kind': 'metadata-key', 'name': k, 'title': '', 'detail': d,
                 'function': 'GameCore::Serializer::Manager::SaveMetaData' if k != 'IsMod' else 'GameCore::Serializer::Manager::ApplyModdingState',
                 'function_rva': '0x16d500' if k != 'IsMod' else '0x1639b0', 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': 'key of the MetaData table of a save, written in SaveMetaData (0x16d500) / read in ApplyModdingState (0x1639b0)'}]})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_loading.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'entries;', dict(collections.Counter(e['kind'] for e in ents)))
for e in ents:
    if e['kind'] == 'state':
        print(e['name'], e['title'], '|', e['stage_label'], e['log_markers'], e['timed_steps'], e['timed_blocks'], e['next'])
print(OPTS)
print(uns)
