#!/usr/bin/env python3
"""Generate data/devce_methods.json: the Lua methods the Dev CE test build adds (generated native bridge), merged with
  * dev-ce/data/exposed.json            what is exposed (object, C++ function, signature, how `this` is found)
  * dev-ce/batch/out/batch_*.jsonl      per-function summaries written by AI agents from the decompiled code (status: inferred)
  * dev-ce/data/function_status.json    in-game test results per function (plumbing / delta probe)
  * dev-ce/data/oracle_results.json     oracle comparison per Lua object (vanilla getter vs bridge getter of the same class)
and marks the corresponding native entities in data/native.json as exposed via Dev CE.
Run after extract_ce_native.py (it rewrites native.json) and before build.py.
"""
import glob, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
DEV = os.path.join(ROOT, 'dev-ce')

man = [e for e in json.load(open(os.path.join(DEV, 'data', 'exposed.json'), encoding='utf-8')) if not e.get('oracle')]
status = json.load(open(os.path.join(DEV, 'data', 'function_status.json'), encoding='utf-8'))
oracle = json.load(open(os.path.join(DEV, 'data', 'oracle_results.json'), encoding='utf-8')) if os.path.exists(os.path.join(DEV, 'data', 'oracle_results.json')) else {}
agent = {}
for f in glob.glob(os.path.join(DEV, 'batch', 'out', 'batch_*.jsonl')) + glob.glob(os.path.join(DEV, 'batch', 'out2', 'batch_*.jsonl')):
    for l in open(f, encoding='utf-8'):
        if l.strip():
            o = json.loads(l)
            agent[o['function'].replace('GameCore::', '', 1)] = o
natives = json.load(open(os.path.join(DATA, 'native.json'), encoding='utf-8'))
nat_by_id = {n['id']: n for n in natives}
findex = json.load(open(os.path.join(DATA, 'function_index.json'), encoding='utf-8'))['rows']
by_name = {}
for r in findex:
    by_name.setdefault(r[0], []).append(r)

LUA_T = {'INT': 'integer', 'UINT': 'integer', 'I64': 'number', 'BOOL': 'boolean', 'FIXED': 'number (fixed point, 1/256 steps)'}
RET_T = {'VOID': [], 'BOOL': ['boolean'], 'INT': ['number'], 'UINT': ['number'], 'I64': ['number'], 'FIXED': ['number']}
AI_NOTE = ('Description written by an AI assistant from the decompiled code of the symbol build (Windows DLL from the symbol-bearing build); not reviewed by a human. '
           'Behaviour was not tested in the running game unless a test result below says so.')

out = []
for e in man:
    qn = e['cpp'].replace('GameCore::', '', 1)
    obj, meth = e['lua'].split('.', 1)
    ag = agent.get(qn)
    st = status.get(e['lua'], {})
    rows = by_name.get(qn, [])
    old_rva = rows[0][1] if rows else None
    cmap = rows[0][6] if rows else None
    params = []
    for i, a in enumerate(e['args']):
        p = {'name': a['name'], 'type': a['type'], 'lua_type': LUA_T[a['kind']]}
        if ag:
            for ap in ag.get('params', []):
                if ap.get('name') == a['name'] and ap.get('meaning'):
                    p['meaning'] = {'summary': ap['meaning'], 'status': 'verified' if ap.get('evidence') == 'verified' else 'inferred'}
        params.append(p)
    tests = {'plumbing': st.get('plumbing', 'not-run')}
    ev = [{'kind': 'static-analysis', 'note': 'exposed by the generated native bridge (tools/gen_bridge.py); address and signature from the symbol-build map and the Linux debug info'}]
    if ag:
        ev.append({'kind': 'static-analysis', 'note': AI_NOTE})
    if tests['plumbing'] == 'PASS':
        ev.append({'kind': 'runtime', 'note': 'plumbing test in the running game (build 15038592, single player): native function entered once, this non-null, all sentinel arguments received exactly, return value round-trips'})
    dp = st.get('delta_probe')
    verified = False
    if dp:
        dp = dict(dp, changed_getters=[re.sub(r'^\d+\.', '', x) for x in dp['changed_getters']])   # drop the snapshot group index
        tests['delta_probe'] = dp
        ev.append({'kind': 'runtime', 'note': 'delta probe in the running game: called with +1 then -1 (all reversible=%s); visible through vanilla getters: %s' % (
            dp['reversible'], ', '.join(dp['changed_getters']) if dp['visible_effect'] else 'nothing (no vanilla getter exposes this state)')})
        verified = dp['visible_effect'] and dp['reversible']
    orc = oracle.get(e['iface'])
    if orc:
        tests['this_oracle'] = orc
    rec = {'id': 'devce:%s' % e['lua'], 'object': obj, 'method': meth, 'static': False, 'interface': e['iface'], 'this_resolution': e['this_kind'],
           'signatures': [{'params': params, 'returns': RET_T[e['returns']]}],
           'builds': {'symbol': {'rva': old_rva or ''}, 'current': {'rva': e['rva'], 'map': cmap}} if old_rva else {'symbol': {'rva': ''}, 'current': {'rva': e['rva']}},
           'native': ('native:' + qn) if ('native:' + qn) in nat_by_id else None,
           'tests': tests, 'status': 'verified' if verified else 'inferred', 'evidence': ev}
    if ag:
        rec['analysis'] = {k: ag.get(k) for k in ('purpose', 'returns', 'writes_state', 'reads_state', 'side_effects', 'validation', 'preconditions', 'multiplayer', 'risk',
                                                  'risk_reason', 'modder_use', 'confidence', 'verified_facts', 'inferred_facts', 'open_questions')}
    out.append(rec)

notes_p = os.path.join(DEV, 'data', 'devce_notes.json')
manual = json.load(open(notes_p, encoding='utf-8')) if os.path.exists(notes_p) else {}
for r in out:
    key = r['id'][len('devce:'):]
    if key in manual:
        r['notes'] = [{'text': n['text'], 'status': n['status'], 'evidence': [n['evidence']]} for n in manual[key]]
        for n in manual[key]:
            r['evidence'].append(n['evidence'])
out.sort(key=lambda r: r['id'])
json.dump(out, open(os.path.join(DATA, 'devce_methods.json'), 'w', encoding='utf-8'), indent=1)

# mark native entities
n_marked = 0
for r in out:
    if r['native']:
        n = nat_by_id[r['native']]
        le = n.setdefault('lua_exposure', {})
        if le.get('status') == 'ce':
            continue
        le['status'] = 'devce'
        le.setdefault('via', []).append(r['id'])
        n_marked += 1
json.dump(natives, open(os.path.join(DATA, 'native.json'), 'w', encoding='utf-8'), indent=1)
print('devce methods', len(out), '| with summaries', sum(1 for r in out if 'analysis' in r), '| verified', sum(1 for r in out if r['status'] == 'verified'),
      '| native entities marked', n_marked)
