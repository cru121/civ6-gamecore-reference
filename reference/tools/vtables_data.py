"""data/vtables.json from linux_depot/out/vtable_slots.tsv (tools/vtables_match.py): per class, the virtual function table.
{cpp_class: {"slots": [{"slot": n, "offset": n*8, "method": "Owner::Name"|"Name", "owner": ..., "new_rva": "0x..", "status": ..}]}}
Only slots with a Linux name are listed; 'unaligned' Windows slots are counted in "unaligned"."""
import csv, json, os, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
T = os.path.join(ROOT, 'linux_depot', 'out', 'vtable_slots.tsv')
out = {}
for r in csv.DictReader(open(T, encoding='utf-8'), delimiter='\t'):
    c = out.setdefault(r['class'], {'slots': [], 'unaligned': 0})
    if r['status'] == 'unaligned' or not r['linux_name']:
        c['unaligned'] += 1
        continue
    full = r['linux_name'].split('(')[0]
    owner, _, meth = full.rpartition('::')
    s = int(r['slot'])
    c['slots'].append({'slot': s, 'offset': s * 8, 'method': meth, 'owner': owner,
                       'new_rva': r['win_new_rva'], 'status': r['status']})
json.dump(out, open(os.path.join(ROOT, 'docs_proto', 'data', 'vtables.json'), 'w', encoding='utf-8'), indent=0)
print(len(out), 'classes,', sum(len(v['slots']) for v in out.values()), 'slots')
