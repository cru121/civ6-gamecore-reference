"""ArtDef vocabulary: which engine functions read which collection and parameter names of the .artdef files, matched with the parameter names and value types in the shipped .artdef files.
Input : linux_depot/out/strmaps.pkl (ASCII strings with referencing functions), findings/data/exe_function_index.json (function names), the game's *.artdef files (read in place; only names, value
        classes and counts are kept; never values or asset paths).
Output: data/exe_artdefs.json (entities exeart:<file stem>, one per template name stored in the files, such as Units or Camera) and data/exe_artdef_consumers.json (the reading functions).
A consumer (a ConfigureFromArtDefs-style function) is assigned to the template (artdef type) whose collection and parameter names cover most of the names the consumer uses (at least 50 percent
and clearly ahead of the second best); this assignment is an inference, the names themselves are verified."""
import collections, json, os, pickle, re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
ws, ls, wm, lm = pickle.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'strmaps.pkl'), 'rb'))
names, rva_of = {}, {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            n = re.sub(r'\(.*$', '', r[0])
            names.setdefault(int(v, 16), n)
            rva_of.setdefault(n, '0x' + v)

# the shipped artdef files: per file stem the collection and parameter names with value classes
CLS = re.compile(r'<Element class="AssetObjects\.\.([A-Za-z0-9]+)">(.*?)</Element>', re.S)
PARAM = re.compile(r'<m_ParamName text="([^"]*)"')
COLL = re.compile(r'<m_CollectionName text="([^"]*)"')
files = collections.defaultdict(lambda: {'files': [], 'params': collections.defaultdict(lambda: {'types': collections.Counter(), 'files': set(), 'count': 0}),
                                         'collections': collections.Counter(), 'template': set()})
for dp, dn, fn in os.walk(GAME):
    for f in fn:
        if f.lower().endswith('.artdef'):
            p = os.path.join(dp, f)
            s = open(p, encoding='utf8', errors='replace').read()
            stem = os.path.splitext(f)[0]
            t = re.search(r'<m_TemplateName text="([^"]*)"', s)
            d = files[t.group(1) if t and t.group(1) else stem]          # grouped by the template name stored in the file (Units covers Units, Unit_Bins, ...)
            rel = os.path.relpath(p, GAME).replace('\\', '/')
            d['files'].append(rel)
            d['template'].add(stem)
            for m in COLL.finditer(s):
                d['collections'][m.group(1)] += 1
            # a value element: class + (m_fValue etc.) + m_ParamName; scan for the class opening and the first ParamName after it
            for m in re.finditer(r'<Element class="AssetObjects\.\.([A-Za-z0-9]+)">', s):
                pm = PARAM.search(s, m.end(), m.end() + 4000)
                if pm:
                    e = d['params'][pm.group(1)]
                    e['types'][m.group(1).replace('Value', '')] += 1
                    e['files'].add(rel)
                    e['count'] += 1

# consumers
ID = re.compile(r'^[A-Za-z_][A-Za-z0-9_ .\-]{1,60}$')
FN = re.compile(r'ArtDef|Landmarks::Loading::|LandmarkArtDefManager')
INFRA = re.compile(r'^(AssetObjects::|BLP::)')            # serialization classes of the artdef format itself, not consumers
cons = collections.defaultdict(set)
for a, s in ws.items():
    s = s.decode('latin1') if isinstance(s, bytes) else s
    if ID.match(s):
        for f in wm.get(a, ()):
            n = names.get(f, '')
            if FN.search(n) and not INFRA.search(n):
                cons[n].add(s)


def vocab(stem):
    d = files[stem]
    return set(d['params']) | set(d['collections'])


assign = {}
rows = []
for n, ss in sorted(cons.items()):
    if len(ss) < 3:
        continue
    sc = sorted(((len(ss & vocab(st)) / float(len(ss)), len(ss & vocab(st)), st) for st in files), reverse=True)
    best, second = sc[0], sc[1]
    ok = best[0] >= 0.5 and best[0] >= second[0] + 0.1 and best[1] >= 3
    rows.append({'function': n, 'rva': rva_of.get(n, ''), 'names': sorted(ss), 'best': best[2], 'best_score': round(best[0], 2), 'best_hits': best[1], 'second': second[2], 'second_score': round(second[0], 2),
                 'assigned': best[2] if ok else None})
    if ok:
        assign.setdefault(best[2], []).append(rows[-1])

ents = []
for stem, d in sorted(files.items()):
    cs = assign.get(stem, [])
    read = set()
    for c in cs:
        read |= set(c['names'])
    params = []
    for name, e in sorted(d['params'].items(), key=lambda kv: (-kv[1]['count'], kv[0])):
        params.append({'name': name, 'types': dict(e['types']), 'files': len(e['files']), 'count': e['count'], 'read_by_exe': name in read,
                       'readers': [c['function'] for c in cs if name in c['names']][:3]})
    colls = [{'name': k, 'count': v, 'read_by_exe': k in read} for k, v in sorted(d['collections'].items(), key=lambda kv: (-kv[1], kv[0]))]
    exe_only = sorted(n for n in read if n not in d['params'] and n not in d['collections'])
    ents.append({'id': 'exeart:%s' % stem, 'stem': stem, 'file_stems': sorted(d['template']), 'files': len(d['files']), 'file_names': d['files'][:60],
                 'collections': colls, 'params': params, 'param_count': len(params),
                 'consumers': [{'function': c['function'], 'rva': c['rva'], 'names': len(c['names']), 'score': c['best_score']} for c in cs],
                 'read_names_not_in_files': exe_only, 'params_not_read': sum(1 for p in params if not p['read_by_exe']) if cs else None,
                 'availability': 'exe', 'status': 'inferred' if cs else 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': 'collection and parameter names referenced by %s' % (', '.join(c['function'] for c in cs) or 'no matched function')},
                              {'kind': 'game-script', 'note': 'names and value classes counted in the %d shipped .artdef files of template %s (no values kept)' % (len(d['files']), stem)}]})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_artdefs.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(rows, open(os.path.join(BASE, 'data', 'exe_artdef_consumers.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'artdef names;', len(rows), 'consumers;', sum(1 for r in rows if r['assigned']), 'assigned;', sum(e['param_count'] for e in ents), 'params')
for r in rows:
    print('%-62s %3d names -> %-18s %.2f (%d)  2nd %-14s %.2f %s' % (r['function'][-62:], len(r['names']), r['best'], r['best_score'], r['best_hits'], r['second'], r['second_score'], '' if r['assigned'] else 'UNASSIGNED'))
