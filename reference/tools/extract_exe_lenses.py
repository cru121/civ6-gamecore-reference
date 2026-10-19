"""The lens system: lens layers (names registered by the exe, the numeric LensLayers constants, the artdef layer list), lenses (Lens collection of Lenses.artdef with their active-layer and permission sets),
and how the game's UI scripts use them (UILens.SetActive, UILens.CreateLensLayerHash).
Input : linux_depot/out/strmaps.pkl (strings of GameCore::App::UI::Lenses::LensManager::LensManager, 0x197000), data/exe_enums.json (LensLayers table), the game's Lenses.artdef files (base game and DLC; names only),
        the game's Lua files (call arguments only)
Output: data/exe_lenses.json (entities exelens:layer:<name> and exelens:lens:<name>), data/exe_lenses_meta.json."""
import collections, glob, json, os, pickle, re
import xml.etree.ElementTree as ET

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"

# 1. exe: layer names registered by the LensManager constructor
ws, ls, wm, lm = pickle.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'strmaps.pkl'), 'rb'))
exe_layers = []
rva = None
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    if r[0].startswith('GameCore::App::UI::Lenses::LensManager::LensManager(') and r[2]:
        rva = int(r[2].split(',')[0], 16)
for a, s in ws.items():
    s = s.decode('latin1') if isinstance(s, bytes) else s
    if rva in wm.get(a, ()) and re.match(r'^[A-Z][A-Za-z_]+$', s):
        exe_layers.append(s)
exe_layers = sorted(set(exe_layers))

# 2. LensLayers enum
enum = {}
for e in json.load(open(os.path.join(BASE, 'data', 'exe_enums.json'), encoding='utf8')):
    if e['table'] == 'LensLayers':
        enum = {m['name']: m['value'] for m in e['members']}


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


# the enum has a few misspellings of the layer names (COMMERICAL, WATER_AVAILABLITY, ARCHAELOGY, TRADE_ROUTE vs TradeRoutes)
ALIASES = {'unitsarchaeology': 'unitsarchaeology', 'districtscommercialhub': 'districtscommericalhub', 'hexcoloringwateravailablity': 'hexcoloringwateravailablity', 'traderoutes': 'traderoute'}
enum_by_norm = {norm(k): (k, v) for k, v in enum.items()}
enum_by_norm_alt = {}
for n in list(enum_by_norm):
    enum_by_norm_alt[n.replace('archaelogy', 'archaeology').replace('commerical', 'commercial').replace('availablity', 'availability').replace('traderoute', 'traderoutes')] = enum_by_norm[n]

# 3. artdefs
layers_art = collections.OrderedDict()      # name -> files
sets = collections.OrderedDict()            # set name -> list of layer names (union over files)
sets_files = collections.defaultdict(set)
lenses = collections.OrderedDict()          # lens name -> {active, permission, files}
for p in sorted(glob.glob(GAME + '/**/Lenses.artdef', recursive=True)):
    rel = os.path.relpath(p, GAME).replace('\\', '/')
    short = rel.split('/ArtDefs/')[0]
    root = ET.parse(p).getroot()
    for coll in root.findall('m_RootCollections/Element'):
        cn = coll.find('m_CollectionName').get('text')
        for el in coll.findall('Element'):
            nm = el.find('m_Name')
            name = nm.get('text') if nm is not None else None
            if not name:
                continue
            if cn == 'LayersList':
                layers_art.setdefault(name, set()).add(short)
            elif cn == 'LensLayers':
                refs = []
                for cc in el.findall('m_ChildCollections/Element'):
                    for le in cc.findall('Element'):
                        for v in le.findall('m_Fields/m_Values/Element'):
                            en = v.find('m_ElementName')
                            if en is not None:
                                refs.append(en.get('text'))
                sets.setdefault(name, [])
                for r in refs:
                    if r not in sets[name]:
                        sets[name].append(r)
                sets_files[name].add(short)
            elif cn == 'Lens':
                d = lenses.setdefault(name, {'active': None, 'permission': None, 'files': set()})
                d['files'].add(short)
                for v in el.findall('m_Fields/m_Values/Element'):
                    pn = v.find('m_ParamName')
                    en = v.find('m_ElementName')
                    if pn is not None and en is not None:
                        if pn.get('text') == 'ActiveLayers':
                            d['active'] = en.get('text')
                        elif pn.get('text') == 'PermissionMask':
                            d['permission'] = en.get('text')

# 4. scripts
uses_lens = collections.Counter()
uses_lens_files = collections.defaultdict(set)
uses_hash = collections.Counter()
uses_hash_files = collections.defaultdict(set)
SET = re.compile(r'UILens\.SetActive\(\s*"([^"]+)"')
HASH = re.compile(r'UILens\.CreateLensLayerHash\(\s*"([^"]+)"')
for dp, dn, fn in os.walk(GAME):
    for f in fn:
        if f.lower().endswith('.lua'):
            try:
                s = open(os.path.join(dp, f), encoding='utf8', errors='replace').read()
            except Exception:
                continue
            for m in SET.finditer(s):
                uses_lens[m.group(1)] += 1
                uses_lens_files[m.group(1)].add(f)
            for m in HASH.finditer(s):
                uses_hash[m.group(1)] += 1
                uses_hash_files[m.group(1)].add(f)

all_layers = sorted(set(exe_layers) | set(layers_art) | set(uses_hash))
ents = []
for ln in all_layers:
    en = enum_by_norm.get(norm(ln)) or enum_by_norm_alt.get(norm(ln))
    in_sets = [s for s, ls_ in sets.items() if ln in ls_]
    ents.append({'id': 'exelens:layer:%s' % ln, 'kind': 'layer', 'name': ln, 'in_exe': ln in exe_layers, 'in_artdef': ln in layers_art, 'artdef_files': sorted(layers_art.get(ln, [])),
                 'enum_name': en[0] if en else None, 'enum_value': en[1] if en else None, 'hash_uses': uses_hash.get(ln, 0), 'hash_files': len(uses_hash_files.get(ln, ())), 'in_sets': in_sets,
                 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': 'registered by GameCore::App::UI::Lenses::LensManager::LensManager (0x%x)' % rva if ln in exe_layers else 'name used by the game scripts or artdef only'},
                              {'kind': 'game-script', 'note': 'Lenses.artdef LayersList and UILens.CreateLensLayerHash arguments (names and counts only)'}]})
for name, d in lenses.items():
    act = sets.get(d['active'], []) if d['active'] else []
    perm = sets.get(d['permission'], []) if d['permission'] else []
    ents.append({'id': 'exelens:lens:%s' % name, 'kind': 'lens', 'name': name, 'active_set': d['active'], 'permission_set': d['permission'], 'active_layers': act, 'permission_layers': perm,
                 'artdef_files': sorted(d['files']), 'script_uses': uses_lens.get(name, 0), 'script_files': len(uses_lens_files.get(name, ())),
                 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'game-script', 'note': 'Lens collection of Lenses.artdef (names only) and UILens.SetActive call arguments'}]})
meta = {'exe_layers': len(exe_layers), 'artdef_layers': len(layers_art), 'enum_members': len(enum), 'sets': {k: {'layers': len(v), 'files': sorted(sets_files[k])} for k, v in sets.items()},
        'lens_names_used_not_in_artdef': sorted(n for n in uses_lens if n not in lenses), 'artdef_lenses_unused': sorted(n for n in lenses if n not in uses_lens),
        'layers_exe_not_artdef': sorted(set(exe_layers) - set(layers_art)), 'layers_artdef_not_exe': sorted(set(layers_art) - set(exe_layers)),
        'enum_unmatched': sorted(k for k in enum if not any(norm(l) in (norm(k),) or (enum_by_norm_alt.get(norm(l)) or (None,))[0] == k for l in all_layers)),
        'hash_uses_total': sum(uses_hash.values()), 'hash_names_unknown': sorted(n for n in uses_hash if n not in set(exe_layers) | set(layers_art)), 'rva': '0x%x' % rva}
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_lenses.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(meta, open(os.path.join(BASE, 'data', 'exe_lenses_meta.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'entries;', len(all_layers), 'layers;', len(lenses), 'lenses;', len(sets), 'layer sets')
for k in ('exe_layers', 'artdef_layers', 'enum_members', 'lens_names_used_not_in_artdef', 'artdef_lenses_unused', 'layers_exe_not_artdef', 'layers_artdef_not_exe', 'enum_unmatched', 'hash_uses_total', 'hash_names_unknown'):
    print(k, meta[k])
