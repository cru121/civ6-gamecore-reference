"""Write topics/90-coverage.md: how much of the reference is complete and how sure each part is. Run before build.py."""
import collections
import glob
import json
import os

import yaml

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def L(n):
    return json.load(open(os.path.join(BASE, 'data', n), encoding='utf8'))


m, ops, en, lay, gl, ce, nat, par = (L(x) for x in ('lua_methods.json', 'operations.json', 'enums.json', 'layouts.json', 'globals.json', 'ce_methods.json', 'native.json', 'op_params.json'))
fx = L('function_index.json')['rows']
ret, arg = L('lua_return_meanings.json'), L('lua_arg_meanings.json')
wo = yaml.safe_load(open(os.path.join(BASE, 'curated', '_windows_offsets.yaml'), encoding='utf8'))['windows_offsets']
sig = [x['signatures'][0] for x in m]
conf = collections.Counter(s['confidence'] for s in sig)
tot_p = sum(len(s['params']) for s in sig)
named = sum(1 for s in sig for p in s['params'] if not p['name'].startswith('arg'))
typed = sum(1 for s in sig for p in s['params'] if p.get('cpp_type'))
am = [a for v in arg.values() for a in v]
returning = sum(1 for s in sig if s['return_count'])
detailed = sum(1 for s in sig if s.get('return_details'))
inref = sum(1 for x in m if x['in_community_reference'])
notes = [n for f in glob.glob(os.path.join(BASE, 'curated', '**', '*.yaml'), recursive=True) if '_windows' not in f for n in (yaml.safe_load(open(f, encoding='utf8')).get('notes') or [])]
opc = collections.Counter(o['status'] for o in ops)
pp = sum(len(o['parameters']) for o in ops)
pe = sum(1 for o in ops for p in o['parameters'] if p.get('game_examples'))
pc = collections.Counter(p['status'] for p in par)
gc = collections.Counter(g['status'] for g in gl)


def pct(a, b):
    return '%d (%.0f%%)' % (a, 100.0 * a / b) if b else str(a)


t = '''---
title: Coverage and confidence
order: 90
---
# Coverage and confidence

Generated from the data files at build time. "Verified" means seen directly in code, data, game scripts or at run time; "inferred" means deduced from verified facts. Counts are for the symbol build mapped to the current build.

## Available out of the box

| Part | Total | How complete | How sure |
|---|---|---|---|
| Lua methods | %d | all registered methods; %s also appear in the community reference, %s do not | registration is read from the DLL tables (verified) |
| Signatures | %d | %s have at least one parameter; %s of %d parameters have a real name; %s have a C++ type | %s high confidence, %s partial (marked ⚠) |
| Return values | %d return something | %s have a detailed description (tables, arrays, types); %s have a stated meaning | meanings: %d verified, %d inferred |
| Argument meanings | %d parameters | %s have a stated meaning | %d verified, %d inferred |
| Operations and commands | %d | all identified with hash, handler, addresses | %d verified, %d inferred (16 handlers matched by class name), %d unknown |
| Operation parameters | %d slots, %d parameter entities | %s slots have an example from the game's scripts | entities: %d verified, %d inferred |
| Lua constant tables | %d tables, %d members | the %d operation and command tables are complete; %d more tables are matched to engine enums through the Companion (only the members it lists are known to be exposed) | operation tables verified from the debug info; the %d others inferred |

## Needs the Community Extension

| Part | Total | How complete | How sure |
|---|---|---|---|
| Community Extension functions | %d | all in its wiki; %s linked to the engine function | wiki + source (verified) |
| Class layouts | %d classes, %d members | all non-template GameCore classes in the Linux build | Linux offsets verified from debug info; **%d members** checked against Windows code |
| Globals | %d | named globals present in both builds | %d verified (mapping rests on 2+ references), %d inferred |

## Engine internals

| Part | Total | How complete | How sure |
|---|---|---|---|
| Function inventory | %d functions | %s mapped to the current build; %s have a Linux signature | mapping method is described in the analysis notes (not yet part of this site) |
| Native function entries | %d | %d analysed in detail (%d notes), %d wrapped by the Community Extension | analysed notes labelled verified / inferred |
| Hand-written notes (all entity types) | %d | a small curated set | %d verified, %d inferred |

## Known gaps
- Return and argument meanings exist where the game's own scripts reveal them; the remaining methods are listed with types only.
- Signature columns marked ⚠ (%d methods) have arguments or returns we could not fully classify.
- Only %d layout members have a checked Windows offset; for the rest use the Linux offset with the stated rule.
- The Events enum lists engine ids (not scriptable). %d of the %d are also Lua events with parameter names from the Civ VI Modding Companion (ChimpanG, WildW); see the Lua events page. These are community-sourced and not checked against the DLL.
''' % (
    len(m), pct(inref, len(m)), pct(len(m) - inref, len(m)),
    len(m), pct(sum(1 for s in sig if s['params']), len(m)), pct(named, tot_p), tot_p, pct(typed, tot_p), pct(conf['high'], len(m)), pct(conf['partial'], len(m)),
    returning, pct(detailed, returning), pct(len(ret), returning), sum(1 for r in ret.values() if r['status'] == 'verified'), sum(1 for r in ret.values() if r['status'] == 'inferred'),
    tot_p, pct(len(am), tot_p), sum(1 for a in am if a['status'] == 'verified'), sum(1 for a in am if a['status'] == 'inferred'),
    len(ops), opc['verified'], opc['inferred'], opc['unknown'],
    pp, len(par), pct(pe, pp), pc['verified'], pc['inferred'],
    sum(1 for e in en if e['kind'] in ('lua-table', 'lua-table-companion')), sum(len(e['members']) for e in en if e['kind'] in ('lua-table', 'lua-table-companion')),
    sum(1 for e in en if e['kind'] == 'lua-table'), sum(1 for e in en if e['kind'] == 'lua-table-companion'), sum(1 for e in en if e['kind'] == 'lua-table-companion'),
    len(ce), pct(sum(1 for c in ce if c['native']), len(ce)),
    len(lay), sum(len(l['members']) for l in lay), len(wo),
    len(gl), gc['verified'], gc['inferred'],
    len(fx), pct(sum(1 for r in fx if r[2]), len(fx)), pct(sum(1 for r in fx if r[7]), len(fx)),
    len(nat), sum(1 for n in nat if 'analysis' in n), sum(len(n['analysis']['notes']) for n in nat if 'analysis' in n), sum(1 for n in nat if n['lua_exposure']['status'] == 'ce'),
    len(notes), sum(1 for n in notes if n['status'] == 'verified'), sum(1 for n in notes if n['status'] == 'inferred'),
    conf['partial'], len(wo),
    sum(1 for m_ in [e for e in en if e['id'] == 'enum:Events'][0]['members'] if m_.get('parameters')), len([e for e in en if e['id'] == 'enum:Events'][0]['members']))
_rtp = os.path.join(BASE, 'data', 'lua_runtime_checks.json')
if os.path.exists(_rtp):
    _rt = json.load(open(_rtp, encoding='utf8'))
    _called = [v for v in _rt.values() if v.get('called')]
    t += ("\n## Checked against a running game\n\n| Part | Total | Result |\n|---|---|---|\n"
          "| Lua methods seen on live objects (UI state) | %d | %d called once: %d returned the documented number of values, %d returned nothing, %d raised errors (each noted on the method page) |\n"
          "\nSee the topic *Checking the reference against a running game*. Not covered: methods with arguments, mutators, the gameplay Lua state, multiplayer.\n"
          % (len(_rt), len(_called), sum(1 for v in _called if v['result'] == 'ok-count-match'),
             sum(1 for v in _called if v['result'] == 'ok-returned-nothing'), sum(1 for v in _called if v['result'] == 'err')))
open(os.path.join(BASE, 'topics', '90-coverage.md'), 'w', encoding='utf8').write(t)
print('wrote topics/90-coverage.md')
