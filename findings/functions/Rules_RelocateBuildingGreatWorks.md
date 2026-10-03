---
function: GameCore::Rules::Cities::Shared::Instance::RelocateBuildingGreatWorks
subsystem: City / great works
rva_symbol_build: 0x64d150
rva_installed_build: 0x64d980
address_mapping: unique (installed = Steam build 15038592; symbol build = older Steam depot 947510)
lua_exposure: "Not exposed. Called from Player::Cities::AddBuildingReplacementOverride / RemoveBuildingReplacementOverride."
analysis: decompiled and read (Ghidra 12.1.4), 2026-09-29
---

# Rules::Cities::Shared::Instance::RelocateBuildingGreatWorks

`void __thiscall RelocateBuildingGreatWorks(Instance* rules, City::Instance& city, const vector<GreatWorkListIndex>& works) const`

Re-homes a list of great works after a building replacement changes a city's slots.

## Verified from the decompilation
- For each work in the list: if the city's own Buildings can take it (`CanAddGreatWork`), it adds it there via `edit()` + `AddGreatWork`.
- Otherwise it walks the player's other cities and, for every other city where `CanAddGreatWork` is true, calls `AddGreatWork`.
- If no city can take it, nothing happens: no notification, no record, no fallback. The work simply ends up in no slot.
- The loop over other cities has no `break`/`return` after a successful add.

## Inferred (not confirmed in-game)
- A work that fits nowhere is silently dropped from all slots (it probably still exists in the game-wide great work list). (Medium.)
- Because the loop does not stop after the first successful add, the same work could be added to more than one other city if `CanAddGreatWork` only checks the target city and not other cities. **Possible duplication bug. (Low: depends on what `CanAddGreatWork` checks, not yet read.)**

## For modders
- One concrete way works "get lost": a building replacement with no spare slots elsewhere. The work is neither archived nor reported.
- Relevant to any 'great works archive' idea: this is a point where a work could be saved instead of dropped.

## Related
- [City::Buildings::AddGreatWork](Buildings_AddGreatWork.md)
- [City::Buildings::RemoveGreatWork](Buildings_RemoveGreatWork.md)

## Caveats
- Only the great-works handling was read; this is not a full analysis of building replacement.
