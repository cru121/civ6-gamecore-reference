"""Page exe/event-data.md: fields of GameCore bus events as read by the exe handlers. Called from build.py: exe_event_data_section.make(add, entries)
Data: data/exe_event_data.json (tools/extract_exe_event_data.py)."""
import re


def esc(v):
    return str(v).replace('|', '\|').replace('\n', ' ')


def make(add, entries):
    n_match = sum(1 for e in entries if e['order_matches_lua_parameters'])
    L = ['# Event data fields (as read by the exe)\n',
         'Each GameCore bus event carries a small data object. This page lists, for %d events, the **fields the exe\'s own handlers read** from it: the byte offset, the width in bytes, how many analysed handlers read it, '
         'and constants a handler compares a field with. It was recovered by tracing how the decompiled handlers use the event data parameter (%d handlers of the renderer, audio, telemetry, UI and network systems).\n' % (len(entries), sum(e['handlers_analysed'] for e in entries)),
         'Offsets are from the start of the event data object. A plot is typically two 4-byte fields (`x`, `y`) that some handlers read as one 8-byte value, so only the wider read is shown. '
         'The Lua parameter column is the parameter list of the matching Lua event from the [GameCore reference](../enums/LuaEvents.md); where the number of fields equals the number of Lua parameters (%d events) the order is **probably** the same, otherwise the two lists are only shown side by side. '
         'Fields that no analysed handler reads are not listed, and the field names are not in the exe.\n' % n_match,
         '**Reliability.** Inferred: handler addresses for the 3D renderer were matched to the Linux build by registration order, a wrong match would show another event\'s fields; handlers that take the event as a second parameter were assumed to do so; '
         'reads through an unresolved indirect call are missed. The method was checked on `TERRAIN_STATE_CHANGED` (the plot at 4 and 8, shown as one field, the state hash at 0xc, the set-or-clear flag at 0x10), which matches a hand disassembly.\n',
         '| Event | Id | Fields read (offset: width in bytes) | Handlers analysed | Lua parameters |', '|---|---|---|---|---|']
    for e in entries:
        fs = ', '.join('`%s`:%s%s' % (f['offset'], '/'.join(str(w) for w in f['widths']), (' (= %s)' % ', '.join(str(c) for c in f['compared_with'][:2])) if f['compared_with'] else '') for f in e['fields'])
        sy = sorted({h['system'].split(' ')[0].split('::')[-1] for h in e['handlers']})
        lp = ', '.join('`%s`' % p['name'] for p in e['lua_parameters']) or '—'
        L.append('| <a id="%d"></a>`%s` | %d | %s | %d (%s) | %s%s |' % (e['event_id'], esc(e['name']), e['event_id'], fs, e['handlers_analysed'], esc(', '.join(sy)), lp, ' *(order probably matches)*' if e['order_matches_lua_parameters'] else ''))
    add('exe/event-data.md', 'Event data fields', '\n'.join(L) + '\n')
