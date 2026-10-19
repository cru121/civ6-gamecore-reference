"""The ForgeUI XML vocabulary: for every control type the exe builds from XML, the attribute and child names its BuildCoreFromXML / BuildFromXML code reads,
cross-checked against the UI XML files shipped with the game.
Sources : identifier string literals referenced by ForgeUI::<Type>::BuildCoreFromXML / BuildFromXML (strmaps.pkl + exe function index),
          the .xml files under the game's UI folders (read in place; only element and attribute names and counts are kept), curated/_exe_uixml.yaml (element aliases).
Outputs : data/exe_uixml.json (entities exeui:<Type>:<Name>), data/exe_uixml_types.json (one record per control type)."""
import collections, json, os, pickle, re
import xml.etree.ElementTree as ET
import yaml

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
O = os.path.join(ROOT, 'linux_depot', 'out')
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
cur = yaml.safe_load(open(os.path.join(BASE, 'curated', '_exe_uixml.yaml'), encoding='utf8'))

# ---------------------------------------------------------------- shipped UI xml
tags = collections.defaultdict(lambda: {'n': 0, 'attrs': collections.Counter()})
nfiles = 0
for r, _, fs in os.walk(GAME):
    rr = r.replace(chr(92), '/')
    if '/UI' not in rr and '/ui' not in rr:
        continue
    for f in fs:
        if not f.lower().endswith('.xml'):
            continue
        try:
            root = ET.parse(os.path.join(r, f)).getroot()
        except Exception:
            continue
        nfiles += 1
        for e in root.iter():
            d = tags[e.tag]
            d['n'] += 1
            for a in e.attrib:
                d['attrs'][a] += 1

# ---------------------------------------------------------------- exe strings per control type
ws, ls, wm, lm = pickle.load(open(os.path.join(O, 'strmaps.pkl'), 'rb'))
fn_name = {}
fn_rva = {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            fn_name.setdefault(int(v, 16), re.sub(r'\(.*$', '', r[0]))
by_type = collections.defaultdict(lambda: collections.defaultdict(set))   # control type -> string -> {function}
for a, s in ws.items():
    s = s.decode('latin1') if isinstance(s, bytes) else s
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]{1,40}$', s):
        continue
    for f in wm.get(a, ()):
        n = fn_name.get(f, '')
        m = re.match(r'^ForgeUI::(\w+)::(BuildCoreFromXML|BuildFromXML)$', n)
        if m:
            by_type[m.group(1)][s].add((n, f))

types = []
ents = []
base_attrs = set(by_type['ControlBase'])
for ctype in sorted(by_type):
    elem = cur['elements'][ctype] if ctype in cur['elements'] else re.sub(r'Control$', '', ctype)
    elem_guess = elem if elem in tags else None
    t = tags.get(elem_guess) if elem_guess else None
    used = t['attrs'] if t else {}
    exe_names = sorted(by_type[ctype])
    types.append({'id': 'exeuitype:' + ctype, 'control_type': ctype, 'xml_element': elem_guess if t else None, 'element_basis': ('curated alias' if ctype in cur['elements'] else 'name match') if t else 'base class (no element of its own)',
                  'shipped_uses': t['n'] if t else 0, 'attributes': len(exe_names), 'inherits': ctype != 'ControlBase',
                  'shipped_only': sorted(((a, n) for a, n in used.items() if a not in set(exe_names) and a not in base_attrs and n >= 10), key=lambda x: -x[1])[:14],
                  'status': 'verified' if t else 'inferred'})
    for n in exe_names:
        fns = sorted(by_type[ctype][n])
        inherited = ctype != 'ControlBase' and n in base_attrs
        ents.append({'id': 'exeui:%s:%s' % (ctype, n), 'control_type': ctype, 'name': n, 'xml_element': elem_guess if t else None,
                     'shipped_uses': used.get(n, 0), 'also_on_base': inherited,
                     'functions': [{'name': f[0], 'rva': '0x%x' % f[1]} for f in fns[:2]], 'note': cur['notes'].get(n),
                     'availability': 'exe', 'status': 'verified',
                     'evidence': [{'kind': 'exe-string', 'note': 'name literal in %s' % fns[0][0]}] + ([{'kind': 'game-script', 'note': 'attribute used %d times on <%s> in the shipped UI XML' % (used[n], elem_guess)}] if used.get(n) else [])})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_uixml.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump({'types': types, 'shipped_files': nfiles}, open(os.path.join(BASE, 'data', 'exe_uixml_types.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(nfiles, 'shipped UI xml files;', len(types), 'control types;', len(ents), 'names;', sum(1 for e in ents if e['shipped_uses']), 'used in shipped xml')
print([(t['control_type'], t['xml_element'], t['element_basis'], t['shipped_uses']) for t in types][:40])
