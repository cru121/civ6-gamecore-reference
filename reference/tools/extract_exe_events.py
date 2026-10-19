"""Engine event entities: the exe's event buses (GameCore, LocalMachine, Serial, UIEvent, Sequencer, MovieEvent), the translators that turn
GameCore events into GameCore-bus events, and the exe systems that subscribe.
Inputs : findings/tables/exe_event_translators_linux.tsv, exe_event_subscriptions_linux.tsv, worldview_event_subscriptions.tsv,
         linux_depot/out (scan_lin.pkl, civ6_exe_demangled.tsv), findings/data/exe_function_index.json, data/enums.json (Events members)
Method : a translator calls the constructor / sender of `GameCoreEvent_Template<N,...>`; N is the event id on the GameCore bus (callee names of the Linux build).
Outputs: data/exe_events.json (one record per bus event), data/exe_event_buses.json."""
import collections, csv, json, os, pickle, re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
T = os.path.join(ROOT, 'findings', 'tables')
O = os.path.join(ROOT, 'linux_depot', 'out')
def rows(p): return list(csv.DictReader(open(p, encoding='utf8'), delimiter='\t'))

L = pickle.load(open(os.path.join(O, 'scan_lin.pkl'), 'rb')); lf = {x[0]: x for x in L}
dem = {}
for l in open(os.path.join(O, 'civ6_exe_demangled.tsv'), encoding='utf-8'):
    va, sz, m, d = l.rstrip('\n').split('\t')
    if not m.startswith('_ZT'):
        dem.setdefault(int(va, 16), d)
SYSTEM_NAMES = {   # registration functions that have no symbol name in the Linux build (names from the exe analysis topic notes)
    'sub_332ceb0': 'WorldView (3D map renderer)', 'sub_3300fc0': 'StrategicView (2D map)', 'sub_32f4ca0': 'UI event dispatcher',
    'sub_2f6e380': 'Application console handler', 'sub_3327e10': 'unnamed system (0x3327e10)'}
winof = {}      # linux va -> (windows rva, confidence)
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    if r[1] and r[2] and ',' not in r[2]:
        winof[int(r[1], 16)] = ('0x' + r[2], r[3])
enums = json.load(open(os.path.join(BASE, 'data', 'enums.json'), encoding='utf8'))
ev_members = {m['name']: m for x in enums if x['id'] == 'enum:Events' for m in x['members']}

# ---------------------------------------------------------------- translators -> bus ids
tr_by_id = collections.defaultdict(list)
for t in rows(os.path.join(T, 'exe_event_translators_linux.tsv')):
    va = int(t['translator_va'], 16)
    x = lf.get(va)
    ids = set(); dts = set()
    if x:
        for c in list(x[2]) + list(x[4]):
            m = re.match(r'GameCoreEvent_Template<(\d+)u, ([\w:]+)', dem.get(c, ''))
            if m:
                ids.add(int(m.group(1))); dts.add(m.group(2))
    w = winof.get(va)
    rec = {'hash': t['hash'], 'event_name': t['event_name'], 'translator': t['translator'].split('::')[-1], 'linux_va': '0x' + t['translator_va'],
           'windows_rva': w[0] if w else None, 'windows_confidence': w[1] if w else None, 'data_types': sorted(dts)}
    for i in ids:
        tr_by_id[i].append(rec)

# ---------------------------------------------------------------- subscriptions
wv = {r['event_id']: r for r in rows(os.path.join(T, 'worldview_event_subscriptions.tsv'))}
subs = collections.defaultdict(list)
dtype_of = {}
for s in rows(os.path.join(T, 'exe_event_subscriptions_linux.tsv')):
    hv = int(s['handler_va'], 16) if re.match(r'^[0-9a-f]+$', s['handler_va']) else 0
    if hv == 0:
        continue                                          # the generic SubscribeToMessage<> template function, not a handler
    key = (s['bus'], int(s['event_id']))
    sf = s['subscriber_function']
    if re.match(r'^[0-9a-f]+$', sf):
        sf = dem.get(int(sf, 16), 'sub_' + sf)
    system = re.sub(r'::(SubscribeToEvents|SubscribeToMessages|Startup|Begin|Listener)\(.*$', '', sf)
    system = re.sub(r'\(.*$', '', system).strip() or sf
    system = SYSTEM_NAMES.get(system, system)
    system = re.sub(r'::(Initialize|Enable|Start|StartupGame|SetMovie|SetMovieMask|UpdateSubscription|CheckNewButtonFlags|ProcessMouse|Update|OnPostLoadBegin)$', '', system)
    system = re.sub(r'^(\w+)::\1$', r'\1', system)
    hn = s['handler'] if not re.match(r'^[0-9a-f]+$', s['handler']) else dem.get(int(s['handler'], 16), '')
    hn = re.sub(r'\(Events::EventTemplate.*$|\(GameCoreEvent_Template.*$', '', hn) or None
    w = winof.get(hv)
    sub = {'system': system, 'handler': hn, 'linux_va': '0x%x' % hv, 'windows_rva': w[0] if w else None, 'windows_confidence': w[1] if w else None}
    if s['bus'] == 'GameCore' and str(key[1]) in wv and wv[str(key[1])]['linux_handler_va'] == ('%x' % hv):
        sub['windows_rva'] = '0x' + wv[str(key[1])]['windows_handler_rva']; sub['windows_confidence'] = 'inferred (registration order + size)'
    subs[key].append(sub)
    dtype_of.setdefault(key, s['data_type'])

# ---------------------------------------------------------------- entities
events = []
gc_ids = set(tr_by_id) | {k[1] for k in subs if k[0] == 'GameCore'}
for i in sorted(gc_ids):
    trs = tr_by_id.get(i, [])
    names = [t['event_name'] for t in trs]
    dt = dtype_of.get(('GameCore', i)) or (trs[0]['data_types'][0] if trs and trs[0]['data_types'] else None)
    stem = re.sub(r'^GameCoreEvent::|_EventData$', '', dt) if dt else None
    name = names[0] if len(names) == 1 else (' / '.join(names) if names else (stem or 'event %d' % i))
    lua = []
    params = None
    for n in names:
        m = ev_members.get(n)
        if m and m.get('lua_event'):
            lua.append(m['lua_event'])
            params = params or m.get('parameters')
    ent = {
        'id': 'exeevt:GameCore.%d' % i, 'bus': 'GameCore', 'event_id': i, 'name': name, 'engine_events': names,
        'engine_hashes': [t['hash'] for t in trs], 'lua_events': lua, 'lua_parameters': params,
        'data_type': dt.replace('Events::NullEventClass', 'none') if dt else None,
        'translators': [{k: t[k] for k in ('translator', 'linux_va', 'windows_rva', 'windows_confidence')} for t in trs],
        'subscribers': sorted(subs.get(('GameCore', i), []), key=lambda s: (s['system'], s['handler'] or '')),
        'availability': 'exe', 'status': 'verified' if trs else 'inferred',
        'evidence': [{'kind': 'exe-disassembly', 'note': ('the translator %s sends GameCoreEvent_Template<%d,...> (callee names of the Linux build)' % (trs[0]['translator'], i)) if trs else 'subscribed in the exe; no translator found for this id'}] +
                    ([{'kind': 'exe-registration', 'note': '%d subscriber handlers registered in the exe' % len(subs[('GameCore', i)])}] if subs.get(('GameCore', i)) else []),
    }
    events.append(ent)
buses = collections.OrderedDict()
for (bus, i), ss in sorted(subs.items()):
    if bus == 'GameCore':
        continue
    dt = dtype_of.get((bus, i))
    stem = re.sub(r'^(?:\w+::)*|_EventData$|Data$', '', dt or '') if dt else None
    nm = (stem or 'event') if dt and 'NullEventClass' not in dt else 'event %d (no data)' % i
    events.append({'id': 'exeevt:%s.%d' % (bus, i), 'bus': bus, 'event_id': i, 'name': nm, 'engine_events': [], 'engine_hashes': [], 'lua_events': [], 'lua_parameters': None,
                   'data_type': dt.replace('Events::NullEventClass', 'none') if dt else None, 'translators': [],
                   'subscribers': sorted(ss, key=lambda s: (s['system'], s['handler'] or '')), 'availability': 'exe', 'status': 'inferred',
                   'evidence': [{'kind': 'exe-registration', 'note': '%d subscriber handlers registered in the exe; the event name is the data type name' % len(ss)}]})
BUS_TEXT = {
    'GameCore': 'Events from GameCore (the game rules library), translated by the exe and delivered to the UI, renderer, audio and telemetry systems.',
    'LocalMachine': 'App-local UI events: resolution changed, show leader screen, toggle grid, exit to menu, and similar. Not part of the game state.',
    'Serial': 'Ordered UI and state events published in sequence: loads, saves, selection changes, option changes, network state.',
    'UIEvent': 'Input and debug console events (`UIE_DebugConsoleInput` is id 15) and UI system updates.',
    'Sequencer': 'Start-up and shutdown sequencing of the application states (init complete, main menu done, game view done).',
    'MovieEvent': 'Movie playback events (clip finished, clip frame).'}
bus_rec = []
for b in ('GameCore', 'LocalMachine', 'Serial', 'UIEvent', 'Sequencer', 'MovieEvent'):
    es = [e for e in events if e['bus'] == b]
    bus_rec.append({'id': 'exebus:' + b, 'name': b, 'description': BUS_TEXT[b], 'events': len(es), 'subscriptions': sum(len(e['subscribers']) for e in es)})
json.dump(events, open(os.path.join(BASE, 'data', 'exe_events.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(bus_rec, open(os.path.join(BASE, 'data', 'exe_event_buses.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
gc = [e for e in events if e['bus'] == 'GameCore']
print(len(events), 'events;', 'GameCore', len(gc), '(with translator', sum(1 for e in gc if e['translators']), ', with subscribers', sum(1 for e in gc if e['subscribers']), ', Lua events', sum(1 for e in gc if e['lua_events']), ')')
print([(b['name'], b['events'], b['subscriptions']) for b in bus_rec])
