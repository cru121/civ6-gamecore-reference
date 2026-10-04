#!/usr/bin/env python3
"""Generate topics/40-worldbuilder.md: the World Builder Lua API grouped by manager, with call forms, returns, undo behaviour and cautions.

Input: data/worldbuilder_notes.json (per-method notes written by AI agents from the decompiled Lua wrappers and the static call graph;
all of it is labelled inferred on the page). Run before build.py.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
notes = json.load(open(os.path.join(DATA, 'worldbuilder_notes.json'), encoding='utf-8'))
by = {n['id']: n for n in notes}
model = by.get('model:undo')

GROUPS = [
    ('WorldBuilderManager', 'WorldBuilder (the global)', 'Entry point and undo control. `WorldBuilder.CityManager()`, `MapManager()`, `PlayerManager()`, `UnitManager()`, `ModManager()` and `ConfigurationManager()` return the sub-managers below.'),
    ('WorldBuilderManager_Inactive', 'WorldBuilderManager_Inactive', 'A separate registration with one method.'),
    ('WorldBuilderCityManager', 'City manager', 'Create and remove cities, buildings and districts, move plot ownership, read and write city and district values.'),
    ('WorldBuilderUnitManager', 'Unit manager', 'Create and remove units.'),
    ('WorldBuilderMapManager', 'Map manager', 'Terrain, features, resources, improvements, routes, rivers, cliffs, continents, reveal state and the placement checks.'),
    ('WorldBuilderPlayerManager', 'Player manager', 'Initialize and remove players, set leader, era, gold, faith, civics, technologies and start positions.'),
    ('WorldBuilderConfigurationManager', 'Configuration manager', 'Map-level configuration values.'),
    ('WorldBuilderModManager', 'Mod manager', 'The mod metadata strings of a World Builder map.'),
]

def cell(s, n=None):
    s = (s or '').replace('|', '/').replace('\n', ' ').strip()
    return s

def row(n):
    obj, meth = n['id'][4:].split('.')
    undo = {'yes': 'yes', 'no': 'no', 'unknown': 'unknown'}.get(n.get('undo'), '?')
    if n.get('confidence') != 'high' and undo != 'unknown':
        undo += ' (probably)'
    conf = {'high': 'high', 'medium': 'medium', 'low': 'low'}.get(n.get('confidence'), '?')
    call = cell(n['usage'])
    call = '`%s`' % call if call and '`' not in call else call
    cautions = cell(n.get('cautions'))
    summ = cell(n['summary'])
    text = summ + (' ' + cautions if cautions else '')
    return '| <a id="%s"></a>[%s](lua/%s.md#%s) | %s | %s | %s | %s | %s |' % (
        meth.lower(), meth, obj, meth.lower(), call, cell(n['returns']), undo, conf, text)

out = ['---', 'title: World Builder from Lua', 'order: 40', '---', '# World Builder from Lua', '']
out += [
    '> **Status.** Everything on this page was read from the decompiled C++ of the Lua wrappers and from the static call graph of the symbol build. '
    'The per-method notes were written by an AI assistant and are **inferred**; nothing here was run by us in a game. '
    'A "confidence" column says how sure the reading is. Real mod code that uses these calls is quoted only where it is public (Gedemon\'s Civ6-GCO).',
    '',
    '## What it is',
    '',
    'The World Builder is the game\'s map and scenario editor. Its engine side is a set of managers (cities, units, map, players, configuration, mod metadata) '
    'and a family of **command objects** that give the editor undo and redo. The game also registers **99 Lua methods** for these managers on 8 objects, '
    'in the **gameplay** Lua state. None of them appear in the community reference, so this page groups them by task.',
    '',
    'They reach editor code paths that ordinary gameplay Lua has no method for: placing a building in a city directly, setting the owner of any plot, '
    'initializing or removing a player. Mods use them as a workaround where an ordinary method does not exist or does not work (for example the two-step plot owner flip: '
    'clear with `SetPlotOwner(x, y, false)`, then assign `SetPlotOwner(x, y, city)`; see also `Plot.SetOwner`).',
    '',
    '```lua',
    'local city = Players[playerID]:GetCities():FindID(cityID)     -- an ordinary city object',
    'WorldBuilder.CityManager():CreateBuilding(city, buildingType, 100)',
    'WorldBuilder.CityManager():SetPlotOwner(x, y, false)           -- clear',
    'WorldBuilder.CityManager():SetPlotOwner(x, y, city)            -- assign',
    '```',
    '',
    '## The undo model',
    '',
]
if model:
    out += [cell(model['summary']), '', '*Inferred.* ' + cell(model.get('cautions')), '',
            'Methods marked **undo: yes** below construct a command (so they appear in the editor\'s undo history and are reversible with `WorldBuilder.Undo()`); '
            '**no** means the call edits state directly or only reads. Whether a missing command means "not undoable" is itself inferred from the call data.', '']
out += [
    '## Things to know before you rely on it',
    '',
    '* **Silent failure.** Several wrappers return without doing anything when an argument is missing, instead of raising an error. Example: `PlayerManager:SetPlayerHasCivic` and `SetPlayerHasTech` need **all** arguments, including the progress value; with one fewer they do nothing.',
    '* **Return values do not always report success.** `CityManager:RemoveDistrict` always returns `false` (the wrapper pushes a constant), and `MapManager:SetCoastalLowland` and `SetImprovementPillaged` also always return `false`, even when they worked. `PlayerManager:InitializePlayer` and `SetPlayerSlotStatus` return `true` whenever arguments were present, ignoring the engine\'s result.',
    '* **Not everything is undoable.** Several setters write state directly (see the *Undo* column). `PlayerManager:UninitializePlayer` removes all units and cities of the player, grouped in one undo block.',
    '* **Argument forms vary.** Plots can usually be given as `(x, y)` or as a plot object; cities and districts as objects or id pairs; types as numbers or type-name strings. The helper functions that decide this were not decompiled, so those forms are inferred from argument counts.',
    '* **Fixed point.** `SetPlayerGold` and `SetPlayerFaith` store their argument shifted left by 8 bits (fixed point), as the wrapper code shows.',
    '* **Possible bug.** `ConfigurationManager:GetMapValue` reads its type argument from the first stack slot (the object itself on a colon call), `SetMapValue` from the second; call `GetMapValue` carefully.',
    '',
]
for obj, title, blurb in GROUPS:
    ms = sorted([n for n in notes if n['id'].startswith('lua:%s.' % obj)], key=lambda n: n['id'])
    if not ms:
        continue
    out += ['## %s' % title, '', blurb + ' %d methods.' % len(ms), '',
            '| Method | Call | Returns | Undo | Confidence | What it does, and cautions |', '|---|---|---|---|---|---|']
    out += [row(n) for n in ms]
    out.append('')
out += [
    '## Provenance',
    '',
    'Method names, registration state and addresses come from the Lua registration tables of the GameCore DLL. Argument forms, return values and undo behaviour come from reading each wrapper\'s decompilation and the direct and second-level callees in the call graph; where the code was not visible the entry says "probably" and carries a lower confidence. '
    'Test these in a scratch game before using them in a release, and report what you observe.',
    '',
]
open(os.path.join(HERE, '..', 'topics', '40-worldbuilder.md'), 'w', encoding='utf-8').write('\n'.join(out))
print('wrote topics/40-worldbuilder.md', len(notes) - 1, 'methods')
