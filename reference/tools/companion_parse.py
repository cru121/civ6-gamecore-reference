"""Parse the Events and Objects sheets of 'Civ VI Modding Companion 2.0.xlsx' (ChimpanG, expanded by WildW) into
linux_depot/out/companion.json. Read-only comparison input; nothing from it is copied into the reference data."""
import collections
import json
import os
import re
import sys

import openpyxl

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
wb = openpyxl.load_workbook(os.path.join(ROOT, 'Civ VI Modding Companion 2.0.xlsx'), data_only=True)


def rows(name):
    return [[c.value for c in r] for r in wb[name].iter_rows()]


def cell(r, i):
    return r[i] if i < len(r) and r[i] not in (None, '') else None


# ------------------------------------------------------------------ events
events = collections.OrderedDict()
cur = None
for r in rows('Events')[1:]:
    ev, par, typ, order = cell(r, 4), cell(r, 5), cell(r, 6), cell(r, 7)
    if not ev:
        continue
    if typ == 'GameCoreEvent' or not par:
        cur = events.setdefault(ev, {'params': [], 'game_event': cell(r, 2), 'flags': [cell(r, 8), cell(r, 9)], 'header_type': typ})
    elif ev in events:
        events[ev]['params'].append({'name': par, 'type': typ, 'order': order})

# ------------------------------------------------------------------ objects
objs = collections.OrderedDict()   # table -> {'kind':..., 'methods': {name: {...}}}
for r in rows('Objects')[3:]:
    ident, kind, table, invoke = cell(r, 1), cell(r, 10), cell(r, 11), cell(r, 12)
    if not ident or not table:
        continue
    o = objs.setdefault(table, {'invoke': invoke, 'methods': collections.OrderedDict(), 'kinds': set()})
    o['kinds'].add(kind)
    fn = cell(r, 13) or cell(r, 14) or cell(r, 15)
    if kind not in ('ACTION', 'QUERY') or not fn:
        continue
    m = o['methods'].setdefault(fn, {'kind': kind, 'max_args': cell(r, 2), 'gameplay': False, 'ui': False, 'args': {}, 'rets': {}, 'ident': ident, 'variants': set()})
    m['variants'].add(fn if cell(r, 13) else ('B:' if cell(r, 14) else 'C:') + fn)
    if cell(r, 8):
        m['gameplay'] = True
    if cell(r, 9):
        m['ui'] = True
    argn = cell(r, 3)
    if cell(r, 16) is not None and cell(r, 17):
        m['args'].setdefault(str(cell(r, 16)), {'name': cell(r, 17), 'type': cell(r, 18)})
    if cell(r, 19) is not None and (cell(r, 20) or cell(r, 21)):
        m['rets'].setdefault(str(cell(r, 19)), {'name': cell(r, 20), 'type': cell(r, 21)})

out = {'events': events,
       'objects': {t: {'invoke': o['invoke'], 'kinds': sorted(k for k in o['kinds'] if k), 'methods': {n: {**m, 'variants': sorted(m['variants'])} for n, m in o['methods'].items()}} for t, o in objs.items()}}
json.dump(out, open(os.path.join(ROOT, 'linux_depot', 'out', 'companion.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print('events', len(events), 'with params', sum(1 for e in events.values() if e['params']), 'param rows', sum(len(e['params']) for e in events.values()))
print('objects', len(objs), 'methods', sum(len(o['methods']) for o in objs.values()), 'kinds', collections.Counter(k for o in objs.values() for k in o['kinds']))
print('header types', collections.Counter(e['header_type'] for e in events.values()))
