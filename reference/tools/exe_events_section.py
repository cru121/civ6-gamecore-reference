"""Pages for the exe's event buses (section exeevents/). Called from build.py: exe_events_section.make(add, events, buses)
Data: data/exe_events.json, data/exe_event_buses.json (tools/extract_exe_events.py)."""
import collections, re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s)


def page_of_bus(bus):
    return 'exeevents/%s.md' % safe(bus)


def short(name):
    return re.sub(r'^(?:GameCore::App::|GameCore::|Simulation::|App::)', '', name or '')


def make(add, events, buses):
    by_bus = collections.OrderedDict((b['name'], [e for e in events if e['bus'] == b['name']]) for b in buses)
    gc = by_bus['GameCore']
    n_tr = sum(1 for e in gc if e['translators'])
    n_trans = len({h for e in gc for h in e['engine_hashes']})
    n_sub = sum(1 for e in gc if e['subscribers'])
    n_lua = sum(1 for e in gc if e['lua_events'])

    L = ['# Engine events\n',
         'The engine executable runs its own **event buses**. They are separate from the Lua events scripts subscribe to: they connect the exe\'s own systems (map renderer, audio, UI, telemetry, network) to each other and to GameCore. '
         'This section lists every event on every bus, which GameCore event it carries, and which exe systems handle it.\n',
         '## How a GameCore event reaches the exe (verified in the exe, Windows addresses inferred)\n',
         '1. GameCore reports an event (`Reporting::Event::Send`). The exe receives it in `GameCore::EngineUtility::SendEvent`.\n'
         '2. A **translator** looks the event up by its hash (`Events::Translate::Register` holds %d hash-to-translator entries) and converts it into a numbered **GameCore bus event** (`GameCoreEvent_Template<N, ...>`).\n'
         '3. The bus delivers it to every registered handler: renderer, strategic view, minimap, audio, telemetry, UI manager, network manager, and the Lua layer. A GameCore event without a translator never reaches this bus.\n' % n_trans,
         'The GameCore bus id `N` is not the hash and not the order of the [engine event ids](../enums/Events.md); it was read from the translator code (the translator calls the constructor of `GameCoreEvent_Template<N,...>`). '
         'The Lua event, where one exists, is listed with its [parameters](../enums/LuaEvents.md) in the GameCore reference.\n',
         '## Buses\n', '| Bus | Events | Handler registrations | What it carries |', '|---|---|---|---|']
    for b in buses:
        L.append('| [%s](%s.md) | %d | %d | %s |' % (b['name'], safe(b['name']), b['events'], b['subscriptions'], esc(b['description'])))
    L.append('\n**Numbers.** The GameCore bus has %d events: %d have a translator (the exe can receive them), %d have at least one static handler in the exe, and %d map to a Lua event of the Modding Companion list. '
             'Events with a translator but no static handler are consumed only by the Lua layer or dynamically; the exe code alone does not show who reads them.\n' % (len(gc), n_tr, n_sub, n_lua))
    L.append('See also [exe systems and the events they handle](systems.md) and the [event data fields](../exe/event-data.md) the handlers read.')
    add('exeevents/index.md', 'Engine events', '\n'.join(L) + '\n')

    for b in buses:
        es = by_bus[b['name']]
        L = ['# %s bus\n' % b['name'], b['description'] + '\n']
        if b['name'] == 'GameCore':
            L.append('| Event | Id | Lua event | Data type | Translator (Windows) | Handlers in the exe |')
            L.append('|---|---|---|---|---|---|')
            for e in es:
                lua = ', '.join('`%s`' % x for x in e['lua_events']) if e['lua_events'] else '—'
                tr = ', '.join('`%s` %s' % (t['translator'], ('(%s)' % t['windows_rva']) if t['windows_rva'] else '') for t in e['translators']) or 'none'
                systems = collections.OrderedDict()
                for s in e['subscribers']:
                    systems.setdefault(short(s['system']), []).append(s)
                sub = '; '.join('%s%s' % (n, (' (%s)' % ', '.join(x['windows_rva'] for x in v if x['windows_rva'])) if any(x['windows_rva'] for x in v) else '') for n, v in systems.items()) or '—'
                L.append('| <a id="%d"></a>`%s` | %d | %s | %s | %s | %s |' % (e['event_id'], esc(e['name']), e['event_id'], lua, esc(e['data_type'] or '—'), esc(tr), esc(sub)))
        else:
            L.append('| Event (from its data type) | Id | Data type | Handlers in the exe |')
            L.append('|---|---|---|---|')
            for e in es:
                systems = collections.OrderedDict()
                for s in e['subscribers']:
                    systems.setdefault(short(s['system']), []).append(s)
                sub = '; '.join(systems) or '—'
                L.append('| <a id="%d"></a>`%s` | %d | %s | %s |' % (e['event_id'], esc(e['name']), e['event_id'], esc(e['data_type'] or '—'), esc(sub)))
        if b['name'] == 'GameCore':
            L.append('\n*Windows addresses in brackets are the translator and handler RVAs; those of the WorldView handlers come from matching the registration order of the Linux and Windows builds (inferred). '
                     'Handler addresses of other systems are not mapped to Windows yet.*')
        add(page_of_bus(b['name']), '%s bus' % b['name'], '\n'.join(L) + '\n')

    sysmap = collections.OrderedDict()
    for e in events:
        for s in e['subscribers']:
            sysmap.setdefault(s['system'], collections.OrderedDict()).setdefault((e['bus'], e['event_id']), (e, s))
    L = ['# Exe systems and the events they handle\n',
         'Each system registers handlers for the events listed. Counts are static registrations found in the exe; a system can also subscribe dynamically (for example the Lua event libraries). '
         'The first column is the function that registers the handlers.\n', '| System | Events | Buses | Examples |', '|---|---|---|---|']
    for sname, d in sorted(sysmap.items(), key=lambda kv: -len(kv[1])):
        buses_ = sorted({k[0] for k in d})
        ex = ', '.join('%s %d' % (e['name'] if len(e['name']) < 36 else e['name'][:33] + '...', e['event_id']) for (b, i), (e, s) in list(d.items())[:4])
        L.append('| %s | %d | %s | %s |' % (esc(sname), len(d), ', '.join(buses_), esc(ex)))
    add('exeevents/systems.md', 'Exe systems and events', '\n'.join(L) + '\n')
