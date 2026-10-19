"""Audio vocabulary of the engine exe: the sound event, state, parameter and playlist names the audio systems refer to, grouped by the function that uses them.
Input : linux_depot/out/strmaps.pkl (ASCII strings with referencing functions), findings/data/exe_function_index.json (function names)
Output: data/exe_audio.json (entities exeaudio:<function>:<name>)."""
import collections, json, os, pickle, re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
ws, ls, wm, lm = pickle.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'strmaps.pkl'), 'rb'))
names = {}
rva_of = {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            n = re.sub(r'\(.*$', '', r[0])
            names.setdefault(int(v, 16), n)
            rva_of.setdefault(n, '0x' + v)
AUDIO = re.compile(r'Audio|Sound|Music|Wwise|AudioMiner|LLAudio')
by = collections.defaultdict(set)
for a, s in ws.items():
    s = s.decode('latin1') if isinstance(s, bytes) else s
    if re.match(r'^[A-Za-z][A-Za-z0-9_]{3,60}$', s):
        for f in wm.get(a, ()):
            n = names.get(f, '')
            if AUDIO.search(n):
                by[n].add(s)
def style(s):
    if re.match(r'^[A-Z0-9_]+$', s):
        return 'UPPER_CASE (state, switch, parameter or enum value)'
    if re.match(r'^[A-Z][a-z0-9]+(_[A-Za-z0-9]+)+$', s):
        return 'Event-style name (words joined by underscores)'
    return 'other name'
ents = []
for fn, ss in sorted(by.items()):
    for s in sorted(ss):
        ents.append({'id': 'exeaudio:%s:%s' % (fn, s), 'function': fn, 'function_rva': rva_of.get(fn), 'name': s, 'style': style(s),
                     'availability': 'exe', 'status': 'verified',
                     'evidence': [{'kind': 'exe-string', 'note': 'string literal referenced by %s' % fn}]})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_audio.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'names in', len(by), 'functions')
