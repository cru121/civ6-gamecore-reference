"""Pages for the exe function index (section exefn/). Called from build.py:
    exe_fn_section.make(add, index)         index = data/exe_function_index.json (columns name, linux_va, windows_rva, confidence, method, category, linux_size, notes)
    exe_fn_section.compact(index)           rows for the client-side search (site/exe_function_index.json)"""
import collections, re

CAT_DESC = {
    'other': 'Everything not matched to a subsystem by its name: template instances, standard-library code, small helpers.',
    'ForgeUI': 'The UI toolkit: controls, input, tooltips, animation, and the Lua exposure of the controls.',
    'GameCore bridge': 'Code that talks to GameCore: the cache of game state, event translators and handlers, the engine utility interface.',
    'WorldView': 'The 3D map renderer: terrain, landmarks, units, clutter, water, cameras.',
    'Lua (Havok)': 'Havok Script (the Lua virtual machine) functions the exe exports.',
    'FiraxisLive': 'Firaxis Live / My2K online services client.',
    'VFX': 'The visual effects system.',
    'Lua': 'Lua libraries and bindings hosted by the exe (see the [Lua tables](../exeapi/index.md)).',
    'base library': 'Engine base classes: memory, strings, containers, utilities.',
    'Network': 'Multiplayer: sessions, lobbies, matchmaking, cloud turns.',
    'Graphics': 'The rendering back end: device, shaders, command streams.',
    'Modding': 'The mod framework: loading, ownership checks, content handling.',
    'StrategicView': 'The 2D strategic map.',
    'Platform': 'Operating system and platform layer.',
    'Synthesis': 'Terrain synthesis: ridgelines, rivers, coast splines.',
    'Audio': 'Audio integration and the systems that drive it.',
    'FOW': 'Fog of war.',
    'Database': 'Access to the game database.',
    'Terrain': 'Terrain context, cells and baking.',
    'App': 'The application: start-up, game states, the main loop.',
    'library': 'Third-party libraries.',
    'GameState': 'Game state objects of the application layer.',
    'Events': 'The event system itself (see [engine events](../exeevents/index.md)).',
    'Minimap': 'The minimap.'}
CONF_CODE = {'high': 'h', 'medium': 'm', 'low': 'l', 'export': 'e', 'unmapped': 'u'}


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s)


def la(a):
    return '`0x%s`' % a if a else '—'


def trunc(s, n=150):
    return s if len(s) <= n else s[:n - 1] + '…'


def compact(index):
    rows = [[r[0], r[1], r[2], CONF_CODE[r[3]], r[5], r[6], r[7]] for r in index['rows']]
    cats = [c for c, _ in collections.Counter(r[5] for r in index['rows']).most_common()]
    return {'cats': cats, 'rows': rows}


def make(add, index):
    rows = index['rows']
    n = len(rows)
    conf = collections.Counter(r[3] for r in rows)
    cats = collections.OrderedDict((c, [r for r in rows if r[5] == c]) for c, _ in collections.Counter(r[5] for r in rows).most_common())

    L = ['# Engine executable functions\n',
         ('A searchable index of the engine executable `CivilizationVI.exe` (DX11, July 2024 build). The Windows build has no symbols and no class information, so function names come from the **Linux build of the same engine**, '
          'which exports about 199,000 names; a Windows address is listed where the same function could be found there. %d functions exist only on Windows (no Linux symbol): the exports named by the PE export table (ForgeUI, Havok), and Lua wrappers and control thunks '
          'named by the registration code, WorldView event handlers, the engine utility vtable and the debug console handlers; their Linux address is blank.\n') % sum(1 for r in rows if not r[1]),
         '- [Search all %d functions](all.md): by name, Lua method, note, or by address (a Windows RVA such as `0x547000`, or a Linux address).\n'
         '- Category pages below list the functions that have a Windows address.\n' % n,
         '## What the addresses mean\n',
         'Windows addresses are **RVAs** (add the image base 0x140000000 for the address Ghidra shows). Linux addresses are virtual addresses in the Linux `Civ6` executable. '
         'The DX12 executable has different RVAs and is not covered. Of the 52,101 functions the Windows executable contains, %d are named here; the rest have no Linux counterpart or could not be matched. '
         'The compiler merges identical functions on Windows, so several Linux names can share one Windows address.\n' % (conf['high'] + conf['medium'] + conf['low'] + conf['export']),
         '## Confidence\n',
         '| Confidence | Functions | How the Windows address was found | How reliable |', '|---|---|---|---|',
         '| high | %d | name join with the Windows export table, a string anchor with two or more strings, hand-checked disassembly, name-matched Lua registration wrappers | every check passed: 26 of 26 string anchors against the export ground truth, 5 of 5 Lua wrappers |' % conf['high'],
         '| medium | %d | a single string or rare-constant anchor, call-graph propagation of non-trivial functions, neighbour scoring at a strict threshold | about 94-97%% on hold-out tests, 12 of 12 Lua wrappers |' % conf['medium'],
         '| low | %d | tiny propagated functions, a lenient neighbour threshold, order alignment | **unreliable**: 1 of 19 checked Lua wrappers was right. Verify in the disassembly before using. |' % conf['low'],
         '| export | %d | the Windows export table names it (ForgeUI and Havok); no Linux counterpart | exact |' % conf['export'],
         '| unmapped | %d | no Windows address | name only |' % conf['unmapped'],
         '\nThe measured accuracy per method is in the analysis notes (`findings/topics/exe-analysis-tooling.md`). Names come from the Linux build and can differ in spelling from the Windows build (template arguments, calling conventions).\n',
         '## Categories\n', '| Category | What it is | Functions | With a Windows address |', '|---|---|---|---|']
    for c, rs in cats.items():
        mapped = sum(1 for r in rs if r[2])
        L.append('| [%s](%s.md) | %s | %d | %d |' % (c, safe(c), CAT_DESC.get(c, ''), len(rs), mapped))
    L.append('\nCategories were assigned from the function names and namespaces and are approximate; descriptions are inferred from them.')
    add('exefn/index.md', 'Engine executable functions', '\n'.join(L) + '\n')

    add('exefn/all.md', 'All exe functions (search)', '''# All exe functions: searchable index

Every function in the index (%d), with its Windows address where one was found. Search matches the name, the notes (Lua method names, event handlers, console commands) and the addresses, with or without the `0x`.
Filter by category or confidence; use the **low** filter with care: those addresses are mostly wrong (see [confidence](index.md#confidence)).

<div id="exefnapp">Loading the function index (about 5 MB)…</div>

<script src="{{ROOT}}exefnsearch.js"></script>
''' % n)

    for c, rs in cats.items():
        good = [r for r in rs if r[2] and r[3] in ('high', 'medium', 'export')]
        low = [r for r in rs if r[2] and r[3] == 'low']
        L = ['# %s\n' % c, '%s\n' % CAT_DESC.get(c, ''), '%d functions in this category, %d with a Windows address (%d high or medium confidence or exported, %d low). '
             'The rest are in the [full search](all.md).\n' % (len(rs), sum(1 for r in rs if r[2]), len(good), len(low)),
             '| Function | Windows RVA | Confidence | How mapped | Notes | Linux address | Size |', '|---|---|---|---|---|---|---|']
        for r in sorted(good, key=lambda r: int(r[2], 16)):
            L.append('| `%s` | `0x%s` | %s | %s | %s | %s | %s |' % (esc(trunc(r[0])), r[2], r[3], esc(trunc(r[4], 60)), esc(trunc(r[7], 80)), la(r[1]), r[6] or ''))
        if low:
            L.append('\n<details markdown="1"><summary>Low confidence (%d, unreliable)</summary>\n' % len(low))
            L.append('| Function | Windows RVA | How mapped | Linux address |')
            L.append('|---|---|---|---|')
            for r in sorted(low, key=lambda r: int(r[2], 16)):
                L.append('| `%s` | `0x%s` | %s | %s |' % (esc(trunc(r[0], 110)), r[2], esc(trunc(r[4], 50)), la(r[1])))
            L.append('\n</details>')
        add('exefn/%s.md' % safe(c), c, '\n'.join(L) + '\n')
