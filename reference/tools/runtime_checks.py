#!/usr/bin/env python3
"""Fold the live-game Lua tests (frida/live/luatests) into the reference data.

Input : ../frida/live/luatests/calltest_results.tsv (one row per called getter: object, method, status, runtime returns, verdict)
        ../frida/live/luatests/crawl_out.txt        (runtime method lists per class, matched to reference objects by name overlap)
Output: data/lua_runtime_checks.json  {"Object.Method": {"called": bool, "result": ..., "error": ..., "seen_in_ui_state": true}}
Run after the Frida tests and before extract.py/build.py.
"""
import collections, csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
LT = os.path.join(ROOT, 'frida', 'live', 'luatests')
BUILD, DATE, STATE = 15038592, '2026-10-03', 'UI state'

docs = json.load(open(os.path.join(HERE, '..', 'data', 'lua_methods.json'), encoding='utf-8'))
objs = collections.defaultdict(set)
for x in docs:
    objs[x['object']].add(x['method'])

out = {}
for line in open(os.path.join(LT, 'crawl_out.txt'), encoding='utf-8'):
    line = line.rstrip('\n')
    if line.startswith('#') or '|' not in line:
        continue
    cid, path, ms = line.split('|', 2)
    rt = {m for m in ms.split(',') if m}
    best = max(objs, key=lambda o: len(rt & objs[o]) / max(1, len(rt | objs[o])))
    if len(rt & objs[best]) / max(1, len(rt | objs[best])) < 0.5:
        continue
    for m in rt & objs[best]:
        out.setdefault('%s.%s' % (best, m), {})['seen_in_ui_state'] = True

for r in csv.DictReader(open(os.path.join(LT, 'calltest_results.tsv'), encoding='utf-8'), delimiter='\t'):
    e = out.setdefault('%s.%s' % (r['object'], r['method']), {})
    e['called'] = True
    e['result'] = r['verdict']
    e['runtime_returns'] = r['runtime_returns'] if r['status'] == 'ok' else ''
    if r['status'] == 'err':
        e['error'] = r['runtime_returns'][:100]
    e['state'] = STATE
    e['build'] = BUILD
    e['date'] = DATE

json.dump(out, open(os.path.join(HERE, '..', 'data', 'lua_runtime_checks.json'), 'w', encoding='utf-8'), indent=1, sort_keys=True)
c = collections.Counter(v.get('result', 'seen-only') for v in out.values())
print(len(out), 'methods;', dict(c))
