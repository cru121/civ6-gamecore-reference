"""Engine-exe entities for the reference: AppOptions, command-line switches, debug console commands.
Inputs (all produced by the exe analysis, see ../../tools/README.md):
  ../../findings/tables/exe_app_options_windows.tsv   (tools/exe/winopts.py)
  ../../findings/tables/debug_console_commands.tsv    (help lines, tools/exe/console_cmds.py)
  ../../findings/tables/debug_console_commands_windows.tsv (matched phrases, tools/exe/wincons.py)
  curated/_exe_default_options.yaml, curated/_exe_switches.yaml
Outputs: data/exe_options.json, data/exe_switches.json, data/exe_console.json. Run before build.py."""
import csv, json, os, re, yaml

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
F = os.path.abspath(os.path.join(BASE, '..', 'findings', 'tables'))
def B(*a): return os.path.join(BASE, *a)
def rows(path):
    return list(csv.reader(open(path, encoding='utf8', newline=''), delimiter='\t'))[1:]

# ------------------------------------------------------------------ options
snap = yaml.safe_load(open(B('curated', '_exe_default_options.yaml'), encoding='utf8'))
fkeys = snap['keys']
raw = rows(os.path.join(F, 'exe_app_options_windows.tsv'))
reads = {}
for r in raw:
    if r[0] == 'access':
        reads.setdefault((r[1], r[2]), []).append(r[6])
options = []
for r in raw:
    if r[0] != 'register':
        continue
    kind, sec, key, ty, default, desc, site, fn = r[:8]
    k = '%s.%s' % (sec, key)
    base_ty = 'string' if ty == 'string' else 'integer'
    ff = fkeys.get(k)
    exe_desc = desc.strip()
    file_desc = (ff or {}).get('description', '')
    if exe_desc:
        d_text, d_src = exe_desc, 'exe'
    elif file_desc:
        d_text, d_src = file_desc, 'options-file'
    else:
        d_text, d_src = None, None
    ev = [{'kind': 'exe-registration', 'note': 'RegisterOption call site in CivilizationVI.exe (DX11, Jul 2024)'}]
    if ff:
        ev.append({'kind': 'user-file', 'note': 'key present in %s as written by the game' % ff['file']})
    options.append({
        'id': 'exeopt:%s.%s' % (sec, key),
        'section': sec, 'key': key, 'file': ff['file'] if ff else None, 'value_type': base_ty,
        'default': default if default != '' else None,
        'description': d_text, 'description_source': d_src,
        'cli_override': base_ty == 'integer',
        'registered_at': '0x' + site, 'registered_in': '0x' + fn,
        'read_sites': sorted('0x' + x for x in reads.get((sec, key), [])),
        'availability': 'exe',
        'status': 'verified' if ff and (not exe_desc or not file_desc or exe_desc == file_desc) else 'inferred',
        'evidence': ev,
    })
options.sort(key=lambda o: (o['section'], o['key']))

# ------------------------------------------------------------------ switches
sw = yaml.safe_load(open(B('curated', '_exe_switches.yaml'), encoding='utf8'))
switches = []
for s in sw['switches']:
    switches.append({'id': 'exeswitch:' + s['switch'], 'switch': s['switch'], 'kind': 'fixed', 'function': s['function'], 'rva': s['rva'],
                     'effect': s['effect'], 'availability': 'exe', 'status': s['status'],
                     'evidence': [{'kind': 'exe-string', 'note': 'string literal referenced by %s' % s['function']}]})
g = sw['generic']
switches.append({'id': 'exeswitch:generic-option', 'switch': g['switch'], 'kind': 'generic', 'function': g['function'], 'rva': g.get('rva'),
                 'effect': g['effect'], 'availability': 'exe', 'status': g['status'],
                 'evidence': [{'kind': 'exe-disassembly', 'note': g['evidence_note']}]})

# ------------------------------------------------------------------ console
HANDLERS = {  # windows rva -> (display name, linux-side name/notes)
    '540670': 'WorldView console (terrain, time of day, rendering)',
    '69f10': 'Civ6App (application and graphics)',
    '7d780': 'GameViewState (game view, overlays)',
    '1d69c0': 'CameraSystem',
    '1ee760': 'Leader screen',
    '8e27a0': 'ForgeUI debug (UI)',
    '1f3b20': 'Minimap',
    '4ac10': 'Application-level handler',
    'a4f8d0': 'Color key system',
    'f56b0': 'GameCoreController (game core)',
    '8aa70': 'Main menu',
    '98290': 'Audio',
}
help_rows = rows(os.path.join(F, 'debug_console_commands.tsv'))
phr = {}
for r in rows(os.path.join(F, 'debug_console_commands_windows.tsv')):
    phr.setdefault(r[0], []).append(r)
console = []
seen = set()
for r in help_rows:
    h, lva, wrva, cmd, desc = (r + [''] * 5)[:5]
    if cmd.startswith('(no help'):
        continue
    cmd = cmd.strip()
    cid = 'execmd:%s:%s' % (wrva, re.sub(r'\s+', ' ', cmd))
    if cid in seen:
        continue
    seen.add(cid)
    console.append({'id': cid, 'command': cmd, 'description': desc.strip() or None, 'handler': HANDLERS.get(wrva, wrva),
                    'handler_rva': '0x' + wrva, 'availability': 'exe', 'status': 'verified',
                    'evidence': [{'kind': 'exe-string', 'note': 'help line printed by the handler'}]})
console.sort(key=lambda c: (c['handler'], c['command']))
matched = []
for h, rs in phr.items():
    for r in rs:
        lit = r[3].strip()
        if not lit or ' ---' in lit or lit.startswith('-' * 5):
            continue
        calls = [x.strip() for x in r[5].split(' | ') if x.strip()] if len(r) > 5 else []
        matched.append({'handler': HANDLERS.get(h, h), 'handler_rva': '0x' + h, 'phrase': lit, 'site': '0x' + r[2], 'calls': calls[:6]})
matched.sort(key=lambda m: (m['handler'], int(m['site'], 16)))

json.dump(options, open(B('data', 'exe_options.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(switches, open(B('data', 'exe_switches.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump({'commands': console, 'matched_phrases': matched}, open(B('data', 'exe_console.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print('exe options %d (%d with a file), switches %d, console commands %d, matched phrases %d' % (
    len(options), sum(1 for o in options if o['file']), len(switches), len(console), len(matched)))
