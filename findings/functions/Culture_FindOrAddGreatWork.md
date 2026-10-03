---
function: GameCore::Game::Culture::FindOrAddGreatWork
subsystem: Game / great works
rva_symbol_build: 0x1c8f00
rva_installed_build: 0x1c80e0
address_mapping: unique (installed = Steam build 15038592; symbol build = older Steam depot 947510)
lua_exposure: "No Lua method. Already wrapped by the Community Extension (FIND_OR_ADD_GREAT_WORK_OFFSET)."
analysis: decompiled and read (Ghidra 12.1.4), 2026-09-30; used in a live experiment
---

# Game::Culture::FindOrAddGreatWork

`int __thiscall FindOrAddGreatWork(Culture* this, GreatWorkTypes type)`

Returns the position (list index) of the game-wide record for a great work type, creating the record if none exists.

## Verified from the decompilation
- Scans the game-wide list (begin at Culture+0x118, end at +0x120, 0x18 bytes per record) for a record whose first field equals `type`; if found, returns its position.
- Otherwise appends a new record through the tracked accessor (`edit()` on the list at Culture+0x108) and returns the new position.
- **Record layout (0x18 bytes):** +0x00 great work type (u32); +0x04 player (s32, initialised to -1); +0x08 the game's current turn at creation (read from the game instance at +0xc0); +0x10 a text string, initialised empty.
- The type is an index into the great work definition collection (`Definitions::GetGreatWorkDefinitions`).

## Observed in-game (2026-09-29/30)
- Called through the Frida tool for works 0 and 1: created records at list indexes 0 and 1; a second call with an existing type returned the existing index and added nothing.
- A tooltip for a work created this way reads "Created in 950 BC" (the other, created a turn earlier, 1000 BC) and shows an **empty "Created by"**.

## Inferred (not confirmed in-game)
- The "Created in <year>" text comes from the record's creation-turn field (fits the observation: two works created one turn apart differ by 50 years). (Medium.)
- The "Created by" text comes from the string at +0x10, which normal creation code (great people, relics, artifacts) probably fills in; works spawned only with this function have it empty. (Medium.)
- The player field (+0x04) starts at -1 and is set by `SetGreatWorkPlayer`; see that note. (Medium.)

## For modders
- An archive that only remembers a work's type would lose its creation turn, creator text and player. To restore a work faithfully, keep the whole record, or leave the record in the game-wide list and only move the slot (what the experiments did).
- Creating a work with this function alone is enough to make it exist in limbo, but it will lack the creator text.

## Related
- [Game::Culture::SetGreatWorkPlayer](Culture_SetGreatWorkPlayer.md)
- [Do great works in limbo grant anything?](../topics/great-works-limbo.md)
