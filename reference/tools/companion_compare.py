"""Compare linux_depot/out/companion.json (Modding Companion 2.0) with our data. Writes linux_depot/out/companion_compare.json."""
import collections, json, os, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
c = json.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'companion.json'), encoding='utf8'))
D = os.path.join(ROOT, 'docs_proto', 'data')
methods = json.load(open(os.path.join(D, 'lua_methods.json'), encoding='utf8'))
enums = json.load(open(os.path.join(D, 'enums.json'), encoding='utf8'))
snake = lambda n: re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', '_', n).upper()
res = {}

# ---- events
ours = {m['name'] for m in [e for e in enums if e['id'] == 'enum:Events'][0]['members']}
ev = c['events']
mine = {snake(n): n for n in ev}
both = sorted(ours & set(mine))
core = {snake(n) for n, e in ev.items() if e['header_type'] in ('GameCoreEvent', 'PlayerGameCoreEvent')}
res['events'] = {'ours': len(ours), 'sheet': len(ev), 'sheet_gamecore': len(core), 'both': len(both),
                 'ours_only': sorted(ours - set(mine)), 'sheet_gamecore_not_ours': sorted(core - ours),
                 'both_with_params': sum(1 for s in both if ev[mine[s]]['params']),
                 'both_header_types': dict(collections.Counter(ev[mine[s]]['header_type'] for s in both))}

# ---- objects
theirs = {(t, n): m for t, o in c['objects'].items() for n, m in o['methods'].items()}
ourm = {(m['object'], m['method']): m for m in methods}
common = sorted(set(theirs) & set(ourm))
res['objects'] = {'ours': len(ourm), 'sheet': len(theirs), 'common': len(common),
                  'sheet_only': len(set(theirs) - set(ourm)), 'ours_only': len(set(ourm) - set(theirs)),
                  'sheet_only_objects': dict(collections.Counter(t for t, _ in set(theirs) - set(ourm)).most_common(15)),
                  'ours_only_objects': dict(collections.Counter(t for t, _ in set(ourm) - set(theirs)).most_common(15))}
argc = collections.Counter(); ctx = collections.Counter(); names = collections.Counter(); retc = collections.Counter()
ex = collections.defaultdict(list)
for k in common:
    t, o = theirs[k], ourm[k]
    s = o['signatures'][0]
    nargs_t = len(t['args']) - (1 if k[0] and t['args'].get('1.0', {}).get('type') == ':object' and False else 0)
    pm = s['params']
    a = 'equal' if nargs_t == len(pm) else ('theirs+1' if nargs_t == len(pm) + 1 else 'differs')
    argc[a] += 1
    if a == 'differs' and len(ex['argc']) < 8: ex['argc'].append((k, nargs_t, len(pm)))
    rt = len(t['rets'])
    retc['equal' if rt == s['return_count'] else ('theirs=0' if rt == 0 else ('ours=0' if not s['return_count'] else 'differs'))] += 1
    reg = set(o['registered_on'])
    tc = ('G' if t['gameplay'] else '') + ('U' if t['ui'] else '')
    oc = ('G' if 'gameplay' in reg else '') + ('U' if 'ui-cache' in reg or 'ui' in reg else '')
    ctx[(tc, oc)] += 1
    for i, p in enumerate(pm):
        tn = t['args'].get('%d.0' % (i + 1))
        if tn and not p['name'].startswith('arg'):
            n1 = re.sub(r'[^a-z0-9]', '', p['name'].lower().lstrip('eibkpnx')); n2 = re.sub(r'[^a-z0-9]', '', tn['name'].split()[-1].lower())
            names['agree' if (n1 == n2 or n1 in n2 or n2 in n1) else 'differ'] += 1
            if not (n1 == n2 or n1 in n2 or n2 in n1) and len(ex['names']) < 12: ex['names'].append((k, p['name'], tn['name']))
        elif tn and p['name'].startswith('arg'):
            names['theirs_names_our_arg'] += 1
res['objects'].update({'arg_count': dict(argc), 'ret_count': dict(retc), 'contexts_theirs_vs_ours': {'%s|%s' % k: v for k, v in ctx.items()}, 'name_compare': dict(names), 'examples': ex})
json.dump(res, open(os.path.join(ROOT, 'linux_depot', 'out', 'companion_compare.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False)[:6000])
