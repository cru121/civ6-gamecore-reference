"""The .modinfo vocabulary of the engine exe: component (action) types, criteria, settings, elements, properties, references, status codes.
Sources : string literals referenced by the exe's modding functions (strmaps.pkl + the exe function index), the 42 .modinfo files shipped with the game (read in place, only
          element and attribute names and counts are kept), curated/_exe_modinfo.yaml (handler classes and notes).
Output  : data/exe_modinfo.json (entities exemodinfo:<kind>:<name>)."""
import collections, json, os, pickle, re
import xml.etree.ElementTree as ET
import yaml

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
O = os.path.join(ROOT, 'linux_depot', 'out')
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
cur = yaml.safe_load(open(os.path.join(BASE, 'curated', '_exe_modinfo.yaml'), encoding='utf8'))

# ------------------------------------------------------------ exe strings per modding function
ws, ls, wm, lm = pickle.load(open(os.path.join(O, 'strmaps.pkl'), 'rb'))
fn_name = {}; fn_rva = {}
rows = json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']
for r in rows:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            fn_name.setdefault(int(v, 16), re.sub(r'\(.*$', '', r[0]))
apply_rva = {}
for r in rows:
    n = re.sub(r'\(.*$', '', r[0])
    m = re.match(r'^((?:Modding\w+|\w+Criterion))::(ApplyComponent|ApplySettings|Apply|Check)$', n)
    if m and r[2] and r[3] in ('high', 'medium') and ',' not in r[2]:
        apply_rva.setdefault(m.group(1), '0x' + r[2])
by_name = collections.defaultdict(lambda: collections.defaultdict(set))   # string -> function -> {}
for a, s in ws.items():
    s = s.decode('latin1') if isinstance(s, bytes) else s
    if re.match(r'^[A-Za-z_][A-Za-z0-9_]{1,40}$', s):
        for f in wm.get(a, ()):
            n = fn_name.get(f, '')
            if re.search(r'Modding|ModDiscovery|ModLoader|ModAssoc|Criterion|AppLuaModdingLibrary', n):
                by_name[s][n] = f
KIND_BY_FN = [   # (function name fragment, kind)
    ('AppModdingFramework::AppModdingFramework', 'component or action type'),
    ('ModdingComponentDiscoveryService', 'criterion type'),
    ('ModdingSettingDiscoveryService', 'setting criterion type'),
    ('GameModeInUseCriterion', 'game mode value'),
    ('PushModRequirementsStatus', 'mod status code'),
    ('lGetSubscriptionDetails', 'subscription status'),
    ('PushModInfo', 'GetModInfo field'),
    ('ParseModXml', 'mod file element or attribute'),
    ('ModLoaderService::ParseMod', 'mod property'),
    ('ModAssociationsService', 'reference element'),
    ('ParseLocalizationBuffer', 'text element or attribute'),
    ('ConfigurationValueMatchesCriterion', 'criterion parameter'),
]

# ------------------------------------------------------------ shipped .modinfo files
roles = collections.defaultdict(lambda: collections.defaultdict(lambda: {'n': 0, 'attrs': collections.Counter()}))
nfiles = 0
for r, _, fs in os.walk(GAME):
    for f in fs:
        if f.lower().endswith('.modinfo'):
            try:
                root = ET.parse(os.path.join(r, f)).getroot()
            except Exception:
                continue
            nfiles += 1
            def walk(e, path):
                for c in e:
                    role = path[-1] if path else 'Mod'
                    d = roles[role][c.tag]; d['n'] += 1
                    for a in c.attrib:
                        d['attrs'][a] += 1
                    walk(c, path + [c.tag])
            walk(root, [])
ROLE_KIND = {'Mod': 'mod element', 'Properties': 'mod or component property', 'Components': 'component or action type', 'Settings': 'setting type', 'InGameActions': 'component or action type',
             'FrontEndActions': 'component or action type', 'Criteria': 'criterion type', 'References': 'reference element', 'Dependencies': 'reference element', 'Items': 'item element', 'ActionCriteria': 'criteria block'}

ents = {}
def ent(kind, name):
    return ents.setdefault((kind, name), {'id': 'exemodinfo:%s:%s' % (kind.replace(' ', '-'), name), 'kind': kind, 'name': name, 'exe_functions': [], 'shipped_uses': 0, 'shipped_attributes': [], 'shipped_roles': [],
                                           'handlers': [], 'note': cur['notes'].get(name), 'availability': 'exe', 'status': 'verified', 'evidence': []})
for role, d in roles.items():
    for tag, v in d.items():
        e = ent(ROLE_KIND.get(role, 'mod element') if role in ROLE_KIND else 'mod element', tag)
        e['shipped_uses'] += v['n']
        e['shipped_roles'].append(role)
        for a, n in v['attrs'].items():
            if a not in e['shipped_attributes']:
                e['shipped_attributes'].append(a)
for s, fns in by_name.items():
    kinds = set()
    for n in fns:
        for frag, k in KIND_BY_FN:
            if frag in n:
                kinds.add(k)
    for k in kinds:
        e = ent(k, s)
        for n in sorted(fns):
            if any(frag in n and kk == k for frag, kk in KIND_BY_FN):
                rv = '0x%x' % fns[n]
                if all(x['rva'] != rv for x in e['exe_functions']):
                    e['exe_functions'].append({'name': n, 'rva': rv})
# merge kinds that are the same concept between shipped roles and exe sources
ELEMENT_KINDS = {'mod element', 'reference element', 'item element', 'criteria block', 'mod file element or attribute', 'text element or attribute'}
shipped_components = {t for role in ('Components', 'InGameActions', 'FrontEndActions') for t in roles[role]}
shipped_criteria = set(roles['Criteria'])
COMPONENT_PROPS = {'Context', 'LuaContext', 'LuaReplace', 'RuleSet', 'Group', 'Priority'}
DB_FIELDS = {'Dependency', 'Version', 'Created', 'LastUpdated', 'IsBasic', 'DBVersion'}
MODES = {'WorldBuilder', 'SinglePlayer', 'HotSeat', 'MultiPlayer'}
def canon_kind(k, n):
    if k in ELEMENT_KINDS:
        return 'attribute' if n[0].islower() else 'mod file element'
    if k == 'mod or component property':
        return 'component property' if n in COMPONENT_PROPS else 'mod property'
    if k == 'mod property' and n in DB_FIELDS:
        return 'mod database field'
    return k
def keep(k, n):
    if k == 'component or action type':
        return n in cur['handlers'] or n in shipped_components or n == 'Custom'
    if k == 'criterion type':
        return n in cur['criteria_classes'] or n in shipped_criteria
    if k == 'game mode value':
        return n in MODES
    return True
final = {}
for (k, n), e in ents.items():
    k2 = canon_kind(k, n)
    if not keep(k2, n):
        continue
    if k2 == 'mod element' and not e['exe_functions'] and n not in cur['notes']:
        pass
    key = (k2, n)
    if key in final:
        m = final[key]
        m['shipped_uses'] += e['shipped_uses']
        m['exe_functions'] += [x for x in e['exe_functions'] if x not in m['exe_functions']]
        m['shipped_attributes'] += [a for a in e['shipped_attributes'] if a not in m['shipped_attributes']]
        m['shipped_roles'] += [r for r in e['shipped_roles'] if r not in m['shipped_roles']]
    else:
        e['kind'] = k2; e['id'] = 'exemodinfo:%s:%s' % (k2.replace(' ', '-'), n); final[key] = e
out = []
for (k, n), e in sorted(final.items()):
    if k in ('component or action type', 'setting type') and n in cur['handlers']:
        e['handlers'] = [{'class': c, 'rva': apply_rva.get(c)} for c in cur['handlers'][n]]
    if k in ('criterion type', 'setting criterion type') and n in cur['criteria_classes']:
        c = cur['criteria_classes'][n]
        e['handlers'] = [{'class': c, 'rva': apply_rva.get(c)}]
    e['exe_functions'] = e['exe_functions'][:3]
    if not e['exe_functions'] and not e['shipped_uses']:
        continue
    ev = []
    if e['exe_functions']:
        ev.append({'kind': 'exe-string', 'note': 'string literal in %s' % e['exe_functions'][0]['name']})
    if e['shipped_uses']:
        ev.append({'kind': 'game-script', 'note': 'used %d times in the %d .modinfo files shipped with the game' % (e['shipped_uses'], nfiles)})
    e['evidence'] = ev
    e['status'] = 'verified'
    out.append(e)
json.dump(out, open(os.path.join(BASE, 'data', 'exe_modinfo.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump({'shipped_files': nfiles}, open(os.path.join(BASE, 'data', 'exe_modinfo_meta.json'), 'w'))
print(len(out), 'entries from', nfiles, 'shipped modinfo files;', collections.Counter(e['kind'] for e in out))
