"""Reflected data types of the exe (layouts of asset, artdef, blueprint and package structures) and reflected enums.
Input : findings/tables/exe_reflected_types_windows.tsv and exe_reflected_enums_windows.tsv (tools/exe/winreflect.py), number of shipped .blp files (count only)
Output: data/exe_reflect.json (entities exetype:<Type> and exetypeenum:<Enum>)."""
import collections, csv, json, os, re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
T = os.path.join(ROOT, 'findings', 'tables')
types = collections.OrderedDict()
for r in csv.DictReader(open(os.path.join(T, 'exe_reflected_types_windows.tsv'), encoding='utf8'), delimiter='\t'):
    t = types.setdefault(r['type'], {'rva': r['rva'], 'size': int(r['size']) if r['size'] else None, 'fields': []})
    t['fields'].append({'name': r['field'], 'type': r['field_type'] or '(not resolved)', 'offset': int(r['offset']), 'type_conf': r['type_conf']})
enums = collections.OrderedDict()
for r in csv.DictReader(open(os.path.join(T, 'exe_reflected_enums_windows.tsv'), encoding='utf8'), delimiter='\t'):
    e = enums.setdefault(r['enum'], {'rva': r['rva'], 'members': []})
    e['members'].append({'name': r['member'], 'value': int(r['value']) if r['value'] != '' else None})
import glob
tags = set()
for p_ in glob.glob(GAME + '/**/*.artdef', recursive=True):
    tags |= set(re.findall(r'<(m_[A-Za-z0-9_]+)', open(p_, encoding='utf8', errors='replace').read()))
blp_files = sum(1 for dp, dn, fn in os.walk(GAME) for f in fn if f.lower().endswith('.blp'))


def ns(name):
    return name.split('::')[0]


ents = []
for name, t in types.items():
    fl = sorted(t['fields'], key=lambda f: f['offset'])
    ents.append({'id': 'exetype:%s' % name, 'kind': 'type', 'name': name, 'namespace': ns(name), 'rva': '0x' + t['rva'], 'size': t['size'], 'fields': fl, 'field_count': len(fl),
                 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-disassembly', 'note': 'field names and offsets are constants in %s::GetTypeInfo (0x%s); field types are the type functions it calls (named through the Linux function map where needed)' % (name, t['rva'])}]})
for name, e in enums.items():
    ents.append({'id': 'exetypeenum:%s' % name, 'kind': 'enum', 'name': name, 'namespace': ns(name), 'rva': '0x' + e['rva'], 'size': None, 'fields': [], 'field_count': 0, 'members': e['members'],
                 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-disassembly', 'note': 'member names and values stored by EnumDescription<%s>::GetEnumInfo (0x%s)' % (name, e['rva'])}]})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_reflect.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
fieldnames = {f['name'] for t in types.values() for f in t['fields']}
json.dump({'blp_files': blp_files, 'artdef_tags': len(tags), 'artdef_tags_matched': len(tags & fieldnames), 'artdef_tags_unmatched': sorted(tags - fieldnames)}, open(os.path.join(BASE, 'data', 'exe_reflect_meta.json'), 'w'))
print(len(types), 'types,', sum(len(t['fields']) for t in types.values()), 'fields;', len(enums), 'enums;', blp_files, 'blp files;', len({ns(n) for n in list(types) + list(enums)}), 'namespaces')
