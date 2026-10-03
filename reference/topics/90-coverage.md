---
title: Coverage and confidence
order: 90
---
# Coverage and confidence

Generated from the data files at build time. "Verified" means seen directly in code, data, game scripts or at run time; "inferred" means deduced from verified facts. Counts are for the symbol build mapped to the current build.

## Available out of the box

| Part | Total | How complete | How sure |
|---|---|---|---|
| Lua methods | 1920 | all registered methods; 1480 (77%) also appear in the community reference, 440 (23%) do not | registration is read from the DLL tables (verified) |
| Signatures | 1920 | 988 (51%) have at least one parameter; 966 (57%) of 1709 parameters have a real name; 512 (30%) have a C++ type | 1773 (92%) high confidence, 147 (8%) partial (marked ⚠) |
| Return values | 1527 return something | 1432 (94%) have a detailed description (tables, arrays, types); 141 (9%) have a stated meaning | meanings: 66 verified, 75 inferred |
| Argument meanings | 1709 parameters | 798 (47%) have a stated meaning | 603 verified, 195 inferred |
| Operations and commands | 154 | all identified with hash, handler, addresses | 137 verified, 16 inferred (16 handlers matched by class name), 1 unknown |
| Operation parameters | 76 slots, 167 parameter entities | 0 (0%) slots have an example from the game's scripts | entities: 73 verified, 94 inferred |
| Lua constant tables | 25 tables, 546 members | the 6 operation and command tables are complete; 19 more tables are matched to engine enums through the Companion (only the members it lists are known to be exposed) | operation tables verified from the debug info; the 19 others inferred |

## Needs the Community Extension

| Part | Total | How complete | How sure |
|---|---|---|---|
| Community Extension functions | 33 | all in its wiki; 17 (52%) linked to the engine function | wiki + source (verified) |
| Class layouts | 1915 classes, 12022 members | all non-template GameCore classes in the Linux build | Linux offsets verified from debug info; **25 members** checked against Windows code |
| Globals | 1314 | named globals present in both builds | 801 verified (mapping rests on 2+ references), 513 inferred |

## Engine internals

| Part | Total | How complete | How sure |
|---|---|---|---|
| Function inventory | 43803 functions | 33271 (76%) mapped to the current build; 21782 (50%) have a Linux signature | mapping method is described in the analysis notes (not yet part of this site) |
| Native function entries | 367 | 17 analysed in detail (106 notes), 17 wrapped by the Community Extension | analysed notes labelled verified / inferred |
| Hand-written notes (all entity types) | 39 | a small curated set | 22 verified, 17 inferred |

## Known gaps
- Return and argument meanings exist where the game's own scripts reveal them; the remaining methods are listed with types only.
- Signature columns marked ⚠ (147 methods) have arguments or returns we could not fully classify.
- Only 25 layout members have a checked Windows offset; for the rest use the Linux offset with the stated rule.
- The Events enum lists engine ids (not scriptable). 152 of the 352 are also Lua events with parameter names from the Civ VI Modding Companion (ChimpanG, WildW); see the Lua events page. These are community-sourced and not checked against the DLL.

## Checked against a running game

| Part | Total | Result |
|---|---|---|
| Lua methods seen on live objects (UI state) | 825 | 453 called once: 439 returned the documented number of values, 8 returned nothing, 6 raised errors (each noted on the method page) |

See the topic *Checking the reference against a running game*. Not covered: methods with arguments, mutators, the gameplay Lua state, multiplayer.
