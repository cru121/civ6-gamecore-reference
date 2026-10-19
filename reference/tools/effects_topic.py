"""Generate topics/70-state-changes.md: which Lua methods write which game state (from data/lua_effects.json).

Run after extract.py (needs data/lua_methods.json with wrapper_rvas) and before build.py.
"""
import json, os, collections

B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
eff = json.load(open(os.path.join(B, 'data', 'lua_effects.json'), encoding='utf8'))
methods = json.load(open(os.path.join(B, 'data', 'lua_methods.json'), encoding='utf8'))

rows = collections.defaultdict(list)       # class -> [(method label, writes, reads)]
seen = set()
for m in methods:
    for r in m.get('wrapper_rvas', []):
        e = eff.get(r)
        if not e or not e['writes'] or (e.get('class') or '').startswith('Cache::'):
            continue
        label = '%s:%s' % (m['object'], m['method'])
        if label in seen:
            break
        seen.add(label)
        c = e['class'] or '?'
        def short(mem): return mem[len(c) + 2:] if mem.startswith(c + '::') else mem
        wf = [w['member'] for w in e['writes']]
        rows[c].append((label, [short(x) for x in wf], [short(x['member']) for x in e['reads'] if x['member'] not in wf]))
        break

out = ['---', 'title: Lua methods that change game state', 'order: 70', '---', '# Lua methods that change game state', '',
       'Generated from a static trace of the code behind each Lua method: which class members the method (and the functions it calls) '
       'writes directly. **Everything here is inferred**: offsets come from the Windows build and are mapped to member names through the '
       'Linux debug info (Windows offset + 8 or equal, kept only when exactly one member fits).', '',
       'Read the lists with these limits in mind:', '',
       '- Many mutators change state by calling game functions that wrap the write (tracked variables, containers). Those show no direct write here, so this list is **incomplete**, not a list of every mutator.',
       '- Virtual calls, writes through aliases and values stored and loaded back are not followed.',
       '- Members shown as `m_x` are the member of the class in the first column; `Other::m_y` is a member reached through a pointer.',
       '- UI-side (`Cache::`) twins of these methods are left out.', '',
       'Where a method name suggests a different effect than the member list, trust the code reading: the trace only says *what is written*, not *when*.', '']
for cls in sorted(rows):
    out += ['## %s' % cls, '', '| Lua method | Writes | Also reads |', '|---|---|---|']
    for label, w, r in sorted(rows[cls]):
        rr = r[:4]
        out.append('| `%s` | %s | %s |' % (label, ', '.join('`%s`' % x for x in w[:6]) + (' …' if len(w) > 6 else ''),
                                           ', '.join('`%s`' % x for x in rr) + (' …' if len(r) > 4 else '') if rr else '—'))
    out.append('')
text = '\n'.join(out)
open(os.path.join(B, 'topics', '70-state-changes.md'), 'w', encoding='utf8', newline='\n').write(text)
print('wrote topics/70-state-changes.md:', sum(len(v) for v in rows.values()), 'methods in', len(rows), 'classes')
