"""Page exe/modinfo.md: the .modinfo vocabulary read from the exe. Called from build.py: exe_modinfo_section.make(add, entries, meta)
Data: data/exe_modinfo.json, data/exe_modinfo_meta.json (tools/extract_exe_modinfo.py)."""
import collections, re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


SECTIONS = [
    ('mod file element', 'Elements of a .modinfo file', 'XML elements the exe reads in a mod file (`<Mod>`, `<Properties>`, `<Components>`, ...). "Shipped" counts how many times the element appears in the .modinfo files that come with the game.'),
    ('attribute', 'Attributes the exe reads', 'XML attributes the exe reads on those elements (`mod_id`, `action_id`, `criteria`, `required`, `inverse`, ...). `id`, `version`, `title` and `any` are read by generic code and not found as separate strings.'),
    ('mod property', 'Mod properties (`<Properties>` of the mod)', 'Key-value children that describe the mod.'),
    ('mod database field', 'Mod database fields', 'Names that the exe handles when it parses a mod into `Mods.sqlite` rather than as .modinfo input: version, creation and update times, `IsBasic`, `DBVersion`, dependencies.'),
    ('component or action type', 'Component and action types', 'The things a mod can do. Old-style files list them under `InGameActions` and `FrontEndActions`, newer files under `Components`. The handler class is the code that applies the component.'),
    ('component property', 'Component properties', 'Key-value children of a component (`<Properties>` inside it).'),
    ('setting type', 'Setting types (`<Settings>`)', 'Component types that appear under `Settings` in shipped files.'),
    ('criterion type', 'Criterion types', 'Conditions that decide whether a component applies, written in a `<Criteria>` block (referenced by the `criteria` attribute of a component). `Check` is the exe function that evaluates it.'),
    ('criterion parameter', 'Criterion parameters', 'Child names of `ConfigurationValueMatches`.'),
    ('setting criterion type', 'Setting criterion types', 'Conditions available to settings.'),
    ('game mode value', 'Values of `GameModeInUse`', 'The game modes the criterion can test.'),
    ('reference element', 'Reference and dependency elements', 'How mods point at each other.'),
    ('mod status code', 'Mod requirement status codes', 'Why a mod cannot be enabled (strings returned by `Modding.CheckRequirements`).'),
    ('subscription status', 'Workshop subscription status values', 'Strings returned by `Modding.GetSubscriptionDetails`.'),
    ('GetModInfo field', '`Modding.GetModInfo` result fields', 'Field names of the table the Lua function returns.')]


def make(add, entries, meta):
    by = collections.OrderedDict((k, [e for e in entries if e['kind'] == k]) for k, _, _ in SECTIONS)
    n_files = meta['shipped_files']
    old_style = sum(e['shipped_uses'] for e in entries if e['name'] == 'InGameActions')
    new_style = sum(e['shipped_uses'] for e in entries if e['name'] == 'Components')
    L = ['# The .modinfo vocabulary\n',
         'Everything the engine executable understands in a mod: the elements and attributes of a `.modinfo` file, the component (action) types, the criteria, the properties, and the codes returned to the mod browser. '
         'The names are the string literals of the code that parses and applies mods (`Modding::XmlModLoader`, `ModLoaderService`, the `Modding*` handlers and criteria classes); '
         'they are cross-checked against the %d `.modinfo` files that ship with the game, so each row shows whether the game itself uses the name.\n' % n_files,
         '**What is verified.** The name exists in the exe, and the function that uses it (or the count in the shipped files). **What is inferred.** The explanation of what a component or criterion does: it comes from the handler class name, '
         'the files that use it and the strings inside its handler, and none of it was tried in the running game.\n',
         'There are two styles in use. Old-style files list components under `InGameActions` / `FrontEndActions` with a separate `ActionCriteria` block (used in %d places by the shipped files); newer files use `Components` and `Settings` '
         '(%d places). The exe reads both.\n' % (old_style, new_style),
         'Names that the exe reads but no shipped file uses are options the game supports without showing an example (for example `AffectsSavedGames` appears once, `Blocks`, `ConflictsWith` and `Exclude` never).\n',
         '## Contents\n'] + ['- [%s](#%s) (%d)' % (t, safe(k), len(by[k])) for k, t, _ in SECTIONS if by[k]]
    for k, title, intro in SECTIONS:
        es = by[k]
        if not es:
            continue
        L.append('\n## <a id="%s"></a>%s\n' % (safe(k), title))
        L.append(intro + '\n')
        L.append('| Name | What it is (inferred) | Shipped | Seen with | In the exe | Handler or check |')
        L.append('|---|---|---|---|---|---|')
        for e in sorted(es, key=lambda e: (-e['shipped_uses'], e['name'].lower())):
            attrs = ', '.join(e['shipped_attributes'][:6]) or '—'
            fn = '; '.join('`%s`' % f['name'].split('::', 1)[-1] if f['name'].count('::') > 1 else '`%s`' % f['name'] for f in e['exe_functions'][:2]) or '—'
            h = '; '.join('`%s`%s' % (x['class'], (' (%s)' % x['rva']) if x['rva'] else '') for x in e['handlers']) or '—'
            L.append('| <a id="%s"></a>`%s` | %s | %d | %s | %s | %s |' % (safe(k + '-' + e['name']), esc(e['name']), esc(e['note'] or '—'), e['shipped_uses'], esc(attrs), esc(fn), esc(h)))
    add('exe/modinfo.md', 'The .modinfo vocabulary', '\n'.join(L) + '\n')
