"""The telemetry configuration compiled into the engine exe: the default ruleset (which events are on, how often) and the UI/gameplay counter tables.
Input : the two XML documents embedded as string literals in the exe (linux_depot/out/strmaps.pkl), found by their root element.
Output: data/exe_telemetry.json (entities exetel:<kind>:<name>), data/exe_telemetry_meta.json."""
import collections, json, os, pickle, re
import xml.etree.ElementTree as ET

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
ws, ls, wm, lm = pickle.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'strmaps.pkl'), 'rb'))
docs = {}
for a, s in ws.items():
    s = s.decode('latin1') if isinstance(s, bytes) else s
    if s.startswith('<?xml'):
        root = ET.fromstring(re.sub(r'^<\?xml[^>]*\?>', '', s))
        docs[root.tag] = (root, a)
ents = []
meta = {}
def ev(kind, name, attrs, extra):
    ents.append({'id': 'exetel:%s:%s' % (kind.replace(' ', '-'), name), 'kind': kind, 'name': name, 'attributes': attrs, 'availability': 'exe', 'status': 'verified', **extra,
                 'evidence': [{'kind': 'exe-string', 'note': 'part of an XML document embedded in the exe as a string literal'}]})
if 'Rulesets' in docs:
    root, _ = docs['Rulesets']
    rulesets = []
    for rs in root.iter('Ruleset'):
        rulesets.append(dict(rs.attrib))
        for e in rs.iter('Event'):
            if rs.get('Name') == 'Default Ruleset':
                ev('event', e.get('Name'), {k: v for k, v in e.attrib.items() if k != 'Name'}, {'enabled': e.get('Enabled') == '1', 'send_flags': int(e.get('SendFlags', '0')), 'turn_interval': int(e['TurnInterval']) if False else (int(e.get('TurnInterval')) if e.get('TurnInterval') else None)})
    meta['rulesets'] = rulesets
    meta['updates'] = [dict(u.attrib) for u in root.iter('Update')]
if 'TelemetryItems' in docs:
    root, _ = docs['TelemetryItems']
    meta['tables'] = []
    for it in root.iter('Item'):
        for t in it.iter('Table'):
            meta['tables'].append({'item': it.get('Name'), 'type': it.get('Type'), 'table': t.get('Name')})
            for ti in t.iter('TableItem'):
                ev('counter', ti.get('Name'), {k: v for k, v in ti.attrib.items() if k != 'Name'}, {'item': it.get('Name'), 'table': t.get('Name'), 'enabled': None, 'send_flags': None, 'turn_interval': None})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_telemetry.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(meta, open(os.path.join(BASE, 'data', 'exe_telemetry_meta.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'entries;', collections.Counter(e['kind'] for e in ents), '; events enabled', sum(1 for e in ents if e['kind'] == 'event' and e['enabled']))
