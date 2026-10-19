"""Page exe/lua-enums.md: Lua enum tables the exe registers. Called from build.py: exe_enums_section.make(add, entries)
Data: data/exe_enums.json (tools/extract_exe_enums.py)."""
import re

GROUP = [('Network::LuaNetworkEnumsLibrary', 'Multiplayer and lobby'), ('LuaUIEnumsLibrary', 'Input, mouse and keys'),
         ('AppLuaUIEnumsLibrary', 'UI and application'), ('GameCore::App::Cache::Lua::IEnums', 'Game state and interface modes')]


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def make(add, entries):
    total = sum(e['member_count'] for e in entries)
    L = ['# Lua enum tables of the exe\n',
         'Besides the [GameCore enums](../enums/index.md) (database types, operations, events), the engine executable registers its own global Lua tables of named numbers: %d tables with %d members. '
         'They are what `Keys.VK_...`, `MouseEvents.LButtonDown`, `ServerType.SERVER_TYPE_STEAM` or `InterfaceModeTypes.SELECTION` mean in the game\'s UI scripts. '
         'The member names and the numeric values were read from the exe\'s registration code (**Verified**: each value is a constant stored by the code). '
         'For the 10 tables that also exist as GameCore enums every shared member has the same value in both places. '
         '"Script uses" counts how often the game\'s own Lua files write `Table.MEMBER`.\n' % (len(entries), total),
         '**Value kinds.** *small numbers* are plain sequence numbers or flags. *hash values* are 32-bit signed numbers computed from the member names (the same hash as GameCore types, so they are not stable to guess, always use the table in Lua). '
         'Values that look like hashes are shown signed, as Lua sees them.\n']
    by = {}
    for e in entries:
        lib = e['libraries'][0]
        by.setdefault(lib, []).append(e)
    for lib, title in GROUP:
        es = sorted(by.get(lib, []), key=lambda e: e['table'].lower())
        if not es:
            continue
        L.append('\n## %s\n' % title)
        L.append('| Table | Members | Value kind | Hash of | Script uses | GameCore enum |')
        L.append('|---|---|---|---|---|---|')
        for e in es:
            gc = ''
            if e['gamecore_enum']:
                c = e['gamecore_compare']
                gc = '[%s](../enums/%s.md) (%d of %d members agree)' % (e['table'], e['table'], c['same_value'], c['same_value'] + c['different_value'])
            hp = ('`%sNAME`' % e['hash_prefix'] if e['hash_prefix'] else 'no simple prefix') if e['kind'].startswith('hash') else ''
            L.append('| [%s](#%s) | %d | %s | %s | %d | %s |' % (esc(e['table']), safe(e['table']), e['member_count'], e['kind'], hp, e['script_uses'], gc))
    for lib, title in GROUP:
        for e in sorted(by.get(lib, []), key=lambda e: e['table'].lower()):
            L.append('\n### <a id="%s"></a>%s\n' % (safe(e['table']), e['table']))
            L.append('%s, %d members, %s%s. Registered by `0x%s`.\n' % (title, e['member_count'], e['kind'],
                                                                      '' if not e['script_files'] else ', used in %d script files' % e['script_files'],
                                                                      ', 0x'.join(e['register_rvas'])))
            L.append('<details%s markdown="1"><summary>%d members</summary>\n' % (' open' if e['member_count'] <= 12 else '', e['member_count']))
            L.append('| Member | Value | Script uses |')
            L.append('|---|---|---|')
            for m in e['members']:
                L.append('| `%s` | %s | %d |' % (esc(m['name']), m['value'], m['script_uses']))
            L.append('\n</details>\n')
    add('exe/lua-enums.md', 'Lua enum tables of the exe', '\n'.join(L) + '\n')
