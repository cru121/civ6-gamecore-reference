"""Files, folders and paths the engine exe refers to: log files it writes, option and data files, folders, database files, mod discovery masks, install layout.
Inputs : linux_depot/out/widestr.pkl (tools/exe/widestr.py: referenced UTF-16 strings), linux_depot/out/strmaps.pkl (ASCII strings with referencing functions),
         findings/data/exe_function_index.json (names for the referencing functions), the player's Logs folder (names only, to mark logs seen in a normal install)
Output : data/exe_files.json (entities exefile:<kind>:<string>)."""
import collections, json, os, pickle, re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
O = os.path.join(ROOT, 'linux_depot', 'out')
wide = pickle.load(open(os.path.join(O, 'widestr.pkl'), 'rb'))
ws, ls, wm, lm = pickle.load(open(os.path.join(O, 'strmaps.pkl'), 'rb'))
names = {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            names.setdefault(int(v, 16), re.sub(r'\(.*$', '', r[0]))
LOGDIR = os.path.expandvars('%LOCALAPPDATA%/Firaxis Games/Sid Meier\'s Civilization VI/Logs')
seen_logs = set(os.listdir(LOGDIR)) if os.path.isdir(LOGDIR) else set()

strings = {}     # (text, enc) -> set(funcs)
for a, (s, fs) in wide.items():
    strings.setdefault((s, 'utf-16'), set()).update(fs)
for a, s in ws.items():
    s = s.decode('latin1') if isinstance(s, bytes) else s
    strings.setdefault((s, 'ascii'), set()).update(wm.get(a, ()))

EXT = r'(log|csv|txt|xml|sql|sqlite|db|json|lua|ini|dat|cfg|bin|dds|blp|artdef|dep|modinfo|modfragment|civ6save|civ6map|civ6cfg|zip|bk2|bnk|ani|ttf|otf|fpk|bs|png)'
FILE = re.compile(r'^[\w .\-/\\%{}:$*]*\.' + EXT + r'$', re.I)
DIRS = {'Logs', 'Dumps', 'Saves', 'Temp', 'DLC', 'Base', 'AutoSave', 'AutoConfig', 'ArtDefs', 'Profile', 'Mods', 'Maps', 'Scenarios', 'Challenges', 'auto', 'auto/prev', 'quick', 'Hotseat', 'Multi', 'Single', 'WorldBuilder',
        'Subtitles/', 'FrontEnd', 'InGame', 'LoadScreen'}
ents = []
def add(kind, text, enc, funcs, note=''):
    fl = sorted(funcs)
    ents.append({'id': 'exefile:%s:%s' % (kind, text), 'kind': kind, 'text': text, 'encoding': enc,
                 'functions': [{'rva': '0x%x' % f, 'name': names.get(f)} for f in fl[:4]], 'function_count': len(fl),
                 'note': note, 'seen_in_logs_folder': (text in seen_logs) if kind == 'log' else None,
                 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': '%s string literal referenced by %d function(s) of CivilizationVI.exe' % (enc, len(fl))}]})

owner = []
for (s, enc), fs in sorted(strings.items()):
    if len(s) < 3 or len(s) > 130 or not fs:
        continue
    if ' ' in s and not s.startswith(chr(92) + 'Firaxis'):
        continue
    if re.match(r'^(\.\./)+Base/Assets/Civ6_[0-9a-f]{16}\.xml$', s):
        owner.append((s, fs)); continue
    if re.match(r'^\*\.\w+$', s) or s in ('.modinfo', '.Civ6Map', '.Civ6Save', '.Civ6Cfg', '.civ6map', '.lua', '.XML', '.fpk', '.csv'):
        add('file mask', s, enc, fs); continue
    if re.search(r'\.(log)$', s, re.I) or re.search(r'(log|Log)\.(csv|txt)$', s) or s in ('Profile.csv', 'AutoArchive.csv', 'FireFX.csv', 'VFX.csv', 'VFXMesh.csv', 'UIWarnings.csv', 'ModelVisTypes_%u.csv') or re.match(r'Game_%02d_GameCoreProfile\.csv', s):
        add('log', s, enc, fs); continue
    if re.search(r'\.(sqlite|sql|db)$', s, re.I):
        add('database', s, enc, fs); continue
    if s in ('AppOptions.txt', 'UserOptions.txt', 'GraphicsOptions.txt', 'EOSOptions.txt', 'SoundOpts.txt', 'InputSettings.json', 'UserContext.bin', 'Banks.ini', 'Init.bnk', 'WorldBuilderTemp.db', 'CurrentPackage.zip'):
        add('user or runtime file', s, enc, fs); continue
    if re.match(r'^(\.\./)+', s) or s.startswith(('Base/', 'Platforms/', 'ForgeUI_Assets', 'Database/', 'UI/', 'GameConfig/', 'App/', 'Assets/')) or s.startswith('/') and FILE.match(s):
        add('install path', s, enc, fs); continue
    if s in DIRS or re.match(r"^\\(Challenges|CivTechLogs|Firaxis Games)", s) or s == 'c:/windows/fonts/':
        add('folder', s, enc, fs); continue
    if FILE.match(s) and not re.match(r'^\w+\.(dll|exe)$', s, re.I) and ' ' not in s.strip():
        add('other file', s, enc, fs); continue
if owner:
    allf = set()
    for _, fs in owner:
        allf |= set(fs)
    add('asset ownership check', '../../../Base/Assets/Civ6_<16 hex digits>.xml', 'utf-16', allf,
        '%d asset file names listed in one function that decides content ownership; the names are hashes' % len(owner))
merged = collections.OrderedDict()
for e in ents:
    k = (e['kind'], e['text'])
    if k in merged:
        m = merged[k]
        m['encoding'] = 'ascii and utf-16' if m['encoding'] != e['encoding'] else m['encoding']
        have = {f['rva'] for f in m['functions']}
        m['functions'] += [f for f in e['functions'] if f['rva'] not in have]
        m['functions'] = m['functions'][:4]
        m['function_count'] += e['function_count']
    else:
        merged[k] = e
ents = list(merged.values())
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_files.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
named = {e['text'] for e in ents if e['kind'] == 'log'}
meta = {'logs_folder_only': sorted(f for f in seen_logs if f not in named and os.path.splitext(f)[0] + '.log' not in named)}
json.dump(meta, open(os.path.join(BASE, 'data', 'exe_files_meta.json'), 'w', encoding='utf8'), indent=1)
print(len(ents), 'entries;', collections.Counter(e['kind'] for e in ents))
print('logs seen in the Logs folder:', sum(1 for e in ents if e['seen_in_logs_folder']), 'of', sum(1 for e in ents if e['kind'] == 'log'))
