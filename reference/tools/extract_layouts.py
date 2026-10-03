"""Generate data/layouts.json (class layouts from the Linux DWARF) and data/globals.json (typed global variables)."""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'docs_proto', 'data')


def P(*a):
    return os.path.join(ROOT, *a)


def short(n):
    return n[len('GameCore::'):] if n.startswith('GameCore::') else n


layouts = []
seen = set()
for l in open(P('linux_depot', 'out', 'types.jsonl'), encoding='utf8'):
    j = json.loads(l)
    nm = j['name']
    if not nm.startswith('GameCore::') or '<' in nm or '(' in nm or '<anon>' in nm:
        continue
    if j['kind'] not in ('class', 'structure', 'union') or not j['size']:
        continue
    mem = [m for m in j['members'] if m[1] is not None and m[0]]
    if not mem:
        continue
    rid = 'layout:' + short(nm)
    if rid in seen:
        continue
    seen.add(rid)
    layouts.append({
        'id': rid, 'cpp': nm, 'kind': j['kind'], 'size': j['size'],
        'bases': [{'name': short(b[0]), 'offset': b[1]} for b in j['bases'] if b[1] is not None],
        'members': [{'name': m[0], 'offset': m[1], 'type': short(m[2]), **({'bits': m[3]} if m[3] else {})} for m in mem],
        'status': 'verified',
        'evidence': [{'kind': 'dwarf', 'note': 'member names, offsets and sizes from the Linux port debug info (Linux layout)'}]})
layouts.sort(key=lambda x: x['id'])
json.dump(layouts, open(os.path.join(OUT, 'layouts.json'), 'w', encoding='utf8'), ensure_ascii=False)
print('wrote layouts.json', len(layouts))

globs = []
seen = set()
for l in list(open(P('findings', 'tables', 'data_symbols.tsv'), encoding='utf8'))[1:]:
    p = l.rstrip('\n').split('\t')
    name, typ, size, sec, old, new, refs, vote = p[:8]
    gid = 'global:' + short(name)
    if gid in seen:
        continue
    seen.add(gid)
    good = int(refs) >= 2 and float(vote) >= 0.9
    globs.append({
        'id': gid, 'cpp': name, 'type': short(typ), 'size': int(size) if size.isdigit() else None, 'section': sec,
        'builds': {'symbol': {'rva': old}, 'current': {'rva': new}},
        'map_support': {'references': int(refs), 'vote_share': float(vote)},
        'status': 'verified' if good else 'inferred',
        'evidence': [{'kind': 'dwarf', 'note': 'name and type from the Linux port debug info'},
                     {'kind': 'static-analysis', 'note': 'address mapped from the symbol build by the data map (%s references, vote %s)' % (refs, vote)}]})
globs.sort(key=lambda x: x['id'])
json.dump(globs, open(os.path.join(OUT, 'globals.json'), 'w', encoding='utf8'), ensure_ascii=False)
print('wrote globals.json', len(globs))
