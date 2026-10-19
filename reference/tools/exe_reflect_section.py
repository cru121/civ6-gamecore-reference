"""Pages exetypes/index.md, exetypes/<namespace>.md and exetypes/other.md: reflected data types of the exe. Called from build.py: exe_reflect_section.make(add, entries, meta)
Data: data/exe_reflect.json, data/exe_reflect_meta.json (tools/extract_exe_reflect.py)."""
import collections, re

NOTE = {'AssetObjects': 'asset and artdef object model (artdef sets, collections, elements, values, instances)', 'BLP': 'blueprint package format (the `.blp` files under `Platforms/Windows/BLPs`)',
        'LeaderHeadPackageEntry': 'leader head package: wig (hair) passes, textures, bones', 'LeaderPackageEntryV2': 'leader package, version 2', 'FOWMeshVisSystem': 'fog-of-war mesh packages',
        'FGXModelFramework': 'model framework: timelines, triggers, behaviours, mesh bindings', 'FGXModel': 'model data', 'ModelMaterialData_VFX': 'material data for effects models', 'ModelMaterialData': 'model materials',
        'DecalDesc': 'decal descriptions', 'DecalDesc2': 'decal descriptions, version 2', 'FireFX': 'particle effect (FireFX) data', 'FireVM': 'effect virtual machine data', 'TimelineSet': 'model timelines',
        'TerrainEditDesc': 'terrain edit descriptions', 'TerrainEditDesc2': 'terrain edit descriptions, version 2', 'TerrainEditDesc3': 'terrain edit descriptions, version 3', 'TextureExport': 'texture export settings',
        'ForgeUI': 'UI types', 'UILensModelData': 'lens model data (see the lenses page)', 'LandmarkPackageEntry': 'landmark (building and district model) packages', 'CoastlineWaves': 'coastline wave settings',
        'Granny': 'Granny animation file wrapper'}
MIN = 15


def esc(v):
    return str(v).replace('|', '\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def page_for(namespace, big):
    return 'exetypes/%s.md' % (safe(namespace) if namespace in big else 'other')


def big_namespaces(entries):
    c = collections.Counter()
    for e in entries:
        c[e['namespace']] += max(1, e['field_count']) if e['kind'] == 'type' else 0
    return {n for n, k in c.items() if k >= MIN}


def type_block(e):
    P = ['\n### <a id="%s"></a>%s\n' % (safe(e['name']), e['name'])]
    P.append('Layout read from `GetTypeInfo` (`%s`)%s.\n' % (e['rva'], (', size %d bytes' % e['size']) if e['size'] else ''))
    P.append('| Offset | Field | Type |')
    P.append('|---|---|---|')
    for f in e['fields']:
        P.append('| %d (0x%x) | `%s` | %s |' % (f['offset'], f['offset'], esc(f['name']), '`%s`' % esc(f['type']) if f['type'] != '(not resolved)' else '(not resolved)'))
    return P


def enum_block(e):
    P = ['\n### <a id="%s"></a>%s (enum)\n' % (safe(e['name']), e['name'])]
    P.append('Members and values stored by `GetEnumInfo` (`%s`).\n' % e['rva'])
    P.append('| Member | Value |')
    P.append('|---|---|')
    for m in e['members']:
        P.append('| `%s` | %s |' % (esc(m['name']), '' if m['value'] is None else m['value']))
    return P


def make(add, entries, meta):
    big = big_namespaces(entries)
    types = [e for e in entries if e['kind'] == 'type']
    enums = [e for e in entries if e['kind'] == 'enum']
    by = collections.defaultdict(list)
    for e in entries:
        by[e['namespace']].append(e)
    L = ['# Reflected data types\n',
         'The exe describes many of its own data structures to a reflection system (`GetTypeInfo` and `GetEnumInfo` functions): every field gets a name, a type and a byte offset, every enum member a name and a value. They are the layouts of the serialized formats the game loads: '
         'the artdef object model, the blueprint (`.blp`) packages (%d `.blp` files ship with the game), leader, landmark and terrain packages, model and effect data. This section lists %d struct layouts (%d fields) and %d enums. '
         '**Verified**: field names, offsets and enum values are constants in the code; **Inferred**: what a structure is used for (from its name). Field types are the type functions the code calls; where the function had no name in the function map its own type-name string is used, and %d fields remain "(not resolved)".\n' % (
             meta['blp_files'], len(types), sum(e['field_count'] for e in types), len(enums), sum(1 for e in types for f in e['fields'] if f['type'] == '(not resolved)')),
         '**Cross-check.** The artdef XML files name their elements after these fields: %d of the %d distinct `m_...` element names in the shipped `.artdef` files (base game and DLC) are field names of the reflected types (not matched: %s).\n' % (meta['artdef_tags_matched'], meta['artdef_tags'], ', '.join('`%s`' % t for t in meta['artdef_tags_unmatched']) or 'none'),
         'These are in-memory layouts of the 64-bit Windows exe (offsets include pointers of 8 bytes and the alignment the compiler chose); they are not the on-disk byte layouts of the files, which can differ.\n',
         '## Namespaces\n', '| Namespace | Types | Fields | Enums | Meaning (inferred) | Page |', '|---|---|---|---|---|---|']
    for n in sorted(by, key=lambda n: -sum(e['field_count'] for e in by[n])):
        ts = [e for e in by[n] if e['kind'] == 'type']
        es = [e for e in by[n] if e['kind'] == 'enum']
        pg = page_for(n, big)
        L.append('| %s | %d | %d | %d | %s | [%s](%s#%s) |' % (n, len(ts), sum(e['field_count'] for e in ts), len(es), NOTE.get(n, ''), pg.split('/')[1][:-3], pg.split('/')[1], safe(n)))
    add('exetypes/index.md', 'Reflected data types', '\n'.join(L) + '\n')
    pages = collections.defaultdict(list)
    for n in sorted(by):
        pages[page_for(n, big)].append(n)
    for pg, nss in pages.items():
        title = nss[0] if len(nss) == 1 else 'Other namespaces'
        P = ['# %s\n' % ('Reflected types: ' + title), 'Back to the [overview](index.md).\n']
        for n in nss:
            if len(nss) > 1:
                P.append('\n## <a id="%s"></a>%s\n' % (safe(n), n))
                if NOTE.get(n):
                    P.append(NOTE[n] + ' (inferred).\n')
            elif NOTE.get(n):
                P.append('<a id="%s"></a>%s (inferred).\n' % (safe(n), NOTE[n][0].upper() + NOTE[n][1:]))
            for e in sorted(by[n], key=lambda e: (e['kind'], e['name'])):
                P += type_block(e) if e['kind'] == 'type' else enum_block(e)
        add(pg, title, '\n'.join(P) + '\n')
    return big
