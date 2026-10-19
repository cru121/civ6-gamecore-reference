"""Page exedb/xml-format.md: the gameplay XML data format. Called from build.py: exe_xmlformat_section.make(add, entries, meta)
Data: data/exe_xmlformat.json, data/exe_xmlformat_meta.json (tools/extract_exe_xmlformat.py)."""
import re

KINDS = [('root', 'Root elements'), ('toplevel', 'Children of the root'), ('rowop', 'Row operations (children of a table element)'), ('child', 'Update parts and key columns'), ('colattr', 'Column attributes (inside a Table definition)')]
EXAMPLE = """```xml
<GameData>
  <Table name="MyThings">
    <Column name="ThingType" type="text" primarykey="true"/>
    <Column name="Cost" type="integer" notnull="true" default="0"/>
  </Table>
  <MyThings>
    <Row ThingType="THING_A" Cost="10"/>
    <Replace ThingType="THING_B" Cost="20"/>
    <Update><Where ThingType="THING_A"/><Set Cost="15"/></Update>
    <Delete ThingType="THING_B"/>
  </MyThings>
</GameData>
```"""


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def make(add, entries, meta):
    total = meta['files']
    L = ['# Gameplay XML data format\n',
         'The XML files that fill the game databases (the `GameData`/`GameInfo` files of the base game, DLCs and mods\' `UpdateDatabase` actions) are read by one loader in the exe, `Database::XMLSerializer`. '
         'This page lists the elements and attributes the loader recognises and the SQL each one produces. **Verified**: names and behaviour read from the decompiled loader functions (addresses in the tables); '
         'the shipped-file counts are from %d data XML files of the installed game (names only). The loader itself is the same for mods; which tables exist is defined by the game (see the [database statements](statements.md) and the GameCore reference).\n' % total,
         '**What the counts show.** The shipped files use `Replace` (%d) and `Row` (%d) for almost everything, plus `Update` (%d), `Delete` (%d) and `InsertOrIgnore` (%d). They define only %d tables with `Table` elements (the three files `Color_Tables.xml`, `Diplomacy_Tables.xml` and `Leader_Tables.xml` in the `Assets/Gameplay/Data/Schema/` folder of the base game; the main schema is SQL, `01_GameplaySchema.sql` and `02_AddTriggers.sql` in the same folder); `Index`, `DeleteMissingReferences`, '
         '`InsertOrAbort` and the column attributes `autoincrement` and `reference` appear in no shipped file, so they are known only from the loader code. Column types used in shipped table definitions: %s.\n' % (
             meta['rowops'].get('Replace', 0), meta['rowops'].get('Row', 0), meta['rowops'].get('Update', 0), meta['rowops'].get('Delete', 0), meta['rowops'].get('InsertOrIgnore', 0),
             sum(1 for e in entries if e['id'] == 'exexml:toplevel:Table' and e['shipped_uses']) and next(e['shipped_uses'] for e in entries if e['id'] == 'exexml:toplevel:Table'),
             ', '.join('`%s` (%d)' % kv for kv in meta['types'].items())),
         '## Structure\n', 'An illustrative file (invented names) showing each construct:\n', EXAMPLE + '\n',
         'Values are given as attributes of the row element or as child elements named after the column (both forms occur in the shipped files); a column named twice is an error. '
         'For tables in the loader\'s package list (it keeps a list of table names) the loader adds a `PackageID` column with the id of the package being loaded to the insert (`PostColumnInsert`, `0x79d7b0`); which tables are in that list was not read out.\n']
    for kind, title in KINDS:
        es = [e for e in entries if e['kind'] == kind]
        if not es:
            continue
        L.append('\n## %s\n' % title)
        L.append('| Name | Meaning | SQL | Function | Shipped uses |')
        L.append('|---|---|---|---|---|')
        for e in es:
            su = '%d' % e['shipped_uses'] if e['shipped_uses'] else '0 (not used by any shipped file)'
            if e['shipped_files'] and e['kind'] in ('toplevel', 'rowop'):
                su += ' in %d files' % e['shipped_files']
            L.append('| <a id="%s"></a>`%s` | %s | %s | `%s` (%s) | %s |' % (safe(e['kind'] + '-' + e['name']), esc(e['name']), esc(e['meaning']), ('`%s`' % esc(e['sql'])) if e['sql'] else '', esc(e['function'].split('::')[-1]),
                                                                          e['function_rva'], su))
    L.append('\n## Error messages of the loader\n')
    L.append('Messages the loader reports (they are also on the [messages](../exe/messages.md) page). Every one is prefixed `Database::XMLSerializer (<file>): `, and a failed table update adds "In XMLSerializer while updating table T from file F." or "... building table ...".\n')
    L.append('| Message | Function |')
    L.append('|---|---|')
    for m, fs in meta['messages'].items():
        L.append('| %s | %s |' % (esc(m), ', '.join('`%s`' % f for f in fs)))
    add('exedb/xml-format.md', 'Gameplay XML data format', '\n'.join(L) + '\n')
