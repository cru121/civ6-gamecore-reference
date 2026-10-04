#!/usr/bin/env python3
"""Generate topics/80-todo.md: groups of engine classes that the DLL contains and this reference does not cover yet.

Counts and class lists come from data/function_index.json (symbol-build function names); the descriptions are hand-written from class names
and are therefore inferred. Run before build.py.
"""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
rows = json.load(open(os.path.join(DATA, 'function_index.json'), encoding='utf-8'))['rows']

cls = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    if '<' in r[0] or '`' in r[0]:
        continue
    p = r[0].split('::')
    if len(p) >= 4:
        cls[(p[0], p[1])][p[2]].append(r)

# (title, [(ns, sub)], what it is, covered today, why it is ripe)
GROUPS = [
    ('AI behavior tree nodes', [('AI', 'BehaviorTree')],
     'The building blocks of the computer players\' decision trees: one class per node type (`UseGreatPersonNode`, `SpyChooseMissionNode`, `BarbarianSpawnRateNode`, ...) plus the tree and factory plumbing.',
     'Only mentioned in passing. No per-node entries.',
     'Node names are the part of AI behaviour a modder can see; what each node reads, decides and calls is undocumented. Each class has a small, regular set of functions, so the method that worked for modifier effects (type name, subject, engine calls) should work here too. Whether the trees and their node parameters can be authored from game data is still to be confirmed.'),
    ('AI control contracts and operations', [('AI', 'Control'), ('AI', 'Operation')],
     'How AI subsystems hand work to each other: contracts such as `CivicResearchContract`, `DiplomaticActionContract`, `UnitRequestContract`, and the AI operation, operation team and operation definition classes.',
     'Not covered. (Player and unit operations are covered under Operations and commands; these AI-side classes are separate.)',
     'Small groups with descriptive names. They explain how the AI turns a goal into a request, which is useful to anyone changing AI behaviour.'),
    ('Gossip types', [('Game', 'Gossip')],
     'One class per gossip event (`Denounced`, `CityFounded`, `ReligionFounded`, `SpyCaptured`, ...) and the manager that collects them.',
     'The Lua object `GameGossipManager` is documented; the individual gossip types, their triggers and parameters are not.',
     'Each type has a name hash and a handler. Listing every type with the code that raises it would show exactly when gossip fires and what it carries.'),
    ('Historic moments', [('Game', 'History')],
     'The `...MomentDispatcher` classes that decide when a historic moment is awarded, and the moment manager.',
     'The Lua object `GameHistoryManager` is documented. The moment names and hashes are in `findings/tables/moments.tsv` but have no pages here.',
     'The trigger conditions are in the dispatcher code. A page per moment (trigger, parameters, engine calls) would answer the most common modder question about moments: why did it (not) fire.'),
    ('Notification types', [('Reporting', 'Notification')],
     'One class per notification type (`BoostTech`, `ChooseCivic`, `ChooseArtifactPlayer`, ...) and the notification manager and pools.',
     'A name and hash table exists in `findings/tables/notifications.tsv`. Not a section of this site.',
     'Which engine events raise which notification, and what each one carries, is readable from the classes.'),
    ('Diplomacy statements and actions', [('Diplomacy', 'Statement'), ('Diplomacy', 'Action')],
     'The diplomatic statements (`DeclareFriend`, `DeclareWar`, `Denounce`, `Embassy`, `Delegation`, ...) and the actions that apply their outcome (`SetAllied`, `SetDelegation`, `RenewAlliance`, ...).',
     'Barely covered. Some diplomacy Lua methods are documented; the statement and action classes are not.',
     'Shows what a statement does when accepted and which state changes follow. Matches the AI and Dev CE diplomacy functions already listed.'),
    ('Quests', [('Quests', 'Logic')],
     'The quest logic classes (`ClearBarbarianCamp`, `SendTradeRoute`, `TrainUnitType`, `RecruitGreatPersonClass`, `TriggerCivicBoost`, ...).',
     'One native function entry; nothing else.',
     'Nine classes; the conditions that complete a quest and what it rewards are all in code.'),
    ('Climate events', [('Game', 'Climate')],
     'The climate classes (`Drought`, `Storm`, `OneOff`, `ClimateData`).',
     'Mentioned only as parts of other pages.',
     'Small, and tied to the Gathering Storm disaster and climate systems, which have few written explanations.'),
    ('Modifier objects', [('GameEffects', 'Objects')],
     'The kinds of object a modifier can be attached to or can iterate (`Improvement`, `Alliance`, `ArtifactExtraction`, `Belief`, `PlotYields`, `CombatResults`, ...).',
     'The modifier effects, requirements and collections are covered; this object layer is not.',
     'It is the data model behind collections and requirements, and explains the arguments they receive.'),
]

out = ['---', 'title: Not yet covered', 'order: 80', '---', '# Not yet covered: ripe for analysis', '',
       'The game library contains more than this reference describes. These are the groups of engine classes we have seen in the function index, '
       'counted from the symbol build, that have little or no coverage here. They are leads, not results: **the descriptions below are guesses from class names** '
       'and nothing here has been read in detail.', '',
       'Most of them follow the same pattern as the [modifier effects](effects/index.md) did before they were covered: one class per named type, '
       'a small fixed set of functions each, and engine calls that can be followed. If you want to pick one up, see [how to read this reference](conventions.md), '
       'then open the group\'s functions on the [All functions](native/all.md) page; corrections and contributions are welcome.', '',
       '| Group | Classes in the DLL | What it is (inferred) | In this reference today |', '|---|---|---|---|']
details = []
for title, keys, what, covered, ripe in GROUPS:
    names = {}
    for k in keys:
        for c, fr in cls.get(k, {}).items():
            names['::'.join(k) + '::' + c] = fr
    n = len(names)
    out.append('| [%s](#%s) | %d | %s | %s |' % (title, title.lower().replace(' ', '-'), n, what, covered))
    lst = ', '.join('`%s` (%d)' % (nm.split('::', 2)[2], len(fr)) for nm, fr in sorted(names.items()))
    details.append(('### %s {#' + title.lower().replace(' ', '-') + '}\n\n%s\n\n**Why it looks ripe.** %s\n\n<details><summary>%d classes with their function counts (symbol build)</summary>\n\n%s\n\n</details>\n') %
                   (title, what, ripe, n, lst))
out += ['', '## Details', ''] + details
wb = sum(len(v) for k, v in cls.items() if k[0] == 'WorldBuilder' and k[1] in ('City', 'Map', 'Player', 'Unit', 'Command') for v in [v])
out += ['## Covered, but needs verification', '',
        'These have pages here, but the pages rest on inference. A contributor can add a verified result without starting from scratch.', '',
        '| Item | What is inferred | How to verify |', '|---|---|---|',
        '| World Builder command classes (%d classes) | The undo model on [World Builder from Lua](worldbuilder.md) is read from function names and the call graph; the `Apply`, `Redo` and `Undo` bodies were not read. | Read the functions of each command in the decompiler and replace the "probably" entries; test undo of one method of each kind in game. |' % wb,
        '| Modifier effect links | Which engine functions an effect calls comes from the static call graph of the symbol build ([effects](effects/index.md)). Calls through helpers or pointers are missing. | Hook one engine function and apply a modifier that uses it; compare with the page. |',
        '| Dev CE functions | The descriptions on the [Dev CE](devce/index.md) pages were written by an AI assistant from decompiled code and are not human-reviewed; most behaviour is untested in game. | Review a description against the code, or run the function in a scratch game and report what changed. |',
        '| World Builder method behaviour | Argument forms, return values and silent-failure paths are read from wrappers whose helper functions were not decompiled. | Call the method in a scratch game with each argument form and note the result. |', '']
open(os.path.join(HERE, '..', 'topics', '80-todo.md'), 'w', encoding='utf-8').write('\n'.join(out))
print('wrote topics/80-todo.md', len(GROUPS), 'groups')
