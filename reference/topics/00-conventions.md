---
title: How to read this reference
order: 0
---
# How to read this reference

**What it is.** A reference for the GameCore library of Sid Meier's Civilization VI: what the Lua API exposes, which operations and commands exist, what identifiers mean, and how the engine is laid out. Everything is generated from analysis data and small hand-written notes.

**Builds.** Every address is given for two builds: the *symbol build* (Steam depot 947510, where the function names come from) and the *current build* (Steam build 15038592). The Linux port (depot 533502) supplies layouts and parameter names. An address of `—` means the function could not be mapped to that build.

**Availability.** Every section is colour-coded by how you can use what it lists:
- **Green, available out of the box:** usable from Lua in the unmodified game (the Lua API, operations and commands you can request, Lua constant tables).
- **Amber, needs the Community Extension:** only works while that mod is active. This covers the functions it adds and raw memory access (class layouts and globals are used through its `ObjMem` and `Mem`).
- **Grey, engine internals:** exists in the game library but has no scripting access today. Native functions are listed so contributors can see what could be exposed next; engine ids explain numbers seen in code.

**Status of a statement.**
- **verified**: seen directly in code, data, game scripts or at run time.
- **inferred**: follows from verified facts but was not observed.
- **unknown**: listed so you know it exists.

**Evidence kinds.** `dll-registration`, `static-analysis`, `dwarf`, `game-script`, `runtime`, `community-reference`.

**Identifiers.** Every entry has a stable id such as `lua:Game.GetGreatWorkPlayer`, `op:player.MOVE_GREAT_WORK`, `enum:Events`. Links between entries use these ids.

**What is generated and what is written by hand.** Tables come from data files produced by scripts. Summaries, usage examples and caveats are hand-written notes attached to an id. Nothing written by hand is overwritten when the data is regenerated.
