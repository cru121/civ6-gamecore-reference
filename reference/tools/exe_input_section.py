"""Page exe/input.md: input actions, categories, contexts and keys. Called from build.py: exe_input_section.make(add, entries, meta)
Data: data/exe_input.json, data/exe_input_meta.json (tools/extract_exe_input.py)."""
import re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def src(s):
    return ', '.join('base game' if x == 'Base' else x for x in s.split(', '))


def make(add, entries, meta):
    cats = [e for e in entries if e['kind'] == 'category']
    ctxs = sorted((e for e in entries if e['kind'] == 'context'), key=lambda e: e['value'])
    acts = [e for e in entries if e['kind'] == 'action']
    keys = [e for e in entries if e['kind'] == 'key']
    L = ['# Input actions (hotkeys)\n',
         'Hotkeys are **data**: the actions, their categories and contexts and the default key or button for each live in the Configuration database (tables `InputActions`, `InputCategories`, `InputContexts`, `InputActionDefaultGestures`, `InputKeyData`), filled by `InputConfiguration.xml` and by the `Config` XML of expansions and scenarios. '
         'The exe loads them with `CivTech::Input::Manager::ReloadInputActions` (`0x96c950`), which joins the tables with this query (**Verified**, string in the exe): '
         '`SELECT ActionId, InputActions.Name AS \'Name\', Description, InputCategories.Name AS \'Category\', InputContexts.Value AS \'Context\', LayoutType FROM InputActions INNER JOIN InputCategories ... INNER JOIN InputContexts ... ORDER BY InputActions.ActionId`, '
         'and the default gestures with `SELECT "Index", GestureType, GestureData FROM InputActionDefaultGestures WHERE ActionId = ?`. Scripts look an action up with `Input.GetActionId("<ActionId>")` (68 calls in the shipped scripts; see the [`Input`](../exeapi/Input.md) table). '
         'This page lists what the installed game defines (%d actions, %d categories, %d contexts, %d key records) and which action names the exe also registers in code. '
         'A new hotkey needs an `InputActions` row (action id, text keys, category, context, layout type) and a default gesture row; the localisation keys (`LOC_OPTIONS_HOTKEY_...`) are text keys, not text.\n' % (len(acts), len(cats), len(ctxs), len(keys)),
         '**Layouts and gestures.** Actions are for the `PC` layout (%d, gesture type `KBMouse`) or the `Console` layout (%d, gesture type `Controller`). Context values are the numbers in the contexts table below; the query returns the **value**, so scripts and code compare numbers.\n' % (
             meta['layouts'].get('PC', 0), meta['layouts'].get('Console', 0)),
         '**Code-registered actions.** `App::InputAction::Manager::SetupActions` (`%s`) names %d actions in code: %s. %d of them are rows of the table; %s %s\n' % (
             meta['exe_rva'], len(meta['exe_names']), ', '.join('`%s`' % n for n in meta['exe_names']), len(meta['exe_names_in_db']),
             ('not in the table (cursor actions that code probably handles by itself, inferred from the names): ' + ', '.join('`%s`' % n for n in meta['exe_names_not_in_db']) + '.') if meta['exe_names_not_in_db'] else '',
             ''),
         '**Script references without a row.** The shipped scripts ask for %s; none of them has an `InputActions` row (the tutorial and popup rows are commented out in `InputConfiguration.xml`), so for those `Input.GetActionId` has nothing to return.\n' % (
             ', '.join('`%s`' % n for n in meta['scripts_unknown_actions']) or 'no unknown action ids'),
         '## Categories\n', '| Category | Text key | Visible | Sort | Actions | Defined in |', '|---|---|---|---|---|---|']
    for e in cats:
        L.append('| <a id="category-%s"></a>`%s` | `%s` | %s | %s | %d | %s |' % (safe(e['name']), e['name'], esc(e['name_key']), e['visible'], e['sort_index'], e['actions'], src(e['source'])))
    L.append('\n## Contexts\n')
    L.append('| Context | Value | Actions |')
    L.append('|---|---|---|')
    for e in ctxs:
        L.append('| <a id="context-%s"></a>`%s` | %d | %d |' % (safe(e['name']), e['name'], e['value'], e['actions']))
    L.append('\n## Actions (%d)\n' % len(acts))
    L.append('| Action | Category | Context | Layout | Default gesture | Defined in | Script uses |')
    L.append('|---|---|---|---|---|---|---|')
    for e in sorted(acts, key=lambda e: (e['category'] or '', e['name'].lower())):
        g = ', '.join('%s: `%s`' % (x['type'], esc(x['data'])) for x in e['gestures']) or '—'
        L.append('| <a id="action-%s"></a>`%s`%s | %s | %s | %s | %s | %s | %s |' % (safe(e['name']), e['name'], ' (exe)' if e['name'] in meta['exe_names'] else '', e['category'], e['context'], e['layout'], g, src(e['source']),
                                                                                  ('%d in %d files' % (e['script_uses'], e['script_files'])) if e['script_uses'] else '0'))
    L.append('\n## Key records (%d)\n' % len(keys))
    L.append('`InputKeyData` maps a key id to the text key shown in the options screen and the icon name. Types: %s.\n' % ', '.join('%s (%d)' % kv for kv in sorted(meta['key_types'].items())))
    L.append('<details markdown="1"><summary>%d key records</summary>\n' % len(keys))
    L.append('| Key id | Type | Text key | Icon |')
    L.append('|---|---|---|---|')
    for e in sorted(keys, key=lambda e: (e['key_type'] or '', e['name'])):
        L.append('| <a id="key-%s"></a>`%s` | %s | `%s` | `%s` |' % (safe(e['name']), e['name'], e['key_type'], esc(e['name_key']), esc(e['icon'])))
    L.append('\n</details>\n')
    add('exe/input.md', 'Input actions (hotkeys)', '\n'.join(L) + '\n')
