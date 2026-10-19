"""C++ classes of the engine exe: inheritance and virtual tables, recovered from the RTTI of the Linux build (tools/exe/classes.py), with Windows addresses of the
virtual functions where the function map has them. Third-party and standard-library classes are left out.
Input : linux_depot/out/exe_classes.pkl, findings/data/exe_function_index.json   Output: data/exe_classes.json (entities execlass:<name>)."""
import collections, json, os, pickle, re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
classes = pickle.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'exe_classes.pkl'), 'rb'))
winof = {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    if r[1] and r[2] and ',' not in r[2] and r[3] in ('high', 'medium'):
        winof[int(r[1], 16)] = ('0x' + r[2], r[3])
EXCL = r'^(icu_56|std|__cxxabiv1|CISL|FireFX|DX11Bytecode|hks|ctp|ASL|ASLCPP|CCallback|boost|tbb|ENet|curl|SSL|crypto|AK|CAkW|Wwise|bk2|Bink|sqlite|IDirect|ID3D|IDXGI|IUnknown|_GUID|testing|ICU|UCharacter|Sprockets|nlohmann|FSL|ASL\w*|IDirect\w*|ID3D\w*|IDXGI\w*|HINTERNET\w*)\b'
def top(n):
    return re.split(r'::|<', n)[0]
keep = {n for n in classes if not re.match(EXCL, n) and not n.endswith('_Mac') and not n.startswith(('std::', 'typeinfo')) and '<' not in n}
derived = collections.defaultdict(list)
for n, c in classes.items():
    for b in c['bases']:
        derived[b].append(n)
def chain(n, seen=None):
    out = []
    cur = n
    while cur in classes and classes[cur]['bases']:
        b = classes[cur]['bases'][0]
        if b in out:
            break
        out.append(b); cur = b
    return out
ents = []
for n in sorted(keep):
    c = classes[n]
    slots = []
    for i, p, name in c.get('slots', []):
        w = winof.get(p)
        slots.append({'slot': i, 'name': re.sub(r'\(.*$', '', name) if name else None, 'windows_rva': w[0] if w else None, 'windows_confidence': w[1] if w else None})
    ents.append({'id': 'execlass:' + n, 'name': n, 'namespace': top(n) if '::' in n else '(global)', 'bases': c['bases'], 'base_chain': chain(n),
                 'derived': sorted(d for d in derived.get(n, []) if d in keep), 'kind': c['kind'] or 'unknown',
                 'vtable_linux_va': '0x%x' % c['vtable_va'] if 'vtable_va' in c else None, 'virtual_slots': slots, 'slot_count': len(slots),
                 'mapped_slots': sum(1 for s in slots if s['windows_rva']), 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-disassembly', 'note': 'typeinfo and vtable objects of the Linux build (RTTI); base classes read from the typeinfo structure'}]})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_classes.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'classes;', collections.Counter(e['namespace'] for e in ents).most_common(25), '; slots', sum(e['slot_count'] for e in ents), 'mapped', sum(e['mapped_slots'] for e in ents))
