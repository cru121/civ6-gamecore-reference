---
function: GameCore::Player::Culture::ReceiveGreatWork
subsystem: Player / great works
rva_symbol_build: 0x283ac0
rva_installed_build: 0x282c20
address_mapping: unique (installed = Steam build 15038592; symbol build = older Steam depot 947510)
lua_exposure: "None."
analysis: decompiled and read (Ghidra 12.1.4), 2026-09-29
---

# Player::Culture::ReceiveGreatWork

`bool __thiscall ReceiveGreatWork(Culture* this, GreatWorkListIndex index)`

Gives a great work to a player by placing it in the first of their cities that can hold it. Returns false if no city has room.

## Verified from the decompilation
- Iterates the player's cities (list from player+0x6d0 -> +0xd0, next node at +0x10). For each: gets the city's Buildings via edit(city+0xca0), calls CanAddGreatWork, and stops at the first city that says yes.
- Then calls Buildings::AddGreatWork on that city and returns true.

## Observed in-game (2026-09-29 to 2026-10-03, single player, Frida live channel)
- Creating a work (FindOrAddGreatWork + SetGreatWorkPlayer) and calling ReceiveGreatWork for the player placed it in the free Palace slot ("PLACED in a slot"); the capital then showed culture +2 and tourism +2 for a Writing work. Repeated on 2026-10-03 with the live channel.

## Inferred (not confirmed in-game)
- none

## For modders
- The placement half of a trade. A false return leaves the work unplaced; the deal code stores it and retries in PostEnact.

## Related
- [City::Buildings::RemoveGreatWork](Buildings_RemoveGreatWork.md)
- [Diplomacy::Deal::Item::GreatWork::PostEnact](DealItemGreatWork_PostEnact.md)
