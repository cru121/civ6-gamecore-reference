"""Copy the exe function index (tools/exe/build_index.py -> findings/data/exe_function_index.json) into data/ for the reference build.
Run before build.py. Columns: name, linux_va, windows_rva, confidence, method, category, linux_size, notes."""
import json, os, shutil

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src = os.path.abspath(os.path.join(BASE, '..', 'findings', 'data', 'exe_function_index.json'))
j = json.load(open(src, encoding='utf8'))
assert j['cols'] == ['name', 'linux_va', 'windows_rva', 'confidence', 'method', 'category', 'linux_size', 'notes'], j['cols']
# ---------------------------------------------------------------- Windows-only functions the analysis identified (no Linux symbol name)
import csv
T = os.path.abspath(os.path.join(BASE, '..', 'findings', 'tables'))
have = {r[2] for r in j['rows'] if r[2]}
extra = []
def add(name, rva, conf, method, cat, notes=''):
    rva = rva.replace('0x', '')
    if not rva or rva in have:
        return
    have.add(rva)
    extra.append([name, '', rva, conf, method, cat, 0, notes])
lua = json.load(open(os.path.join(BASE, 'data', 'exe_lua.json'), encoding='utf8'))
for e in lua:
    if e['object_kind'] == 'control type':
        add('Lua thunk %s:%s' % (e['object'], e['method']), e['wrapper_rva'], 'high', 'Lua registration code (the exe registers this thunk under the method name)', 'ForgeUI',
            'Lua %s:%s' % (e['object'], e['method']) + (' ' + e['cpp_signature'] if e.get('cpp_signature') else ''))
    else:
        add('Lua wrapper %s%s%s' % (e['object'], ':' if e['call_style'] == 'object' else '.', e['method']), e['wrapper_rva'], 'high', 'Lua registration code (the exe registers this wrapper under the method name)', 'Lua',
            'Lua %s.%s' % (e['object'], e['method']))
ev_name = {}
for e in json.load(open(os.path.join(BASE, 'data', 'exe_events.json'), encoding='utf8')):
    if e['bus'] == 'GameCore':
        ev_name[str(e['event_id'])] = e['name']
for rva, nm in (('540670', 'WorldView console'), ('69f10', 'Civ6App console'), ('7d780', 'GameViewState console'), ('1d69c0', 'CameraSystem console'), ('1ee760', 'Leader screen console'),
                ('8e27a0', 'ForgeUI debug console'), ('1f3b20', 'Minimap console'), ('4ac10', 'Application console'), ('a4f8d0', 'Color key console'), ('f56b0', 'GameCoreController console'),
                ('8aa70', 'Main menu console'), ('98290', 'Audio console')):
    add('Debug console handler: %s' % nm, rva, 'high', 'UIE_DebugConsoleInput handler (matches console commands inline)', 'App', 'handles UIEvent event 15 (UIE_DebugConsoleInput)')
for r in csv.DictReader(open(os.path.join(T, 'worldview_event_subscriptions.tsv'), encoding='utf8'), delimiter='	'):
    if r['data_type'].startswith('UIE_'):
        continue                      # UIEvent bus ids share the number space of the table; those handlers are covered by the console rows
    add('WorldView handler for event %s (%s)' % (r['event_id'], r['data_type']), r['windows_handler_rva'], 'medium', 'registration order and size match with the Linux build', 'WorldView',
        'handles GameCore event %s %s' % (r['event_id'], ev_name.get(r['event_id'], '')))
for r in csv.DictReader(open(os.path.join(T, 'EngineUtility_vtable_windows.tsv'), encoding='utf8'), delimiter='	'):
    add(r['name_from_linux_slot_order'], r['win_rva'], 'medium', 'Windows vtable slot order equals the Linux slot order', 'GameCore bridge', 'IEngineUtility1 slot %s' % r['slot'])
j['rows'] = j['rows'] + extra
j['rows'].sort(key=lambda r: (r[5], r[0]))
json.dump(j, open(os.path.join(BASE, 'data', 'exe_function_index.json'), 'w', encoding='utf8'), separators=(',', ':'), ensure_ascii=False)
print(len(j['rows']), 'functions,', len(extra), 'Windows-only rows added')
