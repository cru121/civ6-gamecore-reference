"""Page exe/lenses.md: the lens system (layers, lenses, layer sets). Called from build.py: exe_lenses_section.make(add, entries, meta)
Data: data/exe_lenses.json, data/exe_lenses_meta.json (tools/extract_exe_lenses.py)."""
import re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def src(files):
    return ', '.join('base game' if f == 'Base' else f.replace('DLC/', '') for f in files)


def make(add, entries, meta):
    layers = [e for e in entries if e['kind'] == 'layer']
    lenses = [e for e in entries if e['kind'] == 'lens']
    L = ['# Lenses and lens layers\n',
         'The map lenses (appeal, religion, continent, movement range, ...) are built from **layers**. A layer is a named group of map decorations (hex colouring, icons, labels, borders) that a UI script switches on and off with the `UILens` Lua table. '
         'A **lens** is a named combination: it lists the layers that are active and the layers the player may still toggle on top (the permission set). Lenses and layer sets are defined in `Lenses.artdef`; the exe registers the layer names and the UI scripts select lenses by name. '
         'This page collects the names from the three places and how the game\'s own scripts use them. **Verified**: the names (exe strings, artdef, script call arguments) and the Lua `LensLayers` constants. '
         '**Inferred**: the meaning of the "permission" set (from its name and use).\n',
         '**How it fits together.** `UILens.SetActive("<lens>")` switches to a lens from the `Lens` collection (%d lenses in the base game and DLC artdefs); the lens points to an *ActiveLayers* set and a *PermissionMask* set of the `LensLayers` collection, each a list of layer names from the `LayersList` collection (%d names; note that the artdef collection called `LensLayers` holds these sets and is not the Lua table `LensLayers`, which only holds numeric constants). '
         'Scripts get a layer\'s id with `UILens.CreateLensLayerHash("<layer>")` (%d calls in the game scripts) and toggle it with `ToggleLayerOn`/`ToggleLayerOff`; the numeric `LensLayers.<NAME>` constants of the [enum tables](lua-enums.md#lenslayers) number the same layers. '
         'See the [`UILens`](../exeapi/UILens.md) table for the functions and the [ArtDef vocabulary](../exeart/lenses.md) for the artdef parameters.\n' % (len(lenses), meta['artdef_layers'], meta['hash_uses_total']),
         '**Differences between the sources.** The exe registers %d layer names (`LensManager` constructor, `%s`); the artdef layer list has %d names (base game and DLC). Names only in the artdef: %s. Name only in the exe: %s. '
         'Layer names that scripts hash but neither list contains: %s. Lenses never selected by a literal name in the game scripts (they may be selected through a variable): %s.\n' % (
             meta['exe_layers'], meta['rva'], meta['artdef_layers'], ', '.join('`%s`' % n for n in meta['layers_artdef_not_exe']) or 'none', ', '.join('`%s`' % n for n in meta['layers_exe_not_artdef']) or 'none',
             ', '.join('`%s`' % n for n in meta['hash_names_unknown']) or 'none', ', '.join('`%s`' % n for n in meta['artdef_lenses_unused']) or 'none'),
         '## Lenses (%d)\n' % len(lenses), '| Lens | Active layers | Permission layers | Defined in | Script uses |', '|---|---|---|---|---|']
    for e in sorted(lenses, key=lambda e: e['name'].lower()):
        L.append('| <a id="lens-%s"></a>`%s` | %d (%s) | %d (%s) | %s | %s |' % (safe(e['name']), e['name'], len(e['active_layers']), esc(e['active_set'] or '—'), len(e['permission_layers']), esc(e['permission_set'] or '—'),
                                                                              src(e['artdef_files']), ('%d in %d files' % (e['script_uses'], e['script_files'])) if e['script_uses'] else '0'))
    L.append('\n<details markdown="1"><summary>Layers of each lens</summary>\n')
    L.append('| Lens | Active layers | Permission layers |')
    L.append('|---|---|---|')
    for e in sorted(lenses, key=lambda e: e['name'].lower()):
        L.append('| `%s` | %s | %s |' % (e['name'], ', '.join('`%s`' % x for x in e['active_layers']) or '—', ', '.join('`%s`' % x for x in e['permission_layers']) or '—'))
    L.append('\n</details>\n')
    L.append('## Layers (%d)\n' % len(layers))
    L.append('Columns: whether the exe registers the name, whether the artdef layer list has it (base game / DLC), the `LensLayers` constant (the number scripts can use), script hash calls, and in how many layer sets (active or permission lists) it appears.\n')
    L.append('| Layer | Exe | Artdef | `LensLayers` constant | Hash calls | Layer sets |')
    L.append('|---|---|---|---|---|---|')
    for e in sorted(layers, key=lambda e: e['name'].lower()):
        L.append('| <a id="layer-%s"></a>`%s` | %s | %s | %s | %s | %d |' % (safe(e['name']), e['name'], 'yes' if e['in_exe'] else 'no', src(e['artdef_files']) if e['in_artdef'] else 'no',
                                                                         ('`%s` = %d' % (e['enum_name'], e['enum_value'])) if e['enum_name'] else '—',
                                                                         ('%d in %d files' % (e['hash_uses'], e['hash_files'])) if e['hash_uses'] else '0', len(e['in_sets'])))
    L.append('\n**Note on the constants.** The `LensLayers` table also has `DISTRICTS_FIRST` (= `DISTRICTS_CITY_CENTER`), `DISTRICTS_LAST` (= `DISTRICTS_SPACEPORT`) and `NUM_LENS_LAYERS` (57) as range markers, and the enum spells a few names differently from the layer names '
             '(`COMMERICAL`, `WATER_AVAILABLITY`, `ARCHAELOGY`); the table above matches them ignoring case and those spellings.\n')
    add('exe/lenses.md', 'Lenses and lens layers', '\n'.join(L) + '\n')
