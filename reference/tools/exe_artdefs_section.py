"""Pages exeart/index.md and exeart/<Template>.md: the ArtDef vocabulary the exe reads. Called from build.py: exe_artdefs_section.make(add, entries, consumers)
Data: data/exe_artdefs.json, data/exe_artdef_consumers.json (tools/extract_exe_artdefs.py)."""
import re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def page_for(stem):
    return 'exeart/%s.md' % safe(stem)


def make(add, entries, consumers):
    ncons = sum(1 for e in entries for _ in e['consumers'])
    L = ['# ArtDef vocabulary\n',
         'Art definitions (`.artdef` XML files in `ArtDefs/` folders of the base game and every DLC) tell the renderer, the unit system, the lenses and the audio how things look and behave. The engine executable reads them with '
         '`ConfigureFromArtDefs`-style functions that ask for collections and parameters **by name**. This section lists, for each artdef type (the `m_TemplateName` stored in the file), the collection and parameter names the exe asks for, '
         'the value class each parameter has in the shipped files (Float, Int, Bool, String, Coord2D, RGB, ArtDef reference, BLP entry, ...), how many shipped files use it, and which parameter names the exe never asks for.\n',
         '**What is verified and what is inferred.** The names in the exe and the value classes and counts in the shipped files are **Verified** (strings referenced by a function, names counted in the files; no values or asset paths are kept). '
         'Which artdef type a function belongs to is **Inferred**: a function is assigned to the type whose names cover at least half of the names the function uses and clearly more than any other type (%d of %d functions are assigned; the rest are listed below). '
         '"Not read by the exe" means the name is in shipped files but not in the strings of the assigned functions; it may be read by a function that is not assigned, by a shared helper (for example the keyframe fields `Time`, `FOV` and `Tilt` of the camera curves are read by common curve code), or be unused.\n' % (sum(1 for c in consumers if c['assigned']), len(consumers)),
         '**For modders.** The names listed are the ones the exe code looks up, so they are the names worth using in a new artdef; a parameter that no function looks up is probably without effect (**not tested in the game**: the exe may also log or reject unknown names). '
         'The value classes show how the shipped files store each parameter; the exe code reads a parameter through its own typed accessor, so keep to the class the shipped files use. See also the [files and paths](../exe/files.md) page for where the game looks for `ArtDefs` folders.\n',
         '## Artdef types\n', '| Type | Shipped files | Parameters | Collections | Reading functions | Parameters not read by the exe |', '|---|---|---|---|---|---|']
    for e in sorted(entries, key=lambda e: e['stem'].lower()):
        cs = ', '.join('`%s`' % '::'.join(c['function'].split('::')[:-1][-2:]) for c in e['consumers'][:3])
        if len(e['consumers']) > 3:
            cs += ' (+%d)' % (len(e['consumers']) - 3)
        L.append('| [%s](%s) | %d | %d | %d | %s | %s |' % (e['stem'], safe(e['stem']) + '.md', e['files'], e['param_count'], len(e['collections']), cs or '—',
                                                          '—' if e['params_not_read'] is None else str(e['params_not_read'])))
    L.append('\n## Functions not assigned to a type (%d)\n' % sum(1 for c in consumers if not c['assigned']))
    L.append('| Function | Names | Best match | Score | Second | Score |')
    L.append('|---|---|---|---|---|---|')
    for c in consumers:
        if not c['assigned']:
            L.append('| `%s` (%s) | %d | %s | %s | %s | %s |' % (esc(c['function']), c['rva'] or '?', len(c['names']), c['best'], c['best_score'], c['second'], c['second_score']))
    add('exeart/index.md', 'ArtDef vocabulary', '\n'.join(L) + '\n')
    for e in entries:
        P = ['# %s artdef\n' % e['stem'],
             'Artdef type `%s`: %d shipped files (%s%s), %d parameter names, %d collection names. Back to the [overview](index.md).\n' % (
                 e['stem'], e['files'], ', '.join('`%s.artdef`' % s for s in e['file_stems'][:8]), ', ...' if len(e['file_stems']) > 8 else '', e['param_count'], len(e['collections']))]
        if e['consumers']:
            P.append('## Reading functions (inferred assignment)\n')
            P.append('| Function | Exe address | Names it uses | Names found in this type |')
            P.append('|---|---|---|---|')
            for c in e['consumers']:
                P.append('| `%s` | %s | %d | %d%% |' % (esc(c['function']), c['rva'] or '?', c['names'], round(c['score'] * 100)))
        else:
            P.append('No exe function was assigned to this type, so the "read by the exe" column is empty.\n')
        if e['collections']:
            P.append('\n## Collections\n')
            P.append('| Collection | Occurrences | Read by the exe |')
            P.append('|---|---|---|')
            for c in e['collections']:
                P.append('| <a id="c-%s"></a>`%s` | %d | %s |' % (safe(c['name']), esc(c['name']), c['count'], 'yes' if c['read_by_exe'] else ('' if not e['consumers'] else 'no')))
        if e['params']:
            P.append('\n## Parameters (%d)\n' % e['param_count'])
            P.append('<details%s markdown="1"><summary>%d parameter names</summary>\n' % (' open' if e['param_count'] <= 40 else '', e['param_count']))
            P.append('| Parameter | Value class | Files | Occurrences | Read by the exe |')
            P.append('|---|---|---|---|---|')
            for p in e['params']:
                P.append('| <a id="p-%s"></a>`%s` | %s | %d | %d | %s |' % (safe(p['name']), esc(p['name']), '/'.join(sorted(p['types'])), p['files'], p['count'],
                                                                    ('yes' if p['read_by_exe'] else 'no') if e['consumers'] else ''))
            P.append('\n</details>\n')
        if e['read_names_not_in_files']:
            P.append('\n## Names the exe uses that no shipped file contains (%d)\n' % len(e['read_names_not_in_files']))
            P.append('Strings of the assigned functions that are not collection or parameter names in any shipped file of this type: optional or unused parameters, enum-like values, file names or messages. '
                     'Not every entry is an artdef name.\n')
            P.append(', '.join('`%s`' % esc(n) for n in e['read_names_not_in_files']) + '\n')
        add(page_for(e['stem']), '%s artdef' % e['stem'], '\n'.join(P) + '\n')
