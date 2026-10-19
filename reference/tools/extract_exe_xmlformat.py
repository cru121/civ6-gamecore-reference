"""The gameplay XML data format read by the exe (Database::XMLSerializer): root elements, table definitions, row operations, index and cleanup elements, with the SQL each one produces, the attributes
the code reads, the error messages it can raise, and how often the shipped data files use each element and attribute.
Input : decompiled Database::XMLSerializer functions (linux_depot/out/exetrace/xmlser_decomp*.txt, DecompList.java on ghi-exe; RVAs in xmlser_rvas*.txt), linux_depot/out/strmaps.pkl (messages),
        the game's data XML files (read in place; only element and attribute names and counts are kept)
Output: data/exe_xmlformat.json (entities exexml:<kind>:<name>), data/exe_xmlformat_meta.json."""
import collections, json, os, pickle, re
import xml.etree.ElementTree as ET

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"

# semantics recovered from the decompiled functions (rva = address in the Windows exe)
FN = {'load': ('Database::XMLSerializer::LoadFromMemory', '0x79d320'), 'dispatch': ('Database::XMLSerializer (root dispatch)', '0x79d3a0'), 'table': ('Database::XMLSerializer::BuildTable', '0x799e80'),
      'index': ('Database::XMLSerializer::IndexTable', '0x79bdc0'), 'dmr': ('Database::XMLSerializer::DeleteMissingReferences', '0x79ab90'), 'update_table': ('Database::XMLSerializer::UpdateTable', '0x79e890'),
      'insert': ('Database::XMLSerializer::InsertRow', '0x79c380'), 'update': ('Database::XMLSerializer::UpdateRow', '0x79d930'), 'delete': ('Database::XMLSerializer::DeleteRow', '0x79af50'),
      'package': ('Database::XMLSerializer::PostColumnInsert', '0x79d7b0')}
ITEMS = [
    # kind, name, function key, meaning, sql
    ('root', 'GameData', 'dispatch', 'Root element of a gameplay data file. The three root names are accepted equally.', ''),
    ('root', 'GameInfo', 'dispatch', 'Root element, same as GameData (older style).', ''),
    ('root', 'Database', 'dispatch', 'Root element, same as GameData.', ''),
    ('toplevel', 'Table', 'table', 'Defines a table; its children must all be Column elements (at least one). The table name is the name attribute.', 'create table <name> (<columns>, PRIMARY KEY (...), foreign key (...) references ...)'),
    ('toplevel', 'Index', 'index', 'Creates an index; needs name and table attributes and at least one Column child with a name attribute.', "CREATE INDEX IF NOT EXISTS '<name>' on <table> (<columns>)"),
    ('toplevel', 'DeleteMissingReferences', 'dmr', 'Cleans up rows whose foreign keys point at rows that no longer exist; the table and column attributes pick what to clean (the code reads the foreign key list of each table).', 'DELETE FROM <table> WHERE <column> NOT IN (SELECT <column> FROM <referenced table>)'),
    ('toplevel', '(any table name)', 'update_table', 'Any other child of the root names a table; its children are row operations (Row, Replace, InsertOrIgnore, InsertOrAbort, Update, Delete). Anything else is an error ("Row or Delete expected").', ''),
    ('rowop', 'Row', 'insert', 'Inserts a row. The attributes and child elements of the element are the column values.', 'insert into <table> (<columns>) values (...)'),
    ('rowop', 'Replace', 'insert', 'Inserts a row, replacing an existing row with the same key.', 'insert or replace into <table> ...'),
    ('rowop', 'InsertOrIgnore', 'insert', 'Inserts a row unless a row with the same key exists (the existing row is kept).', 'insert or ignore into <table> ...'),
    ('rowop', 'InsertOrAbort', 'insert', 'Inserts a row and fails on a key conflict.', 'insert or abort into <table> ...'),
    ('rowop', 'Update', 'update', 'Changes rows. Needs exactly one Set element (the new values) and may have one Where element (the condition; shipped files contain Update elements without Where, which then change every row). Both take attributes or child elements, conditions are joined with AND.', 'UPDATE <table> SET <col> = ? ... WHERE <col> = ? AND ...'),
    ('rowop', 'Delete', 'delete', 'Deletes rows; the attributes are conditions joined with AND (equality only, a column named twice is an error).', 'DELETE FROM <table> WHERE <col> = ? AND ...'),
    ('child', 'Where', 'update', 'Condition of an Update (attributes or child elements, at least one, at most one Where per Update).', ''),
    ('child', 'Set', 'update', 'New values of an Update (attributes or child elements, at least one, exactly one Set per Update).', ''),
    ('child', 'Column', 'table', 'A column of a Table (or a key column of an Index).', ''),
    ('colattr', 'name', 'table', 'Column name (required).', ''),
    ('colattr', 'type', 'table', 'SQL type name written as is into the create statement. Default when missing: integer.', ''),
    ('colattr', 'unique', 'table', 'Boolean: adds "unique".', 'unique'),
    ('colattr', 'notnull', 'table', 'Boolean: adds "not null".', 'not null'),
    ('colattr', 'primarykey', 'table', 'Boolean: the column joins the PRIMARY KEY clause (several columns make a composite key).', 'PRIMARY KEY (...)'),
    ('colattr', 'autoincrement', 'table', 'Boolean: with the key, writes "primary key autoincrement".', 'primary key autoincrement'),
    ('colattr', 'default', 'table', 'Default value of the column (written as a quoted literal, or NULL when empty).', 'default <value>'),
    ('colattr', 'reference', 'table', 'Foreign key: the attribute value is written after "references" in a foreign key clause (no shipped file uses it, so the accepted value form, table or table and column, is not confirmed).', 'foreign key (<col>) references <table>'),
]
SETS = {'rowop': ('Row', 'Replace', 'InsertOrIgnore', 'InsertOrAbort', 'Update', 'Delete')}

# shipped files
roots = collections.Counter()
top = collections.Counter()
top_files = collections.defaultdict(set)
rowops = collections.Counter()
rowop_files = collections.defaultdict(set)
colattrs = collections.Counter()
types = collections.Counter()
child = collections.Counter()
files_total = 0
tables_touched = collections.Counter()
for dp, dn, fn in os.walk(GAME):
    for f in fn:
        if not f.lower().endswith('.xml'):
            continue
        p = os.path.join(dp, f)
        try:
            head = open(p, 'rb').read(1200).decode('utf8', 'replace')
        except Exception:
            continue
        m = re.search(r'<(GameData|GameInfo|Database)\b', head)
        if not m:
            continue
        files_total += 1
        roots[m.group(1)] += 1
        stack = []
        try:
            for ev, el in ET.iterparse(p, events=('start', 'end')):
                if ev == 'start':
                    stack.append(el.tag)
                    d = len(stack)
                    if d == 2:
                        t = el.tag
                        if t in ('Table', 'Index', 'DeleteMissingReferences'):
                            top[t] += 1
                            top_files[t].add(f)
                        else:
                            top['(any table name)'] += 1
                            top_files['(any table name)'].add(f)
                            tables_touched[t] += 1
                    elif d == 3:
                        if stack[1] in ('Table', 'Index'):
                            if el.tag == 'Column':
                                child['Column'] += 1
                                if stack[1] == 'Table':
                                    for a, v in el.attrib.items():
                                        colattrs[a] += 1
                                        if a == 'type':
                                            types[v] += 1
                        else:
                            rowops[el.tag] += 1
                            rowop_files[el.tag].add(f)
                    elif d == 4 and el.tag in ('Where', 'Set') and stack[2] == 'Update':
                        child[el.tag] += 1
                else:
                    stack.pop()
                    el.clear()
        except ET.ParseError:
            pass

# messages (strings of the serializer functions)
ws, ls, wm, lm = pickle.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'strmaps.pkl'), 'rb'))
names = {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            names.setdefault(int(v, 16), re.sub(r'\(.*$', '', r[0]))
msgs = collections.defaultdict(set)
for a, s in ws.items():
    s = s.decode('latin1') if isinstance(s, bytes) else s
    for f in wm.get(a, ()):
        n = names.get(f, '')
        if n.startswith('Database::XMLSerializer') and re.search(r'expected|requires|required|Duplicate|Needs|mismatch|error|Empty|Cannot|Could not|contains no|Input XML', s) and not s.startswith('Database::XMLSerializer ('):
            msgs[s].add(n.split('::')[-1])

ents = []
for kind, name, fk, meaning, sql in ITEMS:
    if kind == 'root':
        used, fl = roots.get(name, 0), roots.get(name, 0)
    elif kind == 'toplevel':
        used, fl = top.get(name, 0), len(top_files.get(name, ()))
    elif kind == 'rowop':
        used, fl = rowops.get(name, 0), len(rowop_files.get(name, ()))
    elif kind == 'colattr':
        used, fl = colattrs.get(name, 0), None
    else:
        used, fl = child.get(name, 0), None
    ents.append({'id': 'exexml:%s:%s' % (kind, name), 'kind': kind, 'name': name, 'function': FN[fk][0], 'function_rva': FN[fk][1], 'meaning': meaning, 'sql': sql, 'shipped_uses': used,
                 'shipped_files': fl, 'messages': sorted(m for m, fs in msgs.items() if FN[fk][0].split('::')[-1] in fs) if fk not in ('dispatch',) else [],
                 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-disassembly', 'note': 'element/attribute name compared in %s (%s), decompiled' % (FN[fk][0], FN[fk][1])},
                              {'kind': 'game-script', 'note': 'counts from %d shipped data XML files (names only)' % files_total}]})
meta = {'files': files_total, 'roots': dict(roots), 'types': dict(types.most_common()), 'tables_touched': len(tables_touched), 'rowops': dict(rowops), 'colattrs': dict(colattrs),
        'unknown_rowops': {k: v for k, v in rowops.items() if k not in SETS['rowop']}, 'messages': {m: sorted(f) for m, f in sorted(msgs.items())}}
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_xmlformat.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
json.dump(meta, open(os.path.join(BASE, 'data', 'exe_xmlformat_meta.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'entries;', files_total, 'shipped data files;', dict(roots))
print('rowops', dict(rowops)); print('top', dict(top)); print('colattrs', dict(colattrs)); print('types', dict(types.most_common(8))); print('children', dict(child)); print('unknown rowops', meta['unknown_rowops'])
