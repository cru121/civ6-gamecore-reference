"""Pages for the Lua tables hosted by the engine exe (section exeapi/). Called from build.py:
    exe_lua_section.make(add, entities, tables)
Data: data/exe_lua.json, data/exe_lua_tables.json (tools/extract_exe_lua.py)."""
import collections, re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s)


def sig_text(e):
    sep = ':' if e['call_style'] == 'object' else '.'
    ps = []
    for p in e['params']:
        n = p.get('name') or 'arg%d' % p['index']
        t = p['lua_type']
        s = '%s: %s' % (n, t) if t != 'any' else n
        ps.append('[%s]' % s if p['optional'] else s)
    r = ''
    if e['returns']:
        r = ' -> ' + ', '.join(e['returns'])
    elif e.get('return_count'):
        r = ' -> %d value%s' % (e['return_count'], '' if e['return_count'] == 1 else 's')
    if e.get('param_certainty') == 'partial':
        ps.append('...')
    return '%s%s%s(%s)%s' % (e['object'], sep, e['method'], ', '.join(ps), r)


def page_for(t):
    if t['family'] == 'forgeui':
        return 'exeapi/controls/%s.md' % safe(t['name'])
    return 'exeapi/%s.md' % safe(t['name'])


def make(add, entities, tables, validation, classes=None):
    by_obj = collections.OrderedDict()
    for e in entities:
        by_obj.setdefault(e['object'], []).append(e)
    nat = [t for t in tables if t['family'] == 'native']
    ctl = [t for t in tables if t['family'] == 'forgeui']
    used = sum(1 for e in entities if e.get('usage'))
    n_native = sum(len(by_obj.get(t['name'], [])) for t in nat)
    n_ctl = sum(len(by_obj.get(t['name'], [])) for t in ctl)

    L = ['# Engine Lua tables\n',
         'These Lua tables are **not part of GameCore**: the engine executable registers them, so GameCore hooks (Community Extension, Frida on the DLL) never see them. '
         'They are what UI scripts call: `UI.PlaySound(...)`, `Network.HostGame(...)`, `GameConfiguration.GetValue(...)`, `Locale.Lookup(...)`, and the control methods on `Controls.X:SetHide(...)`.\n',
         'The exe has **no parameter names and no documentation**. What this section shows is recovered three ways, always marked *inferred*:\n',
         '- the **method names and the registering code** (verified: the name is a string literal in the exe and the wrapper address is known);\n'
         '- the **argument reads and return pushes** of the decompiled wrapper (types, optional or not, number of values returned);\n'
         '- **how the game\'s own Lua scripts call it** (argument counts, kinds, and an example call; parameter names appear only where a script passes the same variable name in most calls).\n',
         'ForgeUI control methods are different: the exe prints a C++ signature for most of them (`void SetHide( bool )`), so those types are exact; they are shown as C++ types converted to Lua types.\n',
         '**How to read a signature.** `Table.Method(a: string, [b: number])` is called with a dot; `Type:Method(...)` is called on an object with a colon. `[...]` marks an optional argument. '
         'A trailing `...` means a helper in the wrapper reads further arguments that were not recovered; the example calls show what the game passes. `-> number` is the type pushed back to Lua.\n',
         ('**How reliable is it.** For the %d static-table and object methods that the game scripts also call, the argument count recovered from code agrees with the scripts for %d%% of methods; the code under-counts for %d%% (a helper function hides the read) and over-counts for %d%% (an extra optional slot). '
          'Where they differ the larger number is shown and the other source is in the evidence list.\n') % (
             validation['compared'], round(100 * validation['match'] / validation['compared']), round(100 * validation['under'] / validation['compared']), round(100 * validation['over'] / validation['compared'])),
         '## Static tables and object types\n', '| Name | Kind | Methods | Called by game scripts | How it was named |', '|---|---|---|---|---|']
    for t in sorted(nat, key=lambda t: -t['methods']):
        ms = by_obj.get(t['name'], [])
        L.append('| [%s](%s) | %s | %d | %d | %s |' % (t['name'], page_for(t)[len('exeapi/'):], t['kind'], len(ms), sum(1 for m in ms if m.get('usage')), esc(t['basis'])))
    L.append('\n## ForgeUI control types\n')
    L.append('[%d types](controls/index.md) with %d methods (the `Controls.Name:Method()` API; each type lists the methods registered directly on it; a type may also inherit from `ControlBase`).\n' % (len(ctl), n_ctl))
    L.append('## Event objects\n')
    L.append('The exe creates one **event object** per Lua event (`Events.Name`, `LuaEvents.Name`) and gives each the same seven methods; see [Event objects](events.md).\n')
    add('exeapi/index.md', 'Engine Lua tables', '\n'.join(L) + '\n')

    for t in nat:
        ms = by_obj.get(t['name'], [])
        L = ['# %s\n' % t['name'], '%s with %d methods. *%s.* Registering function `%s`.\n' % (t['kind'].capitalize(), len(ms), t['basis'].rstrip('.'), t['group_rva'] or '-')]
        if t['style'] == 'object':
            L.append('Methods are called on a value of this type with a colon (`obj:Method(...)`).\n')
        else:
            L.append('Methods are called with a dot (`%s.Method(...)`).\n' % t['name'])
        L.append('| Method | Returns | In game scripts | Example | Status |')
        L.append('|---|---|---|---|---|')
        for e in sorted(ms, key=lambda e: e['method']):
            u = e.get('usage')
            ex = esc(u['examples'][0]) if u and u['examples'] else '—'
            rets = ', '.join(e['returns']) if e['returns'] else ('%d value%s' % (e['return_count'], '' if e['return_count'] == 1 else 's') if e.get('return_count') else '—')
            L.append('| <a id="%s"></a>`%s` | %s | %s | %s | %s |' % (
                safe(e['id'][6:]).lower(), esc(sig_text(e).replace('...)', '…)')), esc(rets),
                ('%d calls, %d files' % (u['calls'], u['files'])) if u else 'not called', ('`%s`' % ex) if ex != '—' else '—', e['status']))
        add(page_for(t), t['name'], '\n'.join(L) + '\n')

    L = ['# ForgeUI control types\n',
         'The `Controls.Name:Method()` API of the UI toolkit. Signatures come from the strings the exe prints for each method; the owning type of a method is **inferred** where the same method name exists on several types '
         '(from the neighbouring methods in the code, or the unique name), and is shown per page.\n', '| Type | Methods | Basis |', '|---|---|---|']
    for t in sorted(ctl, key=lambda t: t['name'].lower()):
        L.append('| [%s](%s.md) | %d | %s |' % (t['name'], safe(t['name']), t['methods'], esc(t['basis'])))
    add('exeapi/controls/index.md', 'ForgeUI control types', '\n'.join(L) + '\n')
    for t in ctl:
        ms = by_obj.get(t['name'], [])
        L = ['# %s\n' % t['name'], 'ForgeUI control type (%s). %d methods, called on an instance with a colon: `Controls.SomeName:Method(...)`.\n' % (t.get('cpp_type') or 'unassigned', len(ms))]
        cm = {c['name']: c for c in (classes or [])}
        cc = cm.get(t.get('cpp_type') or '') or cm.get('ForgeUI::' + (t.get('cpp_type') or ''))
        if cc and cc['base_chain']:
            L.append('C++ base classes (from the exe RTTI, see [engine classes](../../execlass/ForgeUI.md)): ' + ' > '.join('`%s`' % b for b in cc['base_chain']) + '. Whether the Lua type also exposes the base class methods was not checked; the methods below are those registered on this type itself.\n')
        L.append('| Method | C++ signature printed by the exe | Lua signature | Owner basis |')
        L.append('|---|---|---|---|')
        for e in sorted(ms, key=lambda e: e['method']):
            L.append('| <a id="%s"></a>`%s` | %s | `%s` | %s |' % (safe(e['id'][6:]).lower(), esc(e['method']), ('`%s`' % esc(e['cpp_signature'])) if e.get('cpp_signature') else '—',
                                                                    esc(sig_text(e)), esc(e.get('owner_basis') or '')))
        add(page_for(t), t['name'], '\n'.join(L) + '\n')

    add('exeapi/events.md', 'Event objects', '''# Event objects

Every Lua event (`Events.Name`, `LuaEvents.Name`) is an object the exe creates and equips with the same seven methods. The exe registers %d such objects, one per event, each with its own copy of the methods.
The event names and their parameters are in the [Lua events list of the GameCore reference](../enums/LuaEvents.md); this page only describes the methods every event object has. All of this is **inferred** from the registration code and the error messages inside the exe.

| Method | What it does (inferred) |
|---|---|
| `Add(function, [dispatch_count])` | Register a handler. The exe's own message: `Invalid number of arguments. Add(function, [dispatch_count])`; a `dispatch_count` of 0 is rejected (`Argument 2 must not be 0.`). The optional count is probably how many times the handler runs before it is removed. |
| `Remove(function)` | Unregister a handler (`Invalid number of arguments. Remove(function)`). |
| `RemoveAll()` | Remove every handler of the event. |
| `Call(...)` | Raise the event with the given arguments. |
| `CallImmediate(...)` | Raise the event and run the handlers immediately (the name suggests `Call` may defer). |
| `Dispatch(...)` | Deliver queued calls to the handlers. |
| `Count()` | Number of registered handlers. |

Handlers are Lua functions; the first argument to `Add` is checked as a function (`luaL_checktype ... function`).
''' % [t for t in tables if t['family'] == 'events'][0]['objects'])
